#!/bin/bash
# =============================================================================
# init-site.sh
# Runs inside the frappe-web container on every startup.
# =============================================================================

export PATH="/usr/local/bin:/home/frappe/frappe-bench/env/bin:$PATH"

SERVE_PORT="${PORT:-8000}"
LOG_FILE="/tmp/init-site.log"

echo "[init-site] Starting at $(date), port=$SERVE_PORT" | tee -a "$LOG_FILE"
echo "[init-site] USER=$(whoami), bench=$(which bench 2>/dev/null || echo NOT_FOUND)" | tee -a "$LOG_FILE"

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

echo "[init-site] site=$SITE db=$DB_HOST:$DB_PORT/$DB_NAME" | tee -a "$LOG_FILE"

cd "${BENCH_DIR}"

# Update common_site_config.json
python3 -c "
import json
config_path = '${BENCH_DIR}/sites/common_site_config.json'
try:
    config = json.load(open(config_path))
except:
    config = {}
config['redis_cache'] = '${REDIS_CACHE}'
config['redis_queue'] = '${REDIS_QUEUE}'
config['redis_socketio'] = '${REDIS_QUEUE}'
json.dump(config, open(config_path, 'w'), indent=2)
print('[init-site] common_site_config.json updated')
" 2>&1 | tee -a "$LOG_FILE"

# Start gunicorn WITHOUT --preload (so it starts even without a site)
echo "[init-site] Starting gunicorn on port $SERVE_PORT..." | tee -a "$LOG_FILE"
/home/frappe/frappe-bench/env/bin/gunicorn \
    --chdir=/home/frappe/frappe-bench/sites \
    --bind=0.0.0.0:${SERVE_PORT} \
    --threads=4 \
    --workers=2 \
    --worker-class=gthread \
    --timeout=120 \
    frappe.app:application &
GUNICORN_PID=$!
echo "[init-site] gunicorn PID=$GUNICORN_PID" | tee -a "$LOG_FILE"

sleep 5
if kill -0 $GUNICORN_PID 2>/dev/null; then
    echo "[init-site] gunicorn running OK" | tee -a "$LOG_FILE"
else
    echo "[init-site] ERROR: gunicorn died!" | tee -a "$LOG_FILE"
    # Try without worker class
    /home/frappe/frappe-bench/env/bin/gunicorn \
        --chdir=/home/frappe/frappe-bench/sites \
        --bind=0.0.0.0:${SERVE_PORT} \
        --timeout=120 \
        frappe.app:application &
    GUNICORN_PID=$!
    echo "[init-site] gunicorn retry PID=$GUNICORN_PID" | tee -a "$LOG_FILE"
    sleep 3
fi

# Run site setup in background
{
    echo "[bg] Site setup starting at $(date)"
    
    # Wait for MariaDB
    echo "[bg] Waiting for MariaDB $DB_HOST:$DB_PORT..."
    for i in $(seq 1 200); do
        if mysqladmin ping -h"$DB_HOST" -P"$DB_PORT" --silent 2>/dev/null; then
            echo "[bg] MariaDB ready after $i attempts"
            break
        fi
        [ $i -eq 200 ] && echo "[bg] ERROR: MariaDB timeout" && exit 1
        [ $((i % 20)) -eq 0 ] && echo "[bg] Still waiting for MariaDB (attempt $i)..."
        sleep 3
    done

    # Check table count
    TABLE_COUNT=$(mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_NAME" -p"$DB_PASSWORD" \
        "$DB_NAME" --skip-column-names -e \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME';" \
        2>/dev/null)
    echo "[bg] Table count: '$TABLE_COUNT'"

    if [ -n "$TABLE_COUNT" ] && [ "$TABLE_COUNT" -gt "10" ] 2>/dev/null; then
        echo "[bg] DB has $TABLE_COUNT tables - restoring site config..."
        mkdir -p "${BENCH_DIR}/sites/${SITE}"
        python3 -c "
import json
cfg = {'db_name': '${DB_NAME}', 'db_password': '${DB_PASSWORD}', 'db_host': '${DB_HOST}', 'db_port': int('${DB_PORT}')}
if '${ENCRYPTION_KEY}': cfg['encryption_key'] = '${ENCRYPTION_KEY}'
json.dump(cfg, open('${BENCH_DIR}/sites/${SITE}/site_config.json', 'w'), indent=2)
print('[bg] site_config.json written')
"
        bench --site "$SITE" migrate 2>&1 || echo "[bg] migrate had errors"
    else
        echo "[bg] Running bench new-site..."
        ARGS=(new-site "$SITE" --db-name "$DB_NAME" --db-password "$DB_PASSWORD" \
              --admin-password "$ADMIN_PASSWORD" --db-host "$DB_HOST" --db-port "$DB_PORT" \
              --no-mariadb-socket --force)
        [ -n "$DB_ROOT_PASSWORD" ] && ARGS+=(--db-root-password "$DB_ROOT_PASSWORD")
        [ -n "$ENCRYPTION_KEY" ] && ARGS+=(--encryption-key "$ENCRYPTION_KEY")
        
        bench "${ARGS[@]}" 2>&1
        echo "[bg] bench new-site exit: $?"
        
        bench --site "$SITE" install-app crm 2>&1
        bench --site "$SITE" migrate 2>&1
    fi

    bench use "$SITE" 2>&1
    echo "[bg] Site setup done at $(date)"
    kill -HUP $GUNICORN_PID 2>/dev/null && echo "[bg] Sent SIGHUP to gunicorn"
} >> "$LOG_FILE" 2>&1 &

echo "[init-site] Background setup PID=$!" | tee -a "$LOG_FILE"

# Keep gunicorn running
wait $GUNICORN_PID
echo "[init-site] gunicorn exited: $?" | tee -a "$LOG_FILE"
