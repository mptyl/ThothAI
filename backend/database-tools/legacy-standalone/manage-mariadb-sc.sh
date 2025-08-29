#!/bin/bash

# Management script for standalone MariaDB California Schools database
# This database is EXTERNAL to the Thoth project network

COMPOSE_FILE="standalone-mariadb-sc.yml"
CONTAINER_NAME="mariadb_sc"

case "$1" in
    start)
        echo "Starting standalone MariaDB for California Schools..."
        docker-compose -f $COMPOSE_FILE up -d
        echo "MariaDB started. Available at localhost:3307"
        echo "Adminer available at http://localhost:8082"
        ;;
    stop)
        echo "Stopping standalone MariaDB..."
        docker-compose -f $COMPOSE_FILE down
        ;;
    restart)
        echo "Restarting standalone MariaDB..."
        docker-compose -f $COMPOSE_FILE down
        docker-compose -f $COMPOSE_FILE up -d
        ;;
    status)
        echo "Checking MariaDB status..."
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        ;;
    logs)
        echo "Showing MariaDB logs..."
        docker logs $CONTAINER_NAME -f
        ;;
    connect)
        echo "Connecting to MariaDB..."
        docker exec -it $CONTAINER_NAME mariadb -u thoth_user -pthoth_password california_schools
        ;;
    import)
        echo "Importing California Schools data..."
        python3 import-california-schools-data.py
        ;;
    clean)
        echo "WARNING: This will remove the database and all data!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose -f $COMPOSE_FILE down
            docker volume rm thoth_mariadb_sc_data
            echo "Database removed."
        else
            echo "Operation cancelled."
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|connect|import|clean}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the MariaDB container"
        echo "  stop     - Stop the MariaDB container"
        echo "  restart  - Restart the MariaDB container"
        echo "  status   - Show container status"
        echo "  logs     - Show container logs"
        echo "  connect  - Connect to MariaDB CLI"
        echo "  import   - Import California Schools data"
        echo "  clean    - Remove database and all data (WARNING: destructive)"
        echo ""
        echo "Database Info:"
        echo "  Host: localhost:3307"
        echo "  Database: california_schools"
        echo "  User: thoth_user"
        echo "  Password: thoth_password"
        echo "  Adminer: http://localhost:8082"
        exit 1
        ;;
esac