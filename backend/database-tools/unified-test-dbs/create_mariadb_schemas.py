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
Create MariaDB schemas with proper table structures and MariaDB-specific configurations
"""

import sqlite3
import mysql.connector
import os
import yaml


def load_config():
    """Load the database configuration"""
    with open("database-config.yml", "r") as f:
        return yaml.safe_load(f)


def sqlite_type_to_mariadb(sqlite_type: str, is_primary_key: bool = False) -> str:
    """Convert SQLite types to MariaDB types"""
    sqlite_type = sqlite_type.upper()

    if "INT" in sqlite_type:
        return "INT"
    elif "REAL" in sqlite_type or "FLOAT" in sqlite_type or "DOUBLE" in sqlite_type:
        return "DECIMAL(10,2)"
    elif "TEXT" in sqlite_type or "CHAR" in sqlite_type or "VARCHAR" in sqlite_type:
        # Use VARCHAR for primary keys to avoid key length issues
        if is_primary_key:
            return "VARCHAR(255)"
        return "TEXT"
    elif "BLOB" in sqlite_type:
        return "LONGBLOB"
    elif "DATE" in sqlite_type:
        return "DATE"
    else:
        # Use VARCHAR for primary keys to avoid key length issues
        if is_primary_key:
            return "VARCHAR(255)"
        return "TEXT"


def quote_identifier(name: str) -> str:
    """Quote MariaDB identifiers that need quoting"""
    # MariaDB reserved words that need quoting (similar to MySQL)
    reserved_words = {
        "cross",
        "match",
        "order",
        "group",
        "having",
        "where",
        "select",
        "from",
        "join",
        "inner",
        "outer",
        "left",
        "right",
        "full",
        "union",
        "intersect",
        "except",
        "all",
        "distinct",
        "case",
        "when",
        "then",
        "else",
        "end",
        "if",
        "null",
        "true",
        "false",
        "and",
        "or",
        "not",
        "in",
        "exists",
        "between",
        "like",
        "similar",
        "is",
        "key",
        "index",
        "primary",
        "foreign",
        "references",
        "constraint",
        "check",
        "default",
        "virtual",
        "rank",
        "status",
        "position",
        "time",
        "date",
        "year",
    }

    # Quote if contains spaces, parentheses, percent signs, starts with number, or is reserved word
    if (
        " " in name
        or "(" in name
        or ")" in name
        or "%" in name
        or name[0].isdigit()
        or "-" in name
        or name.lower() in reserved_words
    ):
        return f"`{name}`"
    return name


def create_mariadb_table(
    db_name: str, table_name: str, sqlite_path: str, descriptions_path: str
):
    """Create a MariaDB table from SQLite schema"""

    # Connect to SQLite to get schema
    sqlite_conn = sqlite3.connect(sqlite_path)
    cursor = sqlite_conn.cursor()

    # Get table info
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    # Load column descriptions
    descriptions = {}
    desc_file = os.path.join(descriptions_path, f"{table_name}.csv")
    if os.path.exists(desc_file):
        try:
            with open(desc_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[1:]:  # Skip header
                    if "," in line:
                        col_name, desc = line.strip().split(",", 1)
                        descriptions[col_name] = desc
        except UnicodeDecodeError:
            try:
                with open(desc_file, "r", encoding="latin-1") as f:
                    lines = f.readlines()
                    for line in lines[1:]:  # Skip header
                        if "," in line:
                            col_name, desc = line.strip().split(",", 1)
                            descriptions[col_name] = desc
            except Exception as e:
                print(f"Warning: Could not read description file {desc_file}: {e}")
        except Exception as e:
            print(f"Warning: Could not read description file {desc_file}: {e}")

    # Connect to MariaDB (using MySQL connector as MariaDB is MySQL-compatible)
    mariadb_conn = mysql.connector.connect(
        host="localhost",
        port=3308,
        database=db_name,
        user="root",
        password="thoth_root_password",
    )
    mariadb_cursor = mariadb_conn.cursor()

    # Check if table already exists
    mariadb_cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
    table_exists = mariadb_cursor.fetchone() is not None

    if table_exists:
        print(f"  Table {table_name} already exists, dropping and recreating")
        mariadb_cursor.execute(f"DROP TABLE {quote_identifier(table_name)}")
        mariadb_conn.commit()

    # Create table SQL
    sql = f"CREATE TABLE {quote_identifier(table_name)} (\n"
    column_defs = []
    pk_columns = []

    for col in columns:
        col_name = col[1]
        is_pk = col[5]
        col_type = sqlite_type_to_mariadb(col[2], is_pk)
        not_null = "NOT NULL" if col[3] else ""

        quoted_name = quote_identifier(col_name)

        # Add column comment if available
        comment = ""
        if col_name in descriptions:
            # Escape single quotes and other problematic characters in descriptions for MariaDB
            safe_description = (
                descriptions[col_name]
                .replace("'", "''")
                .replace('"', '""')
                .replace("\n", " ")
                .replace("\r", " ")
            )
            if len(safe_description) > 255:
                safe_description = safe_description[:252] + "..."
            comment = f" COMMENT '{safe_description}'"

        column_def = f"    {quoted_name} {col_type} {not_null}{comment}".strip()
        column_defs.append(column_def)

        if is_pk:
            pk_columns.append(quoted_name)

    sql += ",\n".join(column_defs)

    if pk_columns:
        sql += f",\n    PRIMARY KEY ({', '.join(pk_columns)})"

    sql += "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"

    print(f"Creating MariaDB table {table_name}...")

    try:
        mariadb_cursor.execute(sql)
        mariadb_conn.commit()
        print(f"✓ Table {table_name} created successfully")

    except Exception as e:
        print(f"✗ Error creating table {table_name}: {e}")
        mariadb_conn.rollback()

    sqlite_conn.close()
    mariadb_conn.close()


def main():
    config = load_config()
    base_path = config["base_path"]

    for db_name, db_config in config["databases"].items():
        if not db_config["enabled"]:
            print(f"Skipping disabled database: {db_name}")
            continue

        print(f"\nProcessing MariaDB database: {db_name}")

        sqlite_path = os.path.join(base_path, db_config["sqlite_file"])
        descriptions_path = os.path.join(base_path, db_config["description_dir"])

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
            if table_name == "sqlite_sequence":
                print(f"  Skipping SQLite-specific table: {table_name}")
                continue
            create_mariadb_table(db_name, table_name, sqlite_path, descriptions_path)


if __name__ == "__main__":
    main()
