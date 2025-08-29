#!/usr/bin/env python3
"""
Import data from SQLite to MySQL with proper column name handling
"""

import sqlite3
import mysql.connector
import os
import yaml
from typing import List, Tuple

def load_config():
    """Load the database configuration"""
    with open('database-config.yml', 'r') as f:
        return yaml.safe_load(f)

def quote_identifier(name: str) -> str:
    """Quote MySQL identifiers that need quoting"""
    if (' ' in name or '(' in name or ')' in name or '%' in name or 
        name[0].isdigit() or '-' in name):
        return f'`{name}`'
    return name

def import_table_data(db_name: str, table_name: str, sqlite_path: str):
    """Import data from SQLite table to MySQL table"""
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cursor = sqlite_conn.cursor()
    
    # Get column info from SQLite
    sqlite_cursor.execute(f'PRAGMA table_info({table_name})')
    columns_info = sqlite_cursor.fetchall()
    sqlite_column_names = [col[1] for col in columns_info]
    
    # Connect to MySQL
    mysql_conn = mysql.connector.connect(
        host='localhost',
        port=3309,
        database=db_name,
        user='root',
        password='thoth_root_password'
    )
    mysql_cursor = mysql_conn.cursor()
    
    # Get MySQL column names in the correct order
    mysql_cursor.execute(f"""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = '{db_name}' AND TABLE_NAME = '{table_name}'
        ORDER BY ORDINAL_POSITION
    """)
    mysql_column_names = [row[0] for row in mysql_cursor.fetchall()]
    
    # Quote the MySQL column names for the INSERT statement
    quoted_columns = [quote_identifier(name) for name in mysql_column_names]
    
    print(f"  SQLite columns: {len(sqlite_column_names)}")
    print(f"  MySQL columns: {len(mysql_column_names)}")
    
    if len(sqlite_column_names) != len(mysql_column_names):
        print(f"  ✗ Column count mismatch: SQLite has {len(sqlite_column_names)}, MySQL has {len(mysql_column_names)}")
        sqlite_conn.close()
        mysql_conn.close()
        return

    # Get all data
    sqlite_cursor.execute(f'SELECT * FROM {table_name}')
    rows = sqlite_cursor.fetchall()
    
    print(f"  Importing {len(rows)} rows to {table_name}...")
    
    if not rows:
        print(f"  No data found in {table_name}")
        sqlite_conn.close()
        mysql_conn.close()
        return

    try:
        # Clear existing data
        mysql_cursor.execute(f'DELETE FROM {quote_identifier(table_name)}')
        
        # Prepare insert statement
        placeholders = ', '.join(['%s'] * len(mysql_column_names))
        insert_sql = f'INSERT INTO {quote_identifier(table_name)} VALUES ({placeholders})'
        
        print(f"  Using INSERT statement: {insert_sql}")

        # Insert data in batches
        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            try:
                mysql_cursor.executemany(insert_sql, batch)
                mysql_conn.commit()
                print(f"    Inserted batch {i//batch_size + 1}/{(len(rows) + batch_size - 1)//batch_size}")
            except Exception as batch_error:
                print(f"    Error in batch {i//batch_size + 1}: {batch_error}")
                # Try inserting rows one by one to identify problematic rows
                mysql_conn.rollback()
                success_count = 0
                for j, row in enumerate(batch):
                    try:
                        mysql_cursor.execute(insert_sql, row)
                        mysql_conn.commit()
                        success_count += 1
                    except Exception as row_error:
                        print(f"      Error in row {i + j + 1}: {row_error}")
                        print(f"      Row data length: {len(row)}, expected: {len(mysql_column_names)}")
                        mysql_conn.rollback()
                print(f"    Successfully inserted {success_count}/{len(batch)} rows from batch")
        
        print(f"  ✓ Successfully imported {len(rows)} rows to {table_name}")
        
    except Exception as e:
        print(f"  ✗ Error importing to {table_name}: {e}")
        mysql_conn.rollback()
    
    sqlite_conn.close()
    mysql_conn.close()

def main():
    config = load_config()
    base_path = config['base_path']
    
    # Process all enabled databases
    for db_name, db_config in config['databases'].items():
        if not db_config['enabled']:
            print(f"Skipping disabled database: {db_name}")
            continue
        
        print(f"\nImporting data to MySQL database: {db_name}")
        
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
            # Skip SQLite-specific tables
            if table_name == 'sqlite_sequence':
                print(f"  Skipping SQLite-specific table: {table_name}")
                continue
            import_table_data(db_name, table_name, sqlite_path)

if __name__ == "__main__":
    main()
