#!/bin/bash
# Frappe scheduler — runs from the bench directory
set -e
cd /home/frappe/frappe-bench
bench use "${FRAPPE_SITE_NAME:-crm-frappe-web.onrender.com}"
exec bench schedule
