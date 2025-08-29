#!/usr/bin/env python3
"""
Fix PostgreSQL schemas by properly quoting column names with spaces and special characters
"""

import sqlite3
import psycopg2
import os
import yaml

def load_config():
    """Load the database configuration"""
    with open('database-config.yml', 'r') as f:
        return yaml.safe_load(f)

def sqlite_type_to_postgres(sqlite_type: str) -> str:
    """Convert SQLite types to PostgreSQL types"""
    sqlite_type = sqlite_type.upper()
    
    if 'INT' in sqlite_type:
        return 'INTEGER'
    elif 'REAL' in sqlite_type or 'FLOAT' in sqlite_type or 'DOUBLE' in sqlite_type:
        return 'DECIMAL(10,2)'
    elif 'TEXT' in sqlite_type or 'CHAR' in sqlite_type or 'VARCHAR' in sqlite_type:
        return 'TEXT'
    elif 'BLOB' in sqlite_type:
        return 'BYTEA'
    elif 'DATE' in sqlite_type:
        return 'DATE'
    else:
        return 'TEXT'

def quote_identifier(name: str) -> str:
    """Quote PostgreSQL identifiers that need quoting"""
    # PostgreSQL reserved words that need quoting
    reserved_words = {
        'cross', 'match', 'order', 'group', 'having', 'where', 'select',
        'from', 'join', 'inner', 'outer', 'left', 'right', 'full', 'union',
        'intersect', 'except', 'all', 'distinct', 'case', 'when', 'then',
        'else', 'end', 'if', 'null', 'true', 'false', 'and', 'or', 'not',
        'in', 'exists', 'between', 'like', 'ilike', 'similar', 'is'
    }

    # Quote if contains spaces, parentheses, percent signs, starts with number, or is reserved word
    if (' ' in name or '(' in name or ')' in name or '%' in name or
        name[0].isdigit() or '-' in name or name.lower() in reserved_words):
        return f'"{name}"'
    return name

def create_postgres_table(db_name: str, table_name: str, sqlite_path: str, descriptions_path: str):
    """Create a PostgreSQL table from SQLite schema with proper quoting"""
    
    # Connect to SQLite to get schema
    sqlite_conn = sqlite3.connect(sqlite_path)
    cursor = sqlite_conn.cursor()
    
    # Get table info
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = cursor.fetchall()
    
    # Load column descriptions
    descriptions = {}
    desc_file = os.path.join(descriptions_path, f'{table_name}.csv')
    if os.path.exists(desc_file):
        try:
            with open(desc_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[1:]:  # Skip header
                    if ',' in line:
                        col_name, desc = line.strip().split(',', 1)
                        descriptions[col_name] = desc
        except UnicodeDecodeError:
            try:
                with open(desc_file, 'r', encoding='latin-1') as f:
                    lines = f.readlines()
                    for line in lines[1:]:  # Skip header
                        if ',' in line:
                            col_name, desc = line.strip().split(',', 1)
                            descriptions[col_name] = desc
            except Exception as e:
                print(f"Warning: Could not read description file {desc_file}: {e}")
        except Exception as e:
            print(f"Warning: Could not read description file {desc_file}: {e}")
    
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(
        host='localhost',
        port=5434,
        database=db_name,
        user='thoth_user',
        password='thoth_password'
    )
    pg_cursor = pg_conn.cursor()

    # Check if table already exists
    pg_cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = %s
        )
    """, (table_name,))
    table_exists = pg_cursor.fetchone()[0]

    if table_exists:
        print(f"  Table {table_name} already exists, skipping creation")
        pg_conn.close()
        sqlite_conn.close()
        return
    
    # Create table SQL
    sql = f"CREATE TABLE {table_name} (\n"
    column_defs = []
    pk_columns = []
    
    for col in columns:
        col_name = col[1]
        col_type = sqlite_type_to_postgres(col[2])
        not_null = "NOT NULL" if col[3] else ""
        is_pk = col[5]
        
        quoted_name = quote_identifier(col_name)
        column_def = f"    {quoted_name} {col_type} {not_null}".strip()
        column_defs.append(column_def)
        
        if is_pk:
            pk_columns.append(quoted_name)
    
    sql += ",\n".join(column_defs)
    
    if pk_columns:
        sql += f",\n    PRIMARY KEY ({', '.join(pk_columns)})"
    
    sql += "\n);"
    
    print(f"Creating table {table_name}...")
    print(sql)
    
    try:
        pg_cursor.execute(sql)
        pg_conn.commit()
        print(f"✓ Table {table_name} created successfully")
        
        # Add column comments
        for col_name, description in descriptions.items():
            quoted_name = quote_identifier(col_name)
            comment_sql = f"COMMENT ON COLUMN {table_name}.{quoted_name} IS '{description}';"
            try:
                pg_cursor.execute(comment_sql)
                pg_conn.commit()
            except Exception as e:
                print(f"Warning: Could not add comment for {col_name}: {e}")
        
        print(f"✓ Comments added for {table_name}")
        
    except Exception as e:
        print(f"✗ Error creating table {table_name}: {e}")
        pg_conn.rollback()
    
    sqlite_conn.close()
    pg_conn.close()

def main():
    config = load_config()
    base_path = config['base_path']

    for db_name, db_config in config['databases'].items():
        if not db_config['enabled']:
            print(f"Skipping disabled database: {db_name}")
            continue

        print(f"\nProcessing database: {db_name}")

        sqlite_path = os.path.join(base_path, db_config['sqlite_file'])
        descriptions_path = os.path.join(base_path, db_config['description_dir'])

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
            create_postgres_table(db_name, table_name, sqlite_path, descriptions_path)

if __name__ == "__main__":
    main()
