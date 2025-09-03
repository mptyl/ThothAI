# Docker Setup Plan - Gestione Gruppi e Utenti

## 1. Preparazione Sistema

### 1.1 Verifica Prerequisiti
```bash
# Verifica installazione Docker
docker --version
docker-compose --version

# Verifica stato Docker daemon
docker info

# Verifica utente corrente
whoami
groups
```

### 1.2 Gestione Gruppi Docker

#### Linux
```bash
# Crea gruppo docker se non esiste
sudo groupadd docker 2>/dev/null || true

# Aggiungi utente corrente al gruppo docker
sudo usermod -aG docker $USER

# Applica modifiche gruppo (evita logout/login)
newgrp docker

# Verifica appartenenza gruppo
groups $USER | grep docker
```

#### macOS
```bash
# Su macOS Docker Desktop gestisce automaticamente i permessi
# Verifica che Docker Desktop sia installato e in esecuzione
docker info
```

## 2. Configurazione Permessi

### 2.1 Struttura Directory
```bash
# Crea struttura directory con permessi corretti
mkdir -p docker/volumes/{postgres,qdrant,redis}
mkdir -p logs/{backend,frontend,sql_generator}
mkdir -p data_exchange/{imports,exports,staging}

# Imposta permessi directory
chmod 755 docker/volumes
chmod 755 logs
chmod 755 data_exchange

# Per volumi Docker (permessi più restrittivi)
chmod 700 docker/volumes/{postgres,qdrant,redis}
```

### 2.2 Gestione Utenti Container

#### Creazione User Mapping
```yaml
# docker-compose.yml - Configurazione utenti
services:
  backend:
    user: "${UID:-1000}:${GID:-1000}"
    environment:
      - USER_ID=${UID:-1000}
      - GROUP_ID=${GID:-1000}
    volumes:
      - ./backend:/app
      - ./data_exchange:/data_exchange
    
  frontend:
    user: "${UID:-1000}:${GID:-1000}"
    volumes:
      - ./frontend:/app
      - ./data_exchange:/data_exchange

  sql-generator:
    user: "${UID:-1000}:${GID:-1000}"
    volumes:
      - ./frontend/sql_generator:/app
      - ./data_exchange:/data_exchange
```

#### Script Setup Utenti
```bash
# setup-docker-users.sh
#!/bin/bash

# Ottieni UID e GID correnti
export UID=$(id -u)
export GID=$(id -g)

# Crea file .env per Docker Compose
cat > .env << EOF
UID=$UID
GID=$GID
COMPOSE_PROJECT_NAME=thoth
EOF

echo "Configurazione utenti Docker completata:"
echo "  UID: $UID"
echo "  GID: $GID"
```

## 3. Gestione Volumi e Permessi

### 3.1 Volumi Named
```yaml
# docker-compose.yml - Volumi named con permessi
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./docker/volumes/postgres
  
  qdrant_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./docker/volumes/qdrant
  
  redis_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./docker/volumes/redis
```

### 3.2 Script Inizializzazione Volumi
```bash
#!/bin/bash
# init-volumes.sh

# Funzione per setup volume con permessi corretti
setup_volume() {
    local volume_path=$1
    local container_uid=${2:-1000}
    local container_gid=${3:-1000}
    
    echo "Setting up volume: $volume_path"
    
    # Crea directory se non esiste
    mkdir -p "$volume_path"
    
    # Imposta proprietario (richiede sudo)
    sudo chown -R $container_uid:$container_gid "$volume_path"
    
    # Imposta permessi
    sudo chmod 755 "$volume_path"
}

# Setup volumi database
setup_volume "./docker/volumes/postgres" 999 999  # PostgreSQL user
setup_volume "./docker/volumes/qdrant" 1000 1000  # Qdrant user
setup_volume "./docker/volumes/redis" 999 999     # Redis user

# Setup directory applicazione
setup_volume "./data_exchange" $(id -u) $(id -g)
setup_volume "./logs" $(id -u) $(id -g)
```

## 4. Sicurezza e Best Practices

### 4.1 Dockerfile Sicuro
```dockerfile
# Esempio Dockerfile con utente non-root
FROM python:3.11-slim

# Crea utente non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Crea directory app con permessi corretti
RUN mkdir -p /app /data_exchange && \
    chown -R appuser:appuser /app /data_exchange

# Cambia a utente non-root
USER appuser

WORKDIR /app

# Copia file con ownership corretta
COPY --chown=appuser:appuser . .

# Installa dipendenze come utente non-root
RUN pip install --user -r requirements.txt

CMD ["python", "manage.py", "runserver"]
```

### 4.2 Network Isolation
```yaml
# docker-compose.yml - Network isolation
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access
  database:
    driver: bridge
    internal: true  # No external access

services:
  proxy:
    networks:
      - frontend
      - backend
  
  backend:
    networks:
      - backend
      - database
  
  postgres:
    networks:
      - database
```

## 5. Script Completo Setup

### 5.1 Master Setup Script
```bash
#!/bin/bash
# docker-setup.sh

set -e  # Exit on error

echo "======================================"
echo "   Docker Setup per ThothAI"
echo "======================================"

# 1. Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "❌ Docker non trovato. Installa Docker prima di continuare."
    exit 1
fi

# 2. Setup Docker group (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "📦 Configurazione gruppo Docker..."
    sudo groupadd docker 2>/dev/null || true
    sudo usermod -aG docker $USER
    echo "✅ Utente aggiunto al gruppo docker"
    echo "⚠️  Potrebbe essere necessario riavviare la sessione"
fi

# 3. Create directory structure
echo "📁 Creazione struttura directory..."
mkdir -p docker/volumes/{postgres,qdrant,redis}
mkdir -p logs/{backend,frontend,sql_generator}
mkdir -p data_exchange/{imports,exports,staging}
mkdir -p scripts

# 4. Set permissions
echo "🔐 Impostazione permessi..."
chmod 755 docker/volumes logs data_exchange scripts
chmod 700 docker/volumes/{postgres,qdrant,redis}

# 5. Create .env file
echo "⚙️  Creazione file .env..."
cat > .env << EOF
# User configuration
UID=$(id -u)
GID=$(id -g)

# Project configuration
COMPOSE_PROJECT_NAME=thoth
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1

# Network configuration
FRONTEND_PORT=3040
BACKEND_PORT=8040
SQL_GENERATOR_PORT=8020
QDRANT_PORT=6333
EOF

# 6. Create docker network
echo "🌐 Creazione network Docker..."
docker network create thoth-network 2>/dev/null || true

# 7. Initialize volumes with correct ownership
echo "💾 Inizializzazione volumi..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo chown -R 999:999 docker/volumes/postgres 2>/dev/null || true
    sudo chown -R 1000:1000 docker/volumes/qdrant 2>/dev/null || true
    sudo chown -R 999:999 docker/volumes/redis 2>/dev/null || true
fi

# 8. Validation
echo ""
echo "======================================"
echo "   Validazione Setup"
echo "======================================"

# Check Docker daemon
if docker info &>/dev/null; then
    echo "✅ Docker daemon attivo"
else
    echo "❌ Docker daemon non risponde"
    exit 1
fi

# Check network
if docker network ls | grep -q thoth-network; then
    echo "✅ Network thoth-network presente"
else
    echo "❌ Network thoth-network non trovata"
fi

# Check directories
for dir in docker/volumes logs data_exchange; do
    if [ -d "$dir" ]; then
        echo "✅ Directory $dir presente"
    else
        echo "❌ Directory $dir mancante"
    fi
done

# Check .env file
if [ -f .env ]; then
    echo "✅ File .env creato"
    echo "   UID: $(grep '^UID=' .env | cut -d= -f2)"
    echo "   GID: $(grep '^GID=' .env | cut -d= -f2)"
else
    echo "❌ File .env non trovato"
fi

echo ""
echo "======================================"
echo "   Setup Completato!"
echo "======================================"
echo ""
echo "Prossimi passi:"
echo "1. Se su Linux, esegui: newgrp docker"
echo "2. Avvia i servizi: docker-compose up -d"
echo "3. Verifica stato: docker-compose ps"
echo ""
```

## 6. Troubleshooting

### 6.1 Problemi Comuni

#### Permission Denied su Socket Docker
```bash
# Linux
sudo chmod 666 /var/run/docker.sock
# O meglio, aggiungi utente al gruppo docker
sudo usermod -aG docker $USER
newgrp docker
```

#### Volumi con Permessi Errati
```bash
# Reset permessi volume
docker-compose down -v
sudo rm -rf docker/volumes/*
./docker-setup.sh
docker-compose up -d
```

#### Container Non Parte per Permessi
```bash
# Verifica logs
docker-compose logs [service-name]

# Esegui container con root per debug
docker-compose run --user root [service-name] /bin/bash

# Fix permessi dall'interno
chown -R appuser:appuser /app
```

### 6.2 Comandi Utili

```bash
# Verifica permessi effettivi nel container
docker-compose exec backend ls -la /app

# Esegui comando come user specifico
docker-compose exec --user root backend chown -R 1000:1000 /data_exchange

# Cleanup completo (ATTENZIONE: cancella tutto)
docker-compose down -v
docker system prune -a --volumes
```

## 7. Checklist Finale

- [ ] Docker e Docker Compose installati
- [ ] Utente aggiunto al gruppo docker (Linux)
- [ ] Directory structure creata
- [ ] Permessi directory configurati
- [ ] File .env con UID/GID creato
- [ ] Network Docker creata
- [ ] Volumi inizializzati con ownership corretta
- [ ] docker-compose.yml configurato con user mapping
- [ ] Test avvio servizi: `docker-compose up -d`
- [ ] Verifica permessi: nessun errore nei logs
- [ ] Verifica accesso: applicazione funzionante

## Note Importanti

1. **macOS**: Docker Desktop gestisce automaticamente i permessi, molti step sono opzionali
2. **Linux**: Richiede configurazione gruppo docker e gestione permessi più attenta
3. **Windows**: Usa WSL2 e segui le istruzioni Linux all'interno di WSL
4. **Production**: Usa secrets Docker invece di file .env per credenziali sensibili
5. **Backup**: Sempre backup dei volumi prima di modifiche ai permessi