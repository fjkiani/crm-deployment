#!/bin/bash
# =============================================================================
# init-site.sh
# Runs inside the frappe-web container on every startup.
# Fully idempotent — safe to run on restarts.
#
# bench init is done at Docker BUILD time (Dockerfile.frappe).
# This script only handles:
#   1. Wait for MariaDB to be ready
#   2. Configure Redis URLs in common_site_config.json
#   3. If site does not exist → bench new-site + install-app crm + migrate
#   4. If site exists         → bench migrate (applies any new patches)
#   5. Set default site
#   6. Generate EAIA API key if not already present (printed to logs)
#   7. Hand off to bench serve
# =============================================================================

set -e

# bench is installed system-wide at /usr/local/bin/bench
export PATH="/usr/local/bin:/home/frappe/frappe-bench/env/bin:$PATH"

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

echo "[init-site] bench dir: ${BENCH_DIR}"
echo "[init-site] site: ${SITE}"
echo "[init-site] db: ${DB_HOST}:${DB_PORT}"

# Verify bench is available (it was installed at build time)
if ! command -v bench &>/dev/null; then
    echo "[init-site] ERROR: bench not found in PATH. Check Dockerfile.frappe."
    exit 1
fi

# ---------------------------------------------------------------------------
# 1. Wait for MariaDB
# ---------------------------------------------------------------------------
echo "[init-site] Waiting for MariaDB at ${DB_HOST}:${DB_PORT}..."
until mysqladmin ping -h"$DB_HOST" -P"$DB_PORT" --silent 2>/dev/null; do
    echo "[init-site] MariaDB not ready — retrying in 3s..."
    sleep 3
done
echo "[init-site] MariaDB is up."

cd "${BENCH_DIR}"

# ---------------------------------------------------------------------------
# 2. Configure Redis URLs in common_site_config.json
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
# 3. Create site or migrate existing
# ---------------------------------------------------------------------------
if [ ! -d "${BENCH_DIR}/sites/${SITE}" ]; then
    echo "[init-site] Site '${SITE}' not found — creating (this takes ~2 min)..."

    bench new-site "$SITE" \
        --db-name "$DB_NAME" \
        --db-password "$DB_PASSWORD" \
        --admin-password "$ADMIN_PASSWORD" \
        --db-host "$DB_HOST" \
        --db-port "$DB_PORT" \
        --no-mariadb-socket \
        ${ENCRYPTION_KEY:+--encryption-key "$ENCRYPTION_KEY"}

    echo "[init-site] Installing CRM app into site..."
    bench --site "$SITE" install-app crm

    echo "[init-site] Running migrations..."
    bench --site "$SITE" migrate

    echo "[init-site] Site '${SITE}' created and CRM installed."
else
    echo "[init-site] Site '${SITE}' already exists — running migrate only."
    bench --site "$SITE" migrate || echo "[init-site] migrate skipped (non-fatal)"
fi

# ---------------------------------------------------------------------------
# 4. Set default site
# ---------------------------------------------------------------------------
bench use "$SITE"

# ---------------------------------------------------------------------------
# 5. Generate API key for the EAIA agent (idempotent)
# ---------------------------------------------------------------------------
echo "[init-site] Checking EAIA API credentials..."
EAIA_USER="${EAIA_API_USER:-Administrator}"

API_KEY=$(bench --site "$SITE" execute frappe.core.doctype.user.user.generate_keys \
    --args "['${EAIA_USER}']" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('api_key',''))
except Exception:
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
