#!/bin/bash
# =============================================================================
# build_site.sh — runs at Docker BUILD TIME (not runtime)
#
# 1. Starts a local MariaDB instance
# 2. Runs bench new-site against it (creates all DocType tables)
# 3. Installs the CRM app
# 4. Dumps the database to db_seed.sql.gz
# 5. Stops MariaDB
#
# The dump is baked into the image. At runtime, frappe_starter.py restores
# it against the real MariaDB in seconds instead of running migrations.
# =============================================================================
set -e

BENCH_DIR="/home/frappe/frappe-bench"
BUILD_SITE="build.localhost"
BUILD_DB="frappe_build"
BUILD_DB_PASS="build_pass_123"
BUILD_ROOT_PASS="build_root_123"
DUMP_PATH="${BENCH_DIR}/sites/db_seed.sql.gz"

echo "=== [build_site.sh] Starting local MariaDB ==="

# Initialize MariaDB data directory
mysql_install_db --user=mysql --datadir=/var/lib/mysql > /dev/null 2>&1 || true

# Start MariaDB in background
mysqld_safe --user=mysql --skip-networking=0 --bind-address=127.0.0.1 &
MYSQL_PID=$!

# Wait for MariaDB to be ready
echo "Waiting for MariaDB..."
for i in $(seq 1 60); do
    if mysqladmin ping -h 127.0.0.1 -u root --silent 2>/dev/null; then
        echo "MariaDB ready after ${i}s"
        break
    fi
    sleep 2
done

# Set root password and create DB user
mysql -h 127.0.0.1 -u root <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED BY '${BUILD_ROOT_PASS}';
CREATE USER IF NOT EXISTS '${BUILD_DB}'@'%' IDENTIFIED BY '${BUILD_DB_PASS}';
GRANT ALL PRIVILEGES ON \`${BUILD_DB}\`.* TO '${BUILD_DB}'@'%';
FLUSH PRIVILEGES;
EOF

echo "=== [build_site.sh] Running bench new-site (this takes ~90 min) ==="

# Write common_site_config.json with dummy Redis (bench new-site doesn't need Redis)
cat > "${BENCH_DIR}/sites/common_site_config.json" <<EOF
{
  "redis_cache": "redis://localhost:13000",
  "redis_queue": "redis://localhost:11000",
  "redis_socketio": "redis://localhost:11000"
}
EOF

# Run bench new-site as frappe user
su -s /bin/bash frappe -c "
    cd ${BENCH_DIR} && \
    /usr/local/bin/bench new-site ${BUILD_SITE} \
        --db-name ${BUILD_DB} \
        --db-password ${BUILD_DB_PASS} \
        --admin-password admin \
        --db-host 127.0.0.1 \
        --db-port 3306 \
        --mariadb-user-host-login-scope '%' \
        --db-root-password ${BUILD_ROOT_PASS} \
        --verbose \
        --force
"

echo "=== [build_site.sh] bench new-site complete ==="

echo "=== [build_site.sh] Installing CRM app ==="
su -s /bin/bash frappe -c "
    cd ${BENCH_DIR} && \
    /usr/local/bin/bench --site ${BUILD_SITE} install-app crm
"
echo "=== [build_site.sh] CRM app installed ==="

echo "=== [build_site.sh] Dumping database to ${DUMP_PATH} ==="
mysqldump \
    -h 127.0.0.1 \
    -u root \
    -p"${BUILD_ROOT_PASS}" \
    --single-transaction \
    --routines \
    --triggers \
    "${BUILD_DB}" \
    | gzip > "${DUMP_PATH}"

echo "=== [build_site.sh] Dump size: $(du -sh ${DUMP_PATH} | cut -f1) ==="

# Write metadata so frappe_starter.py knows what was built
cat > "${BENCH_DIR}/sites/db_seed_meta.json" <<EOF
{
  "build_site": "${BUILD_SITE}",
  "build_db": "${BUILD_DB}",
  "dump_path": "${DUMP_PATH}",
  "apps": ["frappe", "erpnext", "crm"],
  "built_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

# Stop MariaDB
kill $MYSQL_PID 2>/dev/null || true
wait $MYSQL_PID 2>/dev/null || true

echo "=== [build_site.sh] Done. DB seed baked into image. ==="
