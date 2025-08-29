#!/bin/bash

# Master management script for all standalone California Schools databases
# MariaDB, SQL Server, Oracle, and Supabase - all EXTERNAL to Thoth project

DATABASES=("mariadb" "sqlserver" "oracle" "supabase")

show_help() {
    echo "Usage: $0 [database] [command]"
    echo ""
    echo "Databases:"
    echo "  mariadb    - MariaDB on port 3307 (Adminer: 8082)"
    echo "  sqlserver  - SQL Server on port 1433 (Adminer: 8083)"
    echo "  oracle     - Oracle XE on port 1521 (Adminer: 8084)"
    echo "  supabase   - PostgreSQL on port 5433 (Adminer: 8085, API: 3000)"
    echo "  all        - All databases"
    echo ""
    echo "Commands:"
    echo "  start      - Start database(s)"
    echo "  stop       - Stop database(s)"
    echo "  restart    - Restart database(s)"
    echo "  status     - Show status of database(s)"
    echo "  clean      - Remove database(s) and all data (WARNING: destructive)"
    echo ""
    echo "Examples:"
    echo "  $0 mariadb start     - Start only MariaDB"
    echo "  $0 all status        - Show status of all databases"
    echo "  $0 supabase api      - Test Supabase API (special command)"
    echo ""
    echo "Individual Management Scripts:"
    echo "  ./manage-mariadb-sc.sh"
    echo "  ./manage-sqlserver-sc.sh"
    echo "  ./manage-oracle-sc.sh"
    echo "  ./manage-supabase-sc.sh"
}

execute_command() {
    local db=$1
    local cmd=$2
    
    case $db in
        mariadb)
            ./manage-mariadb-sc.sh $cmd
            ;;
        sqlserver)
            ./manage-sqlserver-sc.sh $cmd
            ;;
        oracle)
            ./manage-oracle-sc.sh $cmd
            ;;
        supabase)
            if [[ $cmd == "api" ]]; then
                ./manage-supabase-sc.sh api
            else
                ./manage-supabase-sc.sh $cmd
            fi
            ;;
        *)
            echo "Unknown database: $db"
            return 1
            ;;
    esac
}

if [[ $# -eq 0 ]]; then
    show_help
    exit 1
fi

DATABASE=$1
COMMAND=$2

if [[ -z $COMMAND ]]; then
    echo "Error: Command is required"
    show_help
    exit 1
fi

case $DATABASE in
    all)
        case $COMMAND in
            start|stop|restart|status)
                for db in "${DATABASES[@]}"; do
                    echo "=== $db ==="
                    execute_command $db $COMMAND
                    echo ""
                done
                ;;
            clean)
                echo "WARNING: This will remove ALL databases and data!"
                read -p "Are you sure? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    for db in "${DATABASES[@]}"; do
                        echo "=== Cleaning $db ==="
                        execute_command $db clean
                        echo ""
                    done
                else
                    echo "Operation cancelled."
                fi
                ;;
            *)
                echo "Command '$COMMAND' not supported for 'all'"
                exit 1
                ;;
        esac
        ;;
    mariadb|sqlserver|oracle|supabase)
        execute_command $DATABASE $COMMAND
        ;;
    *)
        echo "Unknown database: $DATABASE"
        show_help
        exit 1
        ;;
esac