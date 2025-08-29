#!/bin/bash

# Management script for standalone Supabase California Schools database
# This database is EXTERNAL to the Thoth project network

COMPOSE_FILE="standalone-supabase-sc.yml"
CONTAINER_NAME="supabase_db"

case "$1" in
    start)
        echo "Starting standalone Supabase for California Schools..."
        docker-compose -f $COMPOSE_FILE up -d
        echo "Supabase PostgreSQL started. Available at localhost:5433"
        echo "PostgREST API available at http://localhost:3000"
        echo "Adminer available at http://localhost:8085"
        ;;
    stop)
        echo "Stopping standalone Supabase..."
        docker-compose -f $COMPOSE_FILE down
        ;;
    restart)
        echo "Restarting standalone Supabase..."
        docker-compose -f $COMPOSE_FILE down
        docker-compose -f $COMPOSE_FILE up -d
        ;;
    status)
        echo "Checking Supabase status..."
        docker ps --filter "name=supabase" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        ;;
    logs)
        echo "Showing Supabase logs..."
        docker logs $CONTAINER_NAME -f
        ;;
    connect)
        echo "Connecting to PostgreSQL..."
        docker exec -it $CONTAINER_NAME psql -U thoth_user -d california_schools
        ;;
    api)
        echo "Testing PostgREST API..."
        echo "Schools count:"
        curl -s "http://localhost:3000/schools?select=count" | jq
        echo ""
        echo "Sample schools:"
        curl -s "http://localhost:3000/schools?select=School,District,County&limit=5" | jq
        ;;
    clean)
        echo "WARNING: This will remove the database and all data!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose -f $COMPOSE_FILE down
            docker volume rm thoth-supabase_supabase_db_data
            echo "Database removed."
        else
            echo "Operation cancelled."
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|connect|api|clean}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the Supabase containers"
        echo "  stop     - Stop the Supabase containers"
        echo "  restart  - Restart the Supabase containers"
        echo "  status   - Show container status"
        echo "  logs     - Show PostgreSQL logs"
        echo "  connect  - Connect to PostgreSQL CLI"
        echo "  api      - Test PostgREST API endpoints"
        echo "  clean    - Remove database and all data (WARNING: destructive)"
        echo ""
        echo "Database Info:"
        echo "  PostgreSQL: localhost:5433"
        echo "  Database: california_schools"
        echo "  User: thoth_user"
        echo "  Password: thoth_password"
        echo "  PostgREST API: http://localhost:3000"
        echo "  Adminer: http://localhost:8085"
        exit 1
        ;;
esac