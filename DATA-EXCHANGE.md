# DATA-EXCHANGE.md

## Sistema di Import/Export CSV in ThothAI

Il sistema di import/export CSV di ThothAI permette lo scambio di dati tra diversi ambienti (locale e Docker) attraverso file CSV. Il sistema utilizza la directory `data_exchange` come punto di scambio universale tra host e container Docker.

## Come Funziona l'Interscambio Host ↔ Docker

### Il Concetto Chiave: Bind Mount

La directory `data_exchange` NON è un volume Docker isolato, ma un **bind mount** che collega direttamente una directory del tuo computer (host) con una directory dentro il container Docker.

Nel `docker-compose.yml`:
```yaml
backend:
  volumes:
    - ./data_exchange:/app/data_exchange
```

Questa configurazione significa:
- `./data_exchange` = directory sul TUO computer (relativa alla root del progetto ThothAI)
- `/app/data_exchange` = directory DENTRO il container Docker
- **Sono la STESSA directory**: qualsiasi file scritto in una è immediatamente visibile nell'altra

### Differenza tra Volume Types in Docker

| Tipo | Sintassi | Accessibilità Host | Uso in ThothAI |
|------|----------|-------------------|----------------|
| **Bind Mount** | `./data_exchange:/app/data_exchange` | ✅ Diretto dal filesystem | `data_exchange` (import/export) |
| **Named Volume** | `thoth-secrets:/secrets` | ❌ Gestito da Docker | Secrets, database storage |

### Flusso di Export (Docker → Host)

```
1. Admin Django (browser) → Click "Export to CSV"
   ↓
2. Django (nel container) scrive: /app/data_exchange/workspace.csv
   ↓
3. File IMMEDIATAMENTE visibile su host: ./data_exchange/workspace.csv
   ↓
4. Utente può aprire con Excel/VS Code/etc dal proprio computer
```

**Esempio pratico:**
```bash
# PRIMA dell'export
$ ls ./data_exchange/
# (directory vuota)

# Fai export da Django Admin (http://localhost:8040/admin)
# Seleziona Workspaces → Actions → Export to CSV

# SUBITO DOPO
$ ls ./data_exchange/
workspace.csv

# Puoi aprirlo direttamente dal tuo computer
$ open ./data_exchange/workspace.csv  # macOS
$ start ./data_exchange/workspace.csv # Windows
```

### Flusso di Import (Host → Docker)

```
1. Utente copia file CSV in: ./data_exchange/users.csv
   ↓
2. File IMMEDIATAMENTE visibile nel container: /app/data_exchange/users.csv
   ↓
3. Django Admin può importarlo con "Import from CSV"
```

**Esempio pratico:**
```bash
# Copia un file nella directory dal tuo computer
$ cp ~/Downloads/users_backup.csv ./data_exchange/users.csv

# Il file è SUBITO disponibile in Docker
$ docker exec -it thoth-backend ls /app/data_exchange/
users.csv

# Ora puoi importarlo da Django Admin
```

## Directory di Scambio Dati

### Directory Principale
- **Sul tuo computer (host)**: `ThothAI/data_exchange/`
- **Dentro Docker**: `/app/data_exchange/`
- **Sono la STESSA directory** grazie al bind mount

### Verifica del Bind Mount
```bash
# Crea un file test dal tuo computer
echo "test dal host" > ./data_exchange/test.txt

# Verifica che sia visibile in Docker
docker exec -it thoth-backend cat /app/data_exchange/test.txt
# Output: test dal host

# Crea un file da Docker
docker exec -it thoth-backend bash -c 'echo "test da docker" > /app/data_exchange/test2.txt'

# Verifica che sia visibile sul tuo computer
cat ./data_exchange/test2.txt
# Output: test da docker
```

## Funzionamento dell'Import/Export

### Export CSV

#### Da Admin Interface
1. **Accesso**: http://localhost:8040/admin → Seleziona modello → Seleziona record(i)
2. **Azione**: Dal menu "Actions" → "Export selected to CSV"
3. **Risultato**: File CSV immediatamente disponibile in `./data_exchange/{model_name}.csv` sul TUO computer
4. **Apertura**: Puoi aprire il file con qualsiasi programma (Excel, Numbers, LibreOffice, VS Code, etc.)

#### Da Command Line
```bash
# Esegui export da Docker
docker exec -it thoth-backend python manage.py export_models

# I file sono SUBITO disponibili sul tuo computer
ls ./data_exchange/
# workspace.csv sqldb.csv sqltable.csv ...

# Oppure in locale (se hai l'ambiente configurato)
cd backend
uv run python manage.py export_models
```

### Import CSV

#### Da Admin Interface
1. **Preparazione**: Metti il file CSV nella directory `./data_exchange/` del TUO computer
2. **Naming**: Il file deve chiamarsi `{model_name}.csv` (es: `workspace.csv`, `users.csv`)
3. **Accesso**: http://localhost:8040/admin → Seleziona modello
4. **Azione**: Dal menu "Actions" → "Import from CSV"
5. **Processo**: Django legge il file da `/app/data_exchange/` (che è la stessa directory)

#### Da Command Line
```bash
# Prima: metti il file nella directory sul tuo computer
cp ~/my_backup/workspace.csv ./data_exchange/

# Poi importa da Docker
docker exec -it thoth-backend python manage.py import_single_csv workspace

# O in locale
cd backend
uv run python manage.py import_single_csv workspace
```

## Gestione Directory

### Creazione Directory
La directory `data_exchange` deve esistere prima di avviare Docker:
```bash
# Crea la directory se non esiste
mkdir -p ./data_exchange

# Verifica i permessi (deve essere scrivibile)
ls -la ./data_exchange

# Se necessario, sistema i permessi
chmod 755 ./data_exchange
```

### Permessi
Il sistema verifica automaticamente:
1. Esistenza della directory
2. Permessi di scrittura
3. Spazio su disco disponibile

### Troubleshooting Bind Mount

Se i file non sono visibili tra host e Docker:

```bash
# Verifica che il container usi il bind mount corretto
docker inspect thoth-backend | grep -A 5 Mounts

# Dovrebbe mostrare qualcosa come:
"Mounts": [
    {
        "Type": "bind",
        "Source": "/Users/tuouser/ThothAI/data_exchange",
        "Destination": "/app/data_exchange",
        "Mode": "rw"
    }
]
```

## Modelli Supportati

Il sistema supporta l'import/export di tutti i modelli Django registrati nell'admin:

| Modello | Nome File CSV | Note |
|---------|---------------|------|
| Workspace | `workspace.csv` | Esclude campi transitori |
| SqlDb | `sqldb.csv` | Database configurati |
| SqlTable | `sqltable.csv` | Struttura tabelle |
| SqlColumn | `sqlcolumn.csv` | Dettagli colonne |
| Relationship | `relationship.csv` | Relazioni FK |
| Agent | `agent.csv` | Configurazioni agenti |
| AiModel | `aimodel.csv` | Modelli AI |
| Setting | `setting.csv` | Impostazioni |
| User | `users.csv` | Utenti (nome speciale) |
| Group | `groups.csv` | Gruppi (nome speciale) |

## Utilizzo Tipico

### Workflow 1: Backup Dati da Docker

```bash
# 1. Export da Django Admin o command line
docker exec -it thoth-backend python manage.py export_models

# 2. I file sono già sul tuo computer in ./data_exchange/
ls -la ./data_exchange/
# workspace.csv sqldb.csv sqltable.csv ...

# 3. Crea un backup compresso
tar -czf backup_$(date +%Y%m%d).tar.gz data_exchange/

# 4. Sposta il backup dove vuoi
mv backup_*.tar.gz ~/Backups/ThothAI/
```

### Workflow 2: Migrazione tra Ambienti

```bash
# SU PRODUZIONE (Docker)
# 1. Export tutti i dati
docker exec -it thoth-prod python manage.py export_models

# 2. I file sono in ./data_exchange/ sul server
tar -czf thoth_export.tar.gz data_exchange/

# 3. Trasferisci sul tuo computer
scp server:~/ThothAI/thoth_export.tar.gz .

# SUL TUO COMPUTER (Development)
# 4. Estrai nella directory corretta
tar -xzf thoth_export.tar.gz

# 5. Import in development (Docker o locale)
docker exec -it thoth-backend python manage.py import_single_csv workspace
# oppure
cd backend && uv run python manage.py import_single_csv workspace
```

### Workflow 3: Modifica Manuale e Re-import

```bash
# 1. Export current data
docker exec -it thoth-backend python manage.py export_single_model Workspace

# 2. Apri con Excel/Numbers direttamente dal tuo computer
open ./data_exchange/workspace.csv

# 3. Modifica e salva il file

# 4. Re-import in Docker
docker exec -it thoth-backend python manage.py import_single_csv workspace
```

## Note Importanti

### Vantaggi del Bind Mount

1. **Accesso Immediato**: Non serve copiare file dentro/fuori dal container
2. **Editing Diretto**: Puoi modificare i CSV con Excel/VS Code senza comandi Docker
3. **Backup Semplice**: I file sono già sul tuo filesystem, pronti per backup
4. **Debug Facile**: Puoi vedere subito cosa ha scritto Django
5. **Bidirezionale**: Modifiche da entrambi i lati sono immediate

### Sicurezza

1. **Dati Sensibili**: Non lasciare file con password/token in `data_exchange`
2. **Pulizia**: Rimuovi i CSV dopo l'uso se contengono dati sensibili
3. **Gitignore**: La directory `data_exchange/` è già in `.gitignore`

### Best Practices

1. **Verifica Bind Mount**: Controlla che la directory sia correttamente montata prima di operazioni critiche
2. **Ordine Import**: Importa prima modelli senza dipendenze (Setting, AiModel), poi quelli con FK (Workspace)
3. **Backup Pre-Import**: Sempre backup del database prima di import massivi
4. **Test con Pochi Record**: Testa l'import con pochi record prima di import completi
5. **Monitoring**: Controlla i log Django durante import per eventuali errori

## Formato CSV

### Header
La prima riga contiene i nomi dei campi del modello Django.

### Esempio Workspace
```csv
id,name,level,description,sql_db_id,setting_id,default_model_id,users,default_workspace
1,"Production Workspace",1,"Main production workspace",2,1,3,"1,2,3","4,5"
```

### Gestione Relazioni
- **ForeignKey**: Salvate come ID numerico (es: `sql_db_id: 2`)
- **ManyToMany**: Lista di ID separati da virgola (es: `users: "1,2,3"`)
- **Campo vuoto**: Lasciare vuoto per valori NULL

## Error Handling

Il sistema fornisce messaggi di errore specifici:

| Errore | Causa | Soluzione |
|--------|-------|-----------|
| Permission Denied | Directory non scrivibile | `chmod 755 ./data_exchange` |
| No such file | Bind mount non configurato | Verifica docker-compose.yml |
| File not found | CSV mancante per import | Verifica nome file in `./data_exchange/` |
| FK constraint | Record referenziato mancante | Importa prima le dipendenze |

## Riepilogo

**Il punto chiave**: La directory `data_exchange` è un **ponte diretto** tra il tuo computer e Docker. Non è isolata dentro Docker, ma è la stessa directory accessibile da entrambi i lati. Questo rende l'import/export estremamente semplice: scrivi da un lato, leggi dall'altro, istantaneamente.