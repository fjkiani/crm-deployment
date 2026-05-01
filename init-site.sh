#!/bin/bash
# =============================================================================
# init-site.sh
# 
# Runs frappe_starter.py which:
# 1. Starts health check server immediately (port 10000)
# 2. Runs site setup in background thread
# 3. Switches to gunicorn when done
# =============================================================================

export PATH="/usr/local/bin:/home/frappe/.local/bin:/home/frappe/frappe-bench/env/bin:$PATH"

echo "=== init-site.sh starting at $(date) ==="
echo "PORT=${PORT:-8000} USER=$(whoami)"
echo "python3=$(which python3 2>/dev/null || echo NOT_FOUND)"

exec python3 /home/frappe/frappe_starter.py
