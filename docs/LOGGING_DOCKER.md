# Gestione Log - Ambiente Docker

## 📋 Panoramica

In ambiente Docker, ThothAI implementa un sistema di logging avanzato che combina:
- **Visibilità in tempo reale** tramite Docker Desktop e `docker logs`
- **Persistenza su volume** per analisi e backup
- **Pulizia automatica** tramite cron job
- **Configurazione centralizzata** tramite variabili d'ambiente

## 🏗️ Architettura del Sistema di Logging

### Doppio Output

Tutti i servizi scrivono i log su due canali:

1. **Console (stdout/stderr)**: Per visibilità immediata in Docker Desktop
2. **File su volume**: Per persistenza e pulizia automatica

```yaml
# docker-compose.yml
volumes:
  thoth-logs:         # Volume condiviso per tutti i log
    name: thoth-logs
```

### Struttura dei Log nel Container

```
/app/logs/                       # Volume montato thoth-logs
├── thoth.log                   # Log backend Django
├── thoth.log.2024-01-15        # Log ruotati backend
├── sql-generator.log            # Log SQL generator
├── sql-generator.log.1          # Log ruotati SQL generator
└── sql-generator-app.log        # Log applicazione
```

## ⚙️ Configurazione

### Variabili d'Ambiente

Le variabili sono definite in `.env.docker` (generato automaticamente da `config.yml.local`):

```bash
# Livello log backend
BACKEND_LOGGING_LEVEL=INFO

# Livello log frontend e SQL generator
FRONTEND_LOGGING_LEVEL=INFO

# Path database backend (isolato)
DB_NAME_DOCKER=/app/backend_db/db.sqlite3

# Path dati utente
DB_ROOT_PATH=/app/data
```

### Livelli di Logging

- `DEBUG`: Informazioni dettagliate (alta verbosità)
- `INFO`: Operazioni normali (default)
- `WARNING`: Situazioni anomale ma gestibili
- `ERROR`: Errori che non bloccano il sistema
- `CRITICAL`: Errori critici del sistema

## 🔄 Rotazione e Pulizia Automatica

### Sistema Cron Integrato

Il container backend include un cron job che esegue automaticamente la pulizia:

```bash
# Esecuzione ogni 6 ore
0 */6 * * * python manage.py cleanup_logs
```

### Politica di Retention

- **Compressione**: Non utilizzata in Docker (spazio su volume)
- **Rimozione**: Log più vecchi di 7 giorni (configurabile)
- **Pattern gestiti**:
  - `thoth.log.*` (backend)
  - `sql-generator.log.*` (SQL generator)
  - `*.log.gz` (eventuali compressi)

## 📊 Monitoraggio dei Log

### Visualizzazione in Tempo Reale

```bash
# Log del backend
docker logs -f backend

# Log del SQL generator
docker logs -f sql-generator

# Ultimi 100 log con timestamp
docker logs --tail 100 -t backend

# Log da un momento specifico
docker logs --since 2h backend  # Ultimi 2 ore
```

### Accesso ai File di Log

```bash
# Esegui shell nel container
docker exec -it backend bash
cd /app/logs
tail -f thoth.log

# Copia log sul host
docker cp backend:/app/logs/thoth.log ./thoth-backup.log

# Visualizza direttamente dal host
docker exec backend tail -n 100 /app/logs/thoth.log
```

## 🧹 Gestione Manuale

### Pulizia Manuale

Se necessario, puoi eseguire la pulizia manualmente:

```bash
# Esegui comando di pulizia
docker exec backend python manage.py cleanup_logs

# Con parametri personalizzati
docker exec backend python manage.py cleanup_logs --days 3

# Modalità dry-run
docker exec backend python manage.py cleanup_logs --dry-run
```

### Backup dei Log

Per salvare i log prima di una pulizia o per analisi:

```bash
# Backup completo della directory log
docker cp backend:/app/logs ./backup-logs-$(date +%Y%m%d)

# Backup specifico file
docker cp backend:/app/logs/thoth.log ./thoth-$(date +%Y%m%d).log
```

## 🔍 Docker Desktop

### Visualizzazione in Docker Desktop

1. Apri Docker Desktop
2. Vai alla sezione "Containers"
3. Clicca sul container desiderato (backend, sql-generator)
4. Tab "Logs" mostra l'output in tempo reale

### Funzionalità Docker Desktop

- **Ricerca**: Usa Ctrl+F per cercare nei log
- **Download**: Esporta i log visibili
- **Clear**: Pulisce la visualizzazione (non cancella i file)
- **Auto-scroll**: Segue automaticamente i nuovi log

## 📈 Metriche e Statistiche

### Controllo Spazio Volume

```bash
# Dimensione del volume logs
docker volume inspect thoth-logs | grep -A 5 "UsageData"

# Spazio utilizzato nel container
docker exec backend du -sh /app/logs

# Dettaglio per file
docker exec backend ls -lah /app/logs
```

### Analisi Log

```bash
# Conta errori nelle ultime 24 ore
docker exec backend grep -c "ERROR" /app/logs/thoth.log

# Analizza pattern di errori
docker exec backend grep "ERROR" /app/logs/thoth.log | tail -20

# Statistiche SQL generator
docker exec sql-generator wc -l /app/logs/sql-generator.log
```

## ⚠️ Best Practices

### Produzione

1. **Mantieni INFO come livello default**: Bilanciamento tra dettaglio e performance
2. **Monitora lo spazio del volume**: I volumi Docker hanno limiti
3. **Backup regolari**: Esporta log importanti prima della pulizia
4. **Centralizzazione**: Considera log aggregation per deployment multi-nodo

### Troubleshooting

1. **Aumenta temporaneamente il livello**:
   ```bash
   # Modifica .env.docker
   BACKEND_LOGGING_LEVEL=DEBUG
   # Riavvia container
   docker-compose restart backend
   ```

2. **Analisi post-mortem**:
   ```bash
   # Salva log per analisi
   docker logs backend > backend-crash.log 2>&1
   ```

## 🛠️ Risoluzione Problemi

### Log non visibili in Docker Desktop

Se i log non appaiono in Docker Desktop:

1. Verifica che il servizio scriva su stdout:
   ```bash
   docker exec backend ps aux | grep python
   ```

2. Controlla la configurazione del logging:
   ```bash
   docker exec backend env | grep LOGGING
   ```

### Volume pieno

Se il volume dei log è pieno:

1. Pulizia immediata:
   ```bash
   docker exec backend python manage.py cleanup_logs --days 1
   ```

2. Ricrea il volume (perdita dati):
   ```bash
   docker-compose down
   docker volume rm thoth-logs
   docker-compose up -d
   ```

### Cron non funzionante

Se la pulizia automatica non funziona:

1. Verifica cron attivo:
   ```bash
   docker exec backend service cron status
   ```

2. Controlla crontab:
   ```bash
   docker exec backend crontab -l
   ```

3. Verifica log di cron:
   ```bash
   docker exec backend cat /var/log/cron.log
   ```

## 🔐 Sicurezza

### Protezione dei Log

1. **Non esporre il volume logs** pubblicamente
2. **Sanitizza i log** prima di condividerli (rimuovi API keys, password)
3. **Limita l'accesso** al volume in produzione
4. **Cripta i backup** dei log sensibili

### Compliance

Per ambienti regolamentati:

1. **Retention policy**: Configura secondo i requisiti normativi
2. **Audit trail**: I log possono contenere dati di audit
3. **Data residency**: Assicurati che i volumi rispettino i requisiti geografici

## 📝 Note Finali

Il sistema di logging Docker di ThothAI è progettato per:
- **Semplicità**: Visibilità immediata senza configurazioni complesse
- **Affidabilità**: Persistenza su volume con pulizia automatica
- **Flessibilità**: Configurabile per diversi ambienti
- **Performance**: Minimo impatto sulle prestazioni del sistema

Per deployment enterprise, considera l'integrazione con stack di logging dedicati come ELK o Splunk.