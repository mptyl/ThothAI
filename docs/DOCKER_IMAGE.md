# Guida Completa al Deployment di ThothAI

Questa guida descrive i tre scenari di deployment disponibili per ThothAI:

1. **Sviluppo Locale** - Esecuzione nativa dei servizi con Docker minimo
2. **Docker Compose** - Tutti i servizi in Docker per deployment locale
3. **Docker Swarm** - Deployment distribuito su server remoto

---

# Panoramica degli Scenari di Deployment

| Scenario | Script di Avvio | Servizi in Docker | Servizi Nativi | Porte Frontend | Porte Backend |
|----------|----------------|-------------------|----------------|-----------------|----------------|
| **Sviluppo Locale** | [`start-all.sh`](start-all.sh:1) / [`start-all.ps1`](start-all.ps1:1) | Qdrant, Mermaid | Django, SQL Generator, Next.js | 3200 | 8200 |
| **Docker Compose** | [`install.sh`](install.sh:1) / [`install.ps1`](install.ps1:1) | Tutti i servizi | Nessuno | 3040 | 8040 |
| **Docker Swarm** | [`install-swarm.sh`](install-swarm.sh:1) / [`install-swarm.ps1`](install-swarm.ps1:1) | Tutti i servizi (remoto) | Nessuno | 3040 (configurabile) | 8040 (configurabile) |

---

# PARTE 1: SVILUPPO LOCALE

## Panoramica

Lo scenario di sviluppo locale esegue Django, SQL Generator e Next.js nativamente sulla macchina locale, mentre Qdrant e Mermaid Service vengono eseguiti in Docker. Questo è ideale per lo sviluppo e il debug.

## Prerequisiti

Assicurati di avere installato sul tuo sistema:
- **Python 3.9+**
- **Node.js 20+** (per Next.js)
- **Docker Desktop** (in esecuzione, per Qdrant e Mermaid)
- **uv** (gestore pacchetti Python) - Installa con: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Passo 1.1: Clonare il Progetto

```bash
# Naviga nella directory desiderata
cd /path/to/your/projects

# Clona il repository
git clone <repository-url> ThothAI

# Entra nella directory del progetto
cd ThothAI
```

## Passo 1.2: Configurare il Progetto

```bash
# Copia il template di configurazione
cp config.yml config.yml.local

# Modifica config.yml.local con le tue impostazioni
nano config.yml.local
```

Imposta i seguenti parametri in [`config.yml.local`](config.yml.local:1):
- **LLM API Keys**: Almeno una tra `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`
- **Embedding Provider**: `EMBEDDING_PROVIDER`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`
- **Database preferences**: MariaDB, SQL Server, ecc. (opzionale)
- **Admin email**: Per il superuser Django (opzionale)
- **Service ports**: Se i default confliggono

Esempio di configurazione minima:
```yaml
llm:
  openai:
    api_key: "sk-..."
    model: "gpt-4"

embedding:
  provider: "openai"
  api_key: "sk-..."
  model: "text-embedding-3-small"

admin:
  email: "admin@example.com"
```

## Passo 1.3: Avviare i Servizi

### Su Linux/macOS

```bash
# Avvia tutti i servizi
./start-all.sh
```

### Su Windows (PowerShell)

```powershell
# Avvia tutti i servizi
.\start-all.ps1
```

Lo script [`start-all.sh`](start-all.sh:1) eseguirà automaticamente:
1. Generazione di [`.env.local`](.env.local:1) da [`config.yml.local`](config.yml.local:1)
2. Risoluzione delle dipendenze del database locale
3. Sincronizzazione delle dipendenze con `uv`
4. Avvio di Django backend su porta 8200
5. Avvio di Qdrant in Docker su porta 6334
6. Avvio di SQL Generator su porta 8180
7. Avvio di Mermaid Service in Docker su porta 8003
8. Avvio di Next.js frontend su porta 3200

## Passo 1.4: Accesso all'Applicazione

Una volta avviati i servizi, accedi a:

| Servizio | URL | Note |
|----------|-----|------|
| **Frontend** | http://localhost:3200 | Interfaccia utente principale |
| **Backend** | http://localhost:8200 | API Django |
| **Admin Panel** | http://localhost:8200/admin | Pannello amministrativo |
| **SQL Generator** | http://localhost:8180 | API SQL Generator |
| **API Docs** | http://localhost:8180/docs | Documentazione FastAPI |
| **Mermaid Service** | http://localhost:8003 | Servizio diagrammi |
| **Qdrant** | http://localhost:6334 | Database vettoriale |

## Passo 1.5: Arrestare i Servizi

Premi `Ctrl+C` per arrestare tutti i servizi. Lo script ti chiederà se desideri arrestare anche i container Docker (Qdrant e Mermaid).

## Risoluzione dei Problemi

### Porte già in uso

Se una porta è già in uso, lo script [`start-all.sh`](start-all.sh:1) tenterà automaticamente di liberarla. Se non riesce:

```bash
# Trova il processo che usa la porta
lsof -ti:3200

# Termina il processo
kill -9 <PID>
```

Oppure modifica le porte in [`config.yml.local`](config.yml.local:1):
```yaml
ports:
  frontend: 3201
  backend: 8201
  sql_generator: 8181
```

### Dipendenze non sincronizzate

Se ricevi errori sulle dipendenze:

```bash
# Sincronizza le dipendenze del backend
cd backend && uv lock --refresh && uv sync && cd ..

# Sincronizza le dipendenze del SQL Generator
cd frontend/sql_generator && uv lock --refresh && uv sync && cd ../..
```

### Qdrant non si avvia

Assicurati che Docker Desktop sia in esecuzione:

```bash
# Verifica lo stato di Docker
docker ps

# Avvia Qdrant manualmente
docker run -d \
    --name qdrant-thoth \
    --restart unless-stopped \
    -p 6334:6333 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

---

# PARTE 2: DOCKER COMPOSE

## Panoramica

Lo scenario Docker Compose esegue tutti i servizi in Docker sulla macchina locale. Questo è ideale per deployment locali completi e testing di produzione.

## Prerequisiti

Assicurati di avere installato sul tuo sistema:
- **Docker Desktop** (in esecuzione, con Docker Compose)
- **Python 3.9+** (per lo script di installazione)

## Passo 2.1: Clonare il Progetto

```bash
# Naviga nella directory desiderata
cd /path/to/your/projects

# Clona il repository
git clone <repository-url> ThothAI

# Entra nella directory del progetto
cd ThothAI
```

## Passo 2.2: Configurare il Progetto

```bash
# Copia il template di configurazione
cp config.yml config.yml.local

# Modifica config.yml.local con le tue impostazioni
nano config.yml.local
```

Imposta i seguenti parametri in [`config.yml.local`](config.yml.local:1):
- **LLM API Keys**: Almeno una tra `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`
- **Embedding Provider**: `EMBEDDING_PROVIDER`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`
- **Database preferences**: MariaDB, SQL Server, ecc. (opzionale)
- **Admin email**: Per il superuser Django (opzionale)
- **Service ports**: Se i defaults confliggono

## Passo 2.3: Eseguire l'Installer

### Su Linux/macOS

```bash
# Esegui l'installer standard
./install.sh

# Con opzioni aggiuntive
./install.sh --clean-cache    # Pulisci la cache di build
./install.sh --prune-all      # Rimuovi tutte le risorse Docker
./install.sh --help           # Mostra tutte le opzioni
```

### Su Windows (PowerShell)

```powershell
# Esegui l'installer standard
.\install.ps1

# Con opzioni aggiuntive
.\install.ps1 -CleanCache
.\install.ps1 -PruneAll
.\install.ps1 -Help
```

Lo script [`install.sh`](install.sh:1) eseguirà automaticamente:
1. Verifica dei prerequisiti (Docker, Python)
2. Validazione della configurazione in [`config.yml.local`](config.yml.local:1)
3. Generazione di [`.env.docker`](.env.docker:1) da [`config.yml.local`](config.yml.local:1)
4. Generazione dei file `pyproject.toml.merged` per backend e sql-generator
5. Creazione dei volumi e delle reti Docker necessarie
6. Build delle immagini Docker locali
7. Avvio dei servizi con `docker compose up -d`
8. Esecuzione dei comandi di setup iniziale

## Passo 2.4: Verificare lo Stato dei Servizi

```bash
# Verifica lo stato dei container
docker compose ps

# Guarda i log in tempo reale
docker compose logs -f

# Guarda i log di un servizio specifico
docker compose logs -f backend
```

## Passo 2.5: Accesso all'Applicazione

Una volta avviati i servizi, accedi a:

| Servizio | URL | Note |
|----------|-----|------|
| **Frontend** | http://localhost:3040 | Interfaccia utente principale |
| **Backend (via proxy)** | http://localhost:8040 | API Django tramite Nginx |
| **Admin Panel** | http://localhost:8040/admin | Pannello amministrativo |
| **API** | http://localhost:8040/api | API endpoints |
| **SQL Generator** | http://localhost:8020 | API SQL Generator |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | Dashboard Qdrant |
| **Mermaid Service** | http://localhost:8003 | Servizio diagrammi |

## Passo 2.6: Comandi Utili

```bash
# Fermare tutti i servizi
docker compose down

# Fermare e rimuovere volumi
docker compose down -v

# Riavviare un servizio specifico
docker compose restart backend

# Guardare i log di un servizio
docker compose logs backend

# Ricostruire le immagini
docker compose build

# Aggiornare il progetto
git pull && ./install.sh
```

## Risoluzione dei Problemi

### Porte già in uso

Se una porta è già in uso, modifica le porte in [`config.yml.local`](config.yml.local:1):

```yaml
ports:
  frontend: 3041
  backend_proxy: 8041
  sql_generator: 8021
  qdrant: 6334
  mermaid_service: 8004
```

Poi riavvia:

```bash
docker compose down
./install.sh
```

### Build fallita

Se la build delle immagini fallisce:

```bash
# Pulisci la cache di build
docker builder prune -a -f

# Riavvia con cache pulita
./install.sh --clean-cache
```

### Servizi non si avviano

Controlla i log per identificare il problema:

```bash
# Guarda tutti i log
docker compose logs

# Guarda i log di un servizio specifico
docker compose logs backend
docker compose logs frontend
docker compose logs sql-generator
```

### Rimuovere tutte le risorse Docker

Se desideri ricominciare da zero:

```bash
# Rimuovi tutte le risorse ThothAI
./install.sh --prune-all

# Oppure manualmente
docker compose down -v
docker volume ls -q --filter "name=^thoth-" | xargs -r docker volume rm
docker network ls -q --filter "name=^thoth-" | xargs -r docker network rm
docker images --format "{{.Repository}}:{{.Tag}}" | grep -i "^thoth-" | xargs -r docker rmi -f
```

---

# PARTE 3: DOCKER SWARM

## Panoramica

Lo scenario Docker Swarm distribuisce ThothAI su un server remoto. Le immagini Docker vengono costruite localmente, pushate su Docker Hub, e poi distribuite su un cluster Swarm remoto. Questo è ideale per deployment in produzione.

## Prerequisiti

### Sul tuo sistema locale:
- **Docker Desktop** (in esecuzione)
- **Python 3.9+** (per lo script di installazione)
- **SSH client** (per connessione al server remoto)
- **Account Docker Hub** (con accesso push)

### Sul server remoto:
- **Docker** (installato e in esecuzione)
- **Docker Swarm** (inizializzato con `docker swarm init`)
- **Accesso SSH** (con chiave o password)

## Passo 3.1: Clonare il Progetto

```bash
# Naviga nella directory desiderata
cd /path/to/your/projects

# Clona il repository
git clone <repository-url> ThothAI

# Entra nella directory del progetto
cd ThothAI
```

## Passo 3.2: Configurare il Progetto

### Configurazione principale

```bash
# Copia il template di configurazione
cp config.yml config.yml.local

# Modifica config.yml.local con le tue impostazioni
nano config.yml.local
```

Imposta i seguenti parametri in [`config.yml.local`](config.yml.local:1):
- **LLM API Keys**: Almeno una tra `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`
- **Embedding Provider**: `EMBEDDING_PROVIDER`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`
- **Database preferences**: MariaDB, SQL Server, ecc. (opzionale)
- **Admin email**: Per il superuser Django (opzionale)

### Configurazione Swarm

```bash
# Copia il template di configurazione Swarm
cp swarm_config.env.template swarm_config.env

# Modifica swarm_config.env con le tue impostazioni
nano swarm_config.env
```

Imposta i seguenti parametri in [`swarm_config.env`](swarm_config.env:1):

```bash
# Docker Configuration
DOCKER_USERNAME=your-dockerhub-username  # REQUIRED: Il tuo username Docker Hub
STACK_NAME=thoth                        # Nome dello stack Swarm

# Service Port Configuration
FRONTEND_PORT=3040                      # Porta frontend (modifica se necessario)
BACKEND_PROXY_PORT=8040                 # Porta backend via proxy
SQL_GENERATOR_PORT=8020                 # Porta SQL Generator
QDRANT_PORT=6333                        # Porta Qdrant
MERMAID_SERVICE_PORT=8003               # Porta Mermaid Service
```

## Passo 3.3: Preparare il Server Remoto

### Inizializzare Swarm sul server remoto

```bash
# Connettiti al server remoto
ssh user@your-server

# Inizializza Swarm (se non già fatto)
docker swarm init

# Verifica che Swarm sia attivo
docker info | grep Swarm
```

### Verificare la connessione SSH

```bash
# Testa la connessione SSH dal tuo sistema locale
ssh user@your-server

# Se usi una chiave SSH personalizzata
ssh -i ~/.ssh/custom_key user@your-server
```

## Passo 3.4: Eseguire il Deployment

### Su Linux/macOS

```bash
# Deployment standard
./install-swarm.sh --server user@your-server

# Con porta SSH personalizzata
./install-swarm.sh --server user@your-server --port 2222

# Con chiave SSH personalizzata
./install-swarm.sh --server user@your-server --key ~/.ssh/custom_key

# Tutte le opzioni
./install-swarm.sh --server user@your-server --port 2222 --key ~/.ssh/custom_key
```

### Su Windows (PowerShell)

```powershell
# Deployment standard
.\install-swarm.ps1 -Server user@your-server

# Con porta SSH personalizzata
.\install-swarm.ps1 -Server user@your-server -Port 2222

# Con chiave SSH personalizzata
.\install-swarm.ps1 -Server user@your-server -Key ~/.ssh/custom_key

# Tutte le opzioni
.\install-swarm.ps1 -Server user@your-server -Port 2222 -Key ~/.ssh/custom_key
```

Lo script [`install-swarm.sh`](install-swarm.sh:1) eseguirà automaticamente:
1. Verifica dei prerequisiti (Docker, SSH, envsubst)
2. Caricamento e validazione della configurazione da [`swarm_config.env`](swarm_config.env:1)
3. Build locale delle immagini Docker (tramite [`install.sh`](install.sh:1))
4. Tag delle immagini con il tuo username Docker Hub
5. Push delle immagini su Docker Hub
6. Login a Docker Hub (se non già loggato)
7. Preparazione del file [`docker-stack-swarm.yml`](docker-stack-swarm.yml:1) con le variabili sostituite
8. Deploy dello stack sul server remoto tramite SSH
9. Creazione dei secrets e configs su Swarm
10. Attesa che tutti i servizi siano avviati

## Passo 3.5: Verificare lo Stato dei Servizi

```bash
# Verifica lo stato dei servizi sul server remoto
docker stack services thoth

# Verifica i task dei servizi
docker stack ps thoth

# Guarda i log di un servizio specifico
docker service logs thoth_backend
docker service logs thoth_frontend
docker service logs thoth_sql-generator
```

## Passo 3.6: Accesso all'Applicazione

Una volta completato il deployment, accedi a:

| Servizio | URL | Note |
|----------|-----|------|
| **Frontend** | http://your-server:3040 | Interfaccia utente principale |
| **Backend (via proxy)** | http://your-server:8040 | API Django tramite Nginx |
| **Admin Panel** | http://your-server:8040/admin | Pannello amministrativo |
| **API** | http://your-server:8040/api | API endpoints |
| **SQL Generator** | http://your-server:8020 | API SQL Generator |
| **Qdrant Dashboard** | http://your-server:6333/dashboard | Dashboard Qdrant |
| **Mermaid Service** | http://your-server:8003 | Servizio diagrammi |

## Passo 3.7: Comandi Utili per Swarm

```bash
# Rimuovere lo stack
docker stack rm thoth

# Vedere i servizi
docker stack services thoth

# Vedere i task
docker stack ps thoth

# Scalare un servizio
docker service scale thoth_frontend=2

# Guardare i log
docker service logs -f thoth_backend

# Aggiornare un servizio
docker service update --image your-dockerhub-username/thoth-backend:latest thoth_backend

# Rollback di un servizio
docker service rollback thoth_backend
```

## Risoluzione dei Problemi

### Docker Hub login fallito

```bash
# Login manuale a Docker Hub
docker login

# Verifica il login
docker info | grep Username
```

### Connessione SSH fallita

```bash
# Testa la connessione SSH
ssh -v user@your-server

# Se usi una chiave SSH personalizzata
ssh -v -i ~/.ssh/custom_key user@your-server

# Verifica che la chiave sia caricata nell'agent
ssh-add -l
ssh-add ~/.ssh/custom_key
```

### Swarm non inizializzato sul server remoto

```bash
# Connettiti al server remoto
ssh user@your-server

# Inizializza Swarm
docker swarm init

# Verifica lo stato
docker info | grep Swarm
```

### Servizi non si avviano

Controlla i log per identificare il problema:

```bash
# Guarda i log di tutti i servizi
docker stack services thoth

# Guarda i task per vedere gli errori
docker stack ps thoth --no-trunc

# Guarda i log di un servizio specifico
docker service logs thoth_backend --tail 100
```

### Porte già in uso sul server remoto

Modifica le porte in [`swarm_config.env`](swarm_config.env:1):

```bash
FRONTEND_PORT=3041
BACKEND_PROXY_PORT=8041
SQL_GENERATOR_PORT=8021
QDRANT_PORT=6334
MERMAID_SERVICE_PORT=8004
```

Poi riavvia il deployment:

```bash
docker stack rm thoth
./install-swarm.sh --server user@your-server
```

### Immagini non trovate su Docker Hub

Assicurati che le immagini siano state pushate correttamente:

```bash
# Verifica che le immagini esistano su Docker Hub
# Visita https://hub.docker.com/u/your-dockerhub-username

# Oppure verifica localmente
docker images | grep thoth

# Push manuale delle immagini
docker push your-dockerhub-username/thoth-backend:latest
docker push your-dockerhub-username/thoth-frontend:latest
docker push your-dockerhub-username/thoth-sql-generator:latest
docker push your-dockerhub-username/thoth-proxy:latest
docker push your-dockerhub-username/thoth-mermaid-service:latest
```

---

# RIEPILOGO COMANDI PRINCIPALI

## Sviluppo Locale

```bash
# Avvio
./start-all.sh          # Linux/macOS
.\start-all.ps1         # Windows (PowerShell)

# Arresto (Ctrl+C)
```

## Docker Compose

```bash
# Installazione
./install.sh            # Linux/macOS
.\install.ps1           # Windows (PowerShell)

# Avvio
docker compose up -d

# Arresto
docker compose down

# Logs
docker compose logs -f

# Aggiornamento
git pull && ./install.sh
```

## Docker Swarm

```bash
# Deployment
./install-swarm.sh --server user@your-server              # Linux/macOS
.\install-swarm.ps1 -Server user@your-server              # Windows (PowerShell)

# Stato
docker stack services thoth

# Logs
docker service logs -f thoth_backend

# Rimozione
docker stack rm thoth
```

---

# CONFRONTO TRA SCENARI

| Caratteristica | Sviluppo Locale | Docker Compose | Docker Swarm |
|----------------|-----------------|----------------|--------------|
| **Complessità** | Bassa | Media | Alta |
| **Risorse Richieste** | Moderate | Alte (Docker) | Alte (Docker + Server) |
| **Tempo di Setup** | Veloce (~5 min) | Medio (~15 min) | Lento (~30 min) |
| **Isolamento** | Parziale | Completo | Completo |
| **Scalabilità** | No | No | Sì |
| **Ideale per** | Sviluppo e Debug | Testing Locale | Produzione |

---

# FILE DI CONFIGURAZIONE RIFERIMENTO

## config.yml.local

File di configurazione principale per tutti gli scenari. Contiene:
- API keys per LLM e embedding
- Preferenze del database
- Email admin
- Porte dei servizi (per sviluppo locale)

## swarm_config.env

File di configurazione specifico per Docker Swarm. Contiene:
- `DOCKER_USERNAME`: Username Docker Hub (REQUIRED)
- `STACK_NAME`: Nome dello stack Swarm
- Porte dei servizi (FRONTEND_PORT, BACKEND_PROXY_PORT, ecc.)

## .env.local

Generato automaticamente da [`config.yml.local`](config.yml.local:1) per lo sviluppo locale. Non modificare manualmente.

## .env.docker

Generato automaticamente da [`config.yml.local`](config.yml.local:1) per Docker Compose e Swarm. Non modificare manualmente.

---

# NOTE IMPORTANTI

1. **Non committare file sensibili**: I file [`.env.local`](.env.local:1), [`.env.docker`](.env.docker:1), [`config.yml.local`](config.yml.local:1) e [`swarm_config.env`](swarm_config.env:1) contengono API keys e non devono essere committati su git.

2. **Docker Hub Username**: Per Docker Swarm, il `DOCKER_USERNAME` in [`swarm_config.env`](swarm_config.env:1) deve corrispondere al tuo username Docker Hub reale.

3. **Porte**: Se le porte di default sono già in uso, modifica i file di configurazione appropriati prima di avviare i servizi.

4. **Prima installazione**: La prima installazione richiede più tempo per il build delle immagini Docker.

5. **Aggiornamenti**: Per aggiornare ThothAI, esegui `git pull` e riavvia lo script di installazione appropriato.

6. **Backup dei dati**: Per Docker Compose e Swarm, i dati sono persistenti nei volumi Docker. Assicurati di fare backup regolari.

---

# RISORSE AGGIUNTIVE

- [README.md](README.md:1) - Documentazione principale del progetto
- [AGENTS.md](AGENTS.md:1) - Guida agli agenti AI
- [docs/DOCKER_INSTALLATION.md](DOCKER_INSTALLATION.md:1) - Guida all'installazione Docker
- [docs/DOCKER_SWARM.md](DOCKER_SWARM.md:1) - Guida dettagliata a Docker Swarm

---

# SUPPORTO

Per problemi o domande:
1. Controlla la sezione "Risoluzione dei Problemi" appropriata
2. Consulta i log dei servizi per identificare l'errore
3. Verifica che tutti i prerequisiti siano installati
4. Assicurati che i file di configurazione siano corretti
