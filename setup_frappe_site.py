#!/usr/bin/env python3
"""
Frappe site setup script.
Runs in background after gunicorn starts.
Uses bench new-site with root password (MariaDB init script grants root@% access).
"""
import os
import sys
import json
import time
import subprocess
import signal

# Configuration from environment
BENCH_DIR = "/home/frappe/frappe-bench"
SITE = os.environ.get("FRAPPE_SITE_NAME", "crm.localhost")
DB_HOST = os.environ.get("DB_HOST", "mariadb")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_NAME = os.environ.get("DB_NAME", "crm_db")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "changeme")
DB_ROOT_PASSWORD = os.environ.get("DB_ROOT_PASSWORD", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
GUNICORN_PID = int(os.environ.get("GUNICORN_PID", "0"))

def log(msg):
    print(f"[setup] {msg}", flush=True)

log(f"Starting site setup at {time.strftime('%Y-%m-%d %H:%M:%S')}")
log(f"SITE={SITE} DB={DB_HOST}:{DB_PORT}/{DB_NAME}")
log(f"GUNICORN_PID={GUNICORN_PID}")
log(f"DB_ROOT_PASSWORD={'SET' if DB_ROOT_PASSWORD else 'NOT SET'}")

# Wait for MariaDB
log("Waiting for MariaDB...")
import pymysql

for i in range(200):
    try:
        conn = pymysql.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_NAME, password=DB_PASSWORD,
            database=DB_NAME, connect_timeout=5
        )
        conn.close()
        log(f"MariaDB ready (attempt {i+1})")
        break
    except Exception as e:
        if i % 10 == 0:
            log(f"Waiting for MariaDB (attempt {i+1}): {e}")
        time.sleep(3)
else:
    log("ERROR: MariaDB timeout after 10 minutes")
    sys.exit(1)

# Test root access
log("Testing root access...")
try:
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user="root", password=DB_ROOT_PASSWORD,
        connect_timeout=5
    )
    conn.close()
    log("Root access OK!")
    has_root = True
except Exception as e:
    log(f"Root access FAILED: {e}")
    has_root = False

def run_bench(args):
    """Run a bench command and return exit code."""
    cmd = ["/usr/local/bin/bench"] + args
    log(f"Running: {' '.join(str(a) for a in cmd)}")
    result = subprocess.run(
        cmd,
        cwd=BENCH_DIR,
        env={**os.environ, "PATH": "/usr/local/bin:/home/frappe/.local/bin:/home/frappe/frappe-bench/env/bin:" + os.environ.get("PATH", "")},
    )
    log(f"Exit code: {result.returncode}")
    return result.returncode

if has_root:
    # Use bench new-site with root password
    log("Running bench new-site...")
    args = [
        "new-site", SITE,
        "--db-name", DB_NAME,
        "--db-password", DB_PASSWORD,
        "--admin-password", ADMIN_PASSWORD,
        "--db-host", DB_HOST,
        "--db-port", str(DB_PORT),
        "--no-mariadb-socket",
        "--force",
    ]
    if DB_ROOT_PASSWORD:
        args += ["--db-root-password", DB_ROOT_PASSWORD]
    if ENCRYPTION_KEY:
        args += ["--encryption-key", ENCRYPTION_KEY]
    
    rc = run_bench(args)
    log(f"bench new-site exit: {rc}")
    
    if rc == 0:
        log("Installing CRM app...")
        rc = run_bench(["--site", SITE, "install-app", "crm"])
        log(f"install-app crm exit: {rc}")
else:
    # No root access - use install-app approach
    log("No root access - using install-app approach...")
    
    # Drop all tables
    try:
        conn = pymysql.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_NAME, password=DB_PASSWORD,
            database=DB_NAME, connect_timeout=10
        )
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
        log("All tables dropped")
    except Exception as e:
        log(f"ERROR dropping tables: {e}")
    
    # Create site directory and config
    site_dir = os.path.join(BENCH_DIR, "sites", SITE)
    os.makedirs(site_dir, exist_ok=True)
    
    site_config = {
        "db_name": DB_NAME,
        "db_password": DB_PASSWORD,
        "db_host": DB_HOST,
        "db_port": DB_PORT,
    }
    if ENCRYPTION_KEY:
        site_config["encryption_key"] = ENCRYPTION_KEY
    
    with open(os.path.join(site_dir, "site_config.json"), "w") as f:
        json.dump(site_config, f, indent=2)
    log("site_config.json written")
    
    log("Installing frappe app...")
    rc = run_bench(["--site", SITE, "install-app", "frappe"])
    log(f"install-app frappe exit: {rc}")
    
    log("Installing crm app...")
    rc = run_bench(["--site", SITE, "install-app", "crm"])
    log(f"install-app crm exit: {rc}")

# Set current site
run_bench(["use", SITE])

log(f"Site setup done at {time.strftime('%Y-%m-%d %H:%M:%S')}")

# Reload gunicorn
if GUNICORN_PID > 0:
    try:
        os.kill(GUNICORN_PID, signal.SIGHUP)
        log(f"Sent SIGHUP to gunicorn (PID={GUNICORN_PID})")
    except Exception as e:
        log(f"SIGHUP failed: {e}")
