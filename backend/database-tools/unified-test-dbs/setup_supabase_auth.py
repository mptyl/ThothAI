#!/usr/bin/env python3
"""
Setup Supabase authentication for external database clients
This script creates the thoth_user and grants necessary permissions
"""

import psycopg2
import sys
import time

def wait_for_supabase():
    """Wait for Supabase container to be ready"""
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5435,
                database='postgres',
                user='supabase_admin',
                password='thoth_password'
            )
            conn.close()
            print("[SUCCESS] Supabase container is ready")
            return True
        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"⏳ Waiting for Supabase... (attempt {attempt + 1}/{max_attempts})")
                time.sleep(2)
            else:
                print(f"[ERROR] Failed to connect to Supabase after {max_attempts} attempts: {e}")
                return False
    return False

def create_thoth_user():
    """Create thoth_user with proper permissions"""
    try:
        # Connect to postgres database as supabase_admin
        conn = psycopg2.connect(
            host='localhost',
            port=5435,
            database='postgres',
            user='supabase_admin',
            password='thoth_password'
        )
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'thoth_user'")
        if cursor.fetchone():
            print("[SUCCESS] thoth_user already exists")
        else:
            # Create user
            cursor.execute("CREATE USER thoth_user WITH PASSWORD 'thoth_password' CREATEDB LOGIN;")
            conn.commit()
            print("[SUCCESS] Created thoth_user")
        
        # Grant database connection permissions
        databases = ['california_schools', 'european_football_2', 'formula_1']
        for db_name in databases:
            try:
                cursor.execute(f"GRANT CONNECT ON DATABASE {db_name} TO thoth_user;")
                conn.commit()
                print(f"[SUCCESS] Granted CONNECT on {db_name}")
            except Exception as e:
                print(f"[WARNING] Could not grant CONNECT on {db_name}: {e}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Error creating thoth_user: {e}")
        return False

def grant_schema_permissions():
    """Grant schema and table permissions on each database"""
    databases = ['california_schools', 'european_football_2', 'formula_1']
    
    for db_name in databases:
        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5435,
                database=db_name,
                user='supabase_admin',
                password='thoth_password'
            )
            cursor = conn.cursor()
            
            # Grant schema usage
            cursor.execute("GRANT USAGE ON SCHEMA public TO thoth_user;")
            
            # Grant table permissions
            cursor.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO thoth_user;")
            
            # Grant sequence permissions
            cursor.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO thoth_user;")
            
            # Grant permissions on future tables
            cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO thoth_user;")
            cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO thoth_user;")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"[SUCCESS] Granted schema permissions on {db_name}")
            
        except Exception as e:
            print(f"[WARNING] Could not grant permissions on {db_name}: {e}")

def test_authentication():
    """Test that thoth_user can connect and query data"""
    databases = ['california_schools', 'european_football_2', 'formula_1']
    test_queries = {
        'california_schools': 'SELECT COUNT(*) FROM frpm',
        'european_football_2': 'SELECT COUNT(*) FROM player',
        'formula_1': 'SELECT COUNT(*) FROM drivers'
    }
    
    print("\n🧪 Testing thoth_user authentication...")
    
    for db_name in databases:
        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5435,
                database=db_name,
                user='thoth_user',
                password='thoth_password'
            )
            cursor = conn.cursor()
            
            # Test query
            if db_name in test_queries:
                cursor.execute(test_queries[db_name])
                count = cursor.fetchone()[0]
                print(f"[SUCCESS] {db_name}: Connected successfully, found {count} records")
            else:
                print(f"[SUCCESS] {db_name}: Connected successfully")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"[ERROR] {db_name}: Connection failed - {e}")

def main():
    """Main setup function"""
    print("[INFO] Setting up Supabase authentication for external clients...")
    print("=" * 60)
    
    # Wait for Supabase to be ready
    if not wait_for_supabase():
        sys.exit(1)
    
    # Create thoth_user
    if not create_thoth_user():
        sys.exit(1)
    
    # Grant schema permissions
    grant_schema_permissions()
    
    # Test authentication
    test_authentication()
    
    print("\n" + "=" * 60)
    print("🎉 Supabase authentication setup complete!")
    print("\n📋 Connection Parameters for DBeaver/pgAdmin:")
    print("   Host: localhost")
    print("   Port: 5435")
    print("   Username: thoth_user")
    print("   Password: thoth_password")
    print("   Database: california_schools (or european_football_2, formula_1)")
    print("\n📖 For troubleshooting, see: SUPABASE_AUTHENTICATION_GUIDE.md")

if __name__ == "__main__":
    main()
