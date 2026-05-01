#!/bin/bash
# Grant root access from any host (needed for bench new-site from frappe-web)
# This runs on first MariaDB startup via docker-entrypoint-initdb.d/
# Note: $MYSQL_ROOT_PASSWORD is available as an environment variable

echo "Granting root access from any host..."
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
SELECT user, host FROM mysql.user WHERE user='root';
"
echo "Root access granted from any host"
