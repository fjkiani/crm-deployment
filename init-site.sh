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

echo "[init-site] Starting on port $SERVE_PORT..."
echo "[init-site] USER: $(whoami)"
echo "[init-site] Python: $(python3 --version 2>&1)"
echo "[init-site] gunicorn: $(which gunicorn 2>&1 || echo 'NOT FOUND')"
echo "[init-site] bench: $(which bench 2>&1 || echo 'NOT FOUND')"

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

echo "[init-site] site: ${SITE}, db: ${DB_HOST}:${DB_PORT}/${DB_NAME}"

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
# This is the same command as the production image's CMD, but on $PORT
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
echo "[init-site] gunicorn started with PID $GUNICORN_PID"

# Give gunicorn a moment to start
sleep 3
echo "[init-site] gunicorn status: $(kill -0 $GUNICORN_PID 2>&1 && echo 'running' || echo 'FAILED')"

# ---------------------------------------------------------------------------
# Wait for MariaDB and do site setup in background
# ---------------------------------------------------------------------------
(
    echo "[init-site] Waiting for MariaDB at ${DB_HOST}:${DB_PORT}..."
    WAIT_COUNT=0
    until mysqladmin ping -h"$DB_HOST" -P"$DB_PORT" --silent 2>/dev/null; do
        WAIT_COUNT=$((WAIT_COUNT + 1))
        if [ $WAIT_COUNT -gt 200 ]; then
            echo "[init-site] ERROR: MariaDB not ready after 10 minutes."
            exit 1
        fi
        echo "[init-site] MariaDB not ready (attempt $WAIT_COUNT) — retrying in 3s..."
        sleep 3
    done
    echo "[init-site] MariaDB is up."

    # Check if the database already has Frappe tables (site was previously set up)
    TABLE_COUNT=$(mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_NAME" -p"$DB_PASSWORD" \
        "$DB_NAME" -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME';" \
        --skip-column-names 2>/dev/null || echo "0")
    
    echo "[init-site] Database table count: $TABLE_COUNT"

    if [ "$TABLE_COUNT" -gt "10" ] 2>/dev/null; then
        # Database already has tables - site was previously set up
        # Just create the site directory and run migrate
        echo "[init-site] Database already initialized ($TABLE_COUNT tables). Setting up site directory..."
        
        # Create site directory if it doesn't exist
        mkdir -p "${BENCH_DIR}/sites/${SITE}"
        
        # Create site_config.json
        python3 - <<PYEOF2
import json
site_config = {
    "db_name": "${DB_NAME}",
    "db_password": "${DB_PASSWORD}",
    "db_host": "${DB_HOST}",
    "db_port": ${DB_PORT},
    "encryption_key": "${ENCRYPTION_KEY}"
}
with open("${BENCH_DIR}/sites/${SITE}/site_config.json", "w") as f:
    json.dump(site_config, f, indent=2)
print("[init-site] site_config.json created.")
PYEOF2
        
        echo "[init-site] Running migrate on existing site..."
        bench --site "$SITE" migrate || echo "[init-site] migrate skipped"
    else
        # Fresh database - run bench new-site
        echo "[init-site] Fresh database. Creating site '${SITE}'..."
        
        # Build bench new-site command args
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
        
        # Add root password if provided
        if [ -n "$DB_ROOT_PASSWORD" ]; then
            BENCH_ARGS+=(--db-root-password "$DB_ROOT_PASSWORD")
        fi
        
        # Add encryption key if provided
        if [ -n "$ENCRYPTION_KEY" ]; then
            BENCH_ARGS+=(--encryption-key "$ENCRYPTION_KEY")
        fi
        
        echo "[init-site] Running bench new-site..."
        bench "${BENCH_ARGS[@]}"
        SITE_EXIT=$?
        
        if [ $SITE_EXIT -ne 0 ]; then
            echo "[init-site] ERROR: bench new-site failed with exit code $SITE_EXIT"
            exit $SITE_EXIT
        fi

        echo "[init-site] Installing CRM app..."
        bench --site "$SITE" install-app crm

        echo "[init-site] Running migrations..."
        bench --site "$SITE" migrate

        echo "[init-site] Site '${SITE}' created and CRM installed."
    fi

    bench use "$SITE"
    echo "[init-site] Site setup complete! Frappe is ready."
    
    # Reload gunicorn to pick up the new site
    echo "[init-site] Sending SIGHUP to gunicorn to reload..."
    kill -HUP $GUNICORN_PID 2>/dev/null || true
) &

# Wait for gunicorn to exit (it runs in foreground)
wait $GUNICORN_PID
EXIT_CODE=$?
echo "[init-site] gunicorn exited with code $EXIT_CODE"
exit $EXIT_CODE
