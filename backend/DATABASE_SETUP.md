# Database Setup Guide for ThothAI

## Default Databases (No System Dependencies Required)

ThothAI comes with support for the following databases out of the box:

- **PostgreSQL** - Full support, no additional setup needed
- **SQLite** - Full support, no additional setup needed

## Optional Databases (System Dependencies Required)

The following databases require system-level dependencies to be installed before they can be used:

### MariaDB

MariaDB requires the MariaDB Connector/C to be installed on your system.

#### Installation Instructions:

**macOS:**
```bash
brew install mariadb-connector-c
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install libmariadb-dev
```

**RHEL/CentOS/Fedora:**
```bash
sudo yum install mariadb-connector-c-devel
# or
sudo dnf install mariadb-connector-c-devel
```

**After installing system dependencies:**
```bash
uv sync --extra mariadb
```

### MySQL

MySQL requires the MySQL client libraries to be installed.

#### Installation Instructions:

**macOS:**
```bash
brew install mysql-client
export PATH="/usr/local/opt/mysql-client/bin:$PATH"
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install libmysqlclient-dev
```

**RHEL/CentOS/Fedora:**
```bash
sudo yum install mysql-devel
# or
sudo dnf install mysql-devel
```

**After installing system dependencies:**
```bash
uv sync --extra mysql
```

### SQL Server

SQL Server requires ODBC drivers to be installed.

#### Installation Instructions:

**All platforms:**
Follow Microsoft's official guide: https://docs.microsoft.com/en-us/sql/connect/odbc/

**macOS:**
```bash
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
brew install msodbcsql17 mssql-tools
```

**Ubuntu/Debian:**
```bash
# Add Microsoft's repository
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list

sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install msodbcsql17
sudo ACCEPT_EULA=Y apt-get install mssql-tools
```

**After installing system dependencies:**
```bash
uv sync --extra sqlserver
```

### Oracle

Oracle requires Oracle Instant Client to be installed.

#### Installation Instructions:

**All platforms:**
1. Download Oracle Instant Client from: https://www.oracle.com/database/technologies/instant-client/
2. Follow the installation instructions for your platform
3. Set the required environment variables (LD_LIBRARY_PATH on Linux, DYLD_LIBRARY_PATH on macOS)

**After installing system dependencies:**
```bash
uv sync --extra oracle
```

## Installing All Database Support

If you want to install support for all databases at once (requires all system dependencies):

```bash
uv sync --extra all-databases
```

## Troubleshooting

### Error: "mariadb_config not found"
This means the MariaDB Connector/C is not installed. Follow the MariaDB installation instructions above.

### Error: "mysql_config not found"
This means the MySQL client libraries are not installed. Follow the MySQL installation instructions above.

### Error: "ODBC Driver not found"
This means the SQL Server ODBC drivers are not installed. Follow the SQL Server installation instructions above.

### Error: "Oracle client libraries not found"
This means Oracle Instant Client is not installed or not in the system path. Follow the Oracle installation instructions above.

## Using the Interactive Installer

The interactive installer (`./install.sh`) will:
1. Let you select which databases you want to use
2. Update the configuration automatically
3. Provide warnings about system dependencies
4. Continue with installation even if optional database drivers fail

The application will always work with PostgreSQL and SQLite, even if other database drivers fail to install.