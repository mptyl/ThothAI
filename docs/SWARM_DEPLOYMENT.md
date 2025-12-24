# ThothAI - Guida al Deployment su Docker Swarm Remoto

Questo documento fornisce istruzioni dettagliate per il deployment di ThothAI su un server Docker Swarm remoto.

## Indice

1. [Prerequisiti](#1-prerequisiti)
2. [Configurazione](#2-configurazione)
3. [Passaggi di Deployment](#3-passaggi-di-deployment)
4. [URL di Accesso](#4-url-di-accesso)
5. [Monitoraggio e Gestione](#5-monitoraggio-e-gestione)
6. [Risoluzione dei Problemi](#6-risoluzione-dei-problemi)
7. [Pulizia](#7-pulizia)

---

## 1. Prerequisiti

### Requisiti di Sistema

Assicurati di avere i seguenti prerequisiti prima di procedere con il deployment:

- **Docker Swarm inizializzato**: Il server remoto deve avere Docker Swarm attivo e configurato come manager node.
- **Accesso SSH**: Accesso SSH al server remoto con chiave privata o autenticazione password.
- **Account Docker Hub**: Un account Docker Hub attivo per il push e il pull delle immagini.
- **config.yml.local configurato**: Il file di configurazione principale deve essere presente e configurato con le API keys e le impostazioni necessarie.
- **swarm_config.env configurato**: Il file di configurazione specifico per Swarm deve essere creato e configurato.

### Verifica dello Stato Swarm

Verifica che Docker Swarm sia attivo sul server remoto:

```bash
# Connessione SSH al server
ssh user@server

# Verifica stato Swarm
docker info | grep Swarm
```

L'output dovrebbe mostrare: `Swarm: active`

Se Swarm non è attivo, inizializzalo con:

```bash
docker swarm init
```

*Nota: Se il server ha più interfacce di rete, potrebbe essere necessario specificare `--advertise-addr <IP>`.*

### Installazione di Docker Locale

Sulla tua macchina locale (da cui eseguirai il deployment), assicurati di avere:

- Docker Engine installato
- Docker CLI
- SSH client
- `envsubst` (su Linux/macOS)

---

## 2. Configurazione

### Creazione di swarm_config.env

Il file `swarm_config.env` contiene tutte le configurazioni specifiche per il deployment su Swarm.

1. **Copia il template**:

   ```bash
   cp swarm_config.env.template swarm_config.env
   ```

2. **Modifica il file** con un editor di testo:

   ```bash
   nano swarm_config.env
   # o
   vim swarm_config.env
   ```

### Spiegazione delle Variabili di Configurazione

#### Configurazione Docker

```ini
# Nome utente Docker Hub per il pull delle immagini
# OBBLIGATORIO per il deployment su Swarm
DOCKER_USERNAME=tuo-dockerhub-username
```

**Importante**: Sostituisci `tuo-dockerhub-username` con il tuo nome utente Docker Hub reale. Questo valore viene utilizzato per taggare e pushare le immagini.

```ini
# Nome dello stack Docker Swarm
# Utilizzato per identificare e gestire il deployment
STACK_NAME=thoth
```

Il nome dello stack deve essere univoco se hai più deployment sullo stesso server Swarm.

#### Configurazione delle Porte

Le porte configurate vengono esposte sull'host remoto per l'accesso ai servizi:

```ini
# Porta pubblica per l'applicazione web Next.js
# Accesso all'interfaccia utente ThothAI: http://server:FRONTEND_PORT
FRONTEND_PORT=3040
```

```ini
# Porta pubblica per il backend Django tramite proxy Nginx
# Accesso all'API: http://server:BACKEND_PROXY_PORT/api
# Accesso al pannello admin: http://server:BACKEND_PROXY_PORT/admin
BACKEND_PROXY_PORT=8040
```

```ini
# Porta pubblica per il servizio SQL Generator (FastAPI)
# Questo servizio gestisce la generazione di query SQL basata su AI
SQL_GENERATOR_PORT=8020
```

```ini
# Porta pubblica per il database vettoriale Qdrant
# Utilizzato per memorizzare e recuperare gli embeddings per il recupero del contesto
QDRANT_PORT=6333
```

```ini
# Porta pubblica per il servizio Mermaid
# Utilizzato per il rendering di diagrammi dello schema del database e visualizzazioni
MERMAID_SERVICE_PORT=8003
```

```ini
# Porte interne (solitamente non modificate)
WEB_PORT=7000              # Proxy principale
BACKEND_PORT=7002          # Backend diretto
```

**Nota sulle porte**: Se una qualsiasi di queste porte è già in uso sul server remoto, modifica i valori in `swarm_config.env` per evitare conflitti.

### Configurazione di config.yml.local

Il file `config.yml.local` deve essere configurato con:

- **API Keys LLM**: Almeno un provider tra OpenAI, Gemini, o Anthropic (opzionalmente Mistral, DeepSeek, OpenRouter, Ollama, LM Studio)
- **Configurazione Embeddings**: Provider, modello e API key
- **Configurazione Database**: Database SQL e vettoriale
- **Utenti Admin**: Credenziali per l'accesso amministrativo

Esempio di configurazione minima:

```yaml
ai_providers:
  openai:
    enabled: true
    api_key: tua-openai-api-key
    model: gpt-4

embedding:
  provider: openai
  model: text-embedding-3-small
  api_key: tua-embedding-api-key

admin:
  username: admin
  email: admin@example.com
  password: tua-password-sicura

demo:
  username: demo
  password: demo-password

ports:
  frontend: 3040
  backend: 8040
  sql_generator: 8020
  qdrant: 6333
```

---

## 3. Passaggi di Deployment

### Deployment da Linux/macOS

Lo script `install-swarm.sh` automatizza l'intero processo di deployment:

```bash
./install-swarm.sh --server user@server [--port 22] [--key ~/.ssh/id_rsa]
```

**Parametri**:

- `--server` (OBBLIGATORIO): Stringa di connessione SSH (es. `user@192.168.1.100` o `user@swarm.example.com`)
- `--port` (OPZIONALE): Porta SSH (default: 22)
- `--key` (OPZIONALE): Percorso alla chiave privata SSH (default: `~/.ssh/id_rsa`)
- `--help`: Mostra il messaggio di aiuto

**Esempi**:

```bash
# Connessione base
./install-swarm.sh --server user@192.168.1.100

# Con porta SSH personalizzata
./install-swarm.sh --server user@swarm.example.com --port 2222

# Con chiave SSH personalizzata
./install-swarm.sh --server user@server --key ~/.ssh/custom_key

# Tutte le opzioni combinate
./install-swarm.sh --server user@server --port 2222 --key ~/.ssh/custom_key
```

### Deployment da Windows

Per Windows, utilizzare lo script PowerShell `install-swarm.ps1`:

```powershell
.\install-swarm.ps1 -Server user@server [-Port 22] [-Key C:\path\to\key]
```

**Parametri**:

- `-Server` (OBBLIGATORIO): Stringa di connessione SSH
- `-Port` (OPZIONALE): Porta SSH (default: 22)
- `-Key` (OPZIONALE): Percorso alla chiave privata SSH (default: `$env:USERPROFILE\.ssh\id_rsa`)

**Esempi**:

```powershell
# Connessione base
.\install-swarm.ps1 -Server user@192.168.1.100

# Con porta SSH personalizzata
.\install-swarm.ps1 -Server user@swarm.example.com -Port 2222

# Con chiave SSH personalizzata
.\install-swarm.ps1 -Server user@server -Key C:\Users\user\.ssh\custom_key
```

### Cosa Fa lo Script di Deployment

Lo script esegue automaticamente i seguenti passaggi:

1. **Verifica dei Prerequisiti**
   - Verifica che Docker sia installato localmente
   - Verifica che il client SSH sia disponibile
   - Verifica che `envsubst` sia disponibile (Linux/macOS)

2. **Caricamento e Validazione della Configurazione**
   - Carica `swarm_config.env`
   - Verifica che `DOCKER_USERNAME` sia impostato e non sia il valore di default
   - Imposta i valori di default per le porte opzionali

3. **Build delle Immagini Locali**
   - Esegue `./install.sh` per costruire tutte le immagini Docker
   - Genera il file `.env.docker` basato su `config.yml.local`

4. **Tag delle Immagini per Docker Hub**
   - Tagga ogni immagine con il formato: `DOCKER_USERNAME/nome-immagine:latest`
   - Immagini taggate:
     - `thoth-backend`
     - `thoth-frontend`
     - `thoth-sql-generator`
     - `thoth-proxy`
     - `thoth-mermaid-service`
     - `thoth-qdrant`

5. **Push delle Immagini su Docker Hub**
   - Verifica il login a Docker Hub
   - Esegue il push di tutte le immagini taggate
   - Richiede l'autenticazione se non si è già loggati

6. **Preparazione del File Stack**
   - Crea `docker-stack-swarm.yml` sostituendo le variabili di ambiente
   - Sostituisce i nomi dei secrets e configs con quelli specifici dello stack

7. **Deployment dello Stack Remoto**
   - Imposta `DOCKER_HOST` per la connessione SSH
   - Verifica che Swarm sia attivo sul server remoto
   - Crea secrets e configs su Swarm remoto
   - Esegue `docker stack deploy` per distribuire lo stack

8. **Attesa dell'Avvio dei Servizi**
   - Monitora lo stato dei servizi
   - Attende che tutti i servizi siano in stato "running"
   - Timeout massimo: 10 minuti

9. **Visualizzazione dello Stato**
   - Mostra lo stato dei servizi dello stack
   - Mostra i task dello stack
   - Visualizza gli URL di accesso

### Verifica del Deployment

Dopo il completamento dello script, verifica che tutti i servizi siano attivi:

```bash
# Imposta DOCKER_HOST per la connessione SSH
export DOCKER_HOST=ssh://user@server:22

# Visualizza i servizi dello stack
docker stack services thoth

# Visualizza i task dello stack
docker stack ps thoth
```

---

## 4. URL di Accesso

Una volta completato il deployment, i servizi saranno accessibili tramite le porte configurate su `swarm_config.env`.

### URL di Accesso Standard

Assumendo che il server sia accessibile a `server.example.com` e le porte di default:

| Servizio | Porta | URL | Descrizione |
|----------|-------|-----|-------------|
| **Frontend** | `FRONTEND_PORT` (3040) | `http://server:3040` | Interfaccia utente ThothAI |
| **Backend API** | `BACKEND_PROXY_PORT` (8040) | `http://server:8040/api` | API REST Django |
| **Admin Panel** | `BACKEND_PROXY_PORT` (8040) | `http://server:8040/admin` | Pannello amministrativo Django |
| **SQL Generator** | `SQL_GENERATOR_PORT` (8020) | `http://server:8020` | API FastAPI SQL Generator |
| **SQL Generator Docs** | `SQL_GENERATOR_PORT` (8020) | `http://server:8020/docs` | Documentazione Swagger |
| **Mermaid Service** | `MERMAID_SERVICE_PORT` (8003) | `http://server:8003` | Servizio rendering diagrammi |
| **Qdrant Dashboard** | `QDRANT_PORT` (6333) | `http://server:6333/dashboard` | Dashboard database vettoriale |
| **Proxy Web** | `WEB_PORT` (7000) | `http://server:7000` | Proxy Nginx principale |

### Accesso tramite SSH Tunnel

Per maggiore sicurezza, puoi configurare un tunnel SSH per accedere ai servizi:

```bash
# Tunnel per il frontend
ssh -L 3040:localhost:3040 user@server

# Ora puoi accedere a http://localhost:3040 dal tuo browser locale
```

### Configurazione del Firewall

Assicurati che il firewall del server consenta il traffico sulle porte configurate:

```bash
# Per UFW (Ubuntu/Debian)
sudo ufw allow 3040/tcp
sudo ufw allow 8040/tcp
sudo ufw allow 8020/tcp
sudo ufw allow 6333/tcp
sudo ufw allow 8003/tcp

# Per firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=3040/tcp
sudo firewall-cmd --permanent --add-port=8040/tcp
sudo firewall-cmd --permanent --add-port=8020/tcp
sudo firewall-cmd --permanent --add-port=6333/tcp
sudo firewall-cmd --permanent --add-port=8003/tcp
sudo firewall-cmd --reload
```

---

## 5. Monitoraggio e Gestione

### Visualizzazione dei Servizi

```bash
# Imposta DOCKER_HOST
export DOCKER_HOST=ssh://user@server:22

# Visualizza tutti i servizi dello stack
docker stack services thoth

# Visualizza con più dettagli
docker stack services thoth --format "table {{.Name}}\t{{.Replicas}}\t{{.State}}\t{{.Ports}}"
```

### Visualizzazione dei Task

```bash
# Visualizza tutti i task dello stack
docker stack ps thoth

# Visualizza con più dettagli
docker stack ps thoth --no-trunc --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}\t{{.Error}}"
```

### Visualizzazione dei Log

```bash
# Log di un servizio specifico (streaming)
docker service logs -f thoth_backend

# Log degli ultimi 100 righe
docker service logs --tail 100 thoth_frontend

# Log con timestamp
docker service logs -t thoth_sql-generator

# Log di tutti i servizi
docker service logs thoth_backend
docker service logs thoth_frontend
docker service logs thoth_sql-generator
docker service logs thoth_proxy
docker service logs thoth_mermaid-service
docker service logs thoth_thoth-qdrant
```

### Scaling dei Servizi

Per modificare il numero di repliche di un servizio:

```bash
# Scaling del frontend a 3 repliche
docker service scale thoth_frontend=3

# Scaling del backend a 2 repliche
docker service scale thoth_backend=2

# Scaling del proxy a 4 repliche
docker service scale thoth_proxy=4
```

**Nota**: Alcuni servizi come `backend` e `sql-generator` hanno vincoli di placement che richiedono l'esecuzione su manager nodes. Verifica i vincoli prima di scalare.

### Aggiornamento dei Servizi

Per aggiornare un servizio con una nuova immagine:

```bash
# Aggiorna il servizio backend
docker service update --image tuo-username/thoth-backend:latest thoth_backend

# Aggiorna con rollback automatico in caso di fallimento
docker service update --rollback-on-failure thoth_frontend

# Aggiorna con ritardo tra repliche
docker service update --update-delay 10s thoth_backend

# Aggiorna con parallelismo limitato
docker service update --update-parallelism 1 thoth_frontend
```

### Rollback di un Servizio

Per eseguire il rollback all'ultima versione stabile:

```bash
# Rollback del servizio backend
docker service rollback thoth_backend

# Rollback con visualizzazione dei dettagli
docker service rollback --detach=false thoth_frontend
```

### Ispezione dei Servizi

```bash
# Ispeziona la configurazione di un servizio
docker service inspect thoth_backend

# Ispeziona in formato JSON leggibile
docker service inspect --pretty thoth_frontend

# Visualizza le variabili di ambiente di un servizio
docker service inspect thoth_backend --format '{{json .Spec.TaskTemplate.ContainerSpec.Env}}' | jq
```

### Gestione dei Volumi

```bash
# Visualizza i volumi dello stack
docker volume ls | grep thoth

# Ispeziona un volume
docker volume inspect thoth_backend-db

# Backup di un volume (esempio)
docker run --rm -v thoth_backend-db:/data -v $(pwd):/backup ubuntu tar czf /backup/backend-db-backup.tar.gz /data
```

---

## 6. Risoluzione dei Problemi

### Problemi di Connessione SSH

#### Errore: "Connection refused"

```bash
# Verifica che il server sia raggiungibile
ping server.example.com

# Verifica che la porta SSH sia aperta
telnet server.example.com 22

# Verifica che il servizio SSH sia in esecuzione sul server
ssh user@server "systemctl status sshd"
```

#### Errore: "Permission denied (publickey)"

```bash
# Verifica che la chiave SSH sia corretta
ssh -i ~/.ssh/id_rsa user@server

# Aggiungi la chiave all'agent SSH
ssh-add ~/.ssh/id_rsa

# Verifica i permessi della chiave
chmod 600 ~/.ssh/id_rsa
```

#### Errore: "Host key verification failed"

```bash
# Rimuovi la chiave host dal known_hosts
ssh-keygen -R server.example.com

# Oppure disabilita temporaneamente la verifica (non raccomandato in produzione)
ssh -o StrictHostKeyChecking=no user@server
```

### Problemi di Autenticazione Docker Hub

#### Errore: "unauthorized: authentication required"

```bash
# Login a Docker Hub
docker login

# Verifica il login
docker info | grep Username

# Logout e nuovo login se necessario
docker logout
docker login
```

#### Errore: "denied: requested access to the resource is denied"

```bash
# Verifica che l'immagine esista sul tuo account
# Apri https://hub.docker.com/u/tuo-username nel browser

# Verifica il nome dell'immagine
docker images | grep tuo-username

# Push esplicito dell'immagine
docker push tuo-username/thoth-backend:latest
```

### Problemi di Porte

#### Errore: "bind: address already in use"

```bash
# Verifica quale processo sta usando la porta
sudo lsof -i :3040
# o
sudo netstat -tulpn | grep 3040

# Modifica le porte in swarm_config.env
nano swarm_config.env

# Rilancia il deployment
./install-swarm.sh --server user@server
```

#### Porte non accessibili dall'esterno

```bash
# Verifica il firewall
sudo ufw status
# o
sudo firewall-cmd --list-ports

# Apri le porte necessarie (vedi sezione "Configurazione del Firewall")
```

### Problemi con i Servizi

#### Servizi non partono

```bash
# Visualizza i log del servizio
docker service logs thoth_backend

# Visualizza i task con errori
docker stack ps thoth --no-trunc

# Ispeziona il servizio
docker service inspect thoth_backend

# Rimuovi e ridistribuisci lo stack
docker stack rm thoth
./install-swarm.sh --server user@server
```

#### Servizi in stato "pending"

```bash
# Verifica i nodi disponibili
docker node ls

# Verifica le risorse disponibili
docker node inspect self --format '{{.Description.Resources}}'

# Verifica i vincoli di placement
docker service inspect thoth_backend --format '{{json .Spec.TaskTemplate.Placement}}' | jq
```

#### Servizi con crash ripetuti

```bash
# Visualizza i log recenti
docker service logs --tail 50 thoth_backend

# Aumenta il limite di tentativi di riavvio
docker service update --restart-max-attempts 5 thoth_backend

# Aumenta il ritardo tra i riavvii
docker service update --restart-delay 30s thoth_backend
```

### Problemi con i Secrets e Configs

#### Secrets non trovati

```bash
# Visualizza i secrets disponibili
docker secret ls

# Crea i secrets mancanti
echo "contenuto" | docker secret create thoth_env_config -

# Verifica i secrets nello stack
docker service inspect thoth_backend --format '{{json .Spec.TaskTemplate.ContainerSpec.Secrets}}' | jq
```

#### Configs non trovati

```bash
# Visualizza le configs disponibili
docker config ls

# Crea le configs mancanti
docker config create thoth_env_docker .env.docker

# Verifica le configs nello stack
docker service inspect thoth_frontend --format '{{json .Spec.TaskTemplate.Configs}}' | jq
```

### Problemi di Rete

#### Servizi non riescono a comunicare

```bash
# Visualizza le reti
docker network ls

# Ispeziona la rete overlay
docker network inspect thoth_thoth-network

# Verifica la connettività tra servizi
docker run --rm --network thoth_thoth-network alpine ping backend
```

#### Problemi di DNS

```bash
# Verifica la risoluzione DNS da un container
docker run --rm --network thoth_thoth-network alpine nslookup backend

# Verifica la configurazione DNS del servizio
docker service inspect thoth_frontend --format '{{.Spec.TaskTemplate.ContainerSpec.DNSConfig}}'
```

### Problemi di Performance

#### Servizi lenti

```bash
# Verifica l'utilizzo delle risorse
docker stats

# Aumenta i limiti di risorse
docker service update --limit-cpu 2.0 --limit-memory 4G thoth_backend

# Verifica i node labels
docker node inspect self --format '{{.Spec.Labels}}'
```

#### Timeout di connessione

```bash
# Aumenta il timeout di healthcheck
docker service update --health-interval 60s --health-timeout 30s thoth_backend

# Aumenta il periodo di avvio
docker service update --health-start-period 1800s thoth_backend
```

### Debug Avanzato

#### Accesso a un container in esecuzione

```bash
# Trova l'ID del container
docker ps | grep thoth_backend

# Accedi al container
docker exec -it <container_id> /bin/bash

# Oppure usa docker exec con il nome del servizio (prima replica)
docker exec -it $(docker ps -q -f name=thoth_backend.1) /bin/bash
```

#### Verifica delle variabili di ambiente

```bash
# Visualizza le variabili di ambiente di un servizio
docker service inspect thoth_backend --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{println .}}{{end}}'

# Oppure accedi al container e verifica
docker exec $(docker ps -q -f name=thoth_backend.1) env | sort
```

---

## 7. Pulizia

### Rimozione dello Stack

Per rimuovere completamente lo stack ThothAI dal server Swarm:

```bash
# Imposta DOCKER_HOST
export DOCKER_HOST=ssh://user@server:22

# Rimuovi lo stack
docker stack rm thoth
```

Questo comando:
- Arresta tutti i servizi
- Rimuove i servizi dal cluster
- Mantiene i volumi e i secrets

### Rimozione dei Secrets

```bash
# Visualizza i secrets
docker secret ls

# Rimuovi i secrets specifici dello stack
docker secret rm thoth_thoth_env_config
docker secret rm thoth_thoth_config_yml
```

### Rimozione delle Configs

```bash
# Visualizza le configs
docker config ls

# Rimuovi le configs specifiche dello stack
docker config rm thoth_thoth_env_docker
```

### Rimozione dei Volumi

**ATTENZIONE**: La rimozione dei volumi elimina tutti i dati persistenti.

```bash
# Visualizza i volumi
docker volume ls | grep thoth

# Rimuovi i volumi (ATTENZIONE: dati persi!)
docker volume rm thoth_backend-db
docker volume rm thoth-backend-static
docker volume rm thoth-backend-media
docker volume rm thoth-frontend-cache
docker volume rm thoth-qdrant-data
docker volume rm thoth-shared-data
docker volume rm thoth-data-exchange
docker volume rm thoth-logs
```

### Rimozione della Rete

```bash
# Visualizza le reti
docker network ls | grep thoth

# Rimuovi la rete (solo se non utilizzata da altri stack)
docker network rm thoth_thoth-network
```

### Pulizia Completa

Per rimuovere tutto (stack, secrets, configs, volumi, rete):

```bash
#!/bin/bash
# Script di pulizia completa

export DOCKER_HOST=ssh://user@server:22
STACK_NAME="thoth"

# Rimuovi lo stack
echo "Rimozione dello stack..."
docker stack rm $STACK_NAME

# Attendi che i servizi siano rimossi
echo "Attesa rimozione servizi..."
sleep 30

# Rimuovi i secrets
echo "Rimozione dei secrets..."
docker secret ls --filter name=${STACK_NAME}_ -q | xargs -r docker secret rm

# Rimuovi le configs
echo "Rimozione delle configs..."
docker config ls --filter name=${STACK_NAME}_ -q | xargs -r docker config rm

# Rimuovi i volumi
echo "Rimozione dei volumi..."
docker volume ls --filter name=thoth -q | xargs -r docker volume rm

# Rimuovi la rete
echo "Rimozione della rete..."
docker network rm ${STACK_NAME}_thoth-network 2>/dev/null || true

echo "Pulizia completata!"
```

### Backup Prima della Pulizia

Prima di rimuovere i volumi, è consigliabile effettuare un backup:

```bash
#!/bin/bash
# Script di backup dei volumi

export DOCKER_HOST=ssh://user@server:22
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup del database backend
echo "Backup del database backend..."
docker run --rm \
  -v thoth_backend-db:/data \
  -v $(pwd)/$BACKUP_DIR:/backup \
  ubuntu tar czf /backup/backend-db.tar.gz /data

# Backup dei dati Qdrant
echo "Backup dei dati Qdrant..."
docker run --rm \
  -v thoth-qdrant-data:/data \
  -v $(pwd)/$BACKUP_DIR:/backup \
  ubuntu tar czf /backup/qdrant-data.tar.gz /data

# Backup dei dati condivisi
echo "Backup dei dati condivisi..."
docker run --rm \
  -v thoth-shared-data:/data \
  -v $(pwd)/$BACKUP_DIR:/backup \
  ubuntu tar czf /backup/shared-data.tar.gz /data

# Backup dei dati data_exchange
echo "Backup di data_exchange..."
docker run --rm \
  -v thoth-data-exchange:/data \
  -v $(pwd)/$BACKUP_DIR:/backup \
  ubuntu tar czf /backup/data-exchange.tar.gz /data

echo "Backup completato in $BACKUP_DIR"
```

---

## Appendice

### Comandi Utili

```bash
# Imposta DOCKER_HOST per tutte le operazioni remote
export DOCKER_HOST=ssh://user@server:22

# Visualizza tutti gli stack
docker stack ls

# Visualizza i nodi del cluster
docker node ls

# Visualizza i servizi di tutti gli stack
docker service ls

# Visualizza i task in esecuzione
docker ps

# Visualizza i container in esecuzione
docker container ls

# Visualizza le risorse utilizzate
docker stats
```

### Riferimenti

- **Documentazione Docker Swarm**: https://docs.docker.com/engine/swarm/
- **Documentazione Docker Stack**: https://docs.docker.com/engine/reference/commandline/stack/
- **Documentazione Docker Service**: https://docs.docker.com/engine/reference/commandline/service/
- **Documentazione ThothAI**: https://thoth-ai.readthedocs.io

### Supporto

Per problemi o domande relative al deployment su Swarm:

- **GitHub Issues**: https://github.com/mptyl/ThothAI/issues
- **Email**: mp@tylconsulting.it

---

<div align="center">
  <b>ThothAI - Docker Swarm Deployment Guide</b><br>
  Versione 1.0<br>
  Ultimo aggiornamento: 2025
</div>
