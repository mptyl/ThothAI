# STARTING-ALL.md - Analisi Dettagliata dello Script start-all.sh

## 📋 Indice
1. [Panoramica](#panoramica)
2. [Prerequisiti e Configurazione Iniziale](#prerequisiti-e-configurazione-iniziale)
3. [Caricamento Variabili d'Ambiente](#caricamento-variabili-dambiente)
4. [Avvio Django Backend](#avvio-django-backend)
5. [Avvio Qdrant](#avvio-qdrant)
6. [Avvio SQL Generator](#avvio-sql-generator)
7. [Avvio Frontend Next.js](#avvio-frontend-nextjs)
8. [Gestione Cleanup e Interruzione](#gestione-cleanup-e-interruzione)
9. [Tabella Riepilogativa](#tabella-riepilogativa)

## Panoramica

Lo script `start-all.sh` è il punto di ingresso per lo sviluppo locale di ThothAI. Avvia tutti i servizi necessari in sequenza, gestendo porte, dipendenze e configurazioni.

### File Utilizzati
- **`.env.local`**: File di configurazione principale (nella root)
- **`config.yml.local`**: NON utilizzato in sviluppo locale
- **`pyproject.toml`**: Uno per ogni servizio Python (backend e sql_generator)

### Porte Utilizzate
- **8200**: Django Backend
- **8180**: SQL Generator (FastAPI)
- **3200**: Frontend (Next.js)
- **6334**: Qdrant (Vector DB)

## Prerequisiti e Configurazione Iniziale

### 1. Variabili di Configurazione (righe 12-30)

```bash
# Configuration
SQL_GEN_DIR="frontend/sql_generator"

# Port configuration from environment
FRONTEND_LOCAL_PORT=${FRONTEND_LOCAL_PORT:-3200}
SQL_GEN_LOCAL_PORT=${SQL_GENERATOR_LOCAL_PORT:-8180}
BACKEND_LOCAL_PORT=${BACKEND_LOCAL_PORT:-8200}
QDRANT_PORT=6334
```

**Dettaglio:**
- Le porte vengono lette da variabili d'ambiente o usano valori di default
- `SQL_GEN_DIR` definisce il percorso relativo del SQL Generator

### 2. Colori per Output (righe 37-42)

```bash
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
```

## Caricamento Variabili d'Ambiente

### Processo (righe 15-24)

```bash
if [ -f .env.local ]; then
    echo -e "${GREEN}Loading environment from .env.local${NC}"
    # Export all variables except PORT to avoid conflicts
    export $(grep -v '^#' .env.local | grep -v '^PORT=' | xargs)
else
    echo -e "${RED}Error: .env.local not found in root directory${NC}"
    echo -e "${YELLOW}Please create .env.local from .env.template${NC}"
    exit 1
fi
```

**Cosa succede:**
1. Verifica esistenza di `.env.local`
2. Carica TUTTE le variabili TRANNE `PORT=` generico
3. Le variabili vengono esportate nell'ambiente shell
4. TUTTI i processi figli erediteranno queste variabili

**Variabili caricate da `.env.local`:**
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc. (API keys LLM)
- `EMBEDDING_PROVIDER`, `EMBEDDING_API_KEY` (servizio embedding)
- `DJANGO_API_KEY`, `SECRET_KEY` (sicurezza Django)
- `BACKEND_URL`, `FRONTEND_URL`, `SQL_GENERATOR_URL` (URL servizi)
- `LOGFIRE_TOKEN` (monitoring)
- NON `PORT` (filtrata per evitare conflitti)

## Avvio Django Backend

### Processo Completo (righe 84-146)

#### 1. Controllo Porta (righe 85-87)
```bash
if check_port $BACKEND_LOCAL_PORT; then
    echo -e "${GREEN}✓ Django backend is already running on port $BACKEND_LOCAL_PORT${NC}"
else
```

#### 2. Verifica Directory Backend (riga 93)
```bash
if [ -d "backend" ]; then
    cd backend
```

#### 3. Gestione Virtual Environment (righe 96-124)

**Se .venv esiste e uv è disponibile:**
```bash
if command -v uv &> /dev/null; then
    echo -e "${GREEN}Starting Django with uv...${NC}"
    (unset VIRTUAL_ENV && uv run python manage.py runserver $BACKEND_LOCAL_PORT) &
    DJANGO_PID=$!
```

**Dettaglio comando uv:**
- `unset VIRTUAL_ENV`: Pulisce variabile per evitare conflitti
- `uv run`: Usa Python gestito da uv (3.13.5)
- `python manage.py runserver $BACKEND_LOCAL_PORT`: Avvia Django sulla porta 8200
- `&`: Esegue in background
- `DJANGO_PID=$!`: Salva il PID del processo

**Se .venv non esiste:**
```bash
echo -e "${YELLOW}Creating virtual environment for Django backend...${NC}"
uv sync
(unset VIRTUAL_ENV && uv run python manage.py runserver $BACKEND_LOCAL_PORT) &
```

**Cosa fa `uv sync`:**
1. Legge `backend/pyproject.toml`
2. Legge `backend/pyproject.toml.local` (se esiste)
3. Crea `.venv` con Python 3.13.5 (da `backend/.python-version`)
4. Installa TUTTE le dipendenze specificate

**File utilizzati:**
- `backend/pyproject.toml`: Dipendenze base
- `backend/pyproject.toml.local`: Dipendenze database aggiuntive (se presente)
- `backend/.python-version`: Specifica Python 3.13.5

#### 4. Attesa Avvio (righe 129-141)
```bash
for i in {1..30}; do
    if check_port $BACKEND_LOCAL_PORT; then
        echo -e "${GREEN}✓ Django backend started successfully on port $BACKEND_LOCAL_PORT${NC}"
        break
    fi
    sleep 1
done
```

**Django utilizza dall'ambiente:**
- Tutte le API keys
- `SECRET_KEY`, `DJANGO_API_KEY`
- `DEBUG=True` (modalità sviluppo)
- Database config (SQLite di default)

## Avvio Qdrant

### Processo Completo (righe 148-191)

#### 1. Controllo Container Esistente (righe 162-166)
```bash
if docker ps -a --format "table {{.Names}}" | grep -q "^qdrant-thoth$"; then
    echo -e "${YELLOW}Starting existing qdrant-thoth container...${NC}"
    docker start qdrant-thoth
```

#### 2. Creazione Nuovo Container (righe 167-174)
```bash
docker run -d \
    --name qdrant-thoth \
    -p 6334:6334 \
    -p 6333:6333 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

**Dettaglio:**
- `--name qdrant-thoth`: Nome container
- `-p 6334:6334`: Porta API REST
- `-p 6333:6333`: Porta gRPC
- `-v $(pwd)/qdrant_storage:/qdrant/storage:z`: Volume persistente per dati

**Qdrant NON usa:**
- `.env.local` (non necessario)
- `pyproject.toml` (è un container Docker)
- `config.yml.local` (non in sviluppo locale)

## Avvio SQL Generator

### Processo Completo (righe 193-234)

#### 1. Cleanup Processi Esistenti (righe 196-202)
```bash
cleanup_sql_generator() {
    echo -e "${YELLOW}Cleaning up any existing SQL Generator processes...${NC}"
    pkill -f "python.*main\.py" 2>/dev/null || true
    pkill -f "sql_generator" 2>/dev/null || true
    sleep 1
}
```

#### 2. Kill Porta se Occupata (righe 199-202)
```bash
if check_port $SQL_GEN_LOCAL_PORT; then
    echo -e "${YELLOW}Port $SQL_GEN_LOCAL_PORT still in use, killing processes...${NC}"
    kill_port $SQL_GEN_LOCAL_PORT
fi
```

#### 3. Cambio Directory e Sync (righe 205-214)
```bash
cd "$SQL_GEN_DIR"

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment for SQL Generator...${NC}"
    (unset VIRTUAL_ENV && uv sync)
else
    echo -e "${YELLOW}Updating SQL Generator dependencies...${NC}"
    (unset VIRTUAL_ENV && uv sync)
fi
```

**Cosa fa `uv sync` per SQL Generator:**
1. Legge `frontend/sql_generator/pyproject.toml`
2. Usa Python 3.13.5 (da `frontend/sql_generator/.python-version`)
3. Crea/aggiorna `.venv`
4. Installa dipendenze:
   - PydanticAI e dipendenze
   - FastAPI, Uvicorn
   - Database drivers
   - LLM client libraries

#### 4. Avvio con PORT Specifica (riga 217)
```bash
(unset VIRTUAL_ENV && PORT=$SQL_GEN_LOCAL_PORT uv run python main.py) &
```

**IMPORTANTE:** Qui `PORT=$SQL_GEN_LOCAL_PORT` sovrascrive qualsiasi PORT nell'ambiente!

**SQL Generator utilizza dall'ambiente:**
- Tutte le API keys LLM
- `EMBEDDING_*` variabili
- `DJANGO_API_KEY` (per comunicare con backend)
- `LOGFIRE_TOKEN` (monitoring)

**File utilizzati:**
- `frontend/sql_generator/pyproject.toml`: Dipendenze
- `frontend/sql_generator/.python-version`: Python 3.13.5
- `frontend/sql_generator/main.py`: Entry point FastAPI

## Avvio Frontend Next.js

### Processo Completo (righe 236-277)

#### 1. Controllo Porta (righe 238-241)
```bash
if check_port $FRONTEND_LOCAL_PORT; then
    echo -e "${GREEN}✓ Frontend is already running on port $FRONTEND_LOCAL_PORT${NC}"
else
```

#### 2. Installazione Dipendenze se Necessario (righe 249-252)
```bash
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing Frontend dependencies...${NC}"
    npm install
fi
```

#### 3. Avvio con PORT Specifica (riga 256)
```bash
PORT=$FRONTEND_LOCAL_PORT npm run dev &
```

**IMPORTANTE:** `PORT=$FRONTEND_LOCAL_PORT` forza Next.js a usare porta 3200!

**Frontend utilizza dall'ambiente:**
- `NEXT_PUBLIC_DJANGO_SERVER=http://localhost:8200`
- `NEXT_PUBLIC_SQL_GENERATOR_URL=http://localhost:8180`
- `NEXTAUTH_URL=http://localhost:3200`
- `NEXTAUTH_SECRET`
- NON usa direttamente le API keys (passano attraverso backend)

**File utilizzati:**
- `frontend/package.json`: Dipendenze Node.js
- `frontend/next.config.js`: Configurazione Next.js
- NON usa `pyproject.toml` (è JavaScript/TypeScript)

## Gestione Cleanup e Interruzione

### Trap per Ctrl+C (riga 329)
```bash
trap cleanup INT
```

### Funzione Cleanup (righe 289-326)
```bash
cleanup() {
    echo -e "\n${YELLOW}Stopping services...${NC}"
    
    # Stop Frontend
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo -e "${GREEN}✓ Frontend stopped${NC}"
    fi
    
    # Stop SQL Generator
    if [ ! -z "$SQL_GEN_PID" ]; then
        kill $SQL_GEN_PID 2>/dev/null
        echo -e "${GREEN}✓ SQL Generator stopped${NC}"
    fi
    
    # Stop Django if we started it
    if [ ! -z "$DJANGO_PID" ]; then
        kill $DJANGO_PID 2>/dev/null
        echo -e "${GREEN}✓ Django backend stopped${NC}"
    fi
    
    # Ask about Qdrant container
    if [ ! -z "$QDRANT_CONTAINER" ]; then
        read -p "Stop Qdrant container? (y/N): " -n 1 -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker stop $QDRANT_CONTAINER
        fi
    fi
}
```

## Tabella Riepilogativa

### File di Configurazione per Servizio

| Servizio | File .env | pyproject.toml | config.yml.local | .python-version |
|----------|-----------|----------------|------------------|-----------------|
| **Django Backend** | `.env.local` (ereditato) | `backend/pyproject.toml` + `.local` | ❌ NON usato | `backend/.python-version` (3.13.5) |
| **SQL Generator** | `.env.local` (ereditato) | `frontend/sql_generator/pyproject.toml` | ❌ NON usato | `frontend/sql_generator/.python-version` (3.13.5) |
| **Frontend** | `.env.local` (ereditato) | ❌ NON usa | ❌ NON usato | ❌ NON usa |
| **Qdrant** | ❌ NON necessario | ❌ NON usa | ❌ NON usato | ❌ NON usa |

### Variabili d'Ambiente Chiave per Servizio

| Servizio | Variabili Utilizzate | Porta | Note |
|----------|---------------------|-------|------|
| **Django** | `SECRET_KEY`, `DJANGO_API_KEY`, API keys, `DEBUG`, `EMBEDDING_*` | 8200 | Eredita tutto da `.env.local` |
| **SQL Generator** | API keys LLM, `EMBEDDING_*`, `DJANGO_API_KEY`, `LOGFIRE_TOKEN` | 8180 | `PORT` sovrascritta esplicitamente |
| **Frontend** | `NEXT_PUBLIC_*`, `NEXTAUTH_*` | 3200 | `PORT` sovrascritta esplicitamente |
| **Qdrant** | Nessuna | 6334 | Container Docker isolato |

### Ordine di Avvio

1. **Django Backend** - Deve partire per primo (database, autenticazione)
2. **Qdrant** - Vector database (può partire in parallelo)
3. **SQL Generator** - Dipende da Django e Qdrant
4. **Frontend** - Dipende da tutti gli altri servizi

### Gestione Python

| Directory | Python Version | Gestito da | Virtual Env |
|-----------|---------------|------------|-------------|
| `backend/` | 3.13.5 | uv | `.venv` creato da `uv sync` |
| `frontend/sql_generator/` | 3.13.5 | uv | `.venv` creato da `uv sync` |
| `frontend/` | N/A | N/A | Node.js/npm |

## Note Importanti

1. **config.yml.local NON è utilizzato** in sviluppo locale - solo per Docker
2. **`.env.local` è l'UNICA fonte** di configurazione per sviluppo locale
3. **PORT generico è filtrato** per evitare conflitti tra servizi
4. **Ogni servizio Python** ha il proprio `pyproject.toml` e `.venv`
5. **Python è gestito da uv**, non dal sistema operativo
6. **Qdrant è l'unico servizio** che richiede Docker in locale

## Troubleshooting

### Problema: Porta già in uso
**Soluzione:** Lo script gestisce automaticamente con `kill_port()`, ma se persiste:
```bash
lsof -ti:PORTA | xargs kill -9
```

### Problema: uv usa Python di sistema
**Soluzione:** Verificare `.python-version` e reinstallare:
```bash
uv python install 3.13.5
rm -rf .venv && uv sync
```

### Problema: Variabili ambiente non caricate
**Soluzione:** Verificare che `.env.local` sia nella root e non contenga errori di sintassi

### Problema: SQL Generator usa porta sbagliata
**Causa:** `PORT` generico in `.env.local` non filtrato
**Soluzione:** Aggiornare `start-all.sh` per filtrare `PORT=`