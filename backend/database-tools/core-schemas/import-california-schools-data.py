#!/usr/bin/env python3
"""
Import California Schools data from SQLite to MariaDB
This script reads data from the SQLite database and imports it into MariaDB
"""

import sqlite3
import mysql.connector
import logging
import sys
import csv
import os
from typing import Dict, Any, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database configurations
SQLITE_DB_PATH = "/Users/mp/thoth_data/dev_databases/california_schools/california_schools.sqlite"
DESCRIPTIONS_DIR = "/Users/mp/thoth_data/dev_databases/california_schools/database_description"
MARIADB_CONFIG = {
    'host': 'localhost',
    'port': 3307,
    'user': 'thoth_user',
    'password': 'thoth_password',
    'database': 'california_schools',
    'charset': 'utf8mb4',
    'autocommit': False
}

def connect_sqlite() -> sqlite3.Connection:
    """Connect to SQLite database"""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        logger.info(f"Connected to SQLite database: {SQLITE_DB_PATH}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to SQLite: {e}")
        raise

def connect_mariadb() -> mysql.connector.MySQLConnection:
    """Connect to MariaDB database"""
    try:
        conn = mysql.connector.connect(**MARIADB_CONFIG)
        logger.info(f"Connected to MariaDB database: {MARIADB_CONFIG['host']}:{MARIADB_CONFIG['port']}")
        return conn
    except mysql.connector.Error as e:
        logger.error(f"Error connecting to MariaDB: {e}")
        raise

def clear_mariadb_tables(mariadb_conn: mysql.connector.MySQLConnection) -> None:
    """Clear existing data from MariaDB tables"""
    cursor = mariadb_conn.cursor()
    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        tables = ['satscores', 'frpm', 'schools']  # Order matters due to foreign keys
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
            logger.info(f"Cleared table: {table}")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        mariadb_conn.commit()
    except mysql.connector.Error as e:
        logger.error(f"Error clearing tables: {e}")
        mariadb_conn.rollback()
        raise
    finally:
        cursor.close()

def import_schools_data(sqlite_conn: sqlite3.Connection, mariadb_conn: mysql.connector.MySQLConnection) -> int:
    """Import schools data from SQLite to MariaDB"""
    logger.info("Importing schools data...")
    
    sqlite_cursor = sqlite_conn.cursor()
    mariadb_cursor = mariadb_conn.cursor()
    
    try:
        # Get data from SQLite
        sqlite_cursor.execute("SELECT * FROM schools")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            logger.warning("No schools data found in SQLite")
            return 0
        
        # Prepare MariaDB insert statement
        columns = [description[0] for description in sqlite_cursor.description]
        placeholders = ', '.join(['%s'] * len(columns))
        insert_query = f"INSERT INTO schools ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Convert rows to tuples and insert
        data_tuples = [tuple(row) for row in rows]
        mariadb_cursor.executemany(insert_query, data_tuples)
        
        mariadb_conn.commit()
        count = len(data_tuples)
        logger.info(f"Successfully imported {count} schools records")
        return count
        
    except (sqlite3.Error, mysql.connector.Error) as e:
        logger.error(f"Error importing schools data: {e}")
        mariadb_conn.rollback()
        raise
    finally:
        sqlite_cursor.close()
        mariadb_cursor.close()

def import_frpm_data(sqlite_conn: sqlite3.Connection, mariadb_conn: mysql.connector.MySQLConnection) -> int:
    """Import FRPM data from SQLite to MariaDB"""
    logger.info("Importing FRPM data...")
    
    sqlite_cursor = sqlite_conn.cursor()
    mariadb_cursor = mariadb_conn.cursor()
    
    try:
        # Get data from SQLite
        sqlite_cursor.execute("SELECT * FROM frpm")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            logger.warning("No FRPM data found in SQLite")
            return 0
        
        # Prepare MariaDB insert statement with proper column escaping
        columns = [f"`{description[0]}`" for description in sqlite_cursor.description]
        placeholders = ', '.join(['%s'] * len(columns))
        insert_query = f"INSERT INTO frpm ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Convert rows to tuples and insert
        data_tuples = [tuple(row) for row in rows]
        mariadb_cursor.executemany(insert_query, data_tuples)
        
        mariadb_conn.commit()
        count = len(data_tuples)
        logger.info(f"Successfully imported {count} FRPM records")
        return count
        
    except (sqlite3.Error, mysql.connector.Error) as e:
        logger.error(f"Error importing FRPM data: {e}")
        mariadb_conn.rollback()
        raise
    finally:
        sqlite_cursor.close()
        mariadb_cursor.close()

def import_satscores_data(sqlite_conn: sqlite3.Connection, mariadb_conn: mysql.connector.MySQLConnection) -> int:
    """Import SAT scores data from SQLite to MariaDB"""
    logger.info("Importing SAT scores data...")
    
    sqlite_cursor = sqlite_conn.cursor()
    mariadb_cursor = mariadb_conn.cursor()
    
    try:
        # Get data from SQLite, only records that have corresponding schools
        sqlite_cursor.execute("""
            SELECT sat.* FROM satscores sat
            INNER JOIN schools s ON sat.cds = s.CDSCode
        """)
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            logger.warning("No SAT scores data found in SQLite")
            return 0
        
        # Prepare MariaDB insert statement
        columns = [description[0] for description in sqlite_cursor.description]
        placeholders = ', '.join(['%s'] * len(columns))
        insert_query = f"INSERT INTO satscores ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Convert rows to tuples and insert
        data_tuples = [tuple(row) for row in rows]
        mariadb_cursor.executemany(insert_query, data_tuples)
        
        mariadb_conn.commit()
        count = len(data_tuples)
        logger.info(f"Successfully imported {count} SAT scores records (filtered orphaned records)")
        return count
        
    except (sqlite3.Error, mysql.connector.Error) as e:
        logger.error(f"Error importing SAT scores data: {e}")
        mariadb_conn.rollback()
        raise
    finally:
        sqlite_cursor.close()
        mariadb_cursor.close()


def verify_import(mariadb_conn: mysql.connector.MySQLConnection) -> None:
    """Verify the data import was successful"""
    logger.info("Verifying data import...")
    
    cursor = mariadb_conn.cursor()
    try:
        # Check row counts
        tables = ['schools', 'frpm', 'satscores']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"Table {table}: {count} rows")
        
        # Check some sample data
        cursor.execute("""
            SELECT s.School, s.District, s.County, f.`Enrollment (K-12)`, sat.NumTstTakr
            FROM schools s
            LEFT JOIN frpm f ON s.CDSCode = f.CDSCode
            LEFT JOIN satscores sat ON s.CDSCode = sat.cds
            WHERE s.StatusType = 'Active'
            ORDER BY f.`Enrollment (K-12)` DESC
            LIMIT 5
        """)
        
        logger.info("Sample of imported data:")
        for row in cursor.fetchall():
            logger.info(f"  {row[0]} ({row[1]}, {row[2]}) - Enrollment: {row[3]}, SAT Takers: {row[4]}")
        
        # Verify schema has comments by checking table structure
        cursor.execute("SHOW CREATE TABLE schools")
        create_table_sql = cursor.fetchone()[1]
        if 'COMMENT' in create_table_sql:
            logger.info("Schema includes column comments from CSV descriptions")
        else:
            logger.warning("Schema does not include column comments")
            
    except mysql.connector.Error as e:
        logger.error(f"Error verifying import: {e}")
        raise
    finally:
        cursor.close()

def main():
    """Main import function"""
    logger.info("Starting California Schools data import...")
    
    sqlite_conn = None
    mariadb_conn = None
    
    try:
        # Connect to databases
        sqlite_conn = connect_sqlite()
        mariadb_conn = connect_mariadb()
        
        # Clear existing data
        clear_mariadb_tables(mariadb_conn)
        
        # Import data in order (schools first due to foreign keys)
        schools_count = import_schools_data(sqlite_conn, mariadb_conn)
        frpm_count = import_frpm_data(sqlite_conn, mariadb_conn)
        satscores_count = import_satscores_data(sqlite_conn, mariadb_conn)
        
        # Verify import
        verify_import(mariadb_conn)
        
        logger.info(f"Import completed successfully!")
        logger.info(f"Total records imported: {schools_count + frpm_count + satscores_count}")
        logger.info(f"  - Schools: {schools_count}")
        logger.info(f"  - FRPM: {frpm_count}")
        logger.info(f"  - SAT Scores: {satscores_count}")
        logger.info("Column descriptions are embedded in the schema as COMMENT attributes")
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)
        
    finally:
        if sqlite_conn:
            sqlite_conn.close()
        if mariadb_conn:
            mariadb_conn.close()

if __name__ == "__main__":
    main()