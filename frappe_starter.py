#!/usr/bin/env python3
"""
Frappe starter - serves health check while site setup runs.
After SUCCESSFUL setup, switches to gunicorn.
If setup FAILS, keeps health server running so logs are visible.
"""
import os
import sys
import json
import time
import threading
import subprocess
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configuration
BENCH_DIR = "/home/frappe/frappe-bench"
SITE = os.environ.get("FRAPPE_SITE_NAME", "crm.localhost")
DB_HOST = os.environ.get("DB_HOST", "mariadb")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_NAME = os.environ.get("DB_NAME", "crm_db")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "changeme")
DB_ROOT_PASSWORD = os.environ.get("DB_ROOT_PASSWORD", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
REDIS_CACHE = os.environ.get("REDIS_CACHE_URL", "redis://redis-cache:13000")
REDIS_QUEUE = os.environ.get("REDIS_QUEUE_URL", "redis://redis-queue:11000")
SERVE_PORT = int(os.environ.get("PORT", "8000"))
LOG_FILE = "/tmp/frappe_setup.log"

LOG_LINES = []
SETUP_DONE = threading.Event()
SETUP_SUCCESS = False

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG_LINES.append(line)
    # Also write to file for persistence
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/setup-log":
            body = "\n".join(LOG_LINES).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/health":
            body = b"OK"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            if SETUP_DONE.is_set() and not SETUP_SUCCESS:
                body = b"Setup FAILED - check /setup-log for details\n"
                self.send_response(503)
            else:
                body = b"Frappe CRM - initializing...\n"
                self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
    def log_message(self, *a): pass

def run_bench(args, capture=True):
    cmd = ["/usr/local/bin/bench"] + args
    log(f"Running: {' '.join(str(a) for a in cmd)}")
    env = {**os.environ, "PATH": "/usr/local/bin:/home/frappe/.local/bin:/home/frappe/frappe-bench/env/bin:" + os.environ.get("PATH", "")}
    result = subprocess.run(cmd, cwd=BENCH_DIR, env=env, capture_output=capture, text=capture)
    if capture:
        if result.stdout:
            for line in result.stdout.strip().split('\n')[-20:]:  # last 20 lines
                log(f"  stdout: {line}")
        if result.stderr:
            for line in result.stderr.strip().split('\n')[-20:]:
                log(f"  stderr: {line}")
    log(f"Exit code: {result.returncode}")
    return result.returncode

def wait_for_tcp(host, port, timeout=600):
    """Wait for TCP port to be open using raw socket (no pymysql needed)."""
    log(f"Waiting for TCP {host}:{port}...")
    start = time.time()
    attempt = 0
    while time.time() - start < timeout:
        try:
            s = socket.create_connection((host, port), timeout=5)
            s.close()
            log(f"TCP {host}:{port} is open (attempt {attempt+1}, {int(time.time()-start)}s)")
            return True
        except Exception as e:
            if attempt % 10 == 0:
                log(f"TCP {host}:{port} not ready (attempt {attempt+1}): {e}")
            attempt += 1
            time.sleep(3)
    log(f"ERROR: TCP {host}:{port} timeout after {timeout}s")
    return False

def test_root_access():
    """Test root MySQL access using pymysql."""
    try:
        import pymysql
        log(f"Testing root access: host={DB_HOST} port={DB_PORT} user=root")
        conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user="root", password=DB_ROOT_PASSWORD, connect_timeout=10)
        conn.close()
        log("Root MySQL access OK!")
        return True
    except ImportError:
        log("pymysql not available - will rely on bench new-site for root access")
        return True  # Assume root access works, bench new-site will tell us
    except Exception as e:
        log(f"Root MySQL access FAILED: {e}")
        return False

def setup_site():
    global SETUP_SUCCESS
    try:
        _setup_site_inner()
    except Exception as e:
        log(f"FATAL ERROR in setup_site: {e}")
        import traceback
        log(traceback.format_exc())
    finally:
        SETUP_DONE.set()

def _setup_site_inner():
    global SETUP_SUCCESS
    
    log(f"Site setup starting at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"SITE={SITE} DB={DB_HOST}:{DB_PORT}/{DB_NAME}")
    log(f"DB_ROOT_PASSWORD set: {'yes' if DB_ROOT_PASSWORD else 'NO - MISSING!'}")
    log(f"ADMIN_PASSWORD set: {'yes' if ADMIN_PASSWORD else 'NO - MISSING!'}")
    
    # Update common_site_config.json
    config_path = os.path.join(BENCH_DIR, "sites", "common_site_config.json")
    try:
        with open(config_path) as f:
            config = json.load(f)
    except Exception as e:
        log(f"Could not read common_site_config.json: {e}")
        config = {}
    config["redis_cache"] = REDIS_CACHE
    config["redis_queue"] = REDIS_QUEUE
    config["redis_socketio"] = REDIS_QUEUE
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    log("common_site_config.json updated")
    
    # Wait for MariaDB using TCP socket (no pymysql needed)
    if not wait_for_tcp(DB_HOST, DB_PORT, timeout=600):
        log("ERROR: MariaDB TCP timeout")
        return
    
    # Small extra wait for MariaDB to fully initialize
    log("MariaDB TCP ready, waiting 10s for full initialization...")
    time.sleep(10)
    
    # Test root access
    has_root = test_root_access()
    
    # Check if site already exists
    site_dir = os.path.join(BENCH_DIR, "sites", SITE)
    site_config = os.path.join(site_dir, "site_config.json")
    site_exists = os.path.exists(site_config)
    log(f"Site directory exists: {site_exists} ({site_dir})")
    
    if site_exists:
        log("Site already configured - running migrate...")
        run_bench(["--site", SITE, "migrate"])
        run_bench(["use", SITE])
        SETUP_SUCCESS = True
        log(f"Site migration done at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    if has_root:
        log("Running bench new-site with root access...")
        args = ["new-site", SITE,
                "--db-name", DB_NAME,
                "--db-password", DB_PASSWORD,
                "--admin-password", ADMIN_PASSWORD,
                "--db-host", DB_HOST,
                "--db-port", str(DB_PORT),
                "--no-mariadb-socket",
                "--force"]
        if DB_ROOT_PASSWORD:
            args += ["--db-root-password", DB_ROOT_PASSWORD]
        if ENCRYPTION_KEY:
            args += ["--encryption-key", ENCRYPTION_KEY]
        
        rc = run_bench(args)
        if rc == 0:
            log("bench new-site succeeded!")
            log("Installing CRM app...")
            run_bench(["--site", SITE, "install-app", "crm"])
        else:
            log(f"bench new-site FAILED with exit code {rc}")
            log("Trying install-app fallback...")
            _install_app_fallback()
            return
    else:
        log("No root access - using install-app fallback...")
        _install_app_fallback()
        return
    
    run_bench(["use", SITE])
    log(f"Site setup done at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    SETUP_SUCCESS = True

def _install_app_fallback():
    """Install frappe/crm without root DB access."""
    global SETUP_SUCCESS
    
    # Drop tables using crm_db user
    try:
        import pymysql
        conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_NAME, password=DB_PASSWORD, database=DB_NAME, connect_timeout=10)
        cursor = conn.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute(f'SELECT table_name FROM information_schema.tables WHERE table_schema="{DB_NAME}"')
        tables = [row[0] for row in cursor.fetchall()]
        log(f"Dropping {len(tables)} tables...")
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"Error dropping tables (may be OK if DB is empty): {e}")
    
    site_dir = os.path.join(BENCH_DIR, "sites", SITE)
    os.makedirs(site_dir, exist_ok=True)
    cfg = {"db_name": DB_NAME, "db_password": DB_PASSWORD, "db_host": DB_HOST, "db_port": DB_PORT}
    if ENCRYPTION_KEY:
        cfg["encryption_key"] = ENCRYPTION_KEY
    with open(os.path.join(site_dir, "site_config.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    log("site_config.json written")
    
    rc1 = run_bench(["--site", SITE, "install-app", "frappe"])
    rc2 = run_bench(["--site", SITE, "install-app", "crm"])
    run_bench(["use", SITE])
    
    if rc1 == 0 and rc2 == 0:
        log("install-app fallback succeeded!")
        SETUP_SUCCESS = True
    else:
        log(f"install-app fallback FAILED: frappe={rc1} crm={rc2}")
    
    log(f"Fallback done at {time.strftime('%Y-%m-%d %H:%M:%S')}")

# ─── Main ───────────────────────────────────────────────────────────────────

# Start health check server
log(f"Starting health check server on port {SERVE_PORT}...")
server = HTTPServer(("0.0.0.0", SERVE_PORT), HealthHandler)
server.allow_reuse_address = True
server_thread = threading.Thread(target=server.serve_forever)
server_thread.daemon = True
server_thread.start()
log(f"Health check server running on port {SERVE_PORT}")
log(f"Check setup log at: https://crm-frappe-web.onrender.com/setup-log")

# Run site setup in background thread
setup_thread = threading.Thread(target=setup_site)
setup_thread.daemon = True
setup_thread.start()

# Wait for setup to complete
log("Waiting for site setup to complete...")
SETUP_DONE.wait()

if SETUP_SUCCESS:
    log("Site setup succeeded! Switching to gunicorn...")
    # Stop health check server
    server.shutdown()
    log("Health check server stopped")
    
    # Start gunicorn
    log(f"Starting gunicorn on port {SERVE_PORT}...")
    env = {**os.environ, "PATH": "/usr/local/bin:/home/frappe/.local/bin:/home/frappe/frappe-bench/env/bin:" + os.environ.get("PATH", "")}
    os.execve(
        "/home/frappe/frappe-bench/env/bin/gunicorn",
        [
            "gunicorn",
            "--chdir=/home/frappe/frappe-bench/sites",
            f"--bind=0.0.0.0:{SERVE_PORT}",
            "--threads=4",
            "--workers=2",
            "--worker-class=gthread",
            "--timeout=120",
            "frappe.app:application",
        ],
        env
    )
else:
    log("Site setup FAILED! Keeping health server running so you can check /setup-log")
    log("Will retry setup in 60 seconds...")
    
    # Keep retrying setup every 60 seconds
    while True:
        time.sleep(60)
        log("Retrying site setup...")
        SETUP_DONE.clear()
        SETUP_SUCCESS = False
        setup_thread = threading.Thread(target=setup_site)
        setup_thread.daemon = True
        setup_thread.start()
        SETUP_DONE.wait()
        
        if SETUP_SUCCESS:
            log("Retry succeeded! Switching to gunicorn...")
            server.shutdown()
            env = {**os.environ, "PATH": "/usr/local/bin:/home/frappe/.local/bin:/home/frappe/frappe-bench/env/bin:" + os.environ.get("PATH", "")}
            os.execve(
                "/home/frappe/frappe-bench/env/bin/gunicorn",
                [
                    "gunicorn",
                    "--chdir=/home/frappe/frappe-bench/sites",
                    f"--bind=0.0.0.0:{SERVE_PORT}",
                    "--threads=4",
                    "--workers=2",
                    "--worker-class=gthread",
                    "--timeout=120",
                    "frappe.app:application",
                ],
                env
            )
        else:
            log("Retry failed. Will try again in 60 seconds...")
