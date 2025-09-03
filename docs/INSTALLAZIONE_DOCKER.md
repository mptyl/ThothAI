# ThothAI – Installazione Docker con dati demo pre-caricati

Questa guida spiega, passo per passo, la procedura di installazione Docker avviata dallo script `install.sh` (`install.ps1`o `install.bat`per Windows). Alla fine dell’installazione avrai uno stack completo (backend, frontend, SQL Generator, proxy Nginx, Qdrant) in esecuzione, con i dati demo del database `california_schools` pre-caricati e un utente `demo` già pronto all’uso.

—

## 1) Prerequisiti

Assicurati di avere installato e funzionante:

- Docker e Docker Compose
- Python 3.9+

Lo script `install.sh` (`install.ps1`o `install.bat`per Windows) verifica automaticamente la presenza dei prerequisiti e interrompe la procedura se qualcosa manca.

—

## 2) Configurazione iniziale (`config.yml.local`)

Alla prima esecuzione, se non trova `config.yml.local`, lo script crea una copia da `config.yml` e chiede di compilarla. La validazione della configurazione avviene tramite `scripts/validate_config.py` che controlla:

- Provider AI in `ai_providers`. Aalmeno un provider deve essere abilitato e con API key. Suggerisco ovviamente OpenRouter perchè tutta la configurazione del workspace demo è pasata su OpenRouter.
- Impostazioni embedding (`embedding.provider`, `embedding.model`, e relativa API key o fallback a quella del provider). Deve esserci almeno un provider embedding abilitato. Suggerisco di iniziare con OpenAI ed usare la mia apikey fino a quando non abbiamo avuto tempo di provare Cohere. L'uso di Cohere però richiede di ricostruire la collection su Qdrant, per cui preferirei prima stablizzare la situazione.
- Configurazione database (`databases`, con SQLite sempre abilitato). il config.yml base ha già tutti i database che ti servono
- Sezione `admin` (almeno `username`, l’email è facoltativa). Suggerisco password admin123. Poi serve `demo` con password=demo1234
- Sezione `monitoring` (se abilitata, richiede `logfire_token`)
- Sezione `ports` con porte non duplicate e nel range 1024–65535. Lascia le default

File di riferimento: `scripts/validate_config.py`.

—

## 3) Esecuzione di `install.sh`:

Il flusso principale è implementato in `scripts/installer.py` ed è richiamato da `install.sh`. Le fasi chiave:

1. Caricamento e validazione configurazione: `ThothInstaller.load_config()` + validazioni base.
2. Password admin: richiesta o lettura da config; viene salvato l’hash in `.admin_password.hash`.
3. Generazione dipendenze locali: crea `backend/pyproject.toml.local` con extra DB necessari e `frontend/sql_generator/pyproject.toml.local`.
4. Merge `pyproject.toml`: produce `pyproject.toml.merged` in `backend/` e `frontend/sql_generator/` unendo base + local.
5. Generazione `.env.docker`: scrive tutte le variabili necessarie (provider AI, embedding, monitoring, admin, port mapping, ecc.). File: `.env.docker`.
6. Rete Docker: crea la rete se assente (default: `thoth-network`).
7. Volumi Docker: crea i volumi persistenti (`thoth-secrets`, `thoth-backend-static`, `thoth-backend-media`, `thoth-frontend-cache`, `thoth-qdrant-data`, `thoth-shared-data`).
8. Segreti Django: genera in volume `thoth-secrets` due file se mancanti: `django_secret_key` e `django_api_key`.
9. Build & up dei servizi: `docker compose build` e poi `docker compose up -d` sul file compose (default: `docker-compose.yml`).
10. Attesa backend: tenta connessione fino alla disponibilità.
11. Setup iniziale (solo installazione “greenfield”): invoca comandi `manage.py` che generano scope, documentazione e scan GDPR se c’è almeno un provider AI abilitato.

File di riferimento: `scripts/installer.py`.

—

## 4) Servizi Docker e rete

Il file `docker-compose.yml` definisce i servizi principali:

- `backend` (Django + Gunicorn). Volumi: static, media, DB SQLite, `thoth-secrets`, `thoth-shared-data`. Avvio tramite `backend/entrypoint-backend.sh` → `/start.sh`.
- `frontend` (Next.js). Legge `DJANGO_API_KEY` dal volume segreti in `docker/scripts/entrypoint-frontend.sh`.
- `sql-generator` (servizio ausiliario). Legge `DJANGO_API_KEY` in `docker/scripts/entrypoint-sql-generator.sh`.
- `proxy` (Nginx). Smista le richieste verso frontend, backend, sql-generator. Config: `docker/nginx.conf`.
- `thoth-qdrant` (Vector DB). Persistenza su volume `thoth-qdrant-data`.

Tutti i servizi sono collegati alla rete Docker dedicata (default `thoth-network`).

File di riferimento: `docker-compose.yml`.

—

## 5) Gestione dei segreti

- Volume segreti: `thoth-secrets` montato come `/secrets` dentro i container.
- Durante l’installazione, `scripts/installer.py` controlla ed eventualmente crea:
  - `/secrets/django_secret_key`
  - `/secrets/django_api_key`
- Il backend li carica in `backend/entrypoint-backend.sh` e `backend/scripts/start.sh`.
- Il frontend e lo `sql-generator` leggono `DJANGO_API_KEY` rispettivamente in:
  - `docker/scripts/entrypoint-frontend.sh`
  - `docker/scripts/entrypoint-sql-generator.sh`

—

## 6) Precaricamento dati demo `california_schools`

I CSV per il workspace demo si trovano in `setup_csv/docker/`:

- `california_schools_tables.csv`
- `california_schools_columns.csv`
- `california_schools_relationships.csv`
- `selected_dbs.csv`, `vectordb.csv` (config aggiuntive)

Il caricamento avviene nello startup del backend, in `backend/scripts/start.sh`, quando il sistema rileva “greenfield” (nessun `Workspace` esistente):

1. Inizializzazione database SQLite e migrazioni (`manage.py migrate`).
2. Pulizia dati residui per installazione pulita.
3. Import gruppi: `manage.py import_groups --source docker`.
4. Creazione utenti da `config.yml.local` (se presente):
   - Admin: `createsuperuser` con username/email/password da config.
   - Demo: `createsuperuser` con username/email/password da config.
5. Associazione gruppi:
   - Admin → gruppi `admin`, `editor`, `technical_user`.
   - Demo → gruppi `editor`, `technical_user`.
6. Caricamento configurazioni di default: `manage.py load_defaults --source docker`.
7. Collegamento workspace demo all’utente demo:
   - Aggiunge lo `Workspace` con `id=1` alla lista workspaces del demo, e lo imposta come default.
8. Operazioni AI-assistite (se sono presenti API key LLM):
   - Generazione scope DB.
   - Generazione documentazione DB.
   - Scan GDPR.
9. Preprocessing per la demo: caricamento evidence, “Gold SQL” (domande/risposte) e avvio task di preprocessing verso Vector DB.

Queste azioni consentono all’utente demo di usare subito il database `california_schools` senza configurazioni manuali.

File di riferimento: `backend/scripts/start.sh`, CSV in `setup_csv/docker/`.

—

## 7) Porte ed URL di accesso

Le porte sono definite in `config.yml.local` (e riversate in `.env.docker`) e mappate in `docker-compose.yml`. Valori tipici:

- Frontend: `http://localhost:<FRONTEND_PORT>` (default 3040)
- Backend API: `http://localhost:<BACKEND_PORT>` (default 8040)
- SQL Generator: `http://localhost:<SQL_GENERATOR_PORT>` (default 8020)
- Nginx (proxy): `http://localhost:<WEB_PORT>` (default 80)

Percorsi utili:

- Applicazione principale via Nginx: `http://localhost:<WEB_PORT>`
- Pannello admin Django: `http://localhost:<WEB_PORT>/admin`

—

## 8) Credenziali di accesso

Vengono impostate da `config.yml.local` durante il primo avvio (greenfield):

- Superuser admin: username/email/password come specificato in `admin`.
- Superuser demo: username/email/password come specificato in `demo`.

Se al riavvio esistono già workspaces, lo script evita di rifare il setup completo ma verifica la presenza degli utenti admin/demo e li crea se mancanti.

—

## 9) Avvio, log e manutenzione

Comandi principali:

- Avvio/ricostruzione: `./install.sh` (esegue l’intera pipeline: build + up)
- Visualizzare log: `docker compose logs -f`
- Riavvio servizi: `docker compose restart`
- Stop stack: `docker compose down`
- Aggiornamento: `git pull && ./install.sh`

—

## 10) Domande frequenti (FAQ)

- Nessun provider AI configurato: l’installazione funziona comunque; saranno saltate analisi AI, documentazione automatica e scan GDPR. Aggiungi un’API key in `config.yml.local` e rilancia `./install.sh`.
- Dove sono i dati persistenti?
  - Segreti: volume `thoth-secrets`
  - Media/static backend: `thoth-backend-media`, `thoth-backend-static`
  - Qdrant: `thoth-qdrant-data`
  - Dati condivisi: `thoth-shared-data`
  - DB SQLite backend: file in `/app/backend_db/` nel container, mappato da volume
- Come cambiare le porte? Modifica la sezione `ports` in `config.yml.local` e rilancia `./install.sh`.

—

## 11) Riferimenti codice

- Pipeline installer: `scripts/installer.py`
- Validazione config/API key: `scripts/validate_config.py`
- Compose e servizi: `docker-compose.yml`
- Dockerfile backend: `docker/backend.Dockerfile`
- Dockerfile frontend: `docker/frontend.Dockerfile`
- Entrypoint backend: `backend/entrypoint-backend.sh`
- Startup backend: `backend/scripts/start.sh`
- Entrypoint frontend: `docker/scripts/entrypoint-frontend.sh`
- Entrypoint SQL Generator: `docker/scripts/entrypoint-sql-generator.sh`
- Proxy: `docker/nginx.conf`
- CSV demo: `setup_csv/docker/`

—

Con questa procedura, l’ambiente Docker di ThothAI viene installato e avviato in modo ripetibile e sicuro, con dati demo pronti per l’uso e un utente demo già configurato. Se desideri attivare le funzionalità AI-assistite, ricorda di valorizzare almeno una API key valida in `config.yml.local` e ripetere l’installazione.
