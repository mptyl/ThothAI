# Installazione Manuale Docker Swarm - ThothAI

Copyright (c) 2025 Tyl Consulting di Pancotti Marco
This file is part of ThothAI and is released under the Apache License 2.0.
See the LICENSE.md file in the project root for full license information.

---

Questa guida descrive come installare ThothAI su Docker Swarm senza utilizzare la CLI, eseguendo i comandi manualmente da terminale Linux. Le immagini verranno scaricate da Docker Hub.

## Indice

1. [Prerequisiti](#prerequisiti)
2. [Struttura dei File](#struttura-dei-file)
3. [Configurazione](#configurazione)
4. [Preparazione Ambiente](#preparazione-ambiente)
5. [Deploy dello Stack](#deploy-dello-stack)
6. [Verifica e Monitoraggio](#verifica-e-monitoraggio)
7. [Troubleshooting](#troubleshooting)
8. [Rimozione dello Stack](#rimozione-dello-stack)

---

## Prerequisiti

### Software Richiesto

```bash
# Verificare che Docker sia installato
docker --version

# Verificare che Docker Swarm sia inizializzato
docker info | grep "Swarm:"
# Se non è inizializzato, eseguire:
docker swarm init

# Verificare envsubst (parte di gettext)
which envsubst || sudo apt-get install -y gettext-base
```

### Requisiti di Sistema

| Componente | Minimo | Consigliato |
|------------|--------|-------------|
| CPU | 4 core | 8+ core |
| RAM | 8 GB | 16+ GB |
| Disco | 20 GB | 50+ GB |

---

## Struttura dei File

Creare una directory di lavoro e scaricare/creare i file necessari:

```bash
mkdir -p /opt/thothai
cd /opt/thothai
```

I file necessari sono:
- `docker-stack.yml` - Template dello stack Docker
- `config.yml.local` - Configurazione principale
- `swarm_config.env` - Configurazione porte e stack name
- `.env.docker` - Variabili d'ambiente (generato dalla configurazione)

---

## Configurazione

### 1. Creare `swarm_config.env`

```bash
cat > swarm_config.env << 'EOF'
# ThothAI Docker Swarm Configuration
# -----------------------------------

# Docker Hub username per il pull delle immagini
DOCKER_USERNAME=tylconsulting

# Nome dello stack Docker Swarm
STACK_NAME=thothai-swarm

# Versione delle immagini da scaricare
VERSION=latest

# Port Configuration
# ------------------
WEB_PORT=7010           # Porta gateway Nginx (principale)
FRONTEND_PORT=7001      # Porta frontend Next.js
BACKEND_PORT=7002       # Porta backend Django
SQL_GENERATOR_PORT=7003 # Porta SQL Generator FastAPI
MERMAID_SERVICE_PORT=7004  # Porta servizio Mermaid
QDRANT_PORT=7005        # Porta vector database Qdrant
EOF
```

### 2. Creare `config.yml.local`

```bash
cat > config.yml.local << 'EOF'
# ThothAI Configuration
# ---------------------

# Admin credentials
admin:
  username: admin
  email: admin@example.com
  password: CAMBIARE_QUESTA_PASSWORD

# AI Providers (configurare almeno uno)
ai_providers:
  openai:
    enabled: true
    api_key: sk-INSERIRE_API_KEY
    model: gpt-4o
  
  # Opzionali
  gemini:
    enabled: false
    api_key: 
  anthropic:
    enabled: false
    api_key: 

# Embedding configuration
embeddings:
  provider: openai
  api_key: sk-INSERIRE_API_KEY
  model: text-embedding-3-large

# Docker settings
docker:
  deployment_mode: swarm
  stack_name: thothai-swarm

# Ports (devono corrispondere a swarm_config.env)
ports:
  nginx: 7010
  frontend: 7001
  backend: 8000
  sql_generator: 7003
EOF
```

### 3. Generare `.env.docker`

Creare il file delle variabili d'ambiente Docker:

```bash
cat > .env.docker << 'EOF'
# ThothAI Docker Environment
# Generato dalla configurazione

# Admin
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=CAMBIARE_QUESTA_PASSWORD

# AI Providers
OPENAI_API_KEY=sk-INSERIRE_API_KEY
OPENAI_MODEL=gpt-4o

# Embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-INSERIRE_API_KEY
EMBEDDING_MODEL=text-embedding-3-large

# Django settings
DJANGO_SECRET_KEY=$(openssl rand -hex 32)
DJANGO_DEBUG=False
ALLOWED_HOSTS=*
CORS_ALLOW_ALL_ORIGINS=True

# Service URLs (interni)
VECTOR_DB_HOST=thoth-qdrant
VECTOR_DB_PORT=6333
DJANGO_SERVER=http://backend:8000
SQL_GENERATOR_URL=http://sql-generator:8020

# Enabled databases
ENABLED_DATABASES=sqlite,postgresql,mariadb,sqlserver
EOF
```

> [!IMPORTANT]
> Sostituire tutti i valori segnaposto (`CAMBIARE_QUESTA_PASSWORD`, `sk-INSERIRE_API_KEY`) con i valori reali.

---

## Preparazione Ambiente

### 1. Caricare le variabili d'ambiente

```bash
cd /opt/thothai
set -a; source swarm_config.env; set +a
```

### 2. Creare i volumi Docker

```bash
# Volumi richiesti per la persistenza dei dati
docker volume create thoth-secrets
docker volume create thoth-backend-static
docker volume create thoth-backend-media
docker volume create thoth-frontend-cache
docker volume create thoth-qdrant-data
docker volume create thoth-shared-data
docker volume create thoth-data-exchange
docker volume create thoth-backend-db
docker volume create thoth-backend-secrets
docker volume create thoth-logs

echo "✓ Volumi creati"
```

### 3. Creare Secrets e Configs

Docker Swarm utilizza secrets e configs per gestire dati sensibili:

```bash
# Rimuovere eventuali secrets/configs esistenti (ignorare errori se non esistono)
docker secret rm ${STACK_NAME}_thoth_env_config 2>/dev/null || true
docker secret rm ${STACK_NAME}_thoth_config_yml 2>/dev/null || true
docker config rm ${STACK_NAME}_thoth_env_docker 2>/dev/null || true

# Creare nuovi secrets
docker secret create ${STACK_NAME}_thoth_env_config .env.docker
docker secret create ${STACK_NAME}_thoth_config_yml config.yml.local

# Creare config
docker config create ${STACK_NAME}_thoth_env_docker .env.docker

echo "✓ Secrets e configs creati"
```

### 4. Scaricare le immagini da Docker Hub

```bash
echo "Scaricamento immagini da Docker Hub..."

docker pull ${DOCKER_USERNAME}/thoth-backend:${VERSION}
docker pull ${DOCKER_USERNAME}/thoth-frontend:${VERSION}
docker pull ${DOCKER_USERNAME}/thoth-sql-generator:${VERSION}
docker pull ${DOCKER_USERNAME}/thoth-proxy:${VERSION}
docker pull ${DOCKER_USERNAME}/thoth-mermaid-service:${VERSION}
docker pull qdrant/qdrant:latest

echo "✓ Tutte le immagini scaricate"
```

### 5. Scaricare e preparare il file docker-stack.yml

```bash
# Scaricare il template docker-stack.yml dal repository
curl -o docker-stack.yml \
  https://raw.githubusercontent.com/tylconsulting/thothai/main/cli/thothai-cli/src/thothai_cli/templates/docker-stack.yml

# Oppure copiarlo dalla sorgente se disponibile
```

### 6. Preparare il file di deploy

Il file `docker-stack.yml` contiene variabili che devono essere sostituite:

```bash
# Esportare le variabili per envsubst
export DOCKER_USERNAME STACK_NAME VERSION
export WEB_PORT FRONTEND_PORT BACKEND_PORT SQL_GENERATOR_PORT MERMAID_SERVICE_PORT QDRANT_PORT

# Sostituire le variabili nel template
envsubst < docker-stack.yml > docker-stack-deploy.yml

# Importante: sostituire i nomi dei secrets/configs con il prefisso dello stack
sed -i "s/thothai-swarm_thoth_env_config/${STACK_NAME}_thoth_env_config/g" docker-stack-deploy.yml
sed -i "s/thothai-swarm_thoth_config_yml/${STACK_NAME}_thoth_config_yml/g" docker-stack-deploy.yml
sed -i "s/thothai-swarm_thoth_env_docker/${STACK_NAME}_thoth_env_docker/g" docker-stack-deploy.yml

echo "✓ File di deploy preparato: docker-stack-deploy.yml"
```

---

## Deploy dello Stack

### Eseguire il deploy

```bash
cd /opt/thothai

# Deploy dello stack
docker stack deploy -c docker-stack-deploy.yml ${STACK_NAME}

echo "Stack '${STACK_NAME}' in fase di avvio..."
```

### Attendere l'avvio dei servizi

```bash
# Script per attendere che tutti i servizi siano pronti
echo "Attendo l'avvio di tutti i servizi..."
MAX_WAIT=600  # 10 minuti
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Ottieni lo stato delle repliche
    REPLICAS=$(docker stack services ${STACK_NAME} --format "{{.Replicas}}")
    ALL_READY=true
    
    for R in $REPLICAS; do
        CURRENT=$(echo $R | cut -d'/' -f1)
        DESIRED=$(echo $R | cut -d'/' -f2)
        if [ "$CURRENT" != "$DESIRED" ]; then
            ALL_READY=false
            break
        fi
    done
    
    if [ "$ALL_READY" = true ]; then
        echo ""
        echo "✓ Tutti i servizi sono attivi!"
        break
    fi
    
    echo -n "."
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo ""
    echo "⚠ Timeout: alcuni servizi potrebbero non essere ancora pronti"
fi
```

---

## Verifica e Monitoraggio

### Controllare lo stato dei servizi

```bash
# Lista dei servizi dello stack
docker stack services ${STACK_NAME}

# Dettaglio task per servizio
docker stack ps ${STACK_NAME}

# Log di un servizio specifico
docker service logs ${STACK_NAME}_backend --tail 100
docker service logs ${STACK_NAME}_frontend --tail 100
docker service logs ${STACK_NAME}_sql-generator --tail 100
```

### Accesso all'applicazione

Una volta che tutti i servizi sono attivi:

| Servizio | URL |
|----------|-----|
| **Main App (Gateway)** | `http://SERVER_IP:7010` |
| **Frontend diretto** | `http://SERVER_IP:7001` |
| **Admin Django** | `http://SERVER_IP:7010/admin` |
| **API Backend** | `http://SERVER_IP:7010/api` |
| **SQL Generator** | `http://SERVER_IP:7003` |

---

## Troubleshooting

### Problema: Servizio non si avvia

```bash
# Verificare i log del servizio
docker service logs ${STACK_NAME}_NOME_SERVIZIO --tail 200

# Verificare lo stato dei task
docker service ps ${STACK_NAME}_NOME_SERVIZIO --no-trunc

# Forzare l'aggiornamento di un servizio
docker service update --force ${STACK_NAME}_NOME_SERVIZIO
```

### Problema: Secrets non trovati

```bash
# Verificare che i secrets esistano
docker secret ls | grep ${STACK_NAME}

# Ricreare se necessario
docker secret rm ${STACK_NAME}_thoth_env_config
docker secret create ${STACK_NAME}_thoth_env_config .env.docker
```

### Problema: Errori di connessione tra servizi

```bash
# Verificare che la rete overlay esista
docker network ls | grep thoth

# Ispezionare la rete
docker network inspect ${STACK_NAME}_thoth-network
```

### Problema: Backend non risponde

```bash
# Il backend ha un lungo start_period (1200s) per la prima inizializzazione
# Verificare i log per monitorare il progresso
docker service logs -f ${STACK_NAME}_backend
```

---

## Rimozione dello Stack

### Rimuovere lo stack completamente

```bash
# Caricare le variabili se non già caricate
source swarm_config.env

# Rimuovere lo stack
docker stack rm ${STACK_NAME}

echo "Attendo la rimozione dei servizi..."
sleep 10

# Rimuovere secrets e configs
docker secret rm ${STACK_NAME}_thoth_env_config 2>/dev/null || true
docker secret rm ${STACK_NAME}_thoth_config_yml 2>/dev/null || true
docker config rm ${STACK_NAME}_thoth_env_docker 2>/dev/null || true

echo "✓ Stack rimosso"
```

### Rimuovere anche i volumi (⚠️ ATTENZIONE: elimina tutti i dati)

```bash
# Attendere che lo stack sia completamente rimosso
sleep 15

# Rimuovere i volumi
docker volume rm thoth-secrets thoth-backend-static thoth-backend-media \
  thoth-frontend-cache thoth-qdrant-data thoth-shared-data \
  thoth-data-exchange thoth-backend-db thoth-backend-secrets thoth-logs

echo "✓ Volumi rimossi"
```

---

## Riferimenti

- [Docker Swarm Documentation](https://docs.docker.com/engine/swarm/)
- [ThothAI GitHub Repository](https://github.com/tylconsulting/thothai)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
