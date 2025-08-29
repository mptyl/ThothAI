#!/usr/bin/env python3
"""
Management script for thoth-test-dbs unified database pool
Provides easy commands to start, stop, status check, and manage the database setup
"""

import subprocess
import sys
import time
import argparse
import yaml
import requests
from typing import Dict, List

CONFIG_FILE = "database-config.yml"
COMPOSE_FILE = "thoth-test-dbs.yml"

def load_config() -> dict:
    """Load the database configuration"""
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

def run_command(cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command"""
    if capture_output:
        return subprocess.run(cmd, capture_output=True, text=True)
    else:
        return subprocess.run(cmd)

def start_services():
    """Start all database services"""
    print("Starting thoth-test-dbs services...")
    result = run_command(['docker-compose', '-f', COMPOSE_FILE, 'up', '-d'], capture_output=False)
    if result.returncode == 0:
        print("Services started successfully")
        print("Waiting for services to be ready...")
        time.sleep(10)
        check_health()
    else:
        print("Failed to start services")
        return False
    return True

def stop_services():
    """Stop all database services"""
    print("Stopping thoth-test-dbs services...")
    result = run_command(['docker-compose', '-f', COMPOSE_FILE, 'down'])
    if result.returncode == 0:
        print("Services stopped successfully")
    else:
        print("Failed to stop services")
        return False
    return True

def restart_services():
    """Restart all database services"""
    print("Restarting thoth-test-dbs services...")
    stop_services()
    time.sleep(2)
    start_services()

def check_status():
    """Check status of all services"""
    print("Checking service status...")
    result = run_command(['docker-compose', '-f', COMPOSE_FILE, 'ps'])
    print(result.stdout)

def check_health():
    """Check health of all database services"""
    config = load_config()
    
    print("Checking database health...")
    
    # Check MariaDB
    if config['servers']['mariadb']['enabled']:
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host='localhost',
                port=config['servers']['mariadb']['port'],
                user=config['shared']['username'],
                password=config['shared']['password'],
                connect_timeout=5
            )
            conn.close()
            print("✓ MariaDB: Healthy")
        except Exception as e:
            print(f"✗ MariaDB: Unhealthy ({e})")
    
    # Check MySQL
    if config['servers']['mysql']['enabled']:
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host='localhost',
                port=config['servers']['mysql']['port'],
                user=config['shared']['username'],
                password=config['shared']['password'],
                connect_timeout=5
            )
            conn.close()
            print("✓ MySQL: Healthy")
        except Exception as e:
            print(f"✗ MySQL: Unhealthy ({e})")
    
    # Check PostgreSQL
    if config['servers']['postgres']['enabled']:
        try:
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                port=config['servers']['postgres']['port'],
                user=config['shared']['username'],
                password=config['shared']['password'],
                database='postgres',
                connect_timeout=5
            )
            conn.close()
            print("✓ PostgreSQL: Healthy")
        except Exception as e:
            print(f"✗ PostgreSQL: Unhealthy ({e})")
    
    # Note: SQL Server and Oracle health checks disabled - using external cloud servers
    # Schema generation and data import scripts are still available for these databases
    
    # Check Supabase
    if config['servers']['supabase']['enabled']:
        try:
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                port=config['servers']['supabase']['port'],
                user='supabase_admin',
                password='thoth_password',
                database='postgres',
                connect_timeout=5
            )
            conn.close()
            print("✓ Supabase: Healthy")
        except Exception as e:
            print(f"✗ Supabase: Unhealthy ({e})")
    
    # Check Adminer
    try:
        response = requests.get(f"http://localhost:{config['shared']['adminer_port']}", timeout=5)
        if response.status_code == 200:
            print("✓ Adminer: Healthy")
        else:
            print(f"✗ Adminer: Unhealthy (HTTP {response.status_code})")
    except Exception as e:
        print(f"✗ Adminer: Unhealthy ({e})")
    
    # Check PostgREST (if PostgreSQL is enabled)
    if config['servers']['postgres']['enabled']:
        try:
            response = requests.get("http://localhost:3100", timeout=5)
            if response.status_code in [200, 404]:  # 404 is normal for root path
                print("✓ PostgREST: Healthy")
            else:
                print(f"✗ PostgREST: Unhealthy (HTTP {response.status_code})")
        except Exception as e:
            print(f"✗ PostgREST: Unhealthy ({e})")
    
    # Check Supabase REST API (if Supabase is enabled)
    if config['servers']['supabase']['enabled']:
        try:
            response = requests.get(f"http://localhost:{config['servers']['supabase']['rest_port']}", timeout=5)
            if response.status_code in [200, 400, 404]:  # 400 is normal for missing auth roles, 404 is normal for root path
                print("✓ Supabase REST API: Healthy")
            else:
                print(f"✗ Supabase REST API: Unhealthy (HTTP {response.status_code})")
        except Exception as e:
            print(f"✗ Supabase REST API: Unhealthy ({e})")

def show_logs(service: str = None):
    """Show logs for services"""
    if service:
        print(f"Showing logs for {service}...")
        run_command(['docker-compose', '-f', COMPOSE_FILE, 'logs', '-f', service], capture_output=False)
    else:
        print("Showing logs for all services...")
        run_command(['docker-compose', '-f', COMPOSE_FILE, 'logs', '-f'], capture_output=False)

def generate_schemas():
    """Generate database schemas"""
    print("Generating database schemas...")
    result = run_command(['python', 'generate-all-schemas.py'])
    if result.returncode == 0:
        print("Schema generation completed")
        print(result.stdout)
    else:
        print("Schema generation failed")
        print(result.stderr)

def import_data():
    """Import data to databases"""
    print("Importing data to databases...")
    result = run_command(['python', 'import-all-data.py'])
    if result.returncode == 0:
        print("Data import completed")
        print(result.stdout)
    else:
        print("Data import failed")
        print(result.stderr)

def setup_all():
    """Complete setup: start services, generate schemas, import data"""
    print("Running complete thoth-test-dbs setup...")
    
    if not start_services():
        return False
    
    print("\nWaiting for databases to be fully ready...")
    time.sleep(30)
    
    generate_schemas()
    
    print("\nWaiting before importing data...")
    time.sleep(10)
    
    import_data()
    
    print("\nSetup completed! Access points:")
    config = load_config()
    print(f"- Adminer: http://localhost:{config['shared']['adminer_port']}")
    if config['servers']['postgres']['enabled']:
        print("- PostgREST API: http://localhost:3100")
    if config['servers']['supabase']['enabled']:
        print(f"- Supabase REST API: http://localhost:{config['servers']['supabase']['rest_port']}")
    print(f"- MariaDB: localhost:{config['servers']['mariadb']['port']}")
    if config['servers']['mysql']['enabled']:
        print(f"- MySQL: localhost:{config['servers']['mysql']['port']}")
    print(f"- PostgreSQL: localhost:{config['servers']['postgres']['port']}")
    if config['servers']['supabase']['enabled']:
        print(f"- Supabase: localhost:{config['servers']['supabase']['port']}")
    print("- SQL Server: External cloud server (schemas available)")
    print("- Oracle: External cloud server (schemas available)")

def show_config():
    """Show current configuration"""
    config = load_config()
    
    print("Current thoth-test-dbs configuration:")
    print(f"Base path: {config['base_path']}")
    
    print("\nEnabled databases:")
    for db_name, db_config in config['databases'].items():
        if db_config['enabled']:
            print(f"  ✓ {db_name}: {db_config['description']}")
    
    print("\nDisabled databases:")
    for db_name, db_config in config['databases'].items():
        if not db_config['enabled']:
            print(f"  ✗ {db_name}: {db_config['description']}")
    
    print("\nEnabled servers:")
    for server_name, server_config in config['servers'].items():
        if server_config['enabled']:
            print(f"  ✓ {server_name}: localhost:{server_config['port']}")

def main():
    parser = argparse.ArgumentParser(description='Manage thoth-test-dbs unified database pool')
    parser.add_argument('command', choices=[
        'start', 'stop', 'restart', 'status', 'health', 'logs', 
        'generate-schemas', 'import-data', 'setup', 'config'
    ], help='Command to execute')
    parser.add_argument('--service', help='Specific service for logs command')
    
    args = parser.parse_args()
    
    if args.command == 'start':
        start_services()
    elif args.command == 'stop':
        stop_services()
    elif args.command == 'restart':
        restart_services()
    elif args.command == 'status':
        check_status()
    elif args.command == 'health':
        check_health()
    elif args.command == 'logs':
        show_logs(args.service)
    elif args.command == 'generate-schemas':
        generate_schemas()
    elif args.command == 'import-data':
        import_data()
    elif args.command == 'setup':
        setup_all()
    elif args.command == 'config':
        show_config()

if __name__ == "__main__":
    main()