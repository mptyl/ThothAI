# Gestione Log - Sviluppo Locale

## 📋 Panoramica

Durante lo sviluppo locale, ThothAI genera log per tutti i servizi principali. La gestione dei log è ottimizzata per fornire informazioni dettagliate durante il debug mantenendo sotto controllo lo spazio su disco.

## 📁 Struttura dei Log

I log vengono salvati in diverse directory in base al servizio:

```
ThothAI/
├── backend/
│   └── logs/
│       └── thoth.log          # Log del backend Django
├── frontend/
│   └── sql_generator/
│       └── logs/
│           └── temp/
│               ├── sql-generator.log    # Log del generatore SQL
│               └── thoth_app.log        # Log dell'applicazione
└── logs/                      # Directory per log centralizzati (futura espansione)
```

## ⚙️ Configurazione

### Variabili d'Ambiente

I livelli di logging sono configurabili tramite il file `.env.local`:

```bash
# Livello di log per il backend Django
BACKEND_LOGGING_LEVEL=INFO

# Livello di log per frontend e SQL generator
FRONTEND_LOGGING_LEVEL=INFO
```

### Livelli Disponibili

- `DEBUG`: Informazioni dettagliate per debug
- `INFO`: Informazioni generali sul funzionamento (default)
- `WARNING`: Avvisi su potenziali problemi
- `ERROR`: Errori che non interrompono l'esecuzione
- `CRITICAL`: Errori critici che possono causare interruzioni

## 🔄 Rotazione dei Log

### Backend (Django)

Il backend utilizza `TimedRotatingFileHandler` che ruota automaticamente i log:
- **Rotazione**: ogni mezzanotte
- **Pattern file**: `thoth.log.YYYY-MM-DD`
- **Retention**: gestita manualmente tramite script di pulizia

### SQL Generator

Il generatore SQL utilizza `RotatingFileHandler`:
- **Dimensione massima**: 10 MB per file
- **File di backup**: massimo 5 (`sql-generator.log.1`, `.2`, etc.)
- **Rotazione automatica**: quando il file raggiunge 10 MB

## 🧹 Pulizia Manuale dei Log

ThothAI fornisce due script per la pulizia manuale dei log:

### Script Bash

```bash
# Pulizia con impostazioni predefinite (mantiene 7 giorni, comprime dopo 1 giorno)
./scripts/cleanup-logs.sh

# Specifica giorni da mantenere e quando comprimere
./scripts/cleanup-logs.sh 30 3  # Mantiene 30 giorni, comprime dopo 3

# Modalità dry-run (mostra cosa verrebbe fatto senza modificare i file)
./scripts/cleanup-logs.sh --dry-run

# Visualizza help
./scripts/cleanup-logs.sh --help
```

### Script Python

```bash
# Pulizia con impostazioni predefinite
python scripts/cleanup_logs.py

# Con parametri personalizzati
python scripts/cleanup_logs.py --days 30 --compress-after 3

# Modalità dry-run
python scripts/cleanup_logs.py --dry-run

# Visualizza help
python scripts/cleanup_logs.py --help
```

## 📊 Funzionalità degli Script

Entrambi gli script offrono:

1. **Compressione Automatica**: I log più vecchi del periodo specificato vengono compressi con gzip
2. **Rimozione Sicura**: I log molto vecchi vengono rimossi definitivamente
3. **Statistiche**: Mostra lo spazio occupato prima e dopo la pulizia
4. **Modalità Dry-Run**: Permette di vedere cosa verrebbe fatto senza modificare i file
5. **Gestione Multi-Servizio**: Pulisce i log di tutti i servizi contemporaneamente

## 💡 Best Practices

### Durante lo Sviluppo

1. **Livello DEBUG solo quando necessario**: Genera molti log e può riempire rapidamente il disco
2. **Pulizia settimanale**: Esegui lo script di pulizia almeno una volta a settimana
3. **Monitora lo spazio**: Controlla periodicamente lo spazio occupato dai log

### Risoluzione Problemi

Per analizzare problemi specifici:

```bash
# Visualizza ultimi errori del backend
tail -f backend/logs/thoth.log | grep ERROR

# Visualizza log in tempo reale del SQL generator
tail -f frontend/sql_generator/logs/temp/sql-generator.log

# Cerca un pattern specifico nei log
grep "workspace_id" backend/logs/thoth.log*
```

## 🔍 Monitoraggio

### Controllo Spazio Occupato

```bash
# Spazio totale occupato dai log
du -sh backend/logs frontend/sql_generator/logs

# Dettaglio per directory
du -h backend/logs frontend/sql_generator/logs
```

### Log Watching

Per monitorare i log in tempo reale durante lo sviluppo:

```bash
# Backend
tail -f backend/logs/thoth.log

# SQL Generator
tail -f frontend/sql_generator/logs/temp/sql-generator.log

# Tutti i log contemporaneamente (richiede multitail)
multitail backend/logs/thoth.log frontend/sql_generator/logs/temp/*.log
```

## ⚠️ Note Importanti

1. **Non committare i log**: Le directory dei log sono già nel `.gitignore`
2. **Backup prima di pulizia massiva**: Se hai log importanti, fai un backup prima di eseguire la pulizia
3. **Spazio disco**: Mantieni almeno 1 GB di spazio libero per il corretto funzionamento
4. **Performance**: Log level DEBUG può impattare le performance in sviluppo

## 🆘 Troubleshooting

### Log non generati

Se i log non vengono generati:

1. Verifica che le directory esistano:
   ```bash
   mkdir -p backend/logs
   mkdir -p frontend/sql_generator/logs/temp
   ```

2. Controlla i permessi:
   ```bash
   chmod 755 backend/logs
   chmod 755 frontend/sql_generator/logs/temp
   ```

3. Verifica le variabili d'ambiente in `.env.local`

### Spazio disco esaurito

Se lo spazio su disco si esaurisce:

1. Esegui immediatamente la pulizia:
   ```bash
   ./scripts/cleanup-logs.sh 1 0  # Mantiene solo 1 giorno
   ```

2. Rimuovi manualmente i log più vecchi:
   ```bash
   find backend/logs frontend/sql_generator/logs -name "*.log.*" -delete
   ```

3. Considera di ridurre il livello di logging a WARNING o ERROR