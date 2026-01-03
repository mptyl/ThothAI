# thothai-data-cli - Manuale Utente

## Indice

1. [Introduzione](#introduzione)
2. [Requisiti](#requisiti)
3. [Installazione](#installazione)
4. [Configurazione](#configurazione)
5. [Comandi CSV](#comandi-csv)
6. [Comandi Database](#comandi-database)
7. [Comandi di Configurazione](#comandi-di-configurazione)
8. [Comando Prune](#comando-prune)
9. [Uso Avanzato](#uso-avanzato)
10. [Risoluzione dei Problemi](#risoluzione-dei-problemi)

---

## Introduzione

`thothai-data-cli` è uno strumento da riga di comando per gestire file CSV e database SQLite nei deployment Docker di ThothAI. Supporta istanze Docker sia locali che remote in esecuzione in modalità Docker Compose o Docker Swarm. 

**Novità**: La CLI ora gestisce automaticamente la creazione di una directory locale `data-exchange` nella cartella di lavoro corrente per facilitare la preparazione dei file.

---

## Requisiti

- **Python**: 3.9 o superiore
- **uv**: Package manager (installare da https://docs.astral.sh/uv/)
- **Docker**: Deployment Docker attivo (locale o remoto)
- **SSH**: Per l'accesso Docker remoto (opzionale)

---

## Installazione

### Passo 1: Creazione dell'Ambiente Virtuale

```bash
# Crea una directory per la CLI
mkdir thothai-data && cd thothai-data

# Crea l'ambiente virtuale con uv
uv venv

# Attiva l'ambiente virtuale
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows PowerShell
```

### Passo 2: Installazione della CLI

```bash
uv pip install thothai-data-cli
```

### Passo 3: Verifica dell'Installazione

```bash
uv run thothai-data --help
```

---

## Configurazione

### Configurazione Automatica

Al primo utilizzo, se non esiste alcun file di configurazione, la CLI ti guiderà nella creazione:

```bash
uv run thothai-data csv list

# Output:
# ✓ Created local directory: /path/to/cwd/data_exchange
# Config file not found: ~/.thothai-data.yml
# Create configuration file? [y/N]: y
# Docker connection type [local/ssh]: local
# Docker mode [compose/swarm]: swarm
# Stack/project name [thothai-swarm]: thothai-swarm
# ✓ Configuration saved to ~/.thothai-data.yml
```

### File di Configurazione: `~/.thothai-data.yml`

```yaml
docker:
  connection: local      # 'local' o 'ssh'
  mode: swarm           # 'compose' o 'swarm'
  stack_name: thothai-swarm
  service: backend
  db_service: sql-generator

ssh:  # Solo per connessioni remote
  host: server.example.com
  user: deploy
  port: 22
  key_file: ""  # Opzionale

paths:
  data_exchange: /app/data_exchange
  shared_data: /app/data
```

### Opzioni di Configurazione

| Opzione | Descrizione | Valori |
|--------|-------------|--------|
| `connection` | Posizione Docker | `local` (stessa macchina), `ssh` (remoto) |
| `mode` | Deployment Docker | `compose` (docker-compose), `swarm` (stack) |
| `stack_name` | Prefisso container/nome stack | Stringa |
| `service` | Nome servizio backend | Default: `backend` |
| `db_service` | Nome servizio database | Default: `sql-generator` |

---

## 5. Comandi CSV (`thothai-data csv`)

I file CSV sono fondamentali in ThothAI per l'importazione di dati strutturati e per il recupero dei risultati delle analisi generate dagli agenti AI. Tutti i file sono archiviati nel volume Docker `thothai-data-exchange`.

### 5.1 Elenca File (`list`)
Fornisce un inventario dettagliato di tutti i file CSV residenti nel volume di scambio `thothai-data-exchange`. Non si limita ad elencare i nomi, ma include metadati vitali come la dimensione del file e l'ultimo timestamp di modifica. Questo è il comando fondamentale per confermare che un'esportazione complessa richiesta dall'interfaccia web sia stata completata con successo sul server prima di procedere al download, o per assicurarsi che un file appena caricato sia nella posizione corretta per essere elaborato dagli agenti AI.

```bash
uv run thothai-data csv list
```

### 5.2 Carica File (`upload`)
Il punto di ingresso primario per i tuoi dati nell'ecosistema ThothAI. Questo comando gestisce in modo intelligente il trasferimento di file strutturati (CSV) dalla tua macchina locale all'infrastruttura Docker, sia che si tratti di un'installazione locale che di un server remoto via SSH. Una volta caricato, il file "alimenta" il sistema, permettendo al backend di mappare le nuove colonne e righe, rendendole immediatamente disponibili per le interrogazioni in linguaggio naturale.

```bash
uv run thothai-data csv upload myfile.csv
```

### 5.3 Scarica File (`download`)
Rappresenta il canale di uscita ufficiale per i risultati delle tue analisi. Quando ThothAI conclude un'operazione di export o genera un report basato sui tuoi dati, questo comando ti permette di portarlo fuori dal container Docker e salvarlo fisicamente sulla tua macchina. L'opzione `--output` (`-o`) ti offre la flessibilità di organizzare i tuoi file in cartelle dedicate, facilitando la gestione di flussi di lavoro BI o l'archiviazione di report periodici.

```bash
# Scarica nella directory corrente
uv run thothai-data csv download report_finale.csv

# Scarica in una directory specifica
uv run thothai-data csv download report_finale.csv -o ./exports/
```

### 5.4 Elimina File (`delete`)
Svolge un ruolo cruciale nella gestione della privacy e nell'ottimizzazione delle risorse. Consente di rimuovere permanentemente file obsoleti, set di dati di test o informazioni sensibili che non devono più risiedere sul server una volta concluso il ciclo di analisi. È uno strumento di governance essenziale per mantenere il volume di scambio ordinato ed evitare l'accumulo di dati non necessari che potrebbero generare confusione o rischi di sicurezza.

```bash
uv run thothai-data csv delete dati_temporanei.csv
```

---

## 6. Comandi Database (`thothai-data db`)

ThothAI permette l'analisi di database SQLite aggiuntivi oltre a quelli predefiniti. Questi database devono essere organizzati nel volume `thoth-shared-data` con una struttura gerarchica specifica.

### 6.1 Elenca Database (`list`)
Visualizza la libreria completa dei database SQLite "vivi" all'interno del sistema ThothAI (volume `thoth-shared-data`). Mostra non solo i database di esempio (come `california_schools`), ma ogni singola sorgente dati aggiunta dagli utenti. È lo strumento di monitoraggio principale per capire quali contesti informativi sono attualmente a disposizione dell'AI per generare query SQL e fornire risposte basate sui dati.

```bash
uv run thothai-data db list
```

### 6.2 Inserisci Database (`insert`)
Trasforma un semplice file SQLite in una risorsa attiva e interrogabile. Questo comando non esegue una banale copia del file, ma crea l'architettura gerarchica necessaria affinché il backend possa gestire correttamente lo schema:
1. Crea una sottodirectory dedicata basata sul nome del DB.
2. Copia il file rinominandolo coerentemente (es: `vendite.sqlite` -> `/app/data/vendite/vendite.sqlite`).
Questa organizzazione garantisce che gli agenti AI possano isolare le interrogazioni ed evitare collisioni tra database diversi. Una volta completato, il database è immediatamente selezionabile nel portale web.

```bash
uv run thothai-data db insert ./nuovo_database.sqlite
```

### 6.3 Rimuovi Database (`remove`)
Provvede allo smantellamento sicuro di una sorgente dati. Quando un database non è più rilevante o deve essere sostituito, questo comando elimina l'intero spazio di lavoro dedicato nel volume Docker, inclusi tutti i file associati. È l'operazione di pulizia finale che assicura che l'intelligenza artificiale non tenti di fare riferimento a dati obsoleti o non più validi, mantenendo l'integrità del sistema di conoscenza.

```bash
uv run thothai-data db remove vecchio_db
```

---

## 7. Comandi di Configurazione (`thothai-data config`)

Questi comandi servono a gestire il comportamento della CLI stessa e la sua connessione con l'infrastruttura Docker di ThothAI.

### 7.1 Mostra Configurazione (`show`)
Visualizza le impostazioni correnti salvate in `~/.thothai-data.yml`, inclusi i parametri Docker (mode, stack name) e le credenziali SSH se presenti.

```bash
uv run thothai-data config show
```

### 7.2 Test Connessione (`test`)
Verifica che la CLI sia in grado di parlare con il demone Docker (locale o remoto) e, cosa più importante, che riesca a identificare correttamente i container del backend e del generatore SQL di ThothAI. Senza un test positivo, le operazioni sui file e sui database falliranno.

```bash
uv run thothai-data config test
```

---

## 12. Comando Prune (`thothai-data prune`)

Il comando `prune` è uno strumento di manutenzione potente che permette di ripulire completamente l'ambiente Docker eliminando gli artefatti legati a ThothAI.

### 12.1 Funzionamento
Rimuove i container (Compose o Swarm), le reti virtuali e, opzionalmente, i volumi persistenti e le immagini Docker.

```bash
uv run thothai-data prune
```

### 12.2 Opzioni Disponibili

| Opzione | Descrizione | Default |
|---------|-------------|---------|
| `--yes`, `-y` | Salta la conferma interattiva | No |
| `--volumes` / `--no-volumes` | Include o esclude la rimozione dei volumi | `include` |
| `--images` / `--no-images` | Include o esclude la rimozione delle immagini | `include` |

> [!CAUTION]
> **Perdita Dati**: L'uso di `prune` con l'opzione `--volumes` (attiva di default) **elimina permanentemente** tutti i database SQLite e i file CSV caricati o esportati. Assicurati di avere un backup se necessario.

---

## Uso Avanzato

### Docker Remoto via SSH

Modifica `~/.thothai-data.yml`:

```yaml
docker:
  connection: ssh
  mode: swarm
  stack_name: thothai-swarm

ssh:
  host: production.example.com
  user: deploy
  port: 22
  key_file: ~/.ssh/production_key
```

Poi usa i comandi normalmente:
```bash
uv run thothai-data csv list  # Esegue sul server remoto
```

### Modalità Docker Compose

Per ambienti di sviluppo che usano docker-compose:

```yaml
docker:
  connection: local
  mode: compose
  stack_name: thothai  # nome progetto docker-compose
```

---

## Risoluzione dei Problemi

### File di configurazione non trovato

**Soluzione**: Esegui qualsiasi comando per crearlo interattivamente, o crea manualmente `~/.thothai-data.yml`.

### Container non trovato

**Problema**: `No container found for service: backend`

**Soluzioni**:
1. Controlla che Docker sia in esecuzione: `docker ps`
2. Verifica che `stack_name` nella config corrisponda allo stack deployato
3. Per Swarm: assicurati che lo stack sia deployato
4. Per Compose: assicurati che i container siano in esecuzione

### Connessione SSH fallita

**Soluzioni**:
1. Verifica l'accesso SSH: `ssh user@host`
2. Controlla il percorso `key_file` nella config
3. Assiscurati che Docker sia installato sul server remoto

### Permesso negato su upload/download

**Soluzioni**:
1. Controlla i permessi del volume Docker
2. Esegui Docker con i permessi utente appropriati
3. Per SSH: assicurati che l'utente abbia accesso a Docker (gruppo `docker`)

---

## Esempi

### Workflow Giornaliero: Export CSV

```bash
# Elenca file correnti
uv run thothai-data csv list

# Carica nuovo export
uv run thothai-data csv upload ./exports/monthly_report.csv

# Scarica per analisi
uv run thothai-data csv download monthly_report.csv -o ./analysis/

# Pulisci vecchi file
uv run thothai-data csv delete old_export.csv
```

### Gestione Database

```bash
# Controlla database esistenti
uv run thothai-data db list

# Aggiungi nuovo database accanto a california_schools
uv run thothai-data db insert ./hr_system.sqlite

# In seguito, rimuovi se non necessario
uv run thothai-data db remove hr_system
```

### Gestione Server Remoto

```bash
# Configura per server di produzione remoto
# Modifica ~/.thothai-data.yml con impostazioni ssh

# Verifica connessione
uv run thothai-data config test

# Carica dati in produzione
uv run thothai-data csv upload production_data.csv
```
