#!/bin/bash

# Management script for standalone SQL Server California Schools database
# This database is EXTERNAL to the Thoth project network

COMPOSE_FILE="standalone-sqlserver-sc.yml"
CONTAINER_NAME="sqlserver_sc"

case "$1" in
    start)
        echo "Starting standalone SQL Server for California Schools..."
        docker-compose -f $COMPOSE_FILE up -d
        echo "SQL Server started. Available at localhost:1433"
        echo "Adminer available at http://localhost:8083"
        ;;
    stop)
        echo "Stopping standalone SQL Server..."
        docker-compose -f $COMPOSE_FILE down
        ;;
    restart)
        echo "Restarting standalone SQL Server..."
        docker-compose -f $COMPOSE_FILE down
        docker-compose -f $COMPOSE_FILE up -d
        ;;
    status)
        echo "Checking SQL Server status..."
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        ;;
    logs)
        echo "Showing SQL Server logs..."
        docker logs $CONTAINER_NAME -f
        ;;
    connect)
        echo "Connecting to SQL Server..."
        docker exec -it $CONTAINER_NAME /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P ThothPassword2024!
        ;;
    clean)
        echo "WARNING: This will remove the database and all data!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose -f $COMPOSE_FILE down
            docker volume rm thoth-sqlserver_sqlserver_sc_data
            echo "Database removed."
        else
            echo "Operation cancelled."
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|connect|clean}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the SQL Server container"
        echo "  stop     - Stop the SQL Server container"
        echo "  restart  - Restart the SQL Server container"
        echo "  status   - Show container status"
        echo "  logs     - Show container logs"
        echo "  connect  - Connect to SQL Server CLI"
        echo "  clean    - Remove database and all data (WARNING: destructive)"
        echo ""
        echo "Database Info:"
        echo "  Host: localhost:1433"
        echo "  Database: california_schools"
        echo "  User: sa"
        echo "  Password: ThothPassword2024!"
        echo "  Adminer: http://localhost:8083"
        exit 1
        ;;
esac