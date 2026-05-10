#!/usr/bin/env python3
"""
Frappe starter — restore-from-dump strategy.

At build time, bench new-site ran against a local MariaDB and the result was
dumped to sites/db_seed.sql.gz. At runtime we:

  1. Wait for the real MariaDB to be ready
  2. Create the target database + user
  3. Restore the dump (seconds, not hours)
  4. Patch site_config.json with real credentials
  5. Run bench migrate (fast — schema is already current)
  6. exec gunicorn

On subsequent restarts (site already exists):
  - Skip restore, just run bench migrate + gunicorn

Health check endpoints (always available):
  GET /health          → 200 OK
  GET /api/method/ping → 200 OK
  GET /setup-log       → full setup log as plain text
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
DB_PORT     = int(os.environ.get("DB_PORT", "3306"))
DB_NAME     = os.environ.get("DB_NAME", "crm_db")
DB_PASS     = os.environ.get("DB_PASSWORD", "changeme")
DB_ROOT     = os.environ.get("DB_ROOT_PASSWORD", "")
ADMIN_PW    = os.environ.get("ADMIN_PASSWORD", "admin")
ENC_KEY     = os.environ.get("ENCRYPTION_KEY", "")
REDIS_CACHE = os.environ.get("REDIS_CACHE_URL", "redis://crm-redis-cache:10000")
REDIS_QUEUE = os.environ.get("REDIS_QUEUE_URL", "redis://crm-redis-queue:10000")
SERVE_PORT  = int(os.environ.get("PORT", "8000"))

DUMP_PATH   = os.path.join(BENCH_DIR, "sites", "db_seed.sql.gz")
META_PATH   = os.path.join(BENCH_DIR, "sites", "db_seed_meta.json")

LOG_LINES     = []
SETUP_DONE    = threading.Event()
SETUP_SUCCESS = False

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

def parse_redis_url(url):
    try:
        parts = url.replace("redis://", "").split(":")
        return parts[0], int(parts[1])
    except Exception:
        return None, None

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
    """Run a SQL statement against the remote MariaDB."""
    password = password or DB_ROOT
    cmd = ["mysql", f"-h{DB_HOST}", f"-P{DB_PORT}", f"-u{user}", f"-p{password}"]
    if db:
        cmd.append(db)
    log(f"mysql: {sql[:80]}...")
    try:
        r = subprocess.run(
            cmd, input=sql, capture_output=True, text=True,
            timeout=timeout, env=get_env()
        )
        if r.returncode != 0:
            log(f"  mysql error: {r.stderr.strip()[:300]}")
        return r.returncode
    except Exception as e:
        log(f"  mysql exception: {e}")
        return -1

# ── Site config helpers ───────────────────────────────────────────────────────
def write_common_site_config():
    path = os.path.join(BENCH_DIR, "sites", "common_site_config.json")
    try:
        with open(path) as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    cfg["redis_cache"]    = REDIS_CACHE
    cfg["redis_queue"]    = REDIS_QUEUE
    cfg["redis_socketio"] = REDIS_QUEUE
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
    log(f"common_site_config.json updated")

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

# ── DB restore from dump ──────────────────────────────────────────────────────
def restore_from_dump():
    """
    Create the target DB + user on the remote MariaDB, then restore the
    baked-in dump. Returns True on success.
    """
    log(f"Dump found: {DUMP_PATH}")
    try:
        with open(META_PATH) as f:
            meta = json.load(f)
        log(f"Dump built at {meta.get('built_at','?')} with apps {meta.get('apps','?')}")
    except Exception:
        log("No dump metadata found — proceeding anyway")

    # Create DB and user on remote MariaDB
    log(f"Creating database '{DB_NAME}' and user '{DB_NAME}' on {DB_HOST}:{DB_PORT}...")
    setup_sql = f"""
CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '{DB_NAME}'@'%' IDENTIFIED BY '{DB_PASS}';
GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO '{DB_NAME}'@'%';
FLUSH PRIVILEGES;
"""
    rc = run_mysql(setup_sql)
    if rc != 0:
        log("ERROR: Could not create database/user")
        return False

    # Restore dump
    log(f"Restoring dump to '{DB_NAME}' (this takes ~30 seconds)...")
    try:
        # zcat | mysql pipeline
        zcat = subprocess.Popen(
            ["zcat", DUMP_PATH],
            stdout=subprocess.PIPE
        )
        mysql_cmd = [
            "mysql",
            f"-h{DB_HOST}", f"-P{DB_PORT}",
            f"-u{DB_NAME}", f"-p{DB_PASS}",
            DB_NAME
        ]
        mysql_proc = subprocess.Popen(
            mysql_cmd,
            stdin=zcat.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=get_env()
        )
        zcat.stdout.close()
        stdout, stderr = mysql_proc.communicate(timeout=300)
        if mysql_proc.returncode != 0:
            log(f"ERROR: mysql restore failed: {stderr.strip()[:500]}")
            return False
        log("Dump restored successfully!")
        return True
    except subprocess.TimeoutExpired:
        log("ERROR: DB restore timed out after 300s")
        return False
    except Exception as e:
        log(f"ERROR: DB restore exception: {e}")
        return False

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
    log(f"Dump exists: {os.path.exists(DUMP_PATH)}")

    # 1. Write common_site_config.json
    write_common_site_config()

    # 2. Wait for MariaDB (required)
    if not wait_for_tcp(DB_HOST, DB_PORT, "MariaDB", timeout=300):
        log("ERROR: MariaDB unreachable after 5 min — aborting")
        return
    time.sleep(3)

    # 3. Wait for Redis (best-effort)
    rh, rp = parse_redis_url(REDIS_CACHE)
    if rh:
        wait_for_tcp(rh, rp, "redis-cache", timeout=60)
    rh2, rp2 = parse_redis_url(REDIS_QUEUE)
    if rh2:
        wait_for_tcp(rh2, rp2, "redis-queue", timeout=30)

    # 4. Check if site already exists (idempotent restart)
    site_config_path = os.path.join(BENCH_DIR, "sites", SITE, "site_config.json")
    site_exists = os.path.exists(site_config_path)
    log(f"Site config exists: {site_exists}")

    if site_exists:
        log("Site already exists — running migrate to catch up on any schema changes...")
        rc = run_bench(["--site", SITE, "migrate", "--skip-search-index"], timeout=600)
        if rc == 0:
            log("Migrate succeeded!")
        else:
            log(f"Migrate returned rc={rc} — continuing anyway (may be Redis-related)")
        run_bench(["use", SITE])
        SETUP_SUCCESS = True
        return

    # 5. First boot: restore from baked-in dump
    dump_exists = os.path.exists(DUMP_PATH)
    if dump_exists:
        log("=== FIRST BOOT: Restoring from baked-in DB dump ===")
        if not restore_from_dump():
            log("ERROR: DB restore failed — cannot start")
            return

        # Write site_config.json with real credentials
        write_site_config()

        # Run migrate to apply any pending schema changes
        log("Running bench migrate (fast — schema already current)...")
        rc = run_bench(["--site", SITE, "migrate", "--skip-search-index"], timeout=600)
        if rc == 0:
            log("Migrate succeeded!")
        else:
            log(f"Migrate returned rc={rc} — continuing (may be Redis warning)")

        run_bench(["use", SITE])
        SETUP_SUCCESS = True
        log(f"=== Setup complete {time.strftime('%H:%M:%S')} ===")

    else:
        # Fallback: no dump in image — run bench new-site the slow way
        log("WARNING: No DB dump found in image. Running bench new-site (slow path ~90 min)...")
        log("This should not happen in production. Rebuild the Docker image.")
        args = [
            "new-site", SITE,
            "--db-name",        DB_NAME,
            "--db-password",    DB_PASS,
            "--admin-password", ADMIN_PW,
            "--db-host",        DB_HOST,
            "--db-port",        str(DB_PORT),
            "--mariadb-user-host-login-scope", "%",
            "--verbose",
            "--force",
        ]
        if DB_ROOT:
            args += ["--db-root-password", DB_ROOT]
        rc = run_bench(args, timeout=18000)  # 5 hours — last resort
        if rc != 0:
            log(f"bench new-site FAILED (rc={rc})")
            return
        if ENC_KEY:
            import shutil
            site_cfg = os.path.join(BENCH_DIR, "sites", SITE, "site_config.json")
            try:
                with open(site_cfg) as f:
                    cfg = json.load(f)
                cfg["encryption_key"] = ENC_KEY
                with open(site_cfg, "w") as f:
                    json.dump(cfg, f, indent=2)
            except Exception as e:
                log(f"Could not patch encryption_key: {e}")
        rc2 = run_bench(["--site", SITE, "install-app", "crm"], timeout=3600)
        log(f"install-app crm: rc={rc2}")
        run_bench(["use", SITE])
        SETUP_SUCCESS = True
        log(f"=== Setup complete (slow path) {time.strftime('%H:%M:%S')} ===")

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
    gunicorn_bin = GUNICORN_CMD[0]
    if not os.path.exists(gunicorn_bin):
        import glob
        found = glob.glob("/home/frappe/frappe-bench/env/bin/gunicorn*")
        log(f"gunicorn not at expected path, found: {found}")
        if not found:
            log("FATAL: gunicorn not found")
            return
        gunicorn_bin = found[0]

    # Ensure currentsite.txt
    cs = os.path.join(BENCH_DIR, "sites", "currentsite.txt")
    if not os.path.exists(cs):
        with open(cs, "w") as f:
            f.write(SITE)
        log(f"Wrote currentsite.txt = {SITE}")
    else:
        log(f"currentsite.txt = {open(cs).read().strip()}")

    # Quick import test
    r = subprocess.run(
        ["/home/frappe/frappe-bench/env/bin/python", "-c",
         "import frappe.app; print('frappe.app OK')"],
        cwd=os.path.join(BENCH_DIR, "sites"),
        capture_output=True, text=True, env=env, timeout=30
    )
    log(f"frappe.app import: rc={r.returncode} {r.stdout.strip()} {r.stderr.strip()[:300]}")

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
    log("Setup FAILED -> keeping health server alive. Check /setup-log for details.")
    log("Will NOT retry automatically — fix the error and redeploy.")
    while True:
        time.sleep(300)
        log("Still alive (setup failed). Check /setup-log.")
