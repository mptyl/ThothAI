#!/bin/bash

# Start MariaDB container for California Schools database
# This script starts the MariaDB container and waits for it to be ready

set -e

echo "[INFO] Starting MariaDB container for California Schools database..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "[ERROR] Docker is not running. Please start Docker first."
    exit 1
fi

# Start the container
echo "[INFO] Starting MariaDB container..."
docker-compose -f docker-compose-mariadb.yml up -d

# Wait for MariaDB to be ready
echo "⏳ Waiting for MariaDB to be ready..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if docker-compose -f docker-compose-mariadb.yml exec -T mariadb-california-schools mysqladmin ping -h localhost -u root -pthoth_root_password >/dev/null 2>&1; then
        echo "[SUCCESS] MariaDB is ready!"
        break
    fi
    
    echo "⏳ Attempt $attempt/$max_attempts - MariaDB not ready yet, waiting..."
    sleep 2
    ((attempt++))
done

if [ $attempt -gt $max_attempts ]; then
    echo "[ERROR] MariaDB failed to start within expected time"
    echo "📋 Container logs:"
    docker-compose -f docker-compose-mariadb.yml logs mariadb-california-schools
    exit 1
fi

# Show container status
echo "📊 Container status:"
docker-compose -f docker-compose-mariadb.yml ps

# Verify database setup
echo "🔍 Verifying database setup..."
docker-compose -f docker-compose-mariadb.yml exec -T mariadb-california-schools mysql -u thoth_user -pthoth_password california_schools -e "
SELECT 'Database verification:' as status;
SELECT table_name, table_rows 
FROM information_schema.tables 
WHERE table_schema = 'california_schools' 
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
"

echo ""
echo "🎉 MariaDB setup completed successfully!"
echo ""
echo "📊 To import the full California Schools dataset, run:"
echo "   python3 import-california-schools-data.py"
echo ""
echo "📝 Connection details:"
echo "   Host: localhost"
echo "   Port: 3307"
echo "   Database: california_schools"
echo "   Username: thoth_user"
echo "   Password: thoth_password"
echo ""
echo "🌐 Access Adminer (Web UI) at: http://localhost:8081"
echo "   Server: mariadb-california-schools:3306"
echo "   Username: thoth_user"
echo "   Password: thoth_password"
echo "   Database: california_schools"
echo ""
echo "🛑 To stop the container: docker-compose -f docker-compose-mariadb.yml down"
echo "🗑️  To remove everything: docker-compose -f docker-compose-mariadb.yml down -v"