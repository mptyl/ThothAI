# Schema Generation Guide

Guida completa alla generazione automatica degli schemi SQL per tutti i database engine supportati.

## 🎯 Panoramica

Il sistema converte automaticamente schemi SQLite in SQL specifico per ogni database engine, preservando:
- **Struttura tabelle** e relazioni
- **Tipi di dato** ottimizzati per ogni engine
- **Descrizioni colonne** come commenti nativi
- **Chiavi primarie** semplici e composite
- **Vincoli NOT NULL**

## 🔄 Processo di Generazione

### 1. Estrazione Schema SQLite
```python
def extract_schema_from_sqlite(sqlite_path):
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()
    
    # Ottieni lista tabelle
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    schemas = []
    for table_name in tables:
        # Ottieni info colonne
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        schemas.append((table_name, columns))
    
    return schemas
```

### 2. Caricamento Descrizioni
```python
def load_column_descriptions(base_path, description_dir):
    descriptions = {}
    desc_path = os.path.join(base_path, description_dir)
    
    for csv_file in os.listdir(desc_path):
        table_name = csv_file.replace('.csv', '')
        descriptions[table_name] = {}
        
        with open(os.path.join(desc_path, csv_file), 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                descriptions[table_name][row['column_name']] = row['description']
    
    return descriptions
```

### 3. Conversione Tipi di Dato

Ogni engine ha una funzione di conversione specifica:

```python
def sqlite_type_to_postgres(sqlite_type):
    type_mapping = {
        'INTEGER': 'INTEGER',
        'TEXT': 'TEXT', 
        'REAL': 'DECIMAL(10,2)',
        'BLOB': 'BYTEA',
        'DATE': 'DATE'
    }
    return type_mapping.get(sqlite_type.upper(), 'TEXT')
```

## 🗄️ Engine-Specific Generation

### 📊 MariaDB

**Caratteristiche:**
- Engine InnoDB per supporto transazioni
- Charset UTF8MB4 per supporto Unicode completo
- Commenti colonne nativi

```sql
CREATE TABLE example (
    id INT PRIMARY KEY COMMENT 'Unique identifier',
    name TEXT NOT NULL COMMENT 'Full name',
    created_date DATE COMMENT 'Creation date'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Implementazione:**
```python
def generate_mariadb_schema(db_name, schemas, descriptions_by_table):
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
            
            comment = ""
            if table_name in descriptions_by_table:
                if col_name in descriptions_by_table[table_name]:
                    desc = descriptions_by_table[table_name][col_name]
                    comment = f" COMMENT '{desc}'"
            
            column_def = f"{col_name} {col_type} {not_null}{comment}".strip()
            column_defs.append(column_def)
        
        # Gestione chiavi primarie composite
        pk_columns = [col[1] for col in columns if col[5]]
        if pk_columns:
            if len(pk_columns) == 1:
                # Single column primary key
                for i, col_def in enumerate(column_defs):
                    if col_def.startswith(pk_columns[0]):
                        column_defs[i] = col_def.replace(col_def.split()[1], 
                                                       col_def.split()[1] + " PRIMARY KEY", 1)
                        break
            else:
                # Composite primary key
                column_defs.append(f"PRIMARY KEY ({', '.join(pk_columns)})")
        
        sql += ",\n".join(column_defs)
        sql += "\n);\n\n"
    
    return sql
```

### 🐬 MySQL

**Caratteristiche:**
- Identico a MariaDB con differenze minori
- Engine InnoDB obbligatorio
- Gestione charset UTF8MB4

```sql
CREATE TABLE example (
    id INT PRIMARY KEY COMMENT 'Unique identifier',
    name TEXT NOT NULL COMMENT 'Full name'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 🐘 PostgreSQL

**Caratteristiche:**
- Extensions UUID, pgcrypto
- Commenti tramite `COMMENT ON COLUMN`
- Supporto nativo per tipi avanzati

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE example (
    id INTEGER,
    name TEXT NOT NULL,
    PRIMARY KEY (id)
);

COMMENT ON COLUMN example.id IS 'Unique identifier';
COMMENT ON COLUMN example.name IS 'Full name';
```

**Implementazione:**
```python
def generate_postgres_schema(db_name, schemas, descriptions_by_table):
    sql = f"-- PostgreSQL schema for {db_name} database\n"
    sql += f"CREATE DATABASE {db_name};\n"
    sql += f"\\c {db_name};\n\n"
    
    # Extensions
    sql += 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";\n'
    sql += 'CREATE EXTENSION IF NOT EXISTS "pgcrypto";\n\n'
    
    for table_name, columns in schemas:
        # Create table
        sql += f"CREATE TABLE {table_name} (\n"
        column_defs = []
        for col_info in columns:
            col_name = col_info[1]
            col_type = sqlite_type_to_postgres(col_info[2])
            not_null = "NOT NULL" if col_info[3] else ""
            column_def = f"    {col_name} {col_type} {not_null}".strip()
            column_defs.append(column_def)
        
        sql += ",\n".join(column_defs)
        
        # Primary key constraint
        pk_columns = [col[1] for col in columns if col[5]]
        if pk_columns:
            sql += f",\n    PRIMARY KEY ({', '.join(pk_columns)})"
        
        sql += "\n);\n\n"
        
        # Column comments
        if table_name in descriptions_by_table:
            for col_name, description in descriptions_by_table[table_name].items():
                sql += f"COMMENT ON COLUMN {table_name}.{col_name} IS '{description}';\n"
            sql += "\n"
    
    return sql
```

### ⚡ Supabase (PostgreSQL Enhanced)

**Caratteristiche Aggiuntive:**
- **JWT Extensions**: pgjwt per token management
- **Auth Schema**: Funzioni di autenticazione
- **Row Level Security**: RLS su tutte le tabelle
- **Realtime/Storage**: Schema per features Supabase

```sql
-- Supabase-specific extensions
CREATE EXTENSION IF NOT EXISTS "pgjwt";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Auth schema
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS realtime;
CREATE SCHEMA IF NOT EXISTS storage;

-- Auth functions
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid AS $$
  SELECT uuid_generate_v4()
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION auth.role() RETURNS text AS $$
  SELECT COALESCE(current_setting('request.jwt.claims', true)::json->>'role', 'anon')
$$ LANGUAGE sql STABLE;

CREATE TABLE example (
    id INTEGER,
    name TEXT NOT NULL,
    PRIMARY KEY (id)
);

-- Enable RLS
ALTER TABLE example ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to example" ON example FOR SELECT USING (true);

COMMENT ON COLUMN example.id IS 'Unique identifier';
```

### 🏢 SQL Server

**Caratteristiche:**
- **Tipi**: NVARCHAR(MAX) per supporto Unicode
- **Commenti**: Extended Properties
- **Batch**: Separatori `GO`

```sql
-- SQL Server schema for database
CREATE DATABASE example_db;
GO
USE example_db;
GO

CREATE TABLE example (
    id INT NOT NULL,
    name NVARCHAR(MAX) NOT NULL,
    PRIMARY KEY (id)
);
GO

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Unique identifier', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'example', 
    @level2type = N'COLUMN', @level2name = N'id';
```

**Conversione Tipi:**
```python
def sqlite_type_to_sqlserver(sqlite_type):
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
```

### 🏛️ Oracle

**Caratteristiche:**
- **Tipi**: CLOB per testo, NUMBER per numeri
- **Commenti**: `COMMENT ON COLUMN` nativo
- **Schema**: SQL standard Oracle

```sql
-- Oracle schema for database
CREATE TABLE example (
    id NUMBER,
    name CLOB NOT NULL,
    CONSTRAINT example_pk PRIMARY KEY (id)
);

COMMENT ON COLUMN example.id IS 'Unique identifier';
COMMENT ON COLUMN example.name IS 'Full name';
```

**Conversione Tipi:**
```python
def sqlite_type_to_oracle(sqlite_type):
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
```

## 🔧 Mapping Tipi di Dato Completo

| SQLite Type | MariaDB | MySQL | PostgreSQL | SQL Server | Oracle | Supabase |
|-------------|---------|-------|------------|------------|--------|----------|
| INTEGER | INT | INT | INTEGER | INT | NUMBER | INTEGER |
| TEXT | TEXT | TEXT | TEXT | NVARCHAR(MAX) | CLOB | TEXT |
| REAL | DECIMAL(10,2) | DECIMAL(10,2) | DECIMAL(10,2) | DECIMAL(10,2) | NUMBER(10,2) | DECIMAL(10,2) |
| FLOAT | DECIMAL(10,2) | DECIMAL(10,2) | DECIMAL(10,2) | DECIMAL(10,2) | NUMBER(10,2) | DECIMAL(10,2) |
| DOUBLE | DECIMAL(10,2) | DECIMAL(10,2) | DECIMAL(10,2) | DECIMAL(10,2) | NUMBER(10,2) | DECIMAL(10,2) |
| BLOB | BLOB | BLOB | BYTEA | VARBINARY(MAX) | BLOB | BYTEA |
| DATE | DATE | DATE | DATE | DATE | DATE | DATE |
| DATETIME | DATETIME | DATETIME | TIMESTAMP | DATETIME | TIMESTAMP | TIMESTAMP |
| VARCHAR(n) | VARCHAR(n) | VARCHAR(n) | VARCHAR(n) | NVARCHAR(n) | VARCHAR2(n) | VARCHAR(n) |

## 📋 Gestione Chiavi Primarie

### Chiave Singola
```python
# SQLite: id INTEGER PRIMARY KEY
# Output per tutti gli engine:
pk_columns = [col[1] for col in columns if col[5]]  # col[5] = pk flag

if len(pk_columns) == 1:
    # Aggiungi PRIMARY KEY alla definizione colonna
    column_def += " PRIMARY KEY"
```

### Chiave Composita
```python
# SQLite: PRIMARY KEY (col1, col2)
if len(pk_columns) > 1:
    # Aggiungi constraint separato
    sql += f"PRIMARY KEY ({', '.join(pk_columns)})"
```

### Esempi Output

**Chiave Singola:**
```sql
-- MariaDB/MySQL
id INT PRIMARY KEY COMMENT 'Unique ID'

-- PostgreSQL/Supabase  
id INTEGER,
PRIMARY KEY (id)

-- SQL Server
id INT NOT NULL,
PRIMARY KEY (id)

-- Oracle
id NUMBER,
CONSTRAINT table_pk PRIMARY KEY (id)
```

**Chiave Composita:**
```sql
-- Tutti gli engine
race_id INT NOT NULL,
driver_id INT NOT NULL,
lap INT NOT NULL,
PRIMARY KEY (race_id, driver_id, lap)
```

## 🏗️ Struttura File Output

### Directory Layout
```
db-init/
├── mariadb/
│   ├── california_schools.sql
│   ├── european_football_2.sql
│   └── formula_1.sql
├── mysql/
│   ├── california_schools.sql
│   ├── european_football_2.sql
│   └── formula_1.sql
├── postgres/
│   ├── california_schools.sql
│   ├── european_football_2.sql
│   └── formula_1.sql
├── supabase/
│   ├── california_schools.sql
│   ├── european_football_2.sql
│   └── formula_1.sql
├── sqlserver/
│   ├── california_schools.sql
│   ├── european_football_2.sql
│   └── formula_1.sql
└── oracle/
    ├── california_schools.sql
    ├── european_football_2.sql
    └── formula_1.sql
```

### Dimensioni File Tipiche

| Database | MariaDB | MySQL | PostgreSQL | Supabase | SQL Server | Oracle |
|----------|---------|-------|------------|----------|------------|--------|
| california_schools | ~6KB | ~6KB | ~4KB | ~8KB | ~22KB | ~9KB |
| european_football_2 | ~8KB | ~8KB | ~6KB | ~12KB | ~31KB | ~13KB |
| formula_1 | ~10KB | ~10KB | ~7KB | ~15KB | ~25KB | ~9KB |

## 🚀 Esecuzione

### Comando Principale
```bash
python generate-all-schemas.py
```

### Output Tipico
```
Generating schemas for thoth-test-dbs...
Processing california_schools...
  Generated MariaDB schema: db-init/mariadb/california_schools.sql
  Generated MySQL schema: db-init/mysql/california_schools.sql
  Generated PostgreSQL schema: db-init/postgres/california_schools.sql
  Generated SQL Server schema: db-init/sqlserver/california_schools.sql
  Generated Oracle schema: db-init/oracle/california_schools.sql
  Generated Supabase schema: db-init/supabase/california_schools.sql
Processing european_football_2...
  ...
Schema generation completed!
```

### Via Management Script
```bash
python manage-thoth-test-dbs.py generate-schemas
```

## 🔍 Verifica Output

### Controllo Sintassi SQL

**PostgreSQL:**
```bash
psql -h localhost -p 5434 -U thoth_user -d template1 -f db-init/postgres/california_schools.sql --dry-run
```

**MariaDB:**
```bash
mysql -h localhost -P 3308 -u thoth_user -p < db-init/mariadb/california_schools.sql
```

**MySQL:**
```bash
mysql -h localhost -P 3309 -u thoth_user -p < db-init/mysql/california_schools.sql
```

### Controllo Descrizioni

```bash
# PostgreSQL - verifica commenti
psql -c "\\d+ table_name"

# MariaDB/MySQL - verifica commenti
SHOW FULL COLUMNS FROM table_name;

# SQL Server - verifica extended properties
SELECT * FROM sys.extended_properties;
```

## 🚨 Troubleshooting

### Schema Vuoto
**Problema**: File SQL generato vuoto o incompleto
**Causa**: Database SQLite non accessibile o vuoto
**Soluzione**: 
```bash
# Verifica percorso database
python -c "import sqlite3; print(sqlite3.connect('path/to/db.sqlite').execute('SELECT count(*) FROM sqlite_master').fetchone())"
```

### Descrizioni Mancanti
**Problema**: Commenti non generati
**Causa**: File CSV descrizioni non trovati o malformati
**Soluzione**:
```bash
# Verifica file CSV
ls -la /path/to/database_description/
head -5 /path/to/database_description/table.csv
```

### Errori Sintassi SQL
**Problema**: SQL generato non valido
**Causa**: Caratteri speciali in nomi colonne/descrizioni
**Soluzione**: Escape automatico implementato per ogni engine

### Performance Lenta
**Problema**: Generazione schemi troppo lenta
**Causa**: Database SQLite molto grandi
**Ottimizzazione**: 
- Cache schema extraction
- Parallel processing per database multipli

## 🔄 Estensioni Future

### Nuovi Engine
Per aggiungere supporto per nuovi database:

1. **Conversione Tipi**: Implementare `sqlite_type_to_newengine()`
2. **Generator**: Implementare `generate_newengine_schema()`
3. **Configurazione**: Aggiungere engine a `database-config.yml`
4. **Testing**: Aggiungere test per sintassi SQL

### Nuove Features
- **Foreign Keys**: Estrazione e generazione FK da SQLite
- **Indexes**: Creazione indici automatica
- **Views**: Support per viste database
- **Stored Procedures**: Generazione procedure specifiche