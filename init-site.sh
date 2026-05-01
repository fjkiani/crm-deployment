#!/bin/bash
# =============================================================================
# init-site.sh - Simplified version for debugging
# =============================================================================

export PATH="/usr/local/bin:/home/frappe/frappe-bench/env/bin:$PATH"
SERVE_PORT="${PORT:-8000}"

echo "=== init-site.sh starting at $(date) ==="
echo "PORT=$SERVE_PORT USER=$(whoami)"
echo "bench=$(which bench 2>/dev/null || echo NOT_FOUND)"
echo "mysqladmin=$(which mysqladmin 2>/dev/null || echo NOT_FOUND)"
echo "mysql=$(which mysql 2>/dev/null || echo NOT_FOUND)"

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

echo "SITE=$SITE DB=$DB_HOST:$DB_PORT/$DB_NAME"

cd "${BENCH_DIR}"

# Update common_site_config.json
python3 -c "
import json
p = '${BENCH_DIR}/sites/common_site_config.json'
try: c = json.load(open(p))
except: c = {}
c['redis_cache'] = '${REDIS_CACHE}'
c['redis_queue'] = '${REDIS_QUEUE}'
c['redis_socketio'] = '${REDIS_QUEUE}'
json.dump(c, open(p, 'w'), indent=2)
print('common_site_config.json updated')
"

# Test MariaDB connectivity BEFORE starting gunicorn
echo "=== Testing MariaDB connectivity ==="
for i in 1 2 3 4 5; do
    if mysqladmin ping -h"$DB_HOST" -P"$DB_PORT" --silent 2>/dev/null; then
        echo "MariaDB ping OK on attempt $i"
        break
    else
        echo "MariaDB ping failed (attempt $i): $(mysqladmin ping -h"$DB_HOST" -P"$DB_PORT" 2>&1)"
        sleep 5
    fi
done

# Test Python DB connection
echo "=== Testing Python DB connection ==="
python3 -c "
import pymysql, sys
try:
    conn = pymysql.connect(host='${DB_HOST}', port=int('${DB_PORT}'), user='${DB_NAME}', password='${DB_PASSWORD}', database='${DB_NAME}', connect_timeout=10)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=\"${DB_NAME}\"')
    count = cursor.fetchone()[0]
    print(f'DB connection OK, table count: {count}')
    conn.close()
except Exception as e:
    print(f'DB connection FAILED: {e}')
" 2>&1

# Start gunicorn
echo "=== Starting gunicorn on port $SERVE_PORT ==="
/home/frappe/frappe-bench/env/bin/gunicorn \
    --chdir=/home/frappe/frappe-bench/sites \
    --bind=0.0.0.0:${SERVE_PORT} \
    --threads=4 \
    --workers=2 \
    --worker-class=gthread \
    --timeout=120 \
    frappe.app:application &
GUNICORN_PID=$!
echo "gunicorn PID=$GUNICORN_PID"

sleep 5
if kill -0 $GUNICORN_PID 2>/dev/null; then
    echo "gunicorn running OK"
else
    echo "ERROR: gunicorn died! Trying without worker class..."
    /home/frappe/frappe-bench/env/bin/gunicorn \
        --chdir=/home/frappe/frappe-bench/sites \
        --bind=0.0.0.0:${SERVE_PORT} \
        --timeout=120 \
        frappe.app:application &
    GUNICORN_PID=$!
    echo "gunicorn retry PID=$GUNICORN_PID"
    sleep 3
fi

# Run site setup in background
{
    echo "[bg] Starting site setup at $(date)"
    
    # Wait for MariaDB
    for i in $(seq 1 200); do
        if mysqladmin ping -h"$DB_HOST" -P"$DB_PORT" --silent 2>/dev/null; then
            echo "[bg] MariaDB ready (attempt $i)"
            break
        fi
        [ $i -eq 200 ] && echo "[bg] ERROR: MariaDB timeout" && exit 1
        [ $((i % 20)) -eq 0 ] && echo "[bg] Waiting for MariaDB (attempt $i)..."
        sleep 3
    done

    # Check table count via Python
    TABLE_COUNT=$(python3 -c "
import pymysql
try:
    conn = pymysql.connect(host='${DB_HOST}', port=int('${DB_PORT}'), user='${DB_NAME}', password='${DB_PASSWORD}', database='${DB_NAME}', connect_timeout=10)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=\"${DB_NAME}\"')
    print(cursor.fetchone()[0])
    conn.close()
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1)
    echo "[bg] Table count: '$TABLE_COUNT'"

    if echo "$TABLE_COUNT" | grep -qE '^[0-9]+$' && [ "$TABLE_COUNT" -gt "10" ] 2>/dev/null; then
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
} &

echo "Background setup PID=$!"

wait $GUNICORN_PID
echo "gunicorn exited: $?"
