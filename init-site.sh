#!/bin/bash
# =============================================================================
# init-site.sh
# 
# Strategy:
# 1. Start gunicorn immediately (returns 404 without site, but port is open)
# 2. Run site setup in background
# 3. When done, send SIGHUP to gunicorn to reload
# =============================================================================

export PATH="/usr/local/bin:/home/frappe/frappe-bench/env/bin:$PATH"
SERVE_PORT="${PORT:-8000}"

echo "=== init-site.sh starting at $(date) ==="
echo "PORT=$SERVE_PORT USER=$(whoami)"

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

# Start gunicorn FIRST (without --preload so it starts even without a site)
echo "Starting gunicorn on port $SERVE_PORT..."
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
    echo "ERROR: gunicorn died! Trying simpler config..."
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
    echo "[bg] Site setup starting at $(date)"
    
    # Wait for MariaDB
    echo "[bg] Waiting for MariaDB $DB_HOST:$DB_PORT..."
    for i in $(seq 1 200); do
        if python3 -c "
import pymysql, sys
try:
    conn = pymysql.connect(host='${DB_HOST}', port=int('${DB_PORT}'), user='${DB_NAME}', password='${DB_PASSWORD}', database='${DB_NAME}', connect_timeout=5)
    conn.close()
    sys.exit(0)
except: sys.exit(1)
" 2>/dev/null; then
            echo "[bg] MariaDB ready (attempt $i)"
            break
        fi
        [ $i -eq 200 ] && echo "[bg] ERROR: MariaDB timeout" && exit 1
        [ $((i % 20)) -eq 0 ] && echo "[bg] Waiting for MariaDB (attempt $i)..."
        sleep 3
    done

    # Check table count
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

    if echo "$TABLE_COUNT" | grep -qE '^[0-9]+$' && [ "$TABLE_COUNT" -gt "50" ] 2>/dev/null; then
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
        bench --site "$SITE" set-admin-password "$ADMIN_PASSWORD" 2>&1 || true
    else
        echo "[bg] Fresh/partial DB ($TABLE_COUNT tables) - dropping and reinstalling..."
        
        python3 -c "
import pymysql
conn = pymysql.connect(host='${DB_HOST}', port=int('${DB_PORT}'), user='${DB_NAME}', password='${DB_PASSWORD}', database='${DB_NAME}', connect_timeout=10)
cursor = conn.cursor()
cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
cursor.execute('SELECT table_name FROM information_schema.tables WHERE table_schema = \"${DB_NAME}\"')
tables = [row[0] for row in cursor.fetchall()]
print(f'[bg] Dropping {len(tables)} tables...')
for table in tables:
    cursor.execute(f'DROP TABLE IF EXISTS \`{table}\`')
cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
conn.commit()
conn.close()
print('[bg] All tables dropped')
" 2>&1
        
        mkdir -p "${BENCH_DIR}/sites/${SITE}"
        python3 -c "
import json
cfg = {'db_name': '${DB_NAME}', 'db_password': '${DB_PASSWORD}', 'db_host': '${DB_HOST}', 'db_port': int('${DB_PORT}')}
if '${ENCRYPTION_KEY}': cfg['encryption_key'] = '${ENCRYPTION_KEY}'
json.dump(cfg, open('${BENCH_DIR}/sites/${SITE}/site_config.json', 'w'), indent=2)
print('[bg] site_config.json written')
"
        
        echo "[bg] Installing Frappe..."
        bench --site "$SITE" install-app frappe 2>&1
        echo "[bg] install-app frappe exit: $?"
        
        echo "[bg] Installing CRM..."
        bench --site "$SITE" install-app crm 2>&1
        echo "[bg] install-app crm exit: $?"
        
        bench --site "$SITE" set-admin-password "$ADMIN_PASSWORD" 2>&1 || true
    fi

    bench use "$SITE" 2>&1
    echo "[bg] Site setup done at $(date)"
    
    # Reload gunicorn
    echo "[bg] Sending SIGHUP to gunicorn PID=$GUNICORN_PID..."
    kill -HUP $GUNICORN_PID 2>/dev/null && echo "[bg] SIGHUP sent" || echo "[bg] SIGHUP failed"
} &

echo "Background setup PID=$!"

# Keep gunicorn running
wait $GUNICORN_PID
echo "gunicorn exited: $?"
