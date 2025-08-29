# Setup and Usage Guide

Guida passo-passo per installare, configurare e utilizzare il sistema Thoth Unified Test Databases.

## 📋 Prerequisiti

### Sistema Operativo
- **macOS**: Testato su macOS (Apple Silicon e Intel)
- **Linux**: Ubuntu/Debian, CentOS/RHEL
- **Windows**: Windows 10/11 con WSL2

### Software Richiesto

#### Docker
```bash
# macOS (Homebrew)
brew install docker docker-compose

# Linux (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install docker.io docker-compose

# Windows
# Installare Docker Desktop da https://docker.com
```

#### Python 3.8+
```bash
# Verifica versione
python3 --version

# macOS
brew install python3

# Linux (Ubuntu/Debian)
sudo apt-get install python3 python3-pip

# Windows (WSL2)
sudo apt-get install python3 python3-pip
```

#### Librerie Python
```bash
pip install pyyaml psycopg2-binary mysql-connector-python pymysql
```

## 🚀 Installazione Rapida

### 1. Clone del Repository
```bash
cd /path/to/your/projects
git clone <repository-url>
cd database-tools/unified-test-dbs
```

### 2. Verifica Configurazione
```bash
# Controlla che i percorsi database siano corretti
python manage-thoth-test-dbs.py config
```

### 3. Setup Completo
```bash
# Setup automatico completo
python manage-thoth-test-dbs.py setup
```

### 4. Verifica Installazione
```bash
# Controlla che tutti i servizi siano attivi
python manage-thoth-test-dbs.py health
```

**Output atteso:**
```
✓ MariaDB: Healthy
✓ MySQL: Healthy  
✓ PostgreSQL: Healthy
✓ Supabase: Healthy
✓ Adminer: Healthy
✓ PostgREST: Healthy
✓ Supabase REST API: Healthy
```

### 5. Accesso Web
Vai su **http://localhost:8080** per accedere ad Adminer.

## 🔧 Installazione Manuale

Se il setup automatico fallisce, procedi manualmente:

### Step 1: Avvio Container
```bash
# Avvia tutti i container
docker-compose -f thoth-test-dbs.yml up -d

# Verifica che i container siano attivi
docker ps
```

### Step 2: Generazione Schemi
```bash
# Genera schemi per tutti i database engine
python generate-all-schemas.py
```

### Step 3: Attesa Inizializzazione
```bash
# Aspetta che i database siano pronti (30-60 secondi)
sleep 60

# Verifica stato
python manage-thoth-test-dbs.py health
```

### Step 4: Import Dati
```bash
# Importa dati in tutti i database
python import-all-data.py
```

## 🗄️ Primo Utilizzo

### Accesso via Adminer

1. **Apri Browser**: `http://localhost:8080`
2. **Seleziona Database**:
   - **Sistema**: MySQL/MariaDB/PostgreSQL
   - **Server**: `mariadb-server`, `mysql-server`, `postgres-server`, `supabase-server`
   - **Utente**: `thoth_user` (o `supabase_admin` per Supabase)
   - **Password**: `thoth_password`
   - **Database**: `california_schools`, `european_football_2`, `formula_1`

> **⚠️ Nota Supabase**: Se riscontri errori di autenticazione con client esterni (DBeaver, pgAdmin),
> esegui il setup dell'autenticazione: `python setup_supabase_auth.py`

### Accesso via Client Esterno

#### DBeaver
1. **Nuova Connessione** → Seleziona database type
2. **Configurazione**:
   - **Host**: `localhost`
   - **Porta**: `3308` (MariaDB), `3309` (MySQL), `5434` (PostgreSQL), `5435` (Supabase)
   - **Database**: `california_schools` (o altro)
   - **Utente/Password**: Come sopra

#### 🔐 Risoluzione Problemi Autenticazione Supabase

Se riscontri errori come `password authentication failed for user 'thoth_user'` con Supabase:

1. **Esegui il setup automatico**:
   ```bash
   python setup_supabase_auth.py
   ```

2. **Verifica manualmente**:
   ```bash
   # Test connessione
   PGPASSWORD=thoth_password psql -h localhost -p 5435 -U thoth_user -d california_schools -c "SELECT COUNT(*) FROM frpm;"
   ```

3. **Consulta la guida completa**: [SUPABASE_AUTHENTICATION_GUIDE.md](SUPABASE_AUTHENTICATION_GUIDE.md)

#### phpMyAdmin (per MySQL/MariaDB)
```bash
# Aggiungi phpMyAdmin se necessario
docker run --name phpmyadmin -d --network thoth-test-dbs_test-dbs-net -p 8081:80 phpmyadmin/phpmyadmin
```

### Test Query di Base

#### SQL di esempio per california_schools:
```sql
-- Conta scuole per county
SELECT County, COUNT(*) as school_count 
FROM schools 
GROUP BY County 
ORDER BY school_count DESC 
LIMIT 10;

-- Media punteggi SAT per district
SELECT dname, AVG(AvgScrMath) as avg_math_score
FROM satscores 
WHERE AvgScrMath IS NOT NULL
GROUP BY dname
ORDER BY avg_math_score DESC
LIMIT 10;
```

## 🔄 Workflow Sviluppo

### Scenario: Aggiungere Nuovo Database

#### 1. Preparazione Dati
```bash
# Crea directory per nuovo database
mkdir -p /Users/mp/data/dev_20240627/dev_databases/new_database
mkdir -p /Users/mp/data/dev_20240627/dev_databases/new_database/database_description

# Copia database SQLite
cp source.sqlite /Users/mp/data/dev_20240627/dev_databases/new_database/new_database.sqlite
```

#### 2. Creazione Descrizioni
```bash
# Crea file CSV per ogni tabella
# Formato: column_name,description
cat > /Users/mp/data/dev_20240627/dev_databases/new_database/database_description/table1.csv << EOF
column_name,description
id,Unique identifier
name,Full name
created_at,Creation timestamp
EOF
```

#### 3. Configurazione
```yaml
# Aggiungi in database-config.yml
databases:
  new_database:
    enabled: true
    sqlite_file: "new_database/new_database.sqlite"
    description_dir: "new_database/database_description"
    description: "Description of the new database"
```

#### 4. Generazione e Test
```bash
# Genera schemi
python generate-all-schemas.py

# Riavvia sistema per reload configurazione
python manage-thoth-test-dbs.py restart

# Importa dati
python import-all-data.py

# Verifica
python manage-thoth-test-dbs.py health
```

### Scenario: Modifica Schema Esistente

#### 1. Update Database SQLite
```bash
# Modifica database sorgente
sqlite3 /path/to/source.sqlite
.tables
ALTER TABLE existing_table ADD COLUMN new_column TEXT;
```

#### 2. Update Descrizioni
```bash
# Aggiorna CSV descrizioni
echo "new_column,Description of new column" >> table.csv
```

#### 3. Rigenera Schemi
```bash
# Rigenera tutti gli schemi
python generate-all-schemas.py

# Re-importa dati (attenzione: cancella dati esistenti!)
python import-all-data.py
```

### Scenario: Debug Performance

#### 1. Analisi Container
```bash
# Resource usage
docker stats

# Log specifico container
docker logs mariadb-server --tail 50

# Connessioni attive
docker exec mariadb-server mysql -u root -p -e "SHOW PROCESSLIST"
```

#### 2. Ottimizzazione Query
```sql
-- MariaDB/MySQL
EXPLAIN SELECT * FROM large_table WHERE condition;
SHOW INDEX FROM large_table;

-- PostgreSQL
EXPLAIN ANALYZE SELECT * FROM large_table WHERE condition;
\d+ large_table
```

#### 3. Monitoring
```bash
# Health check continuo
watch -n 5 'python manage-thoth-test-dbs.py health'

# Log aggregati
python manage-thoth-test-dbs.py logs | grep ERROR
```

## 🔧 Configurazione Avanzata

### Modificare Porte
Se le porte di default sono in conflitto:

```yaml
# database-config.yml
servers:
  mariadb:
    port: 3318  # Cambia da 3308
  mysql:
    port: 3319  # Cambia da 3309
  # etc...
```

```bash
# Riavvia con nuova configurazione
python manage-thoth-test-dbs.py restart
```

### Memory Limits
Per sistemi con RAM limitata:

```yaml
# thoth-test-dbs.yml - aggiungi a ogni servizio
services:
  mariadb-server:
    # ... configurazione esistente
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

### Persistent Volumes
Per preservare dati tra riavvii:

```bash
# Backup volumi
docker run --rm -v thoth-test-dbs_mariadb_data:/data -v $(pwd):/backup alpine tar czf /backup/mariadb_backup.tar.gz /data

# Restore volumi
docker run --rm -v thoth-test-dbs_mariadb_data:/data -v $(pwd):/backup alpine tar xzf /backup/mariadb_backup.tar.gz -C /
```

### Network Isolation
Per isolare network:

```yaml
# thoth-test-dbs.yml
networks:
  test-dbs-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## 🚨 Troubleshooting Comune

### Problema: Porte in Uso
```bash
# Identifica processo che usa porta
lsof -i :3308

# Termina processo
kill -9 <PID>

# Oppure cambia porta in configurazione
```

### Problema: Container Non Si Avvia
```bash
# Verifica log container
docker logs mariadb-server

# Rimuovi container corrotto
docker stop mariadb-server
docker rm mariadb-server
docker volume rm thoth-test-dbs_mariadb_data

# Riavvia
python manage-thoth-test-dbs.py start
```

### Problema: Import Dati Fallisce
```bash
# Verifica che database sia vuoto
docker exec mariadb-server mysql -u thoth_user -p -e "USE california_schools; SHOW TABLES;"

# Cancella database e ricrea
docker exec mariadb-server mysql -u root -p -e "DROP DATABASE california_schools; CREATE DATABASE california_schools;"

# Re-importa
python import-all-data.py
```

### Problema: Schema Generation Errors
```bash
# Verifica percorsi
python -c "
import yaml
with open('database-config.yml') as f:
    config = yaml.safe_load(f)
print('Base path:', config['base_path'])
"

# Testa accesso SQLite
python -c "
import sqlite3
conn = sqlite3.connect('/path/to/database.sqlite')
print('Tables:', conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall())
"
```

### Problema: Adminer Non Accessibile
```bash
# Verifica container Adminer
docker ps | grep adminer

# Verifica network
docker network inspect thoth-test-dbs_test-dbs-net

# Restart Adminer
docker restart thoth-adminer
```

## 📊 Monitoring e Maintenance

### Log Rotation
```bash
# Setup logrotate per container logs
sudo cat > /etc/logrotate.d/docker-containers << EOF
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    missingok
    delaycompress
    copytruncate
}
EOF
```

### Backup Automatico
```bash
#!/bin/bash
# backup-thoth-dbs.sh

BACKUP_DIR="/backup/thoth-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup configuration
cp database-config.yml $BACKUP_DIR/
cp thoth-test-dbs.yml $BACKUP_DIR/

# Backup data volumes
for volume in mariadb_data mysql_data postgres_data supabase_data; do
    docker run --rm -v thoth-test-dbs_${volume}:/data -v ${BACKUP_DIR}:/backup alpine tar czf /backup/${volume}.tar.gz /data
done

echo "Backup completed: $BACKUP_DIR"
```

### Health Check Automatico
```bash
#!/bin/bash
# health-check.sh

if ! python manage-thoth-test-dbs.py health | grep -q "✗"; then
    echo "All services healthy"
    exit 0
else
    echo "Some services unhealthy, restarting..."
    python manage-thoth-test-dbs.py restart
    exit 1
fi
```

### Cron Job Setup
```bash
# Aggiungi a crontab
crontab -e

# Health check ogni 15 minuti
*/15 * * * * /path/to/thoth/health-check.sh

# Backup giornaliero alle 2:00
0 2 * * * /path/to/thoth/backup-thoth-dbs.sh
```

## 🎯 Prossimi Passi

### Per Sviluppatori
1. **Esplora Dati**: Usa Adminer per familiarizzare con i dataset
2. **Test Query**: Prova query complesse su dataset reali
3. **Performance**: Benchmarka query su diversi engine
4. **Extend**: Aggiungi nuovi dataset per i tuoi use case

### Per DevOps
1. **Production Setup**: Pianifica deploy su cloud per SQL Server/Oracle
2. **Monitoring**: Integra con Prometheus/Grafana
3. **Backup**: Automatizza backup e disaster recovery
4. **Scaling**: Considera sharding per dataset grandi

### Per Data Scientists
1. **Jupyter Integration**: Connetti notebook ai database
2. **Data Export**: Usa REST API per data extraction
3. **Visualization**: Connetti a Tableau/PowerBI
4. **ML Pipelines**: Integra con workflow di machine learning

## 📚 Risorse Aggiuntive

- **README.md**: Panoramica completa del sistema
- **DATABASE_CONFIG.md**: Guida configurazione database
- **SCHEMA_GENERATION.md**: Dettagli generazione schemi SQL
- **Docker Compose**: `thoth-test-dbs.yml` per reference container
- **Configuration**: `database-config.yml` per personalizzazioni