# Database Configuration Guide

Guida dettagliata per configurare e gestire i database nel sistema Thoth Unified Test Databases.

## 📋 File di Configurazione

### `database-config.yml`

Il file centrale che controlla tutti gli aspetti del sistema:

```yaml
# Percorso base dei database SQLite sorgente
base_path: "/Users/mp/data/dev_20240627/dev_databases"

# Configurazione database disponibili
databases:
  database_name:
    enabled: true/false        # Se processare questo database
    sqlite_file: "path/to/db.sqlite"  # Percorso relativo a base_path
    description_dir: "path/to/descriptions"  # Directory CSV descrizioni
    description: "Descrizione del database"

# Configurazione server database
servers:
  server_type:
    enabled: true/false        # Se avviare container Docker
    port: 1234                # Porta esposta
    container_name: "name"     # Nome container Docker
    rest_port: 5678           # Porta API REST (se applicabile)

# Configurazione condivisa
shared:
  adminer_port: 8080         # Porta Adminer web interface
  username: "thoth_user"     # Username default
  password: "thoth_password" # Password default
```

## 🗄️ Database Configurati

### california_schools
```yaml
california_schools:
  enabled: true
  sqlite_file: "california_schools/california_schools.sqlite"
  description_dir: "california_schools/database_description"
  description: "California public schools data with enrollment, demographics, and SAT scores"
```

**Struttura Dati:**
- **Sorgente**: `/Users/mp/data/dev_20240627/dev_databases/california_schools/`
- **Database**: `california_schools.sqlite` (11MB)
- **Descrizioni**: 3 file CSV in `database_description/`
- **Tabelle**: `frpm`, `satscores`, `schools`
- **Record**: ~29,941 totali

### european_football_2
```yaml
european_football_2:
  enabled: true
  sqlite_file: "european_football_2/european_football_2.sqlite"
  description_dir: "european_football_2/database_description"
  description: "European football leagues, teams, players, and match data"
```

**Struttura Dati:**
- **Sorgente**: `/Users/mp/data/dev_20240627/dev_databases/european_football_2/`
- **Database**: `european_football_2.sqlite`
- **Descrizioni**: 7 file CSV in `database_description/`
- **Tabelle**: `Country`, `League`, `Match`, `Player`, `Player_Attributes`, `Team`, `Team_Attributes`
- **Record**: ~222,796 totali

### formula_1
```yaml
formula_1:
  enabled: true
  sqlite_file: "formula_1/formula_1.sqlite"
  description_dir: "formula_1/database_description"
  description: "Formula 1 racing data including circuits, drivers, races, and results"
```

**Struttura Dati:**
- **Sorgente**: `/Users/mp/data/dev_20240627/dev_databases/formula_1/`
- **Database**: `formula_1.sqlite`
- **Descrizioni**: 13 file CSV in `database_description/`
- **Tabelle**: `circuits`, `constructors`, `drivers`, `seasons`, `races`, `results`, etc.
- **Record**: ~514,287 totali

### Database Disabilitati

Per i database non attualmente utilizzati:

```yaml
card_games:
  enabled: false
  sqlite_file: "card_games/card_games.sqlite"
  description_dir: "card_games/database_description"
  description: "Trading card game data with sets, cards, and game mechanics"

# Altri database disponibili: codebase_community, debit_card_specializing, 
# financial, student_club, superhero, thrombosis_prediction, toxicology
```

## 🖥️ Server Container Docker

### Database Attivi (Container Locali)

#### MariaDB
```yaml
mariadb:
  enabled: true
  port: 3308
  container_name: "mariadb-server"
```
- **Image**: `mariadb:11.4`
- **Volume**: `mariadb_data:/var/lib/mysql`
- **Init**: `./db-init/mariadb:/docker-entrypoint-initdb.d`

#### MySQL
```yaml
mysql:
  enabled: true
  port: 3309
  container_name: "mysql-server"
```
- **Image**: `mysql:8.0`
- **Volume**: `mysql_data:/var/lib/mysql`
- **Init**: `./db-init/mysql:/docker-entrypoint-initdb.d`

#### PostgreSQL
```yaml
postgres:
  enabled: true
  port: 5434
  container_name: "postgres-server"
```
- **Image**: `postgres:16`
- **Volume**: `postgres_data:/var/lib/postgresql/data`
- **Init**: `./db-init/postgres:/docker-entrypoint-initdb.d`

#### Supabase
```yaml
supabase:
  enabled: true
  port: 5435
  container_name: "supabase-server"
  rest_port: 3001
```
- **Image**: `supabase/postgres:15.1.0.147`
- **Volume**: `supabase_data:/var/lib/postgresql/data`
- **Init**: `./db-init/supabase:/docker-entrypoint-initdb.d`
- **Features**: Auth, RLS, Extensions

### Database Cloud-Only (Solo Schemi)

#### SQL Server
```yaml
sqlserver:
  enabled: false  # Solo generazione schemi per cloud
  port: 1433
  container_name: "sqlserver-server"
```
- **Status**: Container Docker disabilitato (problemi ARM64)
- **Schemi**: Generati in `db-init/sqlserver/`
- **Target**: Azure SQL, AWS RDS SQL Server, etc.

#### Oracle
```yaml
oracle:
  enabled: false  # Solo generazione schemi per cloud
  port: 1521
  container_name: "oracle-server"
```
- **Status**: Container Docker disabilitato (problemi ARM64)
- **Schemi**: Generati in `db-init/oracle/`
- **Target**: Oracle Cloud, AWS RDS Oracle, etc.

## 🔧 Modificare la Configurazione

### Abilitare/Disabilitare Database

Per abilitare un nuovo database:

```yaml
databases:
  new_database:
    enabled: true  # Cambia da false a true
    sqlite_file: "new_database/new_database.sqlite"
    description_dir: "new_database/database_description"
    description: "Description of new database"
```

Poi rigenera gli schemi:
```bash
python generate-all-schemas.py
```

### Modificare Porte

Se le porte sono in conflitto:

```yaml
servers:
  mariadb:
    port: 3308  # Cambia porta se necessario
```

Poi riavvia:
```bash
python manage-thoth-test-dbs.py restart
```

### Aggiungere Nuovo Server

Per aggiungere supporto per un nuovo database engine:

1. **Configurazione**:
```yaml
servers:
  newdb:
    enabled: true
    port: 5432
    container_name: "newdb-server"
```

2. **Docker Compose**: Aggiungere servizio in `thoth-test-dbs.yml`

3. **Schema Generator**: Implementare funzioni in `generate-all-schemas.py`:
   - `sqlite_type_to_newdb()`
   - `generate_newdb_schema()`

4. **Import**: Aggiungere funzione in `import-all-data.py`:
   - `import_to_newdb()`

5. **Health Check**: Aggiungere in `manage-thoth-test-dbs.py`

## 📁 Struttura Directory Descrizioni

Ogni database deve avere una directory `database_description/` con file CSV:

```
database_description/
├── table1.csv
├── table2.csv
└── table3.csv
```

### Formato File CSV Descrizioni

Ogni file CSV deve avere header: `column_name,description`

```csv
column_name,description
id,Unique identifier
name,Full name of the entity
created_at,Creation timestamp
```

**Esempio california_schools/database_description/schools.csv:**
```csv
column_name,description
CDSCode,CDSCode
NCESDist,This field represents the 7-digit National Center for Educational Statistics (NCES) school district identification number
StatusType,This field identifies the status of the district
County,County name
```

## 🔄 Workflow Generazione Schemi

### 1. Lettura Configurazione
```python
config = yaml.safe_load(config_file)
base_path = config['base_path']
databases = config['databases']
servers = config['servers']
```

### 2. Per Ogni Database Abilitato
```python
for db_name, db_config in databases.items():
    if db_config['enabled']:
        # Estrai schema da SQLite
        sqlite_path = os.path.join(base_path, db_config['sqlite_file'])
        schemas = extract_schema_from_sqlite(sqlite_path)
        
        # Carica descrizioni colonne
        descriptions = load_column_descriptions(base_path, db_config['description_dir'])
```

### 3. Generazione Schema Per Engine
```python
# Container locali (condizionale)
if servers['mariadb']['enabled']:
    mariadb_sql = generate_mariadb_schema(db_name, schemas, descriptions)

# Cloud esterni (sempre)
sqlserver_sql = generate_sqlserver_schema(db_name, schemas, descriptions)
oracle_sql = generate_oracle_schema(db_name, schemas, descriptions)
```

### 4. Scrittura File
```python
with open(f"db-init/{engine}/{db_name}.sql", 'w') as f:
    f.write(generated_sql)
```

## 🏗️ Architettura Container

### Network Docker
```yaml
networks:
  test-dbs-net:
    driver: bridge
```

Tutti i container comunicano tramite network isolato `thoth-test-dbs_test-dbs-net`.

### Volumi Persistenti
```yaml
volumes:
  mariadb_data:    # Dati MariaDB
  mysql_data:      # Dati MySQL  
  postgres_data:   # Dati PostgreSQL
  supabase_data:   # Dati Supabase
```

### Health Checks

Ogni container ha health check specifico:

```yaml
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
  start_period: 30s
  interval: 10s
  timeout: 5s
  retries: 3
```

## 🔐 Credenziali

### Credenziali Standard
- **Username**: `thoth_user`
- **Password**: `thoth_password`

### Credenziali Speciali

#### Supabase
- **Admin User**: `supabase_admin`
- **Password**: `thoth_password`
- **Database**: `postgres`

#### SQL Server (quando attivo)
- **SA User**: `sa`
- **Password**: `ThothPassword2024!`

## 🚨 Limitazioni e Note

### Limitazioni Container
- **SQL Server**: Disabilitato su ARM64 (Apple Silicon)
- **Oracle**: Disabilitato su ARM64 (Apple Silicon)
- **Porte**: Verificare che non siano in uso da altri servizi

### Limitazioni Dati
- **Dimensioni**: SQLite file devono essere accessibili localmente
- **Encoding**: Tutti i dati sono trattati come UTF-8
- **Tipi**: Conversione automatica da SQLite verso target database

### Best Practices
- **Backup**: Schemi sono rigenerabili, dati importabili
- **Sviluppo**: Usa sempre ambiente containerizzato
- **Produzione**: Usa server cloud per SQL Server/Oracle

## 🔧 Troubleshooting Configurazione

### File non trovato
```
Error: [Errno 2] No such file or directory: '/path/to/database.sqlite'
```
**Soluzione**: Verificare `base_path` e `sqlite_file` in configurazione.

### Porta in uso
```
Error: Port 3308 is already in use
```
**Soluzione**: Cambiare porta in configurazione e riavviare.

### Schema vuoto
```
Generated schema has 0 tables
```
**Soluzione**: Verificare che il file SQLite esista e contenga tabelle.

### Import fallito
```
Import failed: Access denied for user 'thoth_user'
```
**Soluzione**: Verificare che il container sia healthy e l'utente esista.