#!/bin/bash
# =============================================================================
# init-site.sh
# 
# Strategy:
# 1. Start a minimal HTTP server immediately (returns 200 for health check)
# 2. Do site setup in background
# 3. When site setup is done, switch to gunicorn
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

# ---------------------------------------------------------------------------
# Start a minimal HTTP server immediately for Render's health check
# This returns 200 OK for all requests while site setup is in progress
# ---------------------------------------------------------------------------
echo "Starting minimal HTTP server on port $SERVE_PORT for health check..."
python3 -c "
import http.server, socketserver, threading, os, sys

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Frappe CRM - Site setup in progress...\n')
    def log_message(self, format, *args):
        pass  # Suppress access logs

PORT = int(os.environ.get('PORT', 8000))
httpd = socketserver.TCPServer(('0.0.0.0', PORT), Handler)
httpd.allow_reuse_address = True
print(f'Health check server listening on port {PORT}')
sys.stdout.flush()
httpd.serve_forever()
" &
HEALTH_PID=$!
echo "Health check server PID=$HEALTH_PID"
sleep 2

# ---------------------------------------------------------------------------
# Site setup (runs synchronously, then switches to gunicorn)
# ---------------------------------------------------------------------------
echo "=== Starting site setup at $(date) ==="

# Wait for MariaDB
echo "Waiting for MariaDB at $DB_HOST:$DB_PORT..."
for i in $(seq 1 200); do
    if python3 -c "
import pymysql, sys
try:
    conn = pymysql.connect(host='${DB_HOST}', port=int('${DB_PORT}'), user='${DB_NAME}', password='${DB_PASSWORD}', database='${DB_NAME}', connect_timeout=5)
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'DB error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
        echo "MariaDB ready (attempt $i)"
        break
    fi
    [ $i -eq 200 ] && echo "ERROR: MariaDB timeout after 10 minutes" && break
    [ $((i % 20)) -eq 0 ] && echo "Still waiting for MariaDB (attempt $i)..."
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
echo "Table count: '$TABLE_COUNT'"

if echo "$TABLE_COUNT" | grep -qE '^[0-9]+$' && [ "$TABLE_COUNT" -gt "10" ] 2>/dev/null; then
    echo "DB has $TABLE_COUNT tables - restoring site config..."
    mkdir -p "${BENCH_DIR}/sites/${SITE}"
    python3 -c "
import json
cfg = {'db_name': '${DB_NAME}', 'db_password': '${DB_PASSWORD}', 'db_host': '${DB_HOST}', 'db_port': int('${DB_PORT}')}
if '${ENCRYPTION_KEY}': cfg['encryption_key'] = '${ENCRYPTION_KEY}'
json.dump(cfg, open('${BENCH_DIR}/sites/${SITE}/site_config.json', 'w'), indent=2)
print('site_config.json written')
"
    bench --site "$SITE" migrate 2>&1 || echo "migrate had errors (may be ok)"
else
    echo "Running bench new-site..."
    ARGS=(new-site "$SITE" --db-name "$DB_NAME" --db-password "$DB_PASSWORD" \
          --admin-password "$ADMIN_PASSWORD" --db-host "$DB_HOST" --db-port "$DB_PORT" \
          --no-mariadb-socket --force)
    [ -n "$DB_ROOT_PASSWORD" ] && ARGS+=(--db-root-password "$DB_ROOT_PASSWORD")
    [ -n "$ENCRYPTION_KEY" ] && ARGS+=(--encryption-key "$ENCRYPTION_KEY")
    
    bench "${ARGS[@]}" 2>&1
    echo "bench new-site exit: $?"
    bench --site "$SITE" install-app crm 2>&1
    bench --site "$SITE" migrate 2>&1
fi

bench use "$SITE" 2>&1
echo "=== Site setup done at $(date) ==="

# ---------------------------------------------------------------------------
# Stop health check server and start gunicorn
# ---------------------------------------------------------------------------
echo "Stopping health check server (PID=$HEALTH_PID)..."
kill $HEALTH_PID 2>/dev/null
sleep 1

echo "Starting gunicorn on port $SERVE_PORT..."
exec /home/frappe/frappe-bench/env/bin/gunicorn \
    --chdir=/home/frappe/frappe-bench/sites \
    --bind=0.0.0.0:${SERVE_PORT} \
    --threads=4 \
    --workers=2 \
    --worker-class=gthread \
    --timeout=120 \
    frappe.app:application
