#!/bin/bash
# Frappe background worker — runs from the bench directory
# Render sets FRAPPE_SITE_NAME; bench use sets the default site for this process
set -e
cd /home/frappe/frappe-bench
bench use "${FRAPPE_SITE_NAME:-crm-frappe-web.onrender.com}"
exec bench worker --queue long,default,short
