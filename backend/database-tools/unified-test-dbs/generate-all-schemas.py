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
Unified schema generator for thoth-test-dbs
Reads database-config.yml and generates schemas for all enabled databases across all enabled servers
"""

import yaml
import sqlite3
import csv
import os
from typing import Dict, List, Tuple, Optional
from pathlib import Path

CONFIG_FILE = "database-config.yml"

def load_config() -> dict:
    """Load the database configuration"""
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

def read_column_descriptions(csv_file: str) -> Dict[str, str]:
    """Read column descriptions from CSV file"""
    descriptions = {}
    
    if not os.path.exists(csv_file):
        print(f"Warning: CSV file not found: {csv_file}")
        return descriptions
    
    try:
        # Try different encodings
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                with open(csv_file, 'r', encoding=encoding) as file:
                    reader = csv.DictReader(file)
                    
                    for row in reader:
                        original_column_name = row.get('original_column_name', '').strip()
                        column_description = row.get('column_description', '').strip()
                        
                        if original_column_name and column_description:
                            escaped_description = column_description.replace("'", "''")
                            descriptions[original_column_name] = escaped_description
                break
            except UnicodeDecodeError:
                continue
                    
    except Exception as e:
        print(f"Error reading {csv_file}: {e}")
    
    return descriptions

def get_sqlite_schema(sqlite_path: str) -> List[Tuple[str, str]]:
    """Extract table schemas from SQLite database"""
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()
    
    schemas = []
    for (table_name,) in tables:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        schemas.append((table_name, columns))
    
    conn.close()
    return schemas

def sqlite_type_to_mariadb(sqlite_type: str) -> str:
    """Convert SQLite types to MariaDB types"""
    sqlite_type = sqlite_type.upper()
    
    if 'INT' in sqlite_type:
        return 'INT'
    elif sqlite_type in ['REAL', 'FLOAT', 'DOUBLE']:
        return 'DECIMAL(10,2)'
    elif 'TEXT' in sqlite_type or 'CHAR' in sqlite_type:
        return 'TEXT'
    elif 'BLOB' in sqlite_type:
        return 'BLOB'
    elif 'DATE' in sqlite_type:
        return 'DATE'
    else:
        return 'TEXT'

def sqlite_type_to_mysql(sqlite_type: str) -> str:
    """Convert SQLite types to MySQL types"""
    sqlite_type = sqlite_type.upper()
    
    if 'INT' in sqlite_type:
        return 'INT'
    elif sqlite_type in ['REAL', 'FLOAT', 'DOUBLE']:
        return 'DECIMAL(10,2)'
    elif 'TEXT' in sqlite_type or 'CHAR' in sqlite_type:
        return 'TEXT'
    elif 'BLOB' in sqlite_type:
        return 'LONGBLOB'
    elif 'DATE' in sqlite_type:
        return 'DATE'
    else:
        return 'TEXT'

def sqlite_type_to_postgres(sqlite_type: str) -> str:
    """Convert SQLite types to PostgreSQL types"""
    sqlite_type = sqlite_type.upper()
    
    if 'INT' in sqlite_type:
        return 'INTEGER'
    elif sqlite_type in ['REAL', 'FLOAT', 'DOUBLE']:
        return 'DECIMAL(10,2)'
    elif 'TEXT' in sqlite_type or 'CHAR' in sqlite_type:
        return 'TEXT'
    elif 'BLOB' in sqlite_type:
        return 'BYTEA'
    elif 'DATE' in sqlite_type:
        return 'DATE'
    else:
        return 'TEXT'

def sqlite_type_to_sqlserver(sqlite_type: str) -> str:
    """Convert SQLite types to SQL Server types"""
    sqlite_type = sqlite_type.upper()
    
    if 'INT' in sqlite_type:
        return 'INT'
    elif sqlite_type in ['REAL', 'FLOAT', 'DOUBLE']:
        return 'DECIMAL(10,2)'
    elif 'TEXT' in sqlite_type or 'CHAR' in sqlite_type:
        return 'NVARCHAR(MAX)'
    elif 'BLOB' in sqlite_type:
        return 'VARBINARY(MAX)'
    elif 'DATE' in sqlite_type:
        return 'DATE'
    else:
        return 'NVARCHAR(MAX)'

def sqlite_type_to_oracle(sqlite_type: str) -> str:
    """Convert SQLite types to Oracle types"""
    sqlite_type = sqlite_type.upper()
    
    if 'INT' in sqlite_type:
        return 'NUMBER'
    elif sqlite_type in ['REAL', 'FLOAT', 'DOUBLE']:
        return 'NUMBER(10,2)'
    elif 'TEXT' in sqlite_type or 'CHAR' in sqlite_type:
        return 'CLOB'
    elif 'BLOB' in sqlite_type:
        return 'BLOB'
    elif 'DATE' in sqlite_type:
        return 'DATE'
    else:
        return 'CLOB'

def generate_mariadb_schema(db_name: str, schemas: List[Tuple], descriptions_by_table: Dict[str, Dict[str, str]]) -> str:
    """Generate MariaDB schema with comments"""
    sql = f"-- MariaDB schema for {db_name} database\n"
    sql += f"CREATE DATABASE IF NOT EXISTS {db_name};\n"
    sql += f"USE {db_name};\n\n"
    
    for table_name, columns in schemas:
        sql += f"CREATE TABLE {table_name} (\n"
        
        column_defs = []
        for col_info in columns:
            col_name = col_info[1]
            col_type = sqlite_type_to_mariadb(col_info[2])
            not_null = "NOT NULL" if col_info[3] else ""
            
            # Add comment if available
            comment = ""
            if table_name in descriptions_by_table and col_name in descriptions_by_table[table_name]:
                desc = descriptions_by_table[table_name][col_name]
                comment = f" COMMENT '{desc}'"
            
            column_def = f"{col_name} {col_type} {not_null}{comment}".strip()
            column_defs.append(column_def)
        
        # Add primary key constraint separately
        pk_columns = [col[1] for col in columns if col[5]]
        if pk_columns:
            if len(pk_columns) == 1:
                # Single column primary key - add to column definition
                for i, col_def in enumerate(column_defs):
                    if col_def.startswith(pk_columns[0]):
                        column_defs[i] = col_def.replace(col_def.split()[1], col_def.split()[1] + " PRIMARY KEY", 1)
                        break
            else:
                # Composite primary key - add as constraint
                column_defs.append(f"PRIMARY KEY ({', '.join(pk_columns)})")
        
        sql += ",\n".join(column_defs)
        sql += "\n);\n\n"
    
    return sql

def generate_mysql_schema(db_name: str, schemas: List[Tuple], descriptions_by_table: Dict[str, Dict[str, str]]) -> str:
    """Generate MySQL schema with comments"""
    sql = f"-- MySQL schema for {db_name} database\n"
    sql += f"CREATE DATABASE IF NOT EXISTS {db_name};\n"
    sql += f"USE {db_name};\n\n"
    
    for table_name, columns in schemas:
        sql += f"CREATE TABLE {table_name} (\n"
        
        column_defs = []
        for col_info in columns:
            col_name = col_info[1]
            col_type = sqlite_type_to_mysql(col_info[2])
            not_null = "NOT NULL" if col_info[3] else ""
            
            # Add comment if available
            comment = ""
            if table_name in descriptions_by_table and col_name in descriptions_by_table[table_name]:
                desc = descriptions_by_table[table_name][col_name]
                comment = f" COMMENT '{desc}'"
            
            column_def = f"{col_name} {col_type} {not_null}{comment}".strip()
            column_defs.append(column_def)
        
        # Add primary key constraint separately
        pk_columns = [col[1] for col in columns if col[5]]
        if pk_columns:
            if len(pk_columns) == 1:
                # Single column primary key - add to column definition
                for i, col_def in enumerate(column_defs):
                    if col_def.startswith(pk_columns[0]):
                        column_defs[i] = col_def.replace(col_def.split()[1], col_def.split()[1] + " PRIMARY KEY", 1)
                        break
            else:
                # Composite primary key - add as constraint
                column_defs.append(f"PRIMARY KEY ({', '.join(pk_columns)})")
        
        sql += ",\n".join(column_defs)
        sql += "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\n"
    
    return sql

def generate_postgres_schema(db_name: str, schemas: List[Tuple], descriptions_by_table: Dict[str, Dict[str, str]]) -> str:
    """Generate PostgreSQL schema with comments"""
    sql = f"-- PostgreSQL schema for {db_name} database\n"
    sql += f"CREATE DATABASE {db_name};\n"
    sql += f"\\c {db_name};\n\n"
    
    # Add extensions
    sql += 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";\n'
    sql += 'CREATE EXTENSION IF NOT EXISTS "pgcrypto";\n\n'
    
    for table_name, columns in schemas:
        sql += f"CREATE TABLE {table_name} (\n"
        
        column_defs = []
        for col_info in columns:
            col_name = col_info[1]
            col_type = sqlite_type_to_postgres(col_info[2])
            not_null = "NOT NULL" if col_info[3] else ""

            # Quote column names that contain spaces or special characters
            quoted_col_name = f'"{col_name}"' if ' ' in col_name or '(' in col_name or ')' in col_name or '%' in col_name else col_name
            column_def = f"    {quoted_col_name} {col_type} {not_null}".strip()
            column_defs.append(column_def)
        
        sql += ",\n".join(column_defs)
        
        # Add primary key constraint separately
        pk_columns = [f'"{col[1]}"' if ' ' in col[1] or '(' in col[1] or ')' in col[1] or '%' in col[1] else col[1] for col in columns if col[5]]
        if pk_columns:
            sql += f",\n    PRIMARY KEY ({', '.join(pk_columns)})"
        
        sql += "\n);\n\n"
        
        # Add column comments
        if table_name in descriptions_by_table:
            for col_name, description in descriptions_by_table[table_name].items():
                quoted_col_name = f'"{col_name}"' if ' ' in col_name or '(' in col_name or ')' in col_name or '%' in col_name else col_name
                sql += f"COMMENT ON COLUMN {table_name}.{quoted_col_name} IS '{description}';\n"
            sql += "\n"
    
    return sql

def generate_sqlserver_schema(db_name: str, schemas: List[Tuple], descriptions_by_table: Dict[str, Dict[str, str]]) -> str:
    """Generate SQL Server schema with extended properties"""
    sql = f"-- SQL Server schema for {db_name} database\\n"
    sql += f"CREATE DATABASE {db_name};\\n"
    sql += f"GO\\n"
    sql += f"USE {db_name};\\n"
    sql += f"GO\\n\\n"
    
    for table_name, columns in schemas:
        sql += f"CREATE TABLE {table_name} (\\n"
        
        column_defs = []
        for col_info in columns:
            col_name = col_info[1]
            col_type = sqlite_type_to_sqlserver(col_info[2])
            not_null = "NOT NULL" if col_info[3] else ""
            
            column_def = f"    {col_name} {col_type} {not_null}".strip()
            column_defs.append(column_def)
        
        sql += ",\\n".join(column_defs)
        
        # Add primary key constraint
        pk_columns = [col[1] for col in columns if col[5]]
        if pk_columns:
            sql += f",\\n    PRIMARY KEY ({', '.join(pk_columns)})"
        
        sql += "\\n);\\n"
        sql += "GO\\n\\n"
        
        # Add extended properties for descriptions
        if table_name in descriptions_by_table:
            for col_name, description in descriptions_by_table[table_name].items():
                sql += f"EXEC sp_addextendedproperty @name = N'MS_Description', "
                sql += f"@value = N'{description}', "
                sql += f"@level0type = N'SCHEMA', @level0name = N'dbo', "
                sql += f"@level1type = N'TABLE', @level1name = N'{table_name}', "
                sql += f"@level2type = N'COLUMN', @level2name = N'{col_name}';\\n"
            sql += "GO\\n\\n"
    
    return sql

def generate_oracle_schema(db_name: str, schemas: List[Tuple], descriptions_by_table: Dict[str, Dict[str, str]]) -> str:
    """Generate Oracle schema with comments"""
    sql = f"-- Oracle schema for {db_name} database\\n\\n"
    
    for table_name, columns in schemas:
        sql += f"CREATE TABLE {table_name} (\\n"
        
        column_defs = []
        for col_info in columns:
            col_name = col_info[1]
            col_type = sqlite_type_to_oracle(col_info[2])
            not_null = "NOT NULL" if col_info[3] else ""
            
            column_def = f"    {col_name} {col_type} {not_null}".strip()
            column_defs.append(column_def)
        
        sql += ",\\n".join(column_defs)
        
        # Add primary key constraint
        pk_columns = [col[1] for col in columns if col[5]]
        if pk_columns:
            sql += f",\\n    PRIMARY KEY ({', '.join(pk_columns)})"
        
        sql += "\\n);\\n\\n"
        
        # Add column comments
        if table_name in descriptions_by_table:
            for col_name, description in descriptions_by_table[table_name].items():
                sql += f"COMMENT ON COLUMN {table_name}.{col_name} IS '{description}';\\n"
            sql += "\\n"
    
    sql += "COMMIT;\\n"
    return sql

def generate_supabase_schema(db_name: str, schemas: List[Tuple], descriptions_by_table: Dict[str, Dict[str, str]]) -> str:
    """Generate Supabase PostgreSQL schema with additional features"""
    sql = f"-- Supabase PostgreSQL schema for {db_name} database\n"
    sql += f"CREATE DATABASE {db_name};\n"
    sql += f"\\c {db_name};\n\n"
    
    # Add Supabase extensions and schemas
    sql += '-- Enable Supabase extensions\n'
    sql += 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";\n'
    sql += 'CREATE EXTENSION IF NOT EXISTS "pgcrypto";\n'
    sql += 'CREATE EXTENSION IF NOT EXISTS "pgjwt";\n'
    sql += 'CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";\n\n'
    
    # Create auth schema for Supabase compatibility
    sql += '-- Create auth schema for Supabase compatibility\n'
    sql += 'CREATE SCHEMA IF NOT EXISTS auth;\n'
    sql += 'CREATE SCHEMA IF NOT EXISTS realtime;\n'
    sql += 'CREATE SCHEMA IF NOT EXISTS storage;\n\n'
    
    # Add Supabase auth functions
    sql += '-- Supabase auth functions\n'
    sql += 'CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid AS $$\n'
    sql += '  SELECT uuid_generate_v4()\n'
    sql += '$$ LANGUAGE sql STABLE;\n\n'
    
    sql += 'CREATE OR REPLACE FUNCTION auth.role() RETURNS text AS $$\n'
    sql += '  SELECT COALESCE(current_setting(\'request.jwt.claims\', true)::json->>\'role\', \'anon\')\n'
    sql += '$$ LANGUAGE sql STABLE;\n\n'
    
    # Create tables
    for table_name, columns in schemas:
        sql += f"CREATE TABLE {table_name} (\n"
        
        column_defs = []
        for col_info in columns:
            col_name = col_info[1]
            col_type = sqlite_type_to_postgres(col_info[2])
            not_null = "NOT NULL" if col_info[3] else ""
            
            # Quote column names for PostgreSQL
            if ' ' in col_name or '(' in col_name or ')' in col_name or '%' in col_name:
                quoted_column = f'"{col_name}"'
            else:
                quoted_column = col_name
            
            column_def = f"    {quoted_column} {col_type} {not_null}".strip()
            column_defs.append(column_def)
        
        sql += ",\n".join(column_defs)
        
        # Add primary key constraint
        pk_columns = [col[1] for col in columns if col[5]]
        if pk_columns:
            quoted_pk_columns = []
            for pk_col in pk_columns:
                if ' ' in pk_col or '(' in pk_col or ')' in pk_col or '%' in pk_col:
                    quoted_pk_columns.append(f'"{pk_col}"')
                else:
                    quoted_pk_columns.append(pk_col)
            sql += f",\n    PRIMARY KEY ({', '.join(quoted_pk_columns)})"
        
        sql += "\n);\n\n"
        
        # Enable Row Level Security for Supabase
        sql += f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;\n"
        
        # Create policies for read access
        sql += f'CREATE POLICY "Allow read access to {table_name}" ON {table_name} FOR SELECT USING (true);\n\n'
        
        # Add column comments
        if table_name in descriptions_by_table:
            for col_name, description in descriptions_by_table[table_name].items():
                if ' ' in col_name or '(' in col_name or ')' in col_name or '%' in col_name:
                    quoted_column = f'"{col_name}"'
                else:
                    quoted_column = col_name
                sql += f"COMMENT ON COLUMN {table_name}.{quoted_column} IS '{description}';\n"
            sql += "\n"
    
    return sql

def main():
    """Main function to generate all schemas"""
    config = load_config()
    base_path = config['base_path']
    
    print("Generating schemas for thoth-test-dbs...")
    
    for db_name, db_config in config['databases'].items():
        if not db_config['enabled']:
            print(f"Skipping {db_name} (disabled)")
            continue
            
        print(f"Processing {db_name}...")
        
        # Get paths
        sqlite_path = os.path.join(base_path, db_config['sqlite_file'])
        description_dir = os.path.join(base_path, db_config['description_dir'])
        
        if not os.path.exists(sqlite_path):
            print(f"  Warning: SQLite file not found: {sqlite_path}")
            continue
            
        # Extract schema from SQLite
        schemas = get_sqlite_schema(sqlite_path)
        
        # Load descriptions for all tables
        descriptions_by_table = {}
        if os.path.exists(description_dir):
            for csv_file in os.listdir(description_dir):
                if csv_file.endswith('.csv'):
                    table_name = csv_file[:-4]  # Remove .csv extension
                    csv_path = os.path.join(description_dir, csv_file)
                    descriptions_by_table[table_name] = read_column_descriptions(csv_path)
        
        # Generate schemas for each enabled server
        servers = config['servers']
        
        if servers['mariadb']['enabled']:
            mariadb_sql = generate_mariadb_schema(db_name, schemas, descriptions_by_table)
            with open(f"db-init/mariadb/{db_name}.sql", 'w') as f:
                f.write(mariadb_sql)
            print(f"  Generated MariaDB schema: db-init/mariadb/{db_name}.sql")
        
        if servers['mysql']['enabled']:
            mysql_sql = generate_mysql_schema(db_name, schemas, descriptions_by_table)
            with open(f"db-init/mysql/{db_name}.sql", 'w') as f:
                f.write(mysql_sql)
            print(f"  Generated MySQL schema: db-init/mysql/{db_name}.sql")
        
        if servers['postgres']['enabled']:
            postgres_sql = generate_postgres_schema(db_name, schemas, descriptions_by_table)
            with open(f"db-init/postgres/{db_name}.sql", 'w') as f:
                f.write(postgres_sql)
            print(f"  Generated PostgreSQL schema: db-init/postgres/{db_name}.sql")
        
        # Always generate SQL Server and Oracle schemas (for external cloud use)
        sqlserver_sql = generate_sqlserver_schema(db_name, schemas, descriptions_by_table)
        with open(f"db-init/sqlserver/{db_name}.sql", 'w') as f:
            f.write(sqlserver_sql)
        print(f"  Generated SQL Server schema: db-init/sqlserver/{db_name}.sql")
        
        oracle_sql = generate_oracle_schema(db_name, schemas, descriptions_by_table)
        with open(f"db-init/oracle/{db_name}.sql", 'w') as f:
            f.write(oracle_sql)
        print(f"  Generated Oracle schema: db-init/oracle/{db_name}.sql")
        
        if servers['supabase']['enabled']:
            supabase_sql = generate_supabase_schema(db_name, schemas, descriptions_by_table)
            with open(f"db-init/supabase/{db_name}.sql", 'w') as f:
                f.write(supabase_sql)
            print(f"  Generated Supabase schema: db-init/supabase/{db_name}.sql")
    
    print("\\nSchema generation completed!")

if __name__ == "__main__":
    main()