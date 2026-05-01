#!/bin/bash
# =============================================================================
# init-site.sh
# 
# Strategy:
# 1. Start gunicorn immediately (returns 404 without site, but port is open)
# 2. Run site setup in background
# 3. When done, send SIGHUP to gunicorn to reload
# =============================================================================

export PATH="/usr/local/bin:/home/frappe/.local/bin:/home/frappe/frappe-bench/env/bin:$PATH"
SERVE_PORT="${PORT:-8000}"
LOG="/tmp/frappe-setup.log"

echo "=== init-site.sh starting at $(date) ===" | tee "$LOG"
echo "PORT=$SERVE_PORT USER=$(whoami)" | tee -a "$LOG"
echo "bench=$(which bench 2>/dev/null || echo NOT_FOUND)" | tee -a "$LOG"

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

echo "SITE=$SITE DB=$DB_HOST:$DB_PORT/$DB_NAME" | tee -a "$LOG"

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
" 2>&1 | tee -a "$LOG"

# Start gunicorn FIRST
echo "Starting gunicorn on port $SERVE_PORT..." | tee -a "$LOG"
/home/frappe/frappe-bench/env/bin/gunicorn \
    --chdir=/home/frappe/frappe-bench/sites \
    --bind=0.0.0.0:${SERVE_PORT} \
    --threads=4 \
    --workers=2 \
    --worker-class=gthread \
    --timeout=120 \
    frappe.app:application &
GUNICORN_PID=$!
echo "gunicorn PID=$GUNICORN_PID" | tee -a "$LOG"

sleep 5
if kill -0 $GUNICORN_PID 2>/dev/null; then
    echo "gunicorn running OK" | tee -a "$LOG"
else
    echo "ERROR: gunicorn died!" | tee -a "$LOG"
fi

# Write site setup script to a file and run it
cat > /tmp/setup_site.sh << SETUP_EOF
#!/bin/bash
export PATH="/usr/local/bin:/home/frappe/.local/bin:/home/frappe/frappe-bench/env/bin:\$PATH"
BENCH_DIR="${BENCH_DIR}"
SITE="${SITE}"
DB_HOST="${DB_HOST}"
DB_PORT="${DB_PORT}"
DB_NAME="${DB_NAME}"
DB_PASSWORD="${DB_PASSWORD}"
ADMIN_PASSWORD="${ADMIN_PASSWORD}"
ENCRYPTION_KEY="${ENCRYPTION_KEY}"
GUNICORN_PID="${GUNICORN_PID}"

echo "[bg] Starting at \$(date)"
echo "[bg] PATH=\$PATH"
echo "[bg] bench=\$(which bench 2>/dev/null || echo NOT_FOUND)"
echo "[bg] GUNICORN_PID=\$GUNICORN_PID"

cd "\$BENCH_DIR"

# Wait for MariaDB
echo "[bg] Waiting for MariaDB \$DB_HOST:\$DB_PORT..."
for i in \$(seq 1 200); do
    if python3 -c "
import pymysql, sys
try:
    conn = pymysql.connect(host='\$DB_HOST', port=int('\$DB_PORT'), user='\$DB_NAME', password='\$DB_PASSWORD', database='\$DB_NAME', connect_timeout=5)
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'DB error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
        echo "[bg] MariaDB ready (attempt \$i)"
        break
    fi
    [ \$i -eq 200 ] && echo "[bg] ERROR: MariaDB timeout" && exit 1
    [ \$((\$i % 10)) -eq 0 ] && echo "[bg] Waiting for MariaDB (attempt \$i)..."
    sleep 3
done

# Check table count
TABLE_COUNT=\$(python3 -c "
import pymysql
try:
    conn = pymysql.connect(host='\$DB_HOST', port=int('\$DB_PORT'), user='\$DB_NAME', password='\$DB_PASSWORD', database='\$DB_NAME', connect_timeout=10)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=\"\$DB_NAME\"')
    print(cursor.fetchone()[0])
    conn.close()
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1)
echo "[bg] Table count: '\$TABLE_COUNT'"

if echo "\$TABLE_COUNT" | grep -qE '^[0-9]+\$' && [ "\$TABLE_COUNT" -gt "50" ] 2>/dev/null; then
    echo "[bg] DB has \$TABLE_COUNT tables - restoring site config..."
    mkdir -p "\$BENCH_DIR/sites/\$SITE"
    python3 -c "
import json
cfg = {'db_name': '\$DB_NAME', 'db_password': '\$DB_PASSWORD', 'db_host': '\$DB_HOST', 'db_port': int('\$DB_PORT')}
if '\$ENCRYPTION_KEY': cfg['encryption_key'] = '\$ENCRYPTION_KEY'
json.dump(cfg, open('\$BENCH_DIR/sites/\$SITE/site_config.json', 'w'), indent=2)
print('[bg] site_config.json written')
"
    echo "[bg] Running migrate..."
    bench --site "\$SITE" migrate 2>&1
    echo "[bg] migrate exit: \$?"
    bench --site "\$SITE" set-admin-password "\$ADMIN_PASSWORD" 2>&1 || true
else
    echo "[bg] Fresh/partial DB (\$TABLE_COUNT tables) - dropping and reinstalling..."
    
    python3 -c "
import pymysql
conn = pymysql.connect(host='\$DB_HOST', port=int('\$DB_PORT'), user='\$DB_NAME', password='\$DB_PASSWORD', database='\$DB_NAME', connect_timeout=10)
cursor = conn.cursor()
cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
cursor.execute('SELECT table_name FROM information_schema.tables WHERE table_schema = \"\$DB_NAME\"')
tables = [row[0] for row in cursor.fetchall()]
print(f'[bg] Dropping {len(tables)} tables...')
for table in tables:
    cursor.execute(f'DROP TABLE IF EXISTS \`{table}\`')
cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
conn.commit()
conn.close()
print('[bg] All tables dropped')
" 2>&1
    
    mkdir -p "\$BENCH_DIR/sites/\$SITE"
    python3 -c "
import json
cfg = {'db_name': '\$DB_NAME', 'db_password': '\$DB_PASSWORD', 'db_host': '\$DB_HOST', 'db_port': int('\$DB_PORT')}
if '\$ENCRYPTION_KEY': cfg['encryption_key'] = '\$ENCRYPTION_KEY'
json.dump(cfg, open('\$BENCH_DIR/sites/\$SITE/site_config.json', 'w'), indent=2)
print('[bg] site_config.json written')
"
    
    echo "[bg] Installing frappe app..."
    bench --site "\$SITE" install-app frappe 2>&1
    echo "[bg] install-app frappe exit: \$?"
    
    echo "[bg] Installing crm app..."
    bench --site "\$SITE" install-app crm 2>&1
    echo "[bg] install-app crm exit: \$?"
    
    bench --site "\$SITE" set-admin-password "\$ADMIN_PASSWORD" 2>&1 || true
fi

bench use "\$SITE" 2>&1
echo "[bg] Site setup done at \$(date)"
kill -HUP \$GUNICORN_PID 2>/dev/null && echo "[bg] Sent SIGHUP to gunicorn" || echo "[bg] SIGHUP failed"
SETUP_EOF

chmod +x /tmp/setup_site.sh
echo "Setup script written to /tmp/setup_site.sh" | tee -a "$LOG"

# Run setup script in background
bash /tmp/setup_site.sh >> "$LOG" 2>&1 &
echo "Background setup PID=$!" | tee -a "$LOG"

# Keep gunicorn running
wait $GUNICORN_PID
echo "gunicorn exited: $?" | tee -a "$LOG"
