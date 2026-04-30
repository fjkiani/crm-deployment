#!/bin/bash
# =============================================================================
# init-site.sh
# Runs inside the frappe-web container on every startup.
# Idempotent: safe to run on restarts — skips init if site already exists.
#
# Flow:
#   1. Wait for MariaDB to be ready
#   2. If site does not exist → new-site + install-app crm + migrate
#   3. If site exists         → bench migrate (applies any new patches)
#   4. Generate EAIA API key if not already present (printed to logs)
#   5. Hand off to bench serve
# =============================================================================

set -e

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

cd "$BENCH_DIR"

# ---------------------------------------------------------------------------
# 1. Wait for MariaDB
# ---------------------------------------------------------------------------
echo "[init-site] Waiting for MariaDB at ${DB_HOST}:${DB_PORT}..."
until mysqladmin ping -h"$DB_HOST" -P"$DB_PORT" --silent 2>/dev/null; do
    echo "[init-site] MariaDB not ready — retrying in 3s..."
    sleep 3
done
echo "[init-site] MariaDB is up."

# ---------------------------------------------------------------------------
# 2. Write common_site_config.json (Redis URLs, etc.)
#    This is safe to overwrite on every boot — it contains no secrets.
# ---------------------------------------------------------------------------
cat > sites/common_site_config.json <<EOF
{
    "background_workers": 1,
    "redis_cache": "${REDIS_CACHE}",
    "redis_queue": "${REDIS_QUEUE}",
    "redis_socketio": "${REDIS_CACHE}",
    "serve_default_site": true,
    "webserver_port": 8000,
    "socketio_port": 9000,
    "db_host": "${DB_HOST}",
    "db_port": ${DB_PORT}
}
EOF

# ---------------------------------------------------------------------------
# 3. Create site if it does not exist
# ---------------------------------------------------------------------------
if [ ! -f "sites/${SITE}/site_config.json" ]; then
    echo "[init-site] Site '${SITE}' not found — creating..."

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
    echo "[init-site] Site '${SITE}' already exists — running migrate only."
    bench --site "$SITE" migrate
fi

# ---------------------------------------------------------------------------
# 4. Set default site
# ---------------------------------------------------------------------------
bench use "$SITE"

# ---------------------------------------------------------------------------
# 5. Generate API key for the EAIA agent (idempotent — skips if already set)
#    The key is printed to stdout so it can be captured from container logs.
# ---------------------------------------------------------------------------
echo "[init-site] Checking EAIA API credentials..."
EAIA_USER="${EAIA_API_USER:-Administrator}"

API_KEY=$(bench --site "$SITE" execute frappe.core.doctype.user.user.generate_keys \
    --args "['${EAIA_USER}']" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('api_key',''))
except:
    pass
" 2>/dev/null || echo "")

if [ -n "$API_KEY" ]; then
    echo ""
    echo "================================================================"
    echo "  EAIA API CREDENTIALS (set these as env vars in eaia-agent)"
    echo "  FRAPPE_API_KEY=${API_KEY}"
    echo "  FRAPPE_API_SECRET=<see Frappe user settings for ${EAIA_USER}>"
    echo "================================================================"
    echo ""
fi

# ---------------------------------------------------------------------------
# 6. Start Frappe web server
# ---------------------------------------------------------------------------
echo "[init-site] Starting bench serve on port 8000..."
exec bench serve --port 8000
