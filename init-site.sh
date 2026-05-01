#!/bin/bash
# =============================================================================
# init-site.sh
# 
# Strategy:
# 1. Start gunicorn immediately (returns 404 without site, but port is open)
# 2. Run Python site setup script in background
# 3. When done, send SIGHUP to gunicorn to reload
# =============================================================================

export PATH="/usr/local/bin:/home/frappe/.local/bin:/home/frappe/frappe-bench/env/bin:$PATH"
SERVE_PORT="${PORT:-8000}"

echo "=== init-site.sh starting at $(date) ==="
echo "PORT=$SERVE_PORT USER=$(whoami)"
echo "bench=$(which bench 2>/dev/null || echo NOT_FOUND)"
echo "python3=$(which python3 2>/dev/null || echo NOT_FOUND)"

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

# Start gunicorn FIRST
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

# Run Python site setup script in background
export GUNICORN_PID
python3 /home/frappe/setup_frappe_site.py &
echo "Python setup script PID=$!"

# Keep gunicorn running
wait $GUNICORN_PID
echo "gunicorn exited: $?"
