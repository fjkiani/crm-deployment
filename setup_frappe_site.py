#!/usr/bin/env python3
"""
Frappe site setup script.
Runs in background after gunicorn starts.
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
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
GUNICORN_PID = int(os.environ.get("GUNICORN_PID", "0"))

def log(msg):
    print(f"[setup] {msg}", flush=True)

log(f"Starting site setup at {time.strftime('%Y-%m-%d %H:%M:%S')}")
log(f"SITE={SITE} DB={DB_HOST}:{DB_PORT}/{DB_NAME}")
log(f"GUNICORN_PID={GUNICORN_PID}")

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

# Check table count
try:
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_NAME, password=DB_PASSWORD,
        database=DB_NAME, connect_timeout=10
    )
    cursor = conn.cursor()
    cursor.execute(f'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema="{DB_NAME}"')
    table_count = cursor.fetchone()[0]
    conn.close()
    log(f"Table count: {table_count}")
except Exception as e:
    log(f"ERROR checking table count: {e}")
    table_count = 0

def run_bench(args, check=False):
    """Run a bench command and return exit code."""
    cmd = ["/usr/local/bin/bench"] + args
    log(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=BENCH_DIR,
        capture_output=False,
        text=True
    )
    log(f"Exit code: {result.returncode}")
    return result.returncode

if table_count > 50:
    log(f"DB has {table_count} tables - restoring site config...")
    
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
    
    run_bench(["--site", SITE, "migrate"])
    run_bench(["--site", SITE, "set-admin-password", ADMIN_PASSWORD])
else:
    log(f"Fresh/partial DB ({table_count} tables) - dropping and reinstalling...")
    
    # Drop all tables
    try:
        conn = pymysql.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_NAME, password=DB_PASSWORD,
            database=DB_NAME, connect_timeout=10
        )
        cursor = conn.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute(f'SELECT table_name FROM information_schema.tables WHERE table_schema = "{DB_NAME}"')
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
    
    # Install apps
    log("Installing frappe app...")
    rc = run_bench(["--site", SITE, "install-app", "frappe"])
    log(f"install-app frappe: exit {rc}")
    
    log("Installing crm app...")
    rc = run_bench(["--site", SITE, "install-app", "crm"])
    log(f"install-app crm: exit {rc}")
    
    run_bench(["--site", SITE, "set-admin-password", ADMIN_PASSWORD])

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
