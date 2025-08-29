# tHothAI Database Configuration Tool

Un'applicazione web elegante per configurare i database nel file `requirements.txt` del progetto tHothAI.

## Caratteristiche

- **Interfaccia web moderna** con Bootstrap 5
- **Configurazione database tradizionali**: SQLite, PostgreSQL, MySQL, MariaDB, Supabase, SQL Server, Oracle
- **Configurazione vector database**: Qdrant, Chroma, Milvus, PgVector
- **Validazione intelligente**
- **Persistenza delle scelte** tramite file JSON
- **Aggiornamento automatico** del file requirements.txt
- **Supporto directory sorelle**: Aggiorna automaticamente anche thoth_sl/ThothSL/thothsl
- **Integrazione Docker Compose**: Deploy automatico con monitoraggio in tempo reale
- **Spinner e feedback visivo** per operazioni in background

## Struttura del Progetto

```
thoth_installer_app/
├── main.py              # Backend FastAPI
├── index.html           # Interfaccia web
├── requirements.txt     # File delle dipendenze (modificato dall'app)
├── chosen_db.json       # Configurazione salvata
├── test_app.py          # Suite di test
└── README.md           # Documentazione
```

## Installazione

1. **Installa le dipendenze**:
   ```bash
pip install fastapi uvicorn python-multipart requests
```

2. **Assicurati di avere un file requirements.txt** con le righe:
   ```
thoth-dbmanager[mariadb,sqlite]==x.y.z
thoth-vdbmanager[qdrant]==x.y.z
```

## Utilizzo

### Avvio dell'applicazione

```bash
python main.py
```

L'applicazione sarà disponibile su: http://localhost:8199

### Interfaccia Web

1. **Apri il browser** e vai su http://localhost:8199
2. **Seleziona i database** desiderati dalle checkbox
3. **Seleziona i vector database** desiderati
4. **Clicca "Aggiorna Configurazione"** per salvare le modifiche
5. **Clicca "Deploy Backend"** per eseguire docker compose della directory thoth_be
6. **Clicca "Deploy Frontend"** per eseguire docker compose della directory sorella

### Nuove Funzionalità v2.0

#### 🚀 Deploy Docker Automatico Dual
- **Deploy Backend**: Esegue `docker compose up --build -d` da `../thoth_be`
- **Deploy Frontend**: Esegue `docker compose up --build -d` da directory sorella (`../thoth_sl`)
- **Monitoraggio separato**: Spinner e stati indipendenti per entrambi i deploy
- **Esecuzione parallela**: Possibilità di avviare entrambi i deploy contemporaneamente
- **Feedback visivo**: Progresso e messaggi di stato per ciascun deploy

#### 📁 Supporto Directory Sorelle
- **Aggiornamento multiplo**: Modifica automaticamente i requirements.txt in:
  - Directory corrente (obbligatorio)
  - `../thoth_sl/requirements.txt` (se esiste)
  - `../ThothSL/requirements.txt` (se esiste)
  - `../thothsl/requirements.txt` (se esiste)
- **Formato flessibile**: Supporta sia `==` che `>=` per le versioni

#### 🎯 Miglioramenti UX
- **Porta 8199**: Nuova porta per evitare conflitti
- **Branding tHothAI**: Aggiornato da "Thoth" a "tHothAI"
- **Spinner animati**: Feedback visivo durante le operazioni
- **Stati colorati**: Verde per successo, rosso per errori, blu per in corso

### Funzionalità

- ✅ **Selezione multipla** per database tradizionali
- ✅ **Selezione multipla** per vector database
- ✅ **Ordinamento alfabetico** delle opzioni
- ✅ **Caricamento automatico** delle scelte precedenti
- ✅ **Validazione** dei dati inseriti
- ✅ **Feedback visivo** per successo/errore

## API Endpoints

### GET /api/config
Restituisce la configurazione corrente salvata.

**Risposta**:
```json
{
  "databases": ["sqlite", "postgresql"],
  "vectordbs": ["qdrant", "chroma"],
  "message": "Configurazione caricata con successo"
}
```

### POST /api/update-config
Aggiorna la configurazione e modifica i file requirements.txt (corrente e directory sorelle).

**Richiesta**:
```json
{
  "databases": ["sqlite", "postgresql", "mysql"],
  "vectordbs": ["qdrant", "chroma"]
}
```

**Risposta**:
```json
{
  "databases": ["sqlite", "postgresql", "mysql"],
  "vectordbs": ["qdrant", "chroma"],
  "message": "Configurazione aggiornata con successo"
}
```

### POST /api/docker-deploy
Avvia il processo Docker Compose in background.

**Risposta**:
```json
{
  "status": "started",
  "message": "Docker Compose avviato",
  "phase": "starting"
}
```

### GET /api/docker-status
Restituisce lo stato corrente del processo Docker Compose.

**Risposta**:
```json
{
  "status": "running",
  "message": "Building containers...",
  "phase": "building"
}
```

### POST /api/docker-deploy-sister
Avvia il processo Docker Compose della directory sorella in background.

**Risposta**:
```json
{
  "status": "started",
  "message": "Docker Compose directory sorella avviato",
  "phase": "starting"
}
```

### GET /api/docker-status-sister
Restituisce lo stato corrente del processo Docker Compose della directory sorella.

**Risposta**:
```json
{
  "status": "running",
  "message": "Building containers in ../thoth_sl...",
  "phase": "building"
}
```

**Stati possibili**:
- `idle`: Pronto per nuove operazioni
- `running`: Docker Compose in esecuzione
- `completed`: Operazione completata con successo
- `error`: Errore durante l'esecuzione

## Database Supportati

### Database Tradizionali
- **MariaDB** (`mariadb`)
- **MySQL** (`mysql`)
- **Oracle** (`oracle`)
- **PostgreSQL** (`postgresql`)
- **SQLite** (`sqlite`)
- **SQL Server** (`sqlserver`)
- **Supabase** (`supabase`)

### Vector Database
- **Chroma** (`chroma`)
- **Milvus** (`milvus`)
- **PgVector** (`pgvector`)
- **Qdrant** (`qdrant`)

## Test

Esegui la suite di test completa:

```bash
python test_app.py
```

I test verificano:
- ✅ Connessione al server
- ✅ Caricamento configurazione
- ✅ Aggiornamento requirements.txt
- ✅ Salvataggio chosen_db.json
- ✅ Rimozione Weaviate/Pinecone
- ✅ Validazione input non validi

## File Generati

### chosen_db.json
Salva le scelte dell'utente:
```json
{
  "databases": ["sqlite", "postgresql"],
  "vectordbs": ["qdrant", "chroma"]
}
```

### requirements.txt (modificato)
Le righe vengono aggiornate automaticamente:
```
thoth-dbmanager[mariadb,sqlite]==1.2.3
thoth-vdbmanager[qdrant]==2.1.0
```

## Tecnologie Utilizzate

- **Backend**: FastAPI, Python 3.7+
- **Frontend**: HTML5, JavaScript ES6, Bootstrap 5
- **Icone**: Bootstrap Icons
- **HTTP Client**: Fetch API
- **Validazione**: Pydantic

## Correzioni Applicate

Durante lo sviluppo, ho corretto:
- ✅ **"Chrome" → "Chroma"** (nome corretto del vector database)
- ✅ **Ordinamento alfabetico** delle opzioni
- ✅ **Rimozione Weaviate/Pinecone** dalle opzioni supportate
- ✅ **Gestione errori** robusta
- ✅ **Validazione input** completa

## Licenza

Questo progetto è parte dell'ecosistema Thoth.

## Licenza

Questo progetto è parte dell'ecosistema Thoth.
