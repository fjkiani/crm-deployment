#!/usr/bin/env python3
"""
Frappe starter — idempotent, fast startup.

Key insight: bench migrate checks redis_cache connectivity before running.
We start a local Redis inside the container just for the migrate step,
then switch common_site_config.json to the real Redis before gunicorn.

Boot logic:
  FIRST BOOT  (site_config.json absent on persistent disk):
    1. Start local Redis on 127.0.0.1:6380
    2. Write common_site_config.json pointing at local Redis
    3. Wait for MariaDB
    4. Create DB + user, import framework_mariadb.sql (seconds)
    5. Write site_config.json
    6. bench migrate --skip-search-index  (~5-15 min, uses local Redis)
    7. bench install-app crm
    8. Set admin password
    9. Switch common_site_config.json to real Redis
    10. exec gunicorn

  SUBSEQUENT BOOTS (site_config.json present on persistent disk):
    1. Start local Redis on 127.0.0.1:6380
    2. Write common_site_config.json pointing at local Redis
    3. Wait for MariaDB
    4. bench migrate --skip-search-index  (~30s)
    5. Switch common_site_config.json to real Redis
    6. exec gunicorn

Health endpoints (always available):
  GET /health          → 200 OK
  GET /api/method/ping → 200 OK
  GET /setup-log       → full log as plain text
"""
import os
import sys
import json
import time
import threading
import subprocess
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Configuration ─────────────────────────────────────────────────────────────
BENCH_DIR   = "/home/frappe/frappe-bench"
SITE        = os.environ.get("FRAPPE_SITE_NAME", "crm.localhost")
DB_HOST     = os.environ.get("DB_HOST", "mariadb")
DB_PORT     = int(os.environ.get("DB_PORT", "10000"))
DB_NAME     = os.environ.get("DB_NAME", "crm_db")
DB_PASS     = os.environ.get("DB_PASSWORD", "changeme")
DB_ROOT     = os.environ.get("DB_ROOT_PASSWORD", "")
ADMIN_PW    = os.environ.get("ADMIN_PASSWORD", "admin")
ENC_KEY     = os.environ.get("ENCRYPTION_KEY", "")
REDIS_CACHE = os.environ.get("REDIS_CACHE_URL", "redis://crm-redis-cache:10000")
REDIS_QUEUE = os.environ.get("REDIS_QUEUE_URL", "redis://crm-redis-queue:10000")
SERVE_PORT  = int(os.environ.get("PORT", "8000"))

# Local Redis for migrate (avoids dependency on external Redis during setup)
LOCAL_REDIS_PORT = 6380
LOCAL_REDIS_URL  = f"redis://127.0.0.1:{LOCAL_REDIS_PORT}"

FRAMEWORK_SQL = os.path.join(
    BENCH_DIR, "apps", "frappe", "frappe", "database", "mariadb", "framework_mariadb.sql"
)

LOG_LINES     = []
SETUP_DONE    = threading.Event()
SETUP_SUCCESS = False
_local_redis_proc = None

# ── Logging ───────────────────────────────────────────────────────────────────
def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG_LINES.append(line)
    try:
        with open("/tmp/frappe_setup.log", "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ── Health server ─────────────────────────────────────────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/setup-log":
            body = "\n".join(LOG_LINES).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path in ("/health", "/api/method/ping"):
            body = b"OK"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(body)
        else:
            if SETUP_DONE.is_set() and not SETUP_SUCCESS:
                body = b"Setup FAILED - see /setup-log\n"
                self.send_response(503)
            else:
                body = b"Frappe CRM - initializing...\n"
                self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    def log_message(self, *a):
        pass

# ── TCP helpers ───────────────────────────────────────────────────────────────
def wait_for_tcp(host, port, label=None, timeout=300):
    label = label or f"{host}:{port}"
    log(f"Waiting for {label} ({host}:{port})...")
    start = time.time()
    attempt = 0
    while time.time() - start < timeout:
        try:
            s = socket.create_connection((host, port), timeout=5)
            s.close()
            log(f"{label} ready after {int(time.time()-start)}s")
            return True
        except Exception as e:
            if attempt % 10 == 0:
                log(f"  {label} not ready (attempt {attempt+1}): {e}")
            attempt += 1
            time.sleep(3)
    log(f"ERROR: {label} timeout after {timeout}s")
    return False

# ── Local Redis ───────────────────────────────────────────────────────────────
def start_local_redis():
    """Start a local Redis server for use during migrate."""
    global _local_redis_proc
    log(f"Starting local Redis on port {LOCAL_REDIS_PORT}...")

    # Find redis-server binary
    redis_bin = None
    for path in ["/usr/bin/redis-server", "/usr/local/bin/redis-server"]:
        if os.path.exists(path):
            redis_bin = path
            break

    if not redis_bin:
        # Try to install it
        log("redis-server not found, installing...")
        r = subprocess.run(
            ["apt-get", "install", "-y", "--no-install-recommends", "redis-server"],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            redis_bin = "/usr/bin/redis-server"
        else:
            log(f"Could not install redis-server: {r.stderr[:200]}")
            return False

    try:
        _local_redis_proc = subprocess.Popen(
            [redis_bin, "--port", str(LOCAL_REDIS_PORT),
             "--bind", "127.0.0.1",
             "--save", "",          # disable persistence
             "--loglevel", "warning"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Wait for it to be ready
        for _ in range(20):
            try:
                s = socket.create_connection(("127.0.0.1", LOCAL_REDIS_PORT), timeout=1)
                s.close()
                log(f"Local Redis ready on port {LOCAL_REDIS_PORT}")
                return True
            except Exception:
                time.sleep(0.5)
        log("ERROR: Local Redis did not start in time")
        return False
    except Exception as e:
        log(f"ERROR starting local Redis: {e}")
        return False

def stop_local_redis():
    global _local_redis_proc
    if _local_redis_proc:
        try:
            _local_redis_proc.terminate()
            _local_redis_proc.wait(timeout=5)
            log("Local Redis stopped")
        except Exception:
            pass
        _local_redis_proc = None

# ── bench runner ──────────────────────────────────────────────────────────────
def get_env():
    return {
        **os.environ,
        "PATH": "/usr/local/bin:/home/frappe/.local/bin:/home/frappe/frappe-bench/env/bin:" + os.environ.get("PATH", ""),
    }

def run_bench(args, timeout=600):
    cmd = ["/usr/local/bin/bench"] + [str(a) for a in args]
    log(f"$ {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(
            cmd, cwd=BENCH_DIR, env=get_env(),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        deadline = time.time() + timeout
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log(f"  > {line}")
            if time.time() > deadline:
                proc.kill()
                log(f"ERROR: timed out after {timeout}s")
                return -1
        proc.wait()
        log(f"  exit: {proc.returncode}")
        return proc.returncode
    except Exception as e:
        log(f"ERROR running bench: {e}")
        return -1

def run_mysql(sql, user="root", password=None, db=None, timeout=60):
    password = password or DB_ROOT
    cmd = ["mysql", f"-h{DB_HOST}", f"-P{DB_PORT}", f"-u{user}", f"-p{password}",
           "--connect-timeout=10"]
    if db:
        cmd.append(db)
    try:
        r = subprocess.run(cmd, input=sql, capture_output=True, text=True,
                           timeout=timeout, env=get_env())
        if r.returncode != 0:
            log(f"  mysql error: {r.stderr.strip()[:400]}")
        return r.returncode
    except Exception as e:
        log(f"  mysql exception: {e}")
        return -1

def import_sql_file(sql_path, db_name, timeout=120):
    log(f"Importing {os.path.basename(sql_path)} into {db_name}...")
    cmd = ["mysql", f"-h{DB_HOST}", f"-P{DB_PORT}",
           f"-u{DB_NAME}", f"-p{DB_PASS}",
           "--connect-timeout=10", db_name]
    try:
        with open(sql_path, "rb") as f:
            r = subprocess.run(cmd, stdin=f, capture_output=True, text=True,
                               timeout=timeout, env=get_env())
        if r.returncode != 0:
            log(f"  import error: {r.stderr.strip()[:400]}")
        else:
            log(f"  import OK")
        return r.returncode
    except Exception as e:
        log(f"  import exception: {e}")
        return -1

# ── Site config helpers ───────────────────────────────────────────────────────
def write_common_site_config(redis_cache_url, redis_queue_url):
    path = os.path.join(BENCH_DIR, "sites", "common_site_config.json")
    try:
        with open(path) as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    cfg["redis_cache"]    = redis_cache_url
    cfg["redis_queue"]    = redis_queue_url
    cfg["redis_socketio"] = redis_queue_url
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
    log(f"common_site_config.json: redis_cache={redis_cache_url}")

def write_site_config():
    site_dir = os.path.join(BENCH_DIR, "sites", SITE)
    os.makedirs(os.path.join(site_dir, "logs"), exist_ok=True)
    cfg = {
        "db_name":     DB_NAME,
        "db_password": DB_PASS,
        "db_host":     DB_HOST,
        "db_port":     DB_PORT,
    }
    if ENC_KEY:
        cfg["encryption_key"] = ENC_KEY
    path = os.path.join(site_dir, "site_config.json")
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
    log(f"site_config.json written for {SITE}")

# ── Setup logic ───────────────────────────────────────────────────────────────
def setup_site():
    global SETUP_SUCCESS
    try:
        _setup_site_inner()
    except Exception as e:
        import traceback
        log(f"FATAL: {e}")
        log(traceback.format_exc())
    finally:
        SETUP_DONE.set()

def _setup_site_inner():
    global SETUP_SUCCESS

    log(f"=== Setup start {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    log(f"SITE={SITE}  DB={DB_HOST}:{DB_PORT}/{DB_NAME}  PORT={SERVE_PORT}")
    log(f"DB_ROOT={'set' if DB_ROOT else 'MISSING'}  ADMIN_PW={'set' if ADMIN_PW else 'MISSING'}")
    log(f"REDIS_CACHE={REDIS_CACHE}  REDIS_QUEUE={REDIS_QUEUE}")

    # 1. Start local Redis (used for migrate — avoids external Redis dependency)
    if not start_local_redis():
        log("WARNING: Local Redis failed to start — migrate may fail")

    # 2. Point common_site_config at local Redis for migrate
    write_common_site_config(LOCAL_REDIS_URL, LOCAL_REDIS_URL)

    # 3. Wait for MariaDB
    if not wait_for_tcp(DB_HOST, DB_PORT, "MariaDB", timeout=300):
        log("ERROR: MariaDB unreachable after 5 min — aborting")
        return
    time.sleep(3)

    # 4. Check if site already exists on the persistent disk
    site_config_path = os.path.join(BENCH_DIR, "sites", SITE, "site_config.json")
    site_exists = os.path.exists(site_config_path)
    log(f"Site config exists on disk: {site_exists}")

    if site_exists:
        # ── FAST PATH: subsequent boots ──────────────────────────────────────
        log("Site exists — running migrate (fast schema diff, ~30s)...")
        rc = run_bench(["--site", SITE, "migrate", "--skip-search-index"], timeout=600)
        if rc == 0:
            log("Migrate succeeded!")
        else:
            log(f"Migrate returned rc={rc} — continuing anyway")
        run_bench(["use", SITE])
        SETUP_SUCCESS = True
        log(f"=== Ready {time.strftime('%H:%M:%S')} ===")
        return

    # ── SLOW PATH: first boot only ────────────────────────────────────────────
    log("=== FIRST BOOT: setting up site (runs once, result persists on disk) ===")

    # 5. Create DB and user on remote MariaDB
    log(f"Creating database '{DB_NAME}' and user...")
    setup_sql = f"""
CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '{DB_NAME}'@'%' IDENTIFIED BY '{DB_PASS}';
GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO '{DB_NAME}'@'%';
FLUSH PRIVILEGES;
"""
    rc = run_mysql(setup_sql)
    if rc != 0:
        log("ERROR: Could not create database/user — check DB_ROOT_PASSWORD")
        return

    # 6. Import the base Frappe schema (milliseconds — SQL file already in image)
    if os.path.exists(FRAMEWORK_SQL):
        log(f"Importing base Frappe schema (fast SQL import)...")
        rc = import_sql_file(FRAMEWORK_SQL, DB_NAME)
        if rc != 0:
            log("ERROR: Failed to import framework SQL")
            return
        log("Base schema imported!")
    else:
        log(f"WARNING: {FRAMEWORK_SQL} not found — migrate will create tables from scratch")

    # 7. Write site_config.json so bench knows about this site
    write_site_config()

    # 8. Register site
    run_bench(["use", SITE])

    # 9. bench migrate — applies all DocType schemas
    #    Uses local Redis (started in step 1) so no external Redis dependency.
    #    Much faster than bench new-site because base schema is already imported.
    #    Expected time: 5-15 minutes.
    log("Running bench migrate (5-15 min on first boot)...")
    rc = run_bench(["--site", SITE, "migrate", "--skip-search-index"], timeout=1800)
    if rc != 0:
        log(f"bench migrate failed (rc={rc})")
        return

    log("Migrate succeeded!")

    # 10. Install CRM app
    log("Installing CRM app...")
    rc2 = run_bench(["--site", SITE, "install-app", "crm"], timeout=600)
    if rc2 == 0:
        log("CRM installed!")
    else:
        log(f"CRM install returned rc={rc2} — may already be installed, continuing")

    # 11. Set admin password
    log("Setting admin password...")
    run_bench(["--site", SITE, "set-admin-password", ADMIN_PW], timeout=60)

    run_bench(["use", SITE])
    SETUP_SUCCESS = True
    log(f"=== First boot complete {time.strftime('%H:%M:%S')} ===")
    log("Subsequent boots will skip setup and go straight to gunicorn.")

# ── Gunicorn ──────────────────────────────────────────────────────────────────
GUNICORN_CMD = [
    "/home/frappe/frappe-bench/env/bin/gunicorn",
    "--chdir=/home/frappe/frappe-bench/sites",
    f"--bind=0.0.0.0:{SERVE_PORT}",
    "--threads=4",
    "--workers=2",
    "--worker-class=gthread",
    "--worker-tmp-dir=/dev/shm",
    "--timeout=120",
    "--preload",
    "--log-level=info",
    "frappe.app:application",
]

def exec_gunicorn():
    env = get_env()

    # Switch common_site_config to real Redis before gunicorn starts
    log("Switching to real Redis for gunicorn...")
    write_common_site_config(REDIS_CACHE, REDIS_QUEUE)

    # Stop local Redis (gunicorn will use real Redis)
    stop_local_redis()

    gunicorn_bin = GUNICORN_CMD[0]
    if not os.path.exists(gunicorn_bin):
        import glob
        found = glob.glob("/home/frappe/frappe-bench/env/bin/gunicorn*")
        log(f"gunicorn not at expected path, found: {found}")
        if not found:
            log("FATAL: gunicorn not found")
            return
        gunicorn_bin = found[0]

    cs = os.path.join(BENCH_DIR, "sites", "currentsite.txt")
    if not os.path.exists(cs):
        with open(cs, "w") as f:
            f.write(SITE)
        log(f"Wrote currentsite.txt = {SITE}")
    else:
        log(f"currentsite.txt = {open(cs).read().strip()}")

    r = subprocess.run(
        ["/home/frappe/frappe-bench/env/bin/python", "-c",
         "import frappe.app; print('frappe.app OK')"],
        cwd=os.path.join(BENCH_DIR, "sites"),
        capture_output=True, text=True, env=env, timeout=30
    )
    log(f"frappe.app import: rc={r.returncode} {r.stdout.strip()} {r.stderr.strip()[:200]}")

    log(f"exec gunicorn on port {SERVE_PORT}")
    os.execve(gunicorn_bin, GUNICORN_CMD, env)

# ── Main ──────────────────────────────────────────────────────────────────────
log(f"Starting health server on port {SERVE_PORT}...")
server = HTTPServer(("0.0.0.0", SERVE_PORT), HealthHandler)
server.allow_reuse_address = True
threading.Thread(target=server.serve_forever, daemon=True).start()
log(f"Health server up -> https://crm-frappe-web.onrender.com/setup-log")

threading.Thread(target=setup_site, daemon=True).start()
log("Waiting for setup...")
SETUP_DONE.wait()

if SETUP_SUCCESS:
    log("Setup succeeded -> starting gunicorn")
    server.shutdown()
    exec_gunicorn()
else:
    log("Setup FAILED -> keeping health server alive. Check /setup-log.")
    log("Fix the error and trigger a manual redeploy in Render dashboard.")
    while True:
        time.sleep(300)
        log("Still alive (setup failed). Check /setup-log.")
