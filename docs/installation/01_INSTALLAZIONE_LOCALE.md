# Guida all'Installazione Locale

Questa guida descrive in dettaglio come installare ed eseguire ThothAI in modo nativo sulla tua macchina locale (macOS/Linux). Questo metodo è ideale per **sviluppo**, **debugging** e **test**.

> [!NOTE]
> In questa modalità, il Backend (Django), il Frontend (Next.js) e il Generatore SQL (FastAPI) vengono eseguiti direttamente sul sistema operativo host. I servizi infrastrutturali come Qdrant (Vector DB) e Mermaid Service vengono comunque eseguiti in Docker per comodità.

## Prerequisiti

Assicurati che il tuo sistema soddisfi i seguenti requisiti:

- **OS**: macOS o Linux
- **Python**: 3.9+ installato
- **Node.js**: v18+ e `npm` installati
- **Docker & Docker Compose**: Richiesti per i servizi Qdrant e Mermaid
- **uv**: Moderno gestore di pacchetti Python (fortemente raccomandato)

### 1. Installare `uv` (Raccomandato)

ThothAI utilizza `uv` per una gestione ultra-rapida dei pacchetti Python.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Preparare l'Ambiente

1.  **Clonare la repository**:
    ```bash
    git clone https://github.com/mptyl/ThothAI.git
    cd ThothAI
    ```

2.  **Inizializzare la Configurazione**:
    Copia il template per abilitare le impostazioni locali:
    ```bash
    cp .env.local.template .env.local
    ```

3.  **Configurare `.env.local`**:
    Apri `.env.local` e aggiungi le tue chiavi API. Come minimo, hai bisogno di un provider LLM (come la chiave OpenAI) e un provider di Embedding.
    ```bash
    nano .env.local
    ```
    > [!IMPORTANT]
    > Non saltare questo passaggio! I servizi non si avvieranno senza chiavi API valide.

## Metodo A: Avvio Rapido (Raccomandato)

Forniamo uno script master `start-all.sh` che automatizza l'intero processo di avvio. Gestisce:
- Avvio dei container di storage delle dipendenze (Qdrant, Mermaid)
- Creazione degli ambienti virtuali Python se mancanti
- Installazione delle dipendenze
- Esecuzione delle migrazioni del database
- Avvio di Backend, Frontend e Generatore SQL in parallelo

### Eseguire lo Script

```bash
./start-all.sh
```

Lo script mostrerà lo stato di ogni servizio. Una volta pronto, puoi accedere a:
- **Frontend**: [http://localhost:3040](http://localhost:3040)
- **Backend Admin**: [http://localhost:8040/admin](http://localhost:8040/admin)
- **SQL Generator API**: [http://localhost:8020/docs](http://localhost:8020/docs)

Per arrestare tutti i servizi, premi semplicemente `Ctrl+C`.

---

## Metodo B: Installazione Manuale

Se preferisci eseguire i servizi manualmente (es. per il debugging individuale), segui questi passaggi che replicano sostanzialmente ciò che fa automaticamente `start-all.sh`.

### 1. Servizi Infrastrutturali

Avvia i container Docker di supporto (Qdrant e Mermaid).

```bash
# Avvia Mermaid Service
docker compose up -d mermaid-service

# Avvia Local Qdrant
# Eseguiamo un Qdrant autonomo per lo sviluppo locale per evitare conflitti con i volumi Docker condivisi
docker run -d --name thoth-qdrant-local -p 6333:6333 -v $(pwd)/qdrant_storage_local:/qdrant/storage qdrant/qdrant:latest
```

### 2. Backend (Django)

Apri una nuova scheda del terminale:

```bash
cd backend

# Configura ambiente Python
uv sync

# Esegui Migrazioni
uv run python manage.py migrate
uv run python manage.py createcachetable

# Carica Dati di Default (Solo la prima volta)
uv run python manage.py load_defaults --source local

# Avvia Server
uv run python manage.py runserver 8040
```

### 3. Generatore SQL (FastAPI)

Apri una nuova scheda del terminale:

```bash
cd frontend/sql_generator

# Configura ambiente
uv sync

# Esporta variabili richieste (allineate con .env.local)
export PORT=8020
export DJANGO_SERVER=http://localhost:8040
export VECTOR_DB_HOST=localhost
export VECTOR_DB_PORT=6333

# Avvia Servizio
uv run python main.py
```

### 4. Frontend (Next.js)

Apri una nuova scheda del terminale:

```bash
cd frontend

# Installa Dipendenze
npm install

# Esporta variabili richieste
export PORT=3040
export NEXT_PUBLIC_DJANGO_SERVER=http://localhost:8040
export NEXT_PUBLIC_SQL_GENERATOR_URL=http://localhost:8020

# Avvia Servizio
npm run dev
```

## Risoluzione Problemi

- **Conflitti di Porta**: Assicurati che le porte `8040`, `3040`, `8020` e `6333` siano libere.
- **Problemi Micro-Frontend**: Se il frontend non riesce a comunicare con il backend, verifica che `NEXT_PUBLIC_DJANGO_SERVER` corrisponda esattamente all'URL del backend.
- **Database**: Lo sviluppo locale utilizza SQLite (`backend/db.sqlite3`) per impostazione predefinita, ma supporta PostgreSQL se `DATABASE_URL` è configurato in `.env.local`.
