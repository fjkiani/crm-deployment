#!/bin/bash
# Grant root access from any host (needed for bench new-site from frappe-web)
# This runs on first MariaDB startup via docker-entrypoint-initdb.d/

mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}' WITH GRANT OPTION;
FLUSH PRIVILEGES;
SELECT user, host FROM mysql.user WHERE user='root';
"
echo "Root access granted from any host"
