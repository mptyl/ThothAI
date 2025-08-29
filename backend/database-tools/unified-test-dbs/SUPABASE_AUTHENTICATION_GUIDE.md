# Supabase Authentication Guide for External Database Clients

This guide documents the authentication setup required for connecting external database clients (DBeaver, pgAdmin, etc.) to the Supabase container.

## Problem Background

Supabase containers initially only include the `supabase_admin` user, but many database client tools expect a standard user like `thoth_user` for consistency with other PostgreSQL setups. Additionally, Supabase uses SCRAM-SHA-256 authentication for external connections, which requires proper user configuration.

## Authentication Issue Resolution

### Original Problem
- **Error**: `FATAL: password authentication failed for user 'thoth_user'`
- **Cause**: The `thoth_user` did not exist in the Supabase container
- **Authentication Method**: External connections require SCRAM-SHA-256, not simple password authentication

### Solution Implemented
1. Created `thoth_user` with proper SCRAM-SHA-256 password authentication
2. Granted database connection permissions to all three databases
3. Configured schema and table permissions for full CRUD operations
4. Enabled Row Level Security (RLS) with permissive policies

## Working Connection Parameters

### For DBeaver, pgAdmin, and other PostgreSQL clients:

```
Host: localhost
Port: 5435
Username: thoth_user
Password: thoth_password
Database: california_schools (or european_football_2, formula_1)
```

### Alternative Admin Connection:

```
Host: localhost
Port: 5435
Username: supabase_admin
Password: thoth_password
Database: california_schools (or european_football_2, formula_1)
```

## Available Databases

1. **california_schools** - 3 tables, 29,941 rows
   - `frpm` - Free/Reduced Price Meal data (9,986 rows)
   - `satscores` - SAT score data (2,269 rows)
   - `schools` - School information (17,686 rows)

2. **european_football_2** - 7 tables, 222,796 rows
   - `player_attributes`, `player`, `match`, `team_attributes`, `team`, `league`, `country`

3. **formula_1** - 13 tables, 512,287 rows
   - `laptimes`, `driverstandings`, `results`, `constructorstandings`, etc.

## User Permissions

The `thoth_user` has been configured with:

- ✅ **Login privileges**: Can connect from external clients
- ✅ **Database access**: Can connect to all 3 databases
- ✅ **Full CRUD operations**: SELECT, INSERT, UPDATE, DELETE on all tables
- ✅ **Schema usage**: Can access the public schema
- ✅ **Sequence access**: Can use auto-increment sequences
- ✅ **Create database**: Can create new databases if needed

## Supabase-Specific Considerations

### Row Level Security (RLS)
- **Status**: Enabled on all tables
- **Policies**: Permissive policies allow immediate access
- **Customization**: Can be modified for granular security control

### Authentication Method
- **External connections**: SCRAM-SHA-256 (secure password hashing)
- **Local connections**: Trust (for container-internal access)
- **No JWT required**: Standard PostgreSQL authentication works for database clients

### Mixed-Case Column Names
Many tables contain mixed-case column names that require double quotes in queries:

```sql
-- Correct syntax for mixed-case columns
SELECT cdscode, "Academic Year", "County Name", "School Name" 
FROM frpm 
WHERE "School Name" LIKE '%Elementary%';

-- This will fail without quotes
SELECT Academic Year FROM frpm;  -- ERROR
```

## Setup Commands Reference

If you need to recreate the authentication setup, run these commands:

### 1. Create User (in postgres database as supabase_admin)
```sql
CREATE USER thoth_user WITH PASSWORD 'thoth_password' CREATEDB LOGIN;
```

### 2. Grant Database Connections (in postgres database)
```sql
GRANT CONNECT ON DATABASE california_schools TO thoth_user;
GRANT CONNECT ON DATABASE european_football_2 TO thoth_user;
GRANT CONNECT ON DATABASE formula_1 TO thoth_user;
```

### 3. Grant Schema and Table Permissions (in each database)
```sql
GRANT USAGE ON SCHEMA public TO thoth_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO thoth_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO thoth_user;
```

## Troubleshooting

### Connection Failures
If you get "password authentication failed":
1. Verify user exists: `SELECT rolname FROM pg_roles WHERE rolname = 'thoth_user';`
2. Check pg_hba.conf authentication method (should be scram-sha-256)
3. Ensure correct password: `thoth_password`
4. Use correct port: 5435 (not 5432)

### Permission Denied Errors
If you get permission denied on tables:
1. Check database connection: `SELECT has_database_privilege('thoth_user', 'california_schools', 'CONNECT');`
2. Verify table permissions: `SELECT has_table_privilege('thoth_user', 'frpm', 'SELECT');`
3. Confirm schema usage: `SELECT has_schema_privilege('thoth_user', 'public', 'USAGE');`

### Query Syntax Issues
For mixed-case column names, always use double quotes:
- ✅ `"Academic Year"`
- ❌ `Academic Year`
- ❌ `'Academic Year'`

## Container Status Verification

To verify the Supabase container is running properly:

```bash
# Check container status
docker ps | grep supabase

# Test connection from host
PGPASSWORD=thoth_password psql -h localhost -p 5435 -U thoth_user -d california_schools -c "SELECT COUNT(*) FROM frpm;"
```

## Access Points Summary

| Service | URL/Connection | Credentials |
|---------|---------------|-------------|
| **DBeaver/pgAdmin** | localhost:5435 | `thoth_user` / `thoth_password` |
| **Supabase Admin** | localhost:5435 | `supabase_admin` / `thoth_password` |
| **Supabase REST API** | http://localhost:3001 | JWT required for API |
| **PostgREST API** | http://localhost:3100 | JWT required for API |
| **Adminer Web** | http://localhost:8080 | Use either user above |

This authentication setup ensures compatibility with standard PostgreSQL client tools while maintaining Supabase's security features and functionality.
