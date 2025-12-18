# Installazione ThothAI su Docker Swarm

Guida completa per l'installazione di ThothAI in ambiente Docker Swarm.

---

## 📋 Indice

1. [Prerequisiti](#prerequisiti)
2. [Architettura dell'Applicazione](#architettura-dellapplicazione)
3. [Preparazione dell'Ambiente](#preparazione-dellambiente)
4. [Configurazione](#configurazione)
5. [Build e Push delle Immagini](#build-e-push-delle-immagini)
6. [Setup Secrets e Configs](#setup-secrets-e-configs)
7. [Deploy dello Stack](#deploy-dello-stack)
8. [Verifica e Monitoraggio](#verifica-e-monitoraggio)
9. [Aggiornamenti](#aggiornamenti)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisiti

### Software Richiesto

- **Docker Engine** 20.10+ con supporto Swarm
- **Docker Compose** v2.0+ (per generazione configurazione)
- **Python** 3.9+ (per script di configurazione)
- **Git** (per clonare il repository)
- Accesso a un **Docker Registry** (es: `registry.uni.com`)

### Cluster Swarm

```bash
# Inizializzare Swarm (se non già fatto)
docker swarm init

# Verificare lo stato del cluster
docker node ls
```

### Risorse Minime Consigliate

- **CPU**: 4 core
- **RAM**: 8 GB
- **Disco**: 20 GB liberi
- **Network**: connessione stabile per pull/push immagini

---

## Architettura dell'Applicazione

ThothAI è composta da **6 servizi** interconnessi:

| Servizio | Descrizione | Porta | Replicas |
|----------|-------------|-------|----------|
| **backend** | Django REST API + Admin | 8000 (interno) | 1 |
| **frontend** | Next.js Web App | 3040 | 2 |
| **sql-generator** | FastAPI + PydanticAI agents | 8020 | 1 |
| **proxy** | Nginx reverse proxy | 8040 | 2 |
| **mermaid-service** | Generazione diagrammi | 8003 | 1 |
| **thoth-qdrant** | Vector database (Qdrant) | 6333 | 1 |

### Flusso di Comunicazione

```
User → proxy:8040 → backend:8000 (API/Admin)
                  → frontend:3000 (Web UI)
                  → sql-generator:8020 (SQL Gen)

frontend → backend (API calls)
         → sql-generator (SQL generation)

sql-generator → backend (metadata)
              → thoth-qdrant (vector search)
```

---

## Preparazione dell'Ambiente

### 1. Clonare il Repository

```bash
# Clonare il repository ThothAI
git clone <repository-url> ThothAI
cd ThothAI
```

### 2. Creare File di Configurazione

```bash
# Copiare il template di configurazione
cp config.yml config.yml.local

# Editare con le proprie credenziali
nano config.yml.local
```

### 3. Configurazione Minima Richiesta

Editare `config.yml.local` con almeno:

```yaml
# === API KEYS (almeno un provider LLM) ===
llm_providers:
  openai:
    api_key: "sk-..."  # OpenAI API key
  # oppure
  anthropic:
    api_key: "sk-ant-..."  # Anthropic API key
  # oppure
  gemini:
    api_key: "..."  # Google Gemini API key

# === EMBEDDING PROVIDER (obbligatorio) ===
embedding:
  provider: "openai"  # o "voyage", "cohere", "gemini"
  api_key: "sk-..."
  model: "text-embedding-3-small"

# === PORTE (opzionale, default mostrati) ===
ports:
  frontend: 3040
  backend: 8040
  sql_generator: 8020
  mermaid_service: 8003

# === ADMIN (opzionale) ===
admin:
  email: "admin@example.com"
  username: "admin"
  password: "changeme123"  # Cambiare in produzione!
```

**⚠️ IMPORTANTE**: Non committare mai `config.yml.local` con credenziali reali!

---

## Configurazione

### Generare File di Ambiente

ThothAI usa uno script Python per generare i file di configurazione:

```bash
# Installare dipendenze Python necessarie
pip install pyyaml requests toml

# Validare la configurazione
python scripts/validate_config.py config.yml.local

# Configurare embedding provider
python scripts/configure_embedding.py config.yml.local

# Generare .env.docker
python scripts/installer.py --generate-env-only
```

Questo creerà il file `.env.docker` con tutte le variabili d'ambiente necessarie.

---

## Build e Push delle Immagini

### Metodo Automatico (Consigliato)

Usare lo script fornito:

```bash
# Sintassi
./build-and-push-images.sh REGISTRY_URL VERSION [OPTIONS]

# Esempio
./build-and-push-images.sh registry.uni.com/tylconsulting/ThothAI 0.1

# Con opzioni
./build-and-push-images.sh registry.uni.com/tylconsulting/ThothAI 0.1 --no-cache
```

Lo script:
1. ✅ Builda tutte le 5 immagini custom
2. ✅ Pulla e tagga Qdrant
3. ✅ Tagga con VERSION e latest
4. ✅ Esegue login al registry
5. ✅ Pusha tutte le immagini

### Metodo Manuale

Se preferisci eseguire i comandi manualmente:

```bash
# Definire variabili
export REGISTRY_URL="registry.uni.com/tylconsulting/ThothAI"
export VERSION="0.1"

# 1. BUILD BACKEND
docker build \
  -f docker/backend.Dockerfile \
  -t thoth-backend:$VERSION \
  -t $REGISTRY_URL/thoth-backend:$VERSION \
  -t $REGISTRY_URL/thoth-backend:latest \
  .

# 2. BUILD FRONTEND
docker build \
  -f docker/frontend.Dockerfile \
  -t thoth-frontend:$VERSION \
  -t $REGISTRY_URL/thoth-frontend:$VERSION \
  -t $REGISTRY_URL/thoth-frontend:latest \
  ./frontend

# 3. BUILD SQL GENERATOR
docker build \
  -f docker/sql-generator.Dockerfile \
  -t thoth-sql-generator:$VERSION \
  -t $REGISTRY_URL/thoth-sql-generator:$VERSION \
  -t $REGISTRY_URL/thoth-sql-generator:latest \
  .

# 4. BUILD PROXY
docker build \
  -f docker/proxy.Dockerfile \
  -t thoth-proxy:$VERSION \
  -t $REGISTRY_URL/thoth-proxy:$VERSION \
  -t $REGISTRY_URL/thoth-proxy:latest \
  ./backend/proxy

# 5. BUILD MERMAID SERVICE
docker build \
  -f docker/mermaid-service/Dockerfile \
  -t thoth-mermaid-service:$VERSION \
  -t $REGISTRY_URL/thoth-mermaid-service:$VERSION \
  -t $REGISTRY_URL/thoth-mermaid-service:latest \
  ./docker/mermaid-service

# 6. PULL E TAG QDRANT
docker pull qdrant/qdrant:latest
docker tag qdrant/qdrant:latest $REGISTRY_URL/thoth-qdrant:$VERSION
docker tag qdrant/qdrant:latest $REGISTRY_URL/thoth-qdrant:latest

# 7. LOGIN AL REGISTRY
docker login $REGISTRY_URL

# 8. PUSH TUTTE LE IMMAGINI
docker push $REGISTRY_URL/thoth-backend:$VERSION
docker push $REGISTRY_URL/thoth-backend:latest
docker push $REGISTRY_URL/thoth-frontend:$VERSION
docker push $REGISTRY_URL/thoth-frontend:latest
docker push $REGISTRY_URL/thoth-sql-generator:$VERSION
docker push $REGISTRY_URL/thoth-sql-generator:latest
docker push $REGISTRY_URL/thoth-proxy:$VERSION
docker push $REGISTRY_URL/thoth-proxy:latest
docker push $REGISTRY_URL/thoth-mermaid-service:$VERSION
docker push $REGISTRY_URL/thoth-mermaid-service:latest
docker push $REGISTRY_URL/thoth-qdrant:$VERSION
docker push $REGISTRY_URL/thoth-qdrant:latest
```

### Verificare le Immagini

```bash
# Verificare che tutte le immagini siano nel registry
docker search $REGISTRY_URL/thoth

# Oppure tramite API registry (se disponibile)
curl -X GET https://$REGISTRY_URL/v2/_catalog
```

---

## Setup Secrets e Configs

Docker Swarm usa **secrets** per gestire dati sensibili in modo sicuro.

### 1. Creare Secret per .env.docker

```bash
# Creare secret dal file .env.docker generato
docker secret create thoth_env_config .env.docker

# Verificare
docker secret ls | grep thoth
```

### 2. Creare Secret per config.yml.local

```bash
# Creare secret per configurazione
docker secret create thoth_config_yml config.yml.local

# Verificare
docker secret ls
```

### 3. Creare Config per .env.docker (alternativa)

Se preferisci usare configs invece di secrets per variabili non sensibili:

```bash
# Creare config
docker config create thoth_env_docker .env.docker

# Verificare
docker config ls | grep thoth
```

### Differenza Secrets vs Configs

- **Secrets**: Encrypted at rest, per dati sensibili (API keys, password)
- **Configs**: Non-encrypted, per configurazioni generali

**Raccomandazione**: Usa secrets per `.env.docker` dato che contiene API keys.

---

## Deploy dello Stack

### 1. Preparare File di Environment per Stack

Creare un file `.env.swarm` con le variabili per il deploy:

```bash
cat > .env.swarm << EOF
REGISTRY_URL=registry.uni.com/tylconsulting/ThothAI
VERSION=0.1
FRONTEND_PORT=3040
BACKEND_PORT=8040
SQL_GENERATOR_PORT=8020
MERMAID_SERVICE_PORT=8003
WEB_PORT=8040
EOF
```

### 2. Deploy dello Stack

```bash
# Deploy con variabili d'ambiente
export $(cat .env.swarm | xargs)

docker stack deploy -c docker-stack.yml thoth
```

### 3. Verificare il Deploy

```bash
# Verificare i servizi
docker stack services thoth

# Output atteso:
# ID             NAME                      MODE         REPLICAS   IMAGE
# xxx            thoth_backend             replicated   1/1        registry.../thoth-backend:0.1
# xxx            thoth_frontend            replicated   2/2        registry.../thoth-frontend:0.1
# xxx            thoth_sql-generator       replicated   1/1        registry.../thoth-sql-generator:0.1
# xxx            thoth_proxy               replicated   2/2        registry.../thoth-proxy:0.1
# xxx            thoth_mermaid-service     replicated   1/1        registry.../thoth-mermaid-service:0.1
# xxx            thoth_thoth-qdrant        replicated   1/1        registry.../thoth-qdrant:0.1

# Verificare i task (container)
docker stack ps thoth

# Verificare i log
docker service logs thoth_backend
docker service logs thoth_frontend
docker service logs thoth_sql-generator
```

### 4. Attendere l'Inizializzazione

Il backend ha un **healthcheck con 20 minuti di start period** per:
- Inizializzazione database
- Caricamento dati iniziali
- Setup AI models e vector DB

```bash
# Monitorare lo stato del backend
watch -n 5 'docker service ps thoth_backend'

# Seguire i log in tempo reale
docker service logs -f thoth_backend
```

---

## Verifica e Monitoraggio

### Accesso all'Applicazione

Dopo il deploy completo:

- **Frontend**: <http://localhost:3040> (o IP del nodo Swarm)
- **Admin Django**: <http://localhost:8040/admin>
- **API Backend**: <http://localhost:8040/api>
- **SQL Generator**: <http://localhost:8020/docs> (Swagger UI)
- **Qdrant Dashboard**: <http://localhost:6333/dashboard>

### Credenziali Default Admin

Se configurate in `config.yml.local`:

- **Username**: admin (o quello specificato)
- **Password**: changeme123 (o quella specificata)

**⚠️ Cambiare immediatamente in produzione!**

### Comandi di Monitoraggio

```bash
# Stato generale dello stack
docker stack ps thoth

# Servizi e replicas
docker stack services thoth

# Logs di un servizio specifico
docker service logs thoth_backend
docker service logs thoth_frontend
docker service logs thoth_sql-generator

# Logs in tempo reale
docker service logs -f thoth_backend

# Ispezionare un servizio
docker service inspect thoth_backend

# Statistiche risorse
docker stats $(docker ps -q --filter "label=com.docker.stack.namespace=thoth")

# Eventi del cluster
docker events --filter 'type=service'
```

### Health Check

```bash
# Backend health
curl http://localhost:8040/admin/login/

# Frontend health
curl http://localhost:3040

# SQL Generator health
curl http://localhost:8020/health

# Qdrant health
curl http://localhost:6333/
```

---

## Aggiornamenti

### Rolling Update

Docker Swarm supporta aggiornamenti rolling senza downtime:

```bash
# 1. Build nuova versione
./build-and-push-images.sh registry.uni.com/tylconsulting/ThothAI 0.2

# 2. Aggiornare un singolo servizio
docker service update \
  --image registry.uni.com/tylconsulting/ThothAI/thoth-backend:0.2 \
  thoth_backend

# 3. Oppure aggiornare tutto lo stack
export VERSION=0.2
docker stack deploy -c docker-stack.yml thoth
```

### Rollback

In caso di problemi:

```bash
# Rollback di un servizio
docker service rollback thoth_backend

# Oppure tornare alla versione precedente
docker service update \
  --image registry.uni.com/tylconsulting/ThothAI/thoth-backend:0.1 \
  thoth_backend
```

### Scaling

```bash
# Scalare frontend (già 2 replicas di default)
docker service scale thoth_frontend=4

# Scalare proxy
docker service scale thoth_proxy=3

# Verificare
docker service ls
```

**⚠️ NOTA**: Backend e SQL Generator sono configurati con 1 replica per gestione stato/database.

---

## Troubleshooting

### Problema: Servizio non si avvia

```bash
# Verificare i task falliti
docker service ps thoth_backend --no-trunc

# Vedere i log dettagliati
docker service logs thoth_backend

# Verificare i secrets
docker secret ls
docker config ls

# Ispezionare il servizio
docker service inspect thoth_backend
```

### Problema: Immagini non trovate

```bash
# Verificare che le immagini siano nel registry
docker pull registry.uni.com/tylconsulting/ThothAI/thoth-backend:0.1

# Verificare login al registry
docker login registry.uni.com

# Re-push se necessario
docker push registry.uni.com/tylconsulting/ThothAI/thoth-backend:0.1
```

### Problema: Secrets non accessibili

```bash
# Ricreare i secrets
docker secret rm thoth_env_config
docker secret create thoth_env_config .env.docker

# Aggiornare il servizio
docker service update --force thoth_backend
```

### Problema: Backend non risponde dopo 20 minuti

```bash
# Verificare i log per errori
docker service logs thoth_backend | grep -i error

# Verificare connettività con Qdrant
docker service logs thoth_thoth-qdrant

# Verificare che i secrets siano corretti
docker service inspect thoth_backend | grep -A 10 Secrets

# Verificare variabili d'ambiente
docker service inspect thoth_backend | grep -A 20 Env
```

### Problema: Frontend non raggiunge il backend

```bash
# Verificare la rete overlay
docker network inspect thoth-network

# Verificare che i servizi siano sulla stessa rete
docker service inspect thoth_frontend | grep -A 5 Networks
docker service inspect thoth_backend | grep -A 5 Networks

# Testare connettività interna
docker exec $(docker ps -q --filter "name=thoth_frontend") \
  curl http://backend:8000/admin/login/
```

### Problema: Volumi non persistenti

```bash
# Verificare i volumi
docker volume ls | grep thoth

# Ispezionare un volume
docker volume inspect thoth_backend-db

# Backup di un volume
docker run --rm \
  -v thoth_backend-db:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/backend-db-backup.tar.gz -C /data .
```

### Rimozione Completa

Per rimuovere completamente lo stack:

```bash
# 1. Rimuovere lo stack
docker stack rm thoth

# 2. Attendere che tutti i container siano fermati
watch docker ps -a

# 3. Rimuovere i volumi (⚠️ ATTENZIONE: cancella i dati!)
docker volume rm $(docker volume ls -q | grep thoth)

# 4. Rimuovere secrets e configs
docker secret rm thoth_env_config thoth_config_yml
docker config rm thoth_env_docker

# 5. Rimuovere la rete (se non usata da altri)
docker network rm thoth-network
```

---

## Best Practices per Produzione

### 1. Sicurezza

- ✅ Usare **secrets** per tutte le credenziali
- ✅ Cambiare password admin default
- ✅ Limitare accesso al registry
- ✅ Usare TLS/HTTPS per il proxy
- ✅ Configurare firewall per limitare porte esposte
- ✅ Rotazione regolare delle API keys

### 2. Backup

```bash
# Script di backup automatico
cat > backup-thoth.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/thoth/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup database
docker run --rm \
  -v thoth_backend-db:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/backend-db.tar.gz -C /data .

# Backup Qdrant
docker run --rm \
  -v thoth_qdrant-data:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/qdrant-data.tar.gz -C /data .

# Backup configs
cp .env.docker "$BACKUP_DIR/"
cp config.yml.local "$BACKUP_DIR/"

echo "Backup completato in $BACKUP_DIR"
EOF

chmod +x backup-thoth.sh
```

### 3. Monitoraggio

Integrare con:

- **Prometheus** + **Grafana** per metriche
- **ELK Stack** o **Loki** per log centralizzati
- **Portainer** per gestione visuale Swarm

### 4. Alta Disponibilità

Per setup production:

- Cluster Swarm multi-nodo (3+ manager nodes)
- Replicas multiple per servizi stateless (frontend, proxy)
- Database esterno (PostgreSQL) invece di SQLite
- Qdrant cluster per vector DB
- Load balancer esterno (HAProxy, Traefik)

### 5. Risorse

Configurare limiti appropriati in `docker-stack.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '0.5'
      memory: 1G
```

---

## Supporto

Per problemi o domande:
- Consultare la documentazione completa in `README.md`
- Verificare i log con `docker service logs`
- Controllare lo stato con `docker stack ps thoth`

---

## Checklist Pre-Deploy

- [ ] Cluster Swarm inizializzato
- [ ] `config.yml.local` configurato con API keys
- [ ] Script di validazione eseguito con successo
- [ ] Immagini buildate e pushate al registry
- [ ] Secrets creati (`thoth_env_config`, `thoth_config_yml`)
- [ ] File `.env.swarm` preparato con REGISTRY_URL e VERSION
- [ ] Porte firewall aperte (3040, 8040, 8020, 6333)
- [ ] Risorse sufficienti sul cluster (CPU, RAM, Disco)
- [ ] Backup strategy definita
- [ ] Monitoraggio configurato

---

**Copyright © 2025 Tyl Consulting di Pancotti Marco**  
*Rilasciato sotto licenza MIT*
