#!/bin/bash
# =============================================================================
# init-site.sh
# Runs inside the frappe-web container on every startup.
# 
# KEY DESIGN: bench serve starts FIRST (in background) so Render's health check
# passes immediately. Site creation happens in the background.
# 
# Render sets PORT=10000 for web services. We use $PORT.
# =============================================================================

set -e

export PATH="/usr/local/bin:/home/frappe/frappe-bench/env/bin:$PATH"

# Render sets PORT=10000 for web services
SERVE_PORT="${PORT:-8000}"

echo "[init-site] Starting on port $SERVE_PORT..."
echo "[init-site] USER: $(whoami)"
echo "[init-site] bench: $(which bench 2>/dev/null || echo 'NOT FOUND')"

BENCH_DIR="/home/frappe/frappe-bench"
SITE="${FRAPPE_SITE_NAME:-crm.localhost}"
DB_HOST="${DB_HOST:-mariadb}"
DB_PORT="${DB_PORT:-3306}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
DB_NAME="${DB_NAME:-crm_db}"
DB_PASSWORD="${DB_PASSWORD:-changeme}"
ENCRYPTION_KEY="${ENCRYPTION_KEY:-}"
REDIS_CACHE="${REDIS_CACHE_URL:-redis://redis-cache:13000}"
REDIS_QUEUE="${REDIS_QUEUE_URL:-redis://redis-queue:11000}"

echo "[init-site] site: ${SITE}, db: ${DB_HOST}:${DB_PORT}"

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
# Start bench serve in background FIRST so Render's health check passes
# Render requires the service to listen on $PORT (default 10000)
# ---------------------------------------------------------------------------
echo "[init-site] Starting bench serve on port $SERVE_PORT..."
bench serve --port "$SERVE_PORT" &
BENCH_PID=$!
echo "[init-site] bench serve started with PID $BENCH_PID"

# Give bench serve a moment to start
sleep 5

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

    # Create site or migrate
    if [ ! -d "${BENCH_DIR}/sites/${SITE}" ]; then
        echo "[init-site] Creating site '${SITE}'..."
        bench new-site "$SITE" \
            --db-name "$DB_NAME" \
            --db-password "$DB_PASSWORD" \
            --admin-password "$ADMIN_PASSWORD" \
            --db-host "$DB_HOST" \
            --db-port "$DB_PORT" \
            --no-mariadb-socket \
            ${ENCRYPTION_KEY:+--encryption-key "$ENCRYPTION_KEY"}

        echo "[init-site] Installing CRM app..."
        bench --site "$SITE" install-app crm

        echo "[init-site] Running migrations..."
        bench --site "$SITE" migrate

        echo "[init-site] Site '${SITE}' created and CRM installed."
    else
        echo "[init-site] Site '${SITE}' exists — running migrate..."
        bench --site "$SITE" migrate || echo "[init-site] migrate skipped"
    fi

    bench use "$SITE"
    echo "[init-site] Site setup complete! Frappe is ready."
) &

# Wait for bench serve to exit (it runs in foreground)
wait $BENCH_PID
