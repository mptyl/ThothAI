#!/usr/bin/env python3

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Unified data import script for thoth-test-dbs
Imports data from SQLite databases to all enabled target database servers
"""

import yaml
import sqlite3
import mysql.connector
import psycopg2
import pyodbc
import cx_Oracle
import os
import sys
from typing import Dict, List, Tuple

CONFIG_FILE = "database-config.yml"


def load_config() -> dict:
    """Load the database configuration"""
    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f)


def get_sqlite_data(sqlite_path: str, table_name: str) -> Tuple[List[str], List[Tuple]]:
    """Extract data from SQLite table"""
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns_info = cursor.fetchall()
    column_names = [col[1] for col in columns_info]

    # Get all data
    cursor.execute(f"SELECT * FROM {table_name}")
    data = cursor.fetchall()

    conn.close()
    return column_names, data


def get_sqlite_tables(sqlite_path: str) -> List[str]:
    """Get list of tables from SQLite database"""
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [row[0] for row in cursor.fetchall()]

    conn.close()
    return tables


def import_to_mariadb(
    db_name: str, tables_data: Dict[str, Tuple[List[str], List[Tuple]]], config: dict
):
    """Import data to MariaDB"""
    print("  Importing to MariaDB...")

    try:
        conn = mysql.connector.connect(
            host="localhost",
            port=config["servers"]["mariadb"]["port"],
            user=config["shared"]["username"],
            password=config["shared"]["password"],
            database=db_name,
            charset="utf8mb4",
        )
        cursor = conn.cursor()

        for table_name, (columns, data) in tables_data.items():
            if not data:
                continue

            # Clear existing data
            cursor.execute(f"DELETE FROM {table_name}")

            # Prepare insert statement
            placeholders = ", ".join(["%s"] * len(columns))
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            # Insert data in batches
            batch_size = 1000
            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]
                cursor.executemany(insert_sql, batch)
                conn.commit()

            print(f"    {table_name}: {len(data)} rows")

        cursor.close()
        conn.close()
        print("  MariaDB import completed")

    except Exception as e:
        print(f"  MariaDB import failed: {e}")


def import_to_mysql(
    db_name: str, tables_data: Dict[str, Tuple[List[str], List[Tuple]]], config: dict
):
    """Import data to MySQL"""
    print("  Importing to MySQL...")

    try:
        conn = mysql.connector.connect(
            host="localhost",
            port=config["servers"]["mysql"]["port"],
            user=config["shared"]["username"],
            password=config["shared"]["password"],
            database=db_name,
            charset="utf8mb4",
        )
        cursor = conn.cursor()

        for table_name, (columns, data) in tables_data.items():
            if not data:
                continue

            # Clear existing data
            cursor.execute(f"DELETE FROM {table_name}")

            # Prepare insert statement
            placeholders = ", ".join(["%s"] * len(columns))
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            # Insert data in batches
            batch_size = 1000
            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]
                cursor.executemany(insert_sql, batch)
                conn.commit()

            print(f"    {table_name}: {len(data)} rows")

        cursor.close()
        conn.close()
        print("  MySQL import completed")

    except Exception as e:
        print(f"  MySQL import failed: {e}")


def import_to_postgres(
    db_name: str, tables_data: Dict[str, Tuple[List[str], List[Tuple]]], config: dict
):
    """Import data to PostgreSQL"""
    print("  Importing to PostgreSQL...")

    try:
        conn = psycopg2.connect(
            host="localhost",
            port=config["servers"]["postgres"]["port"],
            user=config["shared"]["username"],
            password=config["shared"]["password"],
            database=db_name,
        )
        cursor = conn.cursor()

        for table_name, (columns, data) in tables_data.items():
            if not data:
                continue

            # Clear existing data
            cursor.execute(f"DELETE FROM {table_name}")

            # Quote column names for PostgreSQL
            quoted_columns = [f'"{col}"' for col in columns]
            placeholders = ", ".join(["%s"] * len(columns))
            insert_sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders})"

            # Insert data in batches
            batch_size = 1000
            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]
                cursor.executemany(insert_sql, batch)
                conn.commit()

            print(f"    {table_name}: {len(data)} rows")

        cursor.close()
        conn.close()
        print("  PostgreSQL import completed")

    except Exception as e:
        print(f"  PostgreSQL import failed: {e}")


def import_to_sqlserver(
    db_name: str, tables_data: Dict[str, Tuple[List[str], List[Tuple]]], config: dict
):
    """Import data to SQL Server"""
    print("  Importing to SQL Server...")

    try:
        # SQL Server connection string
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=localhost,{config['servers']['sqlserver']['port']};DATABASE={db_name};UID=sa;PWD=ThothPassword2024!"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        for table_name, (columns, data) in tables_data.items():
            if not data:
                continue

            # Clear existing data
            cursor.execute(f"DELETE FROM {table_name}")

            # Prepare insert statement
            placeholders = ", ".join(["?"] * len(columns))
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            # Insert data in batches
            batch_size = 1000
            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]
                cursor.executemany(insert_sql, batch)
                conn.commit()

            print(f"    {table_name}: {len(data)} rows")

        cursor.close()
        conn.close()
        print("  SQL Server import completed")

    except Exception as e:
        print(f"  SQL Server import failed: {e}")


def import_to_oracle(
    db_name: str, tables_data: Dict[str, Tuple[List[str], List[Tuple]]], config: dict
):
    """Import data to Oracle"""
    print("  Importing to Oracle...")

    try:
        # Oracle connection
        dsn = cx_Oracle.makedsn(
            "localhost", config["servers"]["oracle"]["port"], service_name="XE"
        )
        conn = cx_Oracle.connect(user="thoth_user", password="thoth_password", dsn=dsn)
        cursor = conn.cursor()

        for table_name, (columns, data) in tables_data.items():
            if not data:
                continue

            # Clear existing data
            cursor.execute(f"DELETE FROM {table_name}")

            # Prepare insert statement
            placeholders = ", ".join([":" + str(i + 1) for i in range(len(columns))])
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            # Insert data in batches
            batch_size = 1000
            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]
                cursor.executemany(insert_sql, batch)
                conn.commit()

            print(f"    {table_name}: {len(data)} rows")

        cursor.close()
        conn.close()
        print("  Oracle import completed")

    except Exception as e:
        print(f"  Oracle import failed: {e}")


def import_to_supabase(
    db_name: str, tables_data: Dict[str, Tuple[List[str], List[Tuple]]], config: dict
):
    """Import data to Supabase"""
    print("  Importing to Supabase...")

    try:
        conn = psycopg2.connect(
            host="localhost",
            port=config["servers"]["supabase"]["port"],
            user="supabase_admin",
            password="thoth_password",
            database=db_name,
        )
        cursor = conn.cursor()

        for table_name, (columns, data) in tables_data.items():
            if not data:
                continue

            # Clear existing data
            cursor.execute(f"DELETE FROM {table_name}")

            # Quote column names for PostgreSQL
            quoted_columns = []
            for col in columns:
                if " " in col or "(" in col or ")" in col or "%" in col:
                    quoted_columns.append(f'"{col}"')
                else:
                    quoted_columns.append(col)

            placeholders = ", ".join(["%s"] * len(columns))
            insert_sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders})"

            # Insert data in batches
            batch_size = 1000
            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]
                cursor.executemany(insert_sql, batch)
                conn.commit()

            print(f"    {table_name}: {len(data)} rows")

        cursor.close()
        conn.close()
        print("  Supabase import completed")

    except Exception as e:
        print(f"  Supabase import failed: {e}")


def main():
    """Main function to import data to all enabled databases"""
    config = load_config()
    base_path = config["base_path"]

    print("Importing data to thoth-test-dbs...")

    for db_name, db_config in config["databases"].items():
        if not db_config["enabled"]:
            print(f"Skipping {db_name} (disabled)")
            continue

        print(f"Processing {db_name}...")

        # Get SQLite path
        sqlite_path = os.path.join(base_path, db_config["sqlite_file"])

        if not os.path.exists(sqlite_path):
            print(f"  Warning: SQLite file not found: {sqlite_path}")
            continue

        # Get all tables and their data
        tables = get_sqlite_tables(sqlite_path)
        tables_data = {}

        for table_name in tables:
            columns, data = get_sqlite_data(sqlite_path, table_name)
            tables_data[table_name] = (columns, data)

        print(
            f"  Found {len(tables)} tables with {sum(len(data[1]) for data in tables_data.values())} total rows"
        )

        # Import to each enabled server
        servers = config["servers"]

        if servers["mariadb"]["enabled"]:
            import_to_mariadb(db_name, tables_data, config)

        if servers["mysql"]["enabled"]:
            import_to_mysql(db_name, tables_data, config)

        if servers["postgres"]["enabled"]:
            import_to_postgres(db_name, tables_data, config)

        if servers["sqlserver"]["enabled"]:
            import_to_sqlserver(db_name, tables_data, config)

        if servers["oracle"]["enabled"]:
            import_to_oracle(db_name, tables_data, config)

        if servers["supabase"]["enabled"]:
            import_to_supabase(db_name, tables_data, config)

    print("\nData import completed!")


if __name__ == "__main__":
    print("Note: This script requires the database containers to be running.")
    print("Run 'docker-compose -f thoth-test-dbs.yml up -d' first.")
    print()

    # Check for required Python packages
    required_packages = [
        "mysql-connector-python",
        "psycopg2-binary",
        "pyodbc",
        "cx_Oracle",
    ]
    missing_packages = []

    for package in required_packages:
        try:
            if package == "mysql-connector-python":
                import mysql.connector
            elif package == "psycopg2-binary":
                import psycopg2
            elif package == "pyodbc":
                import pyodbc
            elif package == "cx_Oracle":
                import cx_Oracle
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"Missing required packages: {', '.join(missing_packages)}")
        print(f"Install with: pip install {' '.join(missing_packages)}")
        sys.exit(1)

    main()
