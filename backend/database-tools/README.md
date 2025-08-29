# Database Tools for Thoth Backend

This directory contains database management tools and configurations for the Thoth Backend project, supporting multiple database types and environments.

## Overview

The database tools are organized into two main systems:

1. **Unified Test Databases** (`unified-test-dbs/`) - Recommended modern system
2. **Legacy Standalone** (`legacy-standalone/`) - Archived for reference
3. **Core Schemas** (`core-schemas/`) - Schema generation utilities

## Quick Start (Recommended)

### Unified Test Database System

The unified system manages all supported databases from a single interface:

```bash
# Navigate to unified tools
cd database-tools/unified-test-dbs/

# Start all database services
python manage-thoth-test-dbs.py start

# Check health of all services
python manage-thoth-test-dbs.py health

# Show current configuration
python manage-thoth-test-dbs.py config

# Generate schemas for enabled databases
python generate-all-schemas.py

# Import data to enabled databases
python import-all-data.py

# Stop all services
python manage-thoth-test-dbs.py stop
```

## Supported Databases

| Database | Port | Access | Notes |
|----------|------|--------|--------|
| PostgreSQL | 5434 | Direct connection | Primary test database |
| MariaDB | 3308 | Direct connection | Alternative SQL database |
| MySQL | 3309 | Direct connection | Alternative SQL database |
| Oracle XE | 1521 | Direct connection | Enterprise database |
| SQL Server | 1433 | Direct connection | Microsoft SQL database |
| Supabase | 5435 | REST API + Direct | PostgreSQL with REST API |

## Access Points

- **Adminer (All Databases)**: http://localhost:8080
- **PostgREST API (PostgreSQL)**: http://localhost:3100
- **Supabase REST API**: http://localhost:3001

## Database Content

All databases contain standardized test datasets:

### California Schools Dataset (29,941 rows)
- **Tables**: `frpm`, `satscores`, `schools`
- **Use Case**: Educational data with hierarchical structures
- **Complexity**: Medium - relationships between schools, districts, and counties
- **Features**: Mixed-case columns, demographic data

### European Football Dataset (222,796 rows)
- **Tables**: `Player`, `Team`, `Match`, `Player_Attributes`, `Team_Attributes`, `League`, `Country`
- **Use Case**: Sports data with many-to-many relationships
- **Complexity**: High - players, teams, matches, temporal attributes
- **Features**: Large volumes, temporal relationships

### Formula 1 Dataset (512,287 rows)
- **Tables**: `lapTimes`, `results`, `drivers`, `constructors`, `races`, `circuits`, etc.
- **Use Case**: High-granularity telemetry and performance data
- **Complexity**: Very High - temporal data, complex hierarchies
- **Features**: Largest dataset, complex analytical queries

## Directory Structure

```
database-tools/
├── README.md                        # This file
├── DATABASE_SETUP.md                # Legacy setup documentation
├── DATABASE_TOOLS.md                # Legacy tools reference
├── unified-test-dbs/                # Modern unified system
│   ├── manage-thoth-test-dbs.py    # Main management script
│   ├── generate-all-schemas.py     # Schema generation
│   ├── import-all-data.py          # Data import
│   ├── database-config.yml         # Configuration
│   ├── thoth-test-dbs.yml          # Docker Compose file
│   └── db-init/                    # SQL initialization scripts
│       ├── postgres/               # PostgreSQL schemas
│       ├── mysql/                  # MySQL schemas
│       ├── mariadb/                # MariaDB schemas
│       ├── oracle/                 # Oracle schemas
│       ├── sqlserver/              # SQL Server schemas
│       └── supabase/               # Supabase schemas
├── core-schemas/                    # Schema generation utilities
│   ├── generate-enhanced-schema.py
│   ├── generate-oracle-schema.py
│   ├── generate-sqlserver-schema.py
│   ├── generate-supabase-schema.py
│   └── import-california-schools-data.py
└── legacy-standalone/               # Archived individual setups
    ├── manage-mariadb-sc.sh
    ├── manage-oracle-sc.sh
    ├── standalone-mariadb-sc.yml
    └── ...
```

## Configuration

### Unified Credentials
All databases use the same credentials for simplicity:

| Database | Host | Port | Username | Password | Database |
|----------|------|-------|----------|----------|----------|
| PostgreSQL | localhost | 5434 | thoth_user | thoth_password | california_schools |
| Supabase | localhost | 5435 | thoth_user | thoth_password | california_schools |
| MySQL | localhost | 3309 | thoth_user | thoth_password | california_schools |
| MariaDB | localhost | 3308 | thoth_user | thoth_password | california_schools |

### Main Configuration File
`unified-test-dbs/database-config.yml` controls which databases are enabled and their settings.

### Environment Variables
Required for database connections:
- Database-specific credentials
- Port mappings
- Service configurations

## Database Differences

### PostgreSQL/Supabase
- **Mixed-case Columns**: Double quotes (`"Academic Year"`)
- **Charset**: UTF8
- **Engine**: Native PostgreSQL
- **Extra (Supabase)**: REST API, real-time subscriptions

### MySQL/MariaDB
- **Mixed-case Columns**: Backticks (`` `Academic Year` ``)
- **Charset**: UTF8MB4
- **Engine**: InnoDB
- **Reserved Words**: MySQL standard (Match, Virtual, rank, etc.)

### Oracle
- **Mixed-case Columns**: Double quotes (`"Academic Year"`)
- **Charset**: UTF8
- **Engine**: Oracle XE
- **Features**: Enterprise database features

### SQL Server
- **Mixed-case Columns**: Square brackets (`[Academic Year]`)
- **Charset**: UTF8
- **Engine**: SQL Server 2022
- **Features**: Microsoft SQL Server features

## Example Queries

### Cross-Database Compatibility
```sql
-- PostgreSQL/Supabase: double quotes
SELECT "Academic Year", "County Name", COUNT(*) 
FROM frpm 
WHERE "County Name" = 'Los Angeles'
GROUP BY "Academic Year", "County Name";

-- MySQL/MariaDB: backticks
SELECT `Academic Year`, `County Name`, COUNT(*) 
FROM frpm 
WHERE `County Name` = 'Los Angeles'
GROUP BY `Academic Year`, `County Name`;

-- SQL Server: square brackets
SELECT [Academic Year], [County Name], COUNT(*) 
FROM frpm 
WHERE [County Name] = 'Los Angeles'
GROUP BY [Academic Year], [County Name];
```

### Reserved Words Handling
```sql
-- PostgreSQL: table name quoting
SELECT id, season, "date" FROM "Match" WHERE season = '2015/2016';

-- MySQL/MariaDB: backtick quoting
SELECT id, season, `date` FROM `Match` WHERE season = '2015/2016';

-- SQL Server: square bracket quoting
SELECT id, season, [date] FROM [Match] WHERE season = '2015/2016';
```

## Development Workflow

1. **Setup**: Use `manage-thoth-test-dbs.py start` to initialize all services
2. **Schema Generation**: Run `generate-all-schemas.py` for database schemas
3. **Data Import**: Execute `import-all-data.py` for test data
4. **Testing**: Use configured databases for Thoth backend testing
5. **Cleanup**: Run `manage-thoth-test-dbs.py stop` when finished

## Container Management

### Selective Startup
```bash
# Start specific database
docker start postgres-server
docker start mysql-server
docker start mariadb-server

# Start with compose
cd unified-test-dbs
docker-compose -f thoth-test-dbs.yml up -d postgres-server
```

### Health Checks
```bash
# Check all database health
python manage-thoth-test-dbs.py health

# Check containers
docker ps

# View logs
docker logs postgres-server
docker logs mysql-server
```

## Legacy System (Archived)

The `legacy-standalone/` directory contains the previous system with individual database setups. This is maintained for reference but not recommended for new development.

Each legacy database had its own:
- Docker Compose file (`standalone-*.yml`)
- Management script (`manage-*-sc.sh`)
- Initialization SQL files
- Port configuration

### Migration from Legacy

If you were using the legacy system:

1. Stop legacy containers
2. Use the new unified system: `cd unified-test-dbs/`
3. Run `python manage-thoth-test-dbs.py start`
4. Update connection strings in your code

## Schema Generation

The schema generation tools create database-specific SQL scripts with:
- Table creation statements
- Column descriptions embedded as comments
- Index definitions
- Constraint setup

### Available Generators
- `generate-enhanced-schema.py` - PostgreSQL enhanced schemas
- `generate-oracle-schema.py` - Oracle-specific schemas  
- `generate-sqlserver-schema.py` - SQL Server schemas
- `generate-supabase-schema.py` - Supabase-compatible schemas

## Data Import

Data import tools populate databases with standardized datasets:
- `import-california-schools-data.py` - Main data import utility
- Database-specific import scripts in `unified-test-dbs/`
- Batch processing for large datasets (1000 rows per batch)

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Check if ports are already in use
   ```bash
   lsof -i :5434  # Check PostgreSQL port
   netstat -tulpn | grep :3308  # Check MariaDB port
   ```

2. **Docker Issues**: Ensure Docker is running
   ```bash
   docker ps  # List running containers
   docker stats  # Monitor resource usage
   ```

3. **Permission Issues**: Check Docker permissions
   ```bash
   docker run hello-world  # Test Docker access
   ```

4. **Connection Issues**: Verify credentials and ports
   ```bash
   # Test PostgreSQL connection
   psql -h localhost -p 5434 -U thoth_user -d california_schools
   
   # Test MySQL connection  
   mysql -h localhost -P 3309 -u thoth_user -p california_schools
   ```

### Performance Optimization

- **Use indexes**: All tables have primary keys and common indexes
- **Batch operations**: Import/export in batches for large datasets
- **Monitor resources**: Use `docker stats` to monitor container usage
- **Query optimization**: Use `EXPLAIN` to analyze query performance

## Integration with Thoth Backend

These databases integrate with the main Thoth application through:
- Configuration in `thoth_core` models (`SqlDb` model)
- Test suites in `tests/` directory
- AI workflow testing in `thoth_ai_backend`
- Vector database collections (1:1 relationship with SQL databases)

Connection strings follow the format:
- PostgreSQL: `postgresql://thoth_user:thoth_password@localhost:5434/california_schools`
- MySQL: `mysql://thoth_user:thoth_password@localhost:3309/california_schools`
- MariaDB: `mysql://thoth_user:thoth_password@localhost:3308/california_schools`
- Oracle: `oracle://thoth_user:thoth_password@localhost:1521/XE`
- SQL Server: `mssql://thoth_user:thoth_password@localhost:1433/california_schools`

## Contributing

When adding new database support:
1. Add configuration to `database-config.yml`
2. Create initialization scripts in `db-init/<database>/`
3. Update `manage-thoth-test-dbs.py` for the new database type
4. Add schema generation support in `core-schemas/`
5. Create import scripts for the new database
6. Test with the unified system
7. Update this documentation

## Best Practices

1. **Use one database at a time** to avoid resource conflicts
2. **Test identical queries** on different databases for accurate comparisons
3. **Monitor memory usage** during import of large datasets
4. **Use EXPLAIN** to optimize complex queries
5. **Regular backups** of Docker volumes to preserve data
6. **Follow SQL standards** when possible for cross-database compatibility

## License

These tools are part of the Thoth Backend project and released under the Apache License 2.0. See `LICENSE.md` in the project root for details.