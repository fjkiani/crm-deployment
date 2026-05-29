#!/bin/bash
# Frappe background worker
# Waits for site_config.json to exist before starting — prevents crash-loop
# on first boot when frappe_starter.py hasn't finished site setup yet.
set -e

SITE="${FRAPPE_SITE_NAME:-crm.localhost}"
SITE_CONFIG="/home/frappe/frappe-bench/sites/${SITE}/site_config.json"

echo "[worker] Waiting for site_config.json at ${SITE_CONFIG}..."
for i in $(seq 1 120); do
  if [ -f "${SITE_CONFIG}" ]; then
    echo "[worker] site_config.json found after ${i} attempts (~$((i * 10))s)"
    break
  fi
  if [ "$i" -eq 120 ]; then
    echo "[worker] ERROR: site_config.json not found after 20 minutes — aborting"
    exit 1
  fi
  echo "[worker] Attempt ${i}/120: not ready yet, sleeping 10s..."
  sleep 10
done

cd /home/frappe/frappe-bench
bench use "${SITE}"
exec bench worker --queue long,default,short
