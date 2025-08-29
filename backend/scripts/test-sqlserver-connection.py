#!/usr/bin/env python
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Test SQL Server connection with various driver options."""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_sql_server_connection(connection_string):
    """Test SQL Server connection with thoth-dbmanager."""
    from thoth_dbmanager import ThothDbManager
    
    print(f"\nTesting connection: {connection_string.split('@')[0]}@...")
    
    try:
        # Create manager
        manager = ThothDbManager(connection_string)
        
        # Test connection
        with manager.get_connection() as conn:
            cursor = conn.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            print(f"✓ Connected successfully!")
            print(f"  SQL Server version: {version[:50]}...")
            
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        
        # Provide helpful suggestions
        if "ODBC Driver" in str(e):
            print("  Suggestion: Try using 'ODBC Driver 18 for SQL Server' in the connection string")
            print("  Example: mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes")
        elif "pymssql" in str(e):
            print("  Suggestion: Try using pyodbc instead of pymssql")
        elif "certificate" in str(e).lower() or "ssl" in str(e).lower():
            print("  Suggestion: Add '&TrustServerCertificate=yes' to the connection string for self-signed certificates")
            
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test-sqlserver-connection.py <connection_string>")
        print("\nExamples:")
        print("  pyodbc:  mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+18+for+SQL+Server")
        print("  pymssql: mssql+pymssql://user:pass@server/db")
        print("\nFor self-signed certificates, add: &TrustServerCertificate=yes")
        sys.exit(1)
    
    connection_string = sys.argv[1]
    
    # Test the connection
    success = test_sql_server_connection(connection_string)
    sys.exit(0 if success else 1)