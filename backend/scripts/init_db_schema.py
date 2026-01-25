import os
import sys
import psycopg2
from psycopg2 import sql

def init_db_schema():
    """
    Initialize the database schema if it doesn't exist.
    Uses environment variables for connection validation.
    """
    # check if we are in auto creation mode or not
    auto_create = os.environ.get("AUTO_CREATE_SCHEMA", "false").lower() == "true"
    if not auto_create:
        print("Skipping schema initialization (AUTO_CREATE_SCHEMA is not true)")
        return

    print("Initializing database schema...")

    dbname = os.environ.get("DB_NAME")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT", "5432")
    schema = os.environ.get("DB_SCHEMA")

    if not all([dbname, user, password, host, schema]):
        print("Missing required database environment variables for schema initialization.")
        print(f"DB_NAME: {dbname}, DB_USER: {user}, DB_HOST: {host}, DB_SCHEMA: {schema}")
        sys.exit(1)

    try:
        # Connect to the default database to create the schema
        # We assume the user has permissions to create schemas in the target DB
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            # Create schema if not exists
            print(f"Checking schema '{schema}'...")
            cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                sql.Identifier(schema)
            ))
            print(f"Schema '{schema}' ensured.")
            
        conn.close()
        print("Schema initialization completed successfully.")
        
    except Exception as e:
        print(f"Error initializing schema: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db_schema()
