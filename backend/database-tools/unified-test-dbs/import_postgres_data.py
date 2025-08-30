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
Import data from SQLite to PostgreSQL with proper column name handling
"""

import sqlite3
import psycopg2
import os
import yaml
from typing import List, Tuple

def load_config():
    """Load the database configuration"""
    with open('database-config.yml', 'r') as f:
        return yaml.safe_load(f)

def quote_identifier(name: str) -> str:
    """Quote PostgreSQL identifiers that need quoting"""
    if (' ' in name or '(' in name or ')' in name or '%' in name or 
        name[0].isdigit() or '-' in name):
        return f'"{name}"'
    return name

def import_table_data(db_name: str, table_name: str, sqlite_path: str):
    """Import data from SQLite table to PostgreSQL table"""

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cursor = sqlite_conn.cursor()

    # Get column info from SQLite
    sqlite_cursor.execute(f'PRAGMA table_info({table_name})')
    columns_info = sqlite_cursor.fetchall()
    sqlite_column_names = [col[1] for col in columns_info]

    # Connect to PostgreSQL to get the actual column names
    pg_conn = psycopg2.connect(
        host='localhost',
        port=5434,
        database=db_name,
        user='thoth_user',
        password='thoth_password'
    )
    pg_cursor = pg_conn.cursor()

    # Get PostgreSQL column names in the correct order
    # PostgreSQL converts unquoted table names to lowercase
    pg_cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name.lower(),))
    pg_column_names = [row[0] for row in pg_cursor.fetchall()]

    # Quote the PostgreSQL column names for the INSERT statement
    quoted_columns = [quote_identifier(name) for name in pg_column_names]

    print(f"  SQLite columns: {len(sqlite_column_names)}")
    print(f"  PostgreSQL columns: {len(pg_column_names)}")

    if len(sqlite_column_names) != len(pg_column_names):
        print(f"  ✗ Column count mismatch: SQLite has {len(sqlite_column_names)}, PostgreSQL has {len(pg_column_names)}")
        sqlite_conn.close()
        pg_conn.close()
        return
    
    # Get all data
    sqlite_cursor.execute(f'SELECT * FROM {table_name}')
    rows = sqlite_cursor.fetchall()

    print(f"  Importing {len(rows)} rows to {table_name}...")

    if not rows:
        print(f"  No data found in {table_name}")
        sqlite_conn.close()
        pg_conn.close()
        return
    
    try:
        # Clear existing data
        pg_cursor.execute(f'DELETE FROM {table_name}')
        
        # Prepare insert statement - use VALUES without column names to avoid quoting issues
        placeholders = ', '.join(['%s'] * len(pg_column_names))
        insert_sql = f'INSERT INTO {table_name} VALUES ({placeholders})'

        print(f"  Using INSERT statement: {insert_sql}")
        
        # Insert data in batches
        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            try:
                pg_cursor.executemany(insert_sql, batch)
                pg_conn.commit()
                print(f"    Inserted batch {i//batch_size + 1}/{(len(rows) + batch_size - 1)//batch_size}")
            except Exception as batch_error:
                print(f"    Error in batch {i//batch_size + 1}: {batch_error}")
                # Try inserting rows one by one to identify problematic rows
                pg_conn.rollback()
                success_count = 0
                for j, row in enumerate(batch):
                    try:
                        pg_cursor.execute(insert_sql, row)
                        pg_conn.commit()
                        success_count += 1
                    except Exception as row_error:
                        print(f"      Error in row {i + j + 1}: {row_error}")
                        print(f"      Row data length: {len(row)}, expected: {len(pg_column_names)}")
                        pg_conn.rollback()
                print(f"    Successfully inserted {success_count}/{len(batch)} rows from batch")
        
        print(f"  ✓ Successfully imported {len(rows)} rows to {table_name}")
        
    except Exception as e:
        print(f"  ✗ Error importing to {table_name}: {e}")
        pg_conn.rollback()
    
    sqlite_conn.close()
    pg_conn.close()

def main():
    config = load_config()
    base_path = config['base_path']

    # Process all enabled databases
    for db_name, db_config in config['databases'].items():
        if not db_config['enabled']:
            print(f"Skipping disabled database: {db_name}")
            continue

        print(f"\nImporting data to PostgreSQL database: {db_name}")

        sqlite_path = os.path.join(base_path, db_config['sqlite_file'])

        if not os.path.exists(sqlite_path):
            print(f"SQLite file not found: {sqlite_path}")
            continue

        # Get table names from SQLite
        sqlite_conn = sqlite3.connect(sqlite_path)
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        sqlite_conn.close()

        print(f"Found tables: {tables}")

        for table_name in tables:
            import_table_data(db_name, table_name, sqlite_path)

if __name__ == "__main__":
    main()
