#!/usr/bin/env python3
"""
Frappe starter - serves health check while site setup runs.
After setup, switches to gunicorn.
"""
import os
import sys
import json
import time
import threading
import subprocess
import signal
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

LOG_LINES = []
SETUP_DONE = threading.Event()
SETUP_SUCCESS = False

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG_LINES.append(line)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/setup-log":
            body = "\n".join(LOG_LINES).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            body = b"Frappe CRM - initializing...\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
    def log_message(self, *a): pass

def run_bench(args):
    cmd = ["/usr/local/bin/bench"] + args
    log(f"Running: {' '.join(str(a) for a in cmd)}")
    env = {**os.environ, "PATH": "/usr/local/bin:/home/frappe/.local/bin:/home/frappe/frappe-bench/env/bin:" + os.environ.get("PATH", "")}
    result = subprocess.run(cmd, cwd=BENCH_DIR, env=env)
    log(f"Exit code: {result.returncode}")
    return result.returncode

def setup_site():
    global SETUP_SUCCESS
    
    log(f"Site setup starting at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"SITE={SITE} DB={DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    # Update common_site_config.json
    config_path = os.path.join(BENCH_DIR, "sites", "common_site_config.json")
    try:
        with open(config_path) as f:
            config = json.load(f)
    except:
        config = {}
    config["redis_cache"] = REDIS_CACHE
    config["redis_queue"] = REDIS_QUEUE
    config["redis_socketio"] = REDIS_QUEUE
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    log("common_site_config.json updated")
    
    # Wait for MariaDB using root credentials (crm_db user doesn't exist until bench new-site creates it)
    log("Waiting for MariaDB (using root credentials)...")
    import pymysql
    
    has_root = False
    for i in range(200):
        try:
            conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user="root", password=DB_ROOT_PASSWORD, connect_timeout=5)
            conn.close()
            log(f"MariaDB ready with root access (attempt {i+1})")
            has_root = True
            break
        except Exception as e:
            if i % 10 == 0:
                log(f"Waiting for MariaDB root access (attempt {i+1}): {e}")
            time.sleep(3)
    else:
        log("ERROR: MariaDB root access timeout - trying crm_db user as fallback...")
        # Fallback: try crm_db user (site may already be set up)
        for i in range(30):
            try:
                conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_NAME, password=DB_PASSWORD, database=DB_NAME, connect_timeout=5)
                conn.close()
                log(f"MariaDB ready with crm_db user (attempt {i+1})")
                break
            except Exception as e:
                if i % 10 == 0:
                    log(f"Waiting for MariaDB crm_db (attempt {i+1}): {e}")
                time.sleep(3)
        else:
            log("ERROR: MariaDB completely unreachable")
            SETUP_DONE.set()
            return
    
    if has_root:
        log("Running bench new-site...")
        args = ["new-site", SITE, "--db-name", DB_NAME, "--db-password", DB_PASSWORD,
                "--admin-password", ADMIN_PASSWORD, "--db-host", DB_HOST, "--db-port", str(DB_PORT),
                "--no-mariadb-socket", "--force"]
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
    else:
        log("No root access - using install-app approach...")
        # Drop tables and reinstall
        try:
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
            log(f"Error dropping tables: {e}")
        
        site_dir = os.path.join(BENCH_DIR, "sites", SITE)
        os.makedirs(site_dir, exist_ok=True)
        cfg = {"db_name": DB_NAME, "db_password": DB_PASSWORD, "db_host": DB_HOST, "db_port": DB_PORT}
        if ENCRYPTION_KEY:
            cfg["encryption_key"] = ENCRYPTION_KEY
        with open(os.path.join(site_dir, "site_config.json"), "w") as f:
            json.dump(cfg, f, indent=2)
        
        run_bench(["--site", SITE, "install-app", "frappe"])
        run_bench(["--site", SITE, "install-app", "crm"])
    
    run_bench(["use", SITE])
    log(f"Site setup done at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    SETUP_SUCCESS = True
    SETUP_DONE.set()

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
else:
    log("Site setup FAILED! Starting gunicorn anyway...")

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
