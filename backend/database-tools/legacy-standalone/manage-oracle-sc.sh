#!/bin/bash

# Management script for standalone Oracle California Schools database
# This database is EXTERNAL to the Thoth project network

COMPOSE_FILE="standalone-oracle-sc.yml"
CONTAINER_NAME="oracle_sc"

case "$1" in
    start)
        echo "Starting standalone Oracle for California Schools..."
        docker-compose -f $COMPOSE_FILE up -d
        echo "Oracle started. Available at localhost:1521"
        echo "Adminer available at http://localhost:8084"
        ;;
    stop)
        echo "Stopping standalone Oracle..."
        docker-compose -f $COMPOSE_FILE down
        ;;
    restart)
        echo "Restarting standalone Oracle..."
        docker-compose -f $COMPOSE_FILE down
        docker-compose -f $COMPOSE_FILE up -d
        ;;
    status)
        echo "Checking Oracle status..."
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        ;;
    logs)
        echo "Showing Oracle logs..."
        docker logs $CONTAINER_NAME -f
        ;;
    connect)
        echo "Connecting to Oracle..."
        docker exec -it $CONTAINER_NAME sqlplus thoth_user/thoth_password@localhost:1521/california_schools
        ;;
    clean)
        echo "WARNING: This will remove the database and all data!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose -f $COMPOSE_FILE down
            docker volume rm thoth-oracle_oracle_sc_data
            echo "Database removed."
        else
            echo "Operation cancelled."
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|connect|clean}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the Oracle container"
        echo "  stop     - Stop the Oracle container"
        echo "  restart  - Restart the Oracle container"
        echo "  status   - Show container status"
        echo "  logs     - Show container logs"
        echo "  connect  - Connect to Oracle SQL*Plus"
        echo "  clean    - Remove database and all data (WARNING: destructive)"
        echo ""
        echo "Database Info:"
        echo "  Host: localhost:1521"
        echo "  Database: california_schools"
        echo "  User: thoth_user"
        echo "  Password: thoth_password"
        echo "  SID: XE"
        echo "  Adminer: http://localhost:8084"
        exit 1
        ;;
esac