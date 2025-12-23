# Manuale Completo: Creazione, Pubblicazione e Utilizzo delle Immagini ThothAI

## Prerequisiti

Assicurati di avere installato sul tuo Mac:
- Docker Desktop (in esecuzione)
- Python 3.9+
- Un account Docker Hub (https://hub.docker.com/)

---

# PARTE 1: CREARE LE IMMAGINI LOCALMENTE

## Passo 1.1: Preparare la Configurazione

```bash
# Naviga nella directory del progetto
cd /Users/mp/ThothAI

# Crea il file di configurazione se non esiste
cp config.yml config.yml.local

# Modifica config.yml.local con le tue API keys e impostazioni
nano config.yml.local
```

## Passo 1.2: Eseguire l'Installer

L'installer prepara tutti i file necessari per il build:

```bash
# Esegui l'installer
./install.sh
```

Questo script:
- Verifica i prerequisiti (Docker, Python)
- Valida la configurazione
- Genera `.env.docker`
- Genera i file `pyproject.toml.merged` per backend e sql-generator
- Crea i volumi e le reti Docker necessarie

## Passo 1.3: Verificare i File Generati

```bash
# Verifica che i file siano stati generati
ls -la .env.docker
ls -la backend/pyproject.toml.merged
ls -la frontend/sql_generator/pyproject.toml.merged
```

## Passo 1.4: Build delle Immagini

```bash
# Build usando docker-compose (modo più semplice)
docker compose build

# Oppure build singolarmente per ogni immagine
docker build -f docker/backend.Dockerfile -t thoth-backend:latest .
docker build -f docker/frontend.Dockerfile -t thoth-frontend:latest ./frontend
docker build -f docker/sql-generator.Dockerfile -t thoth-sql-generator:latest .
docker build -f docker/proxy.Dockerfile -t thoth-proxy:latest ./backend/proxy
docker build -f docker/mermaid-service/Dockerfile -t thoth-mermaid-service:latest ./docker/mermaid-service
```

## Passo 1.5: Verificare le Immagini Buildate

```bash
# Lista tutte le immagini ThothAI
docker images | grep thoth
```

Dovresti vedere:
```
thoth-backend              latest    <hash>    <tempo fa>    <dimensione>
thoth-frontend             latest    <hash>    <tempo fa>    <dimensione>
thoth-sql-generator        latest    <hash>    <tempo fa>    <dimensione>
thoth-proxy                latest    <hash>    <tempo fa>    <dimensione>
thoth-mermaid-service      latest    <hash>    <tempo fa>    <dimensione>
```

---

# PARTE 2: PUBBLICARE SU DOCKER HUB (IMMAGINI PUBBLICHE)

## Passo 2.1: Creare Account Docker Hub

1. Vai su https://hub.docker.com/
2. Crea un account gratuito o accedi
3. Verifica l'email se richiesto
4. Crea un Access Token (consigliato per sicurezza):
   - Vai a **Account Settings > Security > New Access Token**
   - Descrizione: "ThothAI Mac Build"
   - Salva il token (non sarà più visibile)

## Passo 2.2: Login a Docker Hub

```bash
# Login usando il token come password
docker login
Username: <tuo-username-docker-hub>
Password: <access-token>
```

## Passo 2.3: Taggare le Immagini per Docker Hub

Sostituisci `<tuo-username>` con il tuo username Docker Hub:

```bash
# Tagga ogni immagine con il tuo username
docker tag thoth-backend:latest <tuo-username>/thoth-backend:latest
docker tag thoth-frontend:latest <tuo-username>/thoth-frontend:latest
docker tag thoth-sql-generator:latest <tuo-username>/thoth-sql-generator:latest
docker tag thoth-proxy:latest <tuo-username>/thoth-proxy:latest
docker tag thoth-mermaid-service:latest <tuo-username>/thoth-mermaid-service:latest
```

## Passo 2.4: Push delle Immagini su Docker Hub

```bash
# Push tutte le immagini
docker push <tuo-username>/thoth-backend:latest
docker push <tuo-username>/thoth-frontend:latest
docker push <tuo-username>/thoth-sql-generator:latest
docker push <tuo-username>/thoth-proxy:latest
docker push <tuo-username>/thoth-mermaid-service:latest
```

## Passo 2.5: Rendere le Immagini Pubbliche

1. Accedi a https://hub.docker.com/
2. Vai al tuo profilo
3. Per ogni repository creato:
   - Clicca sul repository (es. `<tuo-username>/thoth-backend`)
   - Vai a **Settings**
   - In **Visibility**, seleziona **Public**
   - Conferma il cambio

## Passo 2.6: Verificare le Immagini Pubbliche

```bash
# Logout da Docker Hub per testare pull anonimo
docker logout

# Prova a pullare le immagini (dovrebbe funzionare senza login)
docker pull <tuo-username>/thoth-backend:latest
docker pull <tuo-username>/thoth-frontend:latest
docker pull <tuo-username>/thoth-sql-generator:latest
docker pull <tuo-username>/thoth-proxy:latest
docker pull <tuo-username>/thoth-mermaid-service:latest

# Riloggia se necessario
docker login
```

---

# PARTE 3: UTILIZZARE LE IMMAGINI IN LOCALE (DOCKER COMPOSE - NON SWARM)

## Passo 3.1: Creare docker-compose-pubblico.yml

Crea un nuovo file `docker-compose-pubblico.yml` nella root del progetto:

```yaml
version: '3.8'

services:
  # === BACKEND SERVICE ===
  backend:
    image: <tuo-username>/thoth-backend:latest
    container_name: thoth-backend
    restart: always
    volumes:
      - thoth-backend-db:/app/backend_db
      - thoth-shared-data:/app/data
      - ./data_exchange:/app/data_exchange
      - thoth-logs:/app/logs
      - backend-static:/vol/static
      - backend-media:/vol/media
      - thoth-secrets:/secrets
      - ./config.yml.local:/app/config.yml.local:ro
    env_file: .env.docker
    environment:
      - HOST_IP=host.docker.internal
      - DOCKER_ENV=development
      - DB_NAME_DOCKER=/app/backend_db/db.sqlite3
      - FRONTEND_URL=http://localhost:3040
    networks:
      - thoth-network
    extra_hosts:
      - "host.docker.internal:host-gateway"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/admin/login/"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 1200s
    depends_on:
      - thoth-qdrant

  # === FRONTEND SERVICE ===
  frontend:
    image: <tuo-username>/thoth-frontend:latest
    container_name: thoth-frontend
    restart: always
    ports:
      - "3040:3000"
    volumes:
      - frontend-cache:/app/.next/cache
      - ./frontend/public:/app/public:ro
      - thoth-secrets:/secrets
      - ./data_exchange:/app/data_exchange:ro
    env_file: .env.docker
    environment:
      - NODE_ENV=production
      - PORT=3000
      - HOSTNAME=0.0.0.0
      - DJANGO_SERVER=http://proxy:80
      - SQL_GENERATOR_URL=http://sql-generator:8020
      - DOCKER_CONTAINER=true
      - HOST_IP=host.docker.internal
      - NEXT_PUBLIC_DJANGO_SERVER=http://localhost:8040
      - NEXT_PUBLIC_SQL_GENERATOR_URL=http://localhost:8020
    networks:
      - thoth-network
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - backend
      - sql-generator

  # === SQL GENERATOR SERVICE ===
  sql-generator:
    image: <tuo-username>/thoth-sql-generator:latest
    container_name: thoth-sql-generator
    restart: always
    ports:
      - "8020:8020"
    volumes:
      - thoth-shared-data:/app/data
      - ./data_exchange:/app/data_exchange
      - thoth-logs:/app/logs
      - thoth-secrets:/secrets
    env_file: .env.docker
    environment:
      - DOCKER_CONTAINER=true
      - HOST_IP=host.docker.internal
      - PORT=8020
      - DJANGO_SERVER=http://backend:8000
      - VECTOR_DB_HOST=thoth-qdrant
      - VECTOR_DB_PORT=6333
      - DB_ROOT_PATH=/app/data
    networks:
      - thoth-network
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - backend
      - thoth-qdrant

  # === PROXY SERVICE ===
  proxy:
    image: <tuo-username>/thoth-proxy:latest
    container_name: thoth-proxy
    restart: always
    ports:
      - "8040:80"
    volumes:
      - backend-static:/vol/static:ro
      - backend-media:/vol/media:ro
      - ./data_exchange:/vol/data_exchange:ro
    environment:
      - APP_HOST=backend
      - APP_PORT=8000
      - FRONTEND_HOST=frontend
      - FRONTEND_PORT=3000
      - SQL_GEN_HOST=sql-generator
      - SQL_GEN_PORT=8020
      - DEBUG=False
    networks:
      - thoth-network
    depends_on:
      backend:
        condition: service_healthy
      frontend:
        condition: service_started
      sql-generator:
        condition: service_started

  # === MERMAID SERVICE ===
  mermaid-service:
    image: <tuo-username>/thoth-mermaid-service:latest
    container_name: thoth-mermaid-service
    restart: always
    ports:
      - "8003:8001"
    networks:
      - thoth-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # === VECTOR DATABASE SERVICE ===
  thoth-qdrant:
    image: qdrant/qdrant:latest
    container_name: thoth-qdrant
    restart: always
    ports:
      - "6333:6333"
    volumes:
      - qdrant-data:/qdrant/storage
    networks:
      - thoth-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  backend-static:
    name: thoth-backend-static
  backend-media:
    name: thoth-backend-media
  frontend-cache:
    name: thoth-frontend-cache
  qdrant-data:
    name: thoth-qdrant-data
  thoth-secrets:
    name: thoth-secrets
  thoth-backend-db:
    name: thoth-backend-db
  thoth-logs:
    name: thoth-logs
  thoth-shared-data:
    name: thoth-shared-data

networks:
  thoth-network:
    external: true
    name: thoth-network
```

## Passo 3.2: Creare Volumi e Reti (se non esistono)

```bash
# Crea la rete se non esiste
docker network create thoth-network || true

# Crea i volumi se non esistono
docker volume create thoth-backend-static || true
docker volume create thoth-backend-media || true
docker volume create thoth-frontend-cache || true
docker volume create thoth-qdrant-data || true
docker volume create thoth-secrets || true
docker volume create thoth-backend-db || true
docker volume create thoth-logs || true
docker volume create thoth-shared-data || true
```

## Passo 3.3: Avviare i Servizi

```bash
# Avvia tutti i servizi
docker compose -f docker-compose-pubblico.yml up -d

# Verifica lo stato
docker compose -f docker-compose-pubblico.yml ps

# Guarda i log
docker compose -f docker-compose-pubblico.yml logs -f
```

## Passo 3.4: Accesso all'Applicazione

Una volta avviati i servizi, accedi a:
- **Frontend**: http://localhost:3040
- **Backend (via proxy)**: http://localhost:8040
- **Admin**: http://localhost:8040/admin
- **API**: http://localhost:8040/api
- **SQL Generator**: http://localhost:8020
- **Qdrant**: http://localhost:6333
- **Mermaid Service**: http://localhost:8003

## Passo 3.5: Comandi Utili

```bash
# Fermare tutti i servizi
docker compose -f docker-compose-pubblico.yml down

# Fermare e rimuovere volumi
docker compose -f docker-compose-pubblico.yml down -v

# Riavviare un servizio specifico
docker compose -f docker-compose-pubblico.yml restart backend

# Guardare i log di un servizio
docker compose -f docker-compose-pubblico.yml logs backend
```

---

# PARTE 4: UTILIZZARE LE IMMAGINI IN LOCALE (DOCKER SWARM)

## Passo 4.1: Inizializzare Docker Swarm

```bash
# Inizializza Swarm sul tuo Mac
docker swarm init

# Verifica che Swarm sia attivo
docker info | grep Swarm
```

## Passo 4.2: Creare docker-stack-pubblico.yml

Crea un nuovo file `docker-stack-pubblico.yml` nella root del progetto:

```yaml
version: '3.8'

services:
  # === BACKEND SERVICE ===
  backend:
    image: <tuo-username>/thoth-backend:latest
    networks:
      - thoth-network
    volumes:
      - thoth-backend-db:/app/backend_db
      - thoth-shared-data:/app/data
      - thoth-logs:/app/logs
      - backend-static:/vol/static
      - backend-media:/vol/media
      - thoth-data-exchange:/app/data_exchange
    environment:
      - HOST_IP=host.docker.internal
      - DOCKER_ENV=production
      - DB_NAME_DOCKER=/app/backend_db/db.sqlite3
      - FRONTEND_URL=http://localhost:3040
      - DOCKER_CONTAINER=true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/admin/login/"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 1200s
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.role == manager
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G

  # === FRONTEND SERVICE ===
  frontend:
    image: <tuo-username>/thoth-frontend:latest
    networks:
      - thoth-network
    ports:
      - target: 3000
        published: 3040
        protocol: tcp
        mode: host
    volumes:
      - frontend-cache:/app/.next/cache
      - thoth-data-exchange:/app/data_exchange:ro
    environment:
      - NODE_ENV=production
      - PORT=3000
      - HOSTNAME=0.0.0.0
      - DJANGO_SERVER=http://proxy:80
      - SQL_GENERATOR_URL=http://sql-generator:8020
      - DOCKER_CONTAINER=true
      - NEXT_PUBLIC_DJANGO_SERVER=http://localhost:8040
      - NEXT_PUBLIC_SQL_GENERATOR_URL=http://localhost:8020
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.25'
          memory: 512M

  # === SQL GENERATOR SERVICE ===
  sql-generator:
    image: <tuo-username>/thoth-sql-generator:latest
    networks:
      - thoth-network
    ports:
      - target: 8020
        published: 8020
        protocol: tcp
        mode: host
    volumes:
      - thoth-shared-data:/app/data
      - thoth-logs:/app/logs
      - thoth-data-exchange:/app/data_exchange
    environment:
      - DOCKER_CONTAINER=true
      - PORT=8020
      - DJANGO_SERVER=http://backend:8000
      - VECTOR_DB_HOST=thoth-qdrant
      - VECTOR_DB_PORT=6333
      - DB_ROOT_PATH=/app/data
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G

  # === PROXY SERVICE ===
  proxy:
    image: <tuo-username>/thoth-proxy:latest
    networks:
      - thoth-network
    ports:
      - target: 80
        published: 8040
        protocol: tcp
        mode: host
    volumes:
      - backend-static:/vol/static:ro
      - backend-media:/vol/media:ro
      - thoth-data-exchange:/vol/data_exchange:ro
    environment:
      - APP_HOST=backend
      - APP_PORT=8000
      - FRONTEND_HOST=frontend
      - FRONTEND_PORT=3000
      - SQL_GEN_HOST=sql-generator
      - SQL_GEN_PORT=8020
      - DEBUG=False
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.1'
          memory: 128M

  # === MERMAID SERVICE ===
  mermaid-service:
    image: <tuo-username>/thoth-mermaid-service:latest
    networks:
      - thoth-network
    ports:
      - target: 8001
        published: 8003
        protocol: tcp
        mode: host
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 1G
        reservations:
          cpus: '0.1'
          memory: 256M

  # === VECTOR DATABASE SERVICE ===
  thoth-qdrant:
    image: qdrant/qdrant:latest
    networks:
      - thoth-network
    ports:
      - target: 6333
        published: 6333
        protocol: tcp
        mode: host
    volumes:
      - qdrant-data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.25'
          memory: 512M

volumes:
  backend-static:
    driver: local
  backend-media:
    driver: local
  frontend-cache:
    driver: local
  qdrant-data:
    driver: local
  thoth-backend-db:
    driver: local
  thoth-logs:
    driver: local
  thoth-shared-data:
    driver: local
  thoth-data-exchange:
    driver: local

networks:
  thoth-network:
    driver: overlay
    attachable: true
```

## Passo 4.3: Deploy dello Stack

```bash
# Deploy dello stack
docker stack deploy -c docker-stack-pubblico.yml thoth

# Verifica lo stato dei servizi
docker stack services thoth

# Guarda i log di un servizio
docker service logs thoth_backend
```

## Passo 4.4: Accesso all'Applicazione

Le stesse URL di prima:
- **Frontend**: http://localhost:3040
- **Backend (via proxy)**: http://localhost:8040
- **Admin**: http://localhost:8040/admin
- **API**: http://localhost:8040/api
- **SQL Generator**: http://localhost:8020
- **Qdrant**: http://localhost:6333
- **Mermaid Service**: http://localhost:8003

## Passo 4.5: Comandi Utili per Swarm

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
docker service update --image <tuo-username>/thoth-backend:latest thoth_backend
```

---

# RIEPILOGO COMANDI PRINCIPALI

## Build e Push
```bash
# Build locale
docker compose build

# Tag per Docker Hub
docker tag thoth-backend:latest <tuo-username>/thoth-backend:latest
docker tag thoth-frontend:latest <tuo-username>/thoth-frontend:latest
docker tag thoth-sql-generator:latest <tuo-username>/thoth-sql-generator:latest
docker tag thoth-proxy:latest <tuo-username>/thoth-proxy:latest
docker tag thoth-mermaid-service:latest <tuo-username>/thoth-mermaid-service:latest

# Push su Docker Hub
docker push <tuo-username>/thoth-backend:latest
docker push <tuo-username>/thoth-frontend:latest
docker push <tuo-username>/thoth-sql-generator:latest
docker push <tuo-username>/thoth-proxy:latest
docker push <tuo-username>/thoth-mermaid-service:latest
```

## Docker Compose (Non Swarm)
```bash
# Avvia
docker compose -f docker-compose-pubblico.yml up -d

# Ferma
docker compose -f docker-compose-pubblico.yml down

# Logs
docker compose -f docker-compose-pubblico.yml logs -f
```

## Docker Swarm
```bash
# Deploy
docker stack deploy -c docker-stack-pubblico.yml thoth

# Rimuovi
docker stack rm thoth

# Stato
docker stack services thoth
```

---

# NOTE IMPORTANTI

1. **Sostituisci `<tuo-username>`** con il tuo username Docker Hub reale in tutti i file e comandi
2. Le immagini pubbliche possono essere pullate da chiunque senza login
3. Assicurati che `.env.docker` e `config.yml.local` siano presenti nella directory del progetto
4. Per Swarm su Mac, usa `mode: host` per le porte pubblicate
5. I volumi vengono mantenuti tra i riavvii dei container
