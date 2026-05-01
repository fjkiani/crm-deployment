#!/bin/bash
# =============================================================================
# init-site.sh
# Runs inside the frappe-web container on every startup.
# 
# KEY DESIGN: gunicorn starts FIRST (in background) so Render's health check
# passes immediately (port 10000 open). Site creation happens in background.
# 
# Render sets PORT=10000 for web services.
# =============================================================================

# Don't use set -e here - we want to handle errors gracefully
export PATH="/usr/local/bin:/home/frappe/frappe-bench/env/bin:$PATH"

# Render sets PORT=10000 for web services
SERVE_PORT="${PORT:-8000}"

# Log file for debugging
LOG_FILE="/tmp/init-site.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[init-site] ============================================"
echo "[init-site] Starting at $(date)"
echo "[init-site] PORT=$SERVE_PORT"
echo "[init-site] USER: $(whoami)"
echo "[init-site] Python: $(python3 --version 2>&1)"
echo "[init-site] gunicorn: $(which gunicorn 2>&1 || echo 'NOT FOUND')"
echo "[init-site] bench: $(which bench 2>&1 || echo 'NOT FOUND')"
echo "[init-site] mysqladmin: $(which mysqladmin 2>&1 || echo 'NOT FOUND')"
echo "[init-site] mysql: $(which mysql 2>&1 || echo 'NOT FOUND')"

BENCH_DIR="/home/frappe/frappe-bench"
SITE="${FRAPPE_SITE_NAME:-crm.localhost}"
DB_HOST="${DB_HOST:-mariadb}"
DB_PORT="${DB_PORT:-3306}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
DB_NAME="${DB_NAME:-crm_db}"
DB_PASSWORD="${DB_PASSWORD:-changeme}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-}"
ENCRYPTION_KEY="${ENCRYPTION_KEY:-}"
REDIS_CACHE="${REDIS_CACHE_URL:-redis://redis-cache:13000}"
REDIS_QUEUE="${REDIS_QUEUE_URL:-redis://redis-queue:11000}"

echo "[init-site] site: ${SITE}"
echo "[init-site] db: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "[init-site] redis_cache: ${REDIS_CACHE}"
echo "[init-site] redis_queue: ${REDIS_QUEUE}"

cd "${BENCH_DIR}"

# ---------------------------------------------------------------------------
# Configure Redis URLs in common_site_config.json
# ---------------------------------------------------------------------------
python3 - <<PYEOF
import json, os
config_path = "${BENCH_DIR}/sites/common_site_config.json"
try:
    with open(config_path) as f:
        config = json.load(f)
except Exception:
    config = {}
config["redis_cache"] = "${REDIS_CACHE}"
config["redis_queue"] = "${REDIS_QUEUE}"
config["redis_socketio"] = "${REDIS_QUEUE}"
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
print("[init-site] common_site_config.json updated.")
PYEOF

# ---------------------------------------------------------------------------
# Start gunicorn in background FIRST so Render's health check passes
# ---------------------------------------------------------------------------
echo "[init-site] Starting gunicorn on port $SERVE_PORT..."
/home/frappe/frappe-bench/env/bin/gunicorn \
    --chdir=/home/frappe/frappe-bench/sites \
    --bind=0.0.0.0:${SERVE_PORT} \
    --threads=4 \
    --workers=2 \
    --worker-class=gthread \
    --timeout=120 \
    frappe.app:application \
    --preload &
GUNICORN_PID=$!
echo "[init-site] gunicorn PID: $GUNICORN_PID"

sleep 3
if kill -0 $GUNICORN_PID 2>/dev/null; then
    echo "[init-site] gunicorn is running"
else
    echo "[init-site] ERROR: gunicorn failed to start!"
fi

# ---------------------------------------------------------------------------
# Site setup in background
# ---------------------------------------------------------------------------
SAVED_GUNICORN_PID=$GUNICORN_PID
(
    echo "[init-site-bg] Starting site setup at $(date)"
    
    echo "[init-site-bg] Waiting for MariaDB at ${DB_HOST}:${DB_PORT}..."
    WAIT_COUNT=0
    until mysqladmin ping -h"$DB_HOST" -P"$DB_PORT" --silent 2>/dev/null; do
        WAIT_COUNT=$((WAIT_COUNT + 1))
        if [ $WAIT_COUNT -gt 200 ]; then
            echo "[init-site-bg] ERROR: MariaDB not ready after 10 minutes."
            exit 1
        fi
        if [ $((WAIT_COUNT % 10)) -eq 0 ]; then
            echo "[init-site-bg] MariaDB not ready (attempt $WAIT_COUNT)..."
        fi
        sleep 3
    done
    echo "[init-site-bg] MariaDB is up at $(date)"

    # Check if database has Frappe tables
    TABLE_COUNT=$(mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_NAME" -p"$DB_PASSWORD" \
        "$DB_NAME" --skip-column-names -e \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME';" \
        2>/dev/null || echo "ERROR")
    
    echo "[init-site-bg] Table count result: '$TABLE_COUNT'"

    if echo "$TABLE_COUNT" | grep -qE '^[0-9]+$' && [ "$TABLE_COUNT" -gt "10" ]; then
        echo "[init-site-bg] Database has $TABLE_COUNT tables - site was previously set up."
        echo "[init-site-bg] Creating site directory and config..."
        
        mkdir -p "${BENCH_DIR}/sites/${SITE}"
        
        python3 - <<PYEOF2
import json
site_config = {
    "db_name": "${DB_NAME}",
    "db_password": "${DB_PASSWORD}",
    "db_host": "${DB_HOST}",
    "db_port": int("${DB_PORT}"),
}
if "${ENCRYPTION_KEY}":
    site_config["encryption_key"] = "${ENCRYPTION_KEY}"
with open("${BENCH_DIR}/sites/${SITE}/site_config.json", "w") as f:
    json.dump(site_config, f, indent=2)
print("[init-site-bg] site_config.json created.")
PYEOF2
        
        echo "[init-site-bg] Running migrate..."
        bench --site "$SITE" migrate 2>&1 || echo "[init-site-bg] migrate had errors (may be ok)"
    else
        echo "[init-site-bg] Fresh database (or error). Running bench new-site..."
        
        BENCH_ARGS=(
            new-site "$SITE"
            --db-name "$DB_NAME"
            --db-password "$DB_PASSWORD"
            --admin-password "$ADMIN_PASSWORD"
            --db-host "$DB_HOST"
            --db-port "$DB_PORT"
            --no-mariadb-socket
            --force
        )
        
        if [ -n "$DB_ROOT_PASSWORD" ]; then
            BENCH_ARGS+=(--db-root-password "$DB_ROOT_PASSWORD")
        fi
        if [ -n "$ENCRYPTION_KEY" ]; then
            BENCH_ARGS+=(--encryption-key "$ENCRYPTION_KEY")
        fi
        
        echo "[init-site-bg] Running: bench new-site $SITE ..."
        bench "${BENCH_ARGS[@]}" 2>&1
        SITE_EXIT=$?
        echo "[init-site-bg] bench new-site exit code: $SITE_EXIT"
        
        if [ $SITE_EXIT -ne 0 ]; then
            echo "[init-site-bg] ERROR: bench new-site failed!"
            exit $SITE_EXIT
        fi

        echo "[init-site-bg] Installing CRM app..."
        bench --site "$SITE" install-app crm 2>&1
        
        echo "[init-site-bg] Running migrations..."
        bench --site "$SITE" migrate 2>&1
        
        echo "[init-site-bg] Site created successfully!"
    fi

    bench use "$SITE" 2>&1
    echo "[init-site-bg] Site setup complete at $(date)!"
    
    # Signal gunicorn to reload
    echo "[init-site-bg] Sending SIGHUP to gunicorn (PID $SAVED_GUNICORN_PID)..."
    kill -HUP $SAVED_GUNICORN_PID 2>/dev/null && echo "[init-site-bg] SIGHUP sent" || echo "[init-site-bg] SIGHUP failed"
) >> "$LOG_FILE" 2>&1 &

echo "[init-site] Site setup running in background (PID $!)"
echo "[init-site] Logs: $LOG_FILE"

# Wait for gunicorn
wait $GUNICORN_PID
EXIT_CODE=$?
echo "[init-site] gunicorn exited with code $EXIT_CODE"
exit $EXIT_CODE
