# ThothAI - Guida al Deployment Locale su Docker Swarm

Questo documento fornisce istruzioni per il deployment di ThothAI su Docker Swarm locale utilizzando le immagini pre-compilate da Docker Hub.

**⚠️ IMPORTANTE**: Il flusso di lavoro consigliato è: **clone → configure → install-swarm-local**

1. **Clone del progetto**: Clona il repository ThothAI
2. **Configura le porte**: Modifica `swarm_config.env` per configurare le porte di accesso e il DOCKER_USERNAME per le immagini su Docker Hub
3. **Esegui install-swarm-local**: Esegui `./install-swarm-local.sh` per deploy locale

Non è necessario fare build locale o push delle immagini - queste sono già su Docker Hub.

---

## 1. Panoramica

Il deployment locale su Docker Swarm permette di testare l'applicazione in un ambiente orchestrato senza la necessità di un server remoto. Questo approccio è ideale per:

- Sviluppatori che vogliono testare il comportamento in Swarm
- Amministratori che vogliono testare la configurazione prima del deploy remoto
- Dimostrazioni locali con funzionalità Swarm

### 1.1 Architettura

```
┌─────────────────────────────────────────────────────────────┐
│              Local Docker Swarm Cluster                   │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐              │
│  │   Frontend   │  │   Backend    │              │
│  │  (Next.js)   │  │  (Django)    │              │
│  └──────────────┘  └──────────────┘              │
│         │                  │                         │
│         └──────────────────┤                         │
│                           │                         │
│                    ┌──────┴──────┐                │
│                    │  SQL Gen    │                │
│                    │  (FastAPI)  │                │
│                    └─────────────┘                │
│                           │                         │
│                    ┌──────┴──────┐                │
│                    │   Qdrant    │                │
│                    │ (Vector DB)  │                │
│                    └─────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Prerequisiti

### 2.1 Requisiti di Sistema

- **Docker Desktop** installato e in esecuzione
- **Docker Swarm** inizializzato (vedi sezione 3)
- **Python 3.9+** installato
- **File di configurazione** `swarm_config.env` creato e configurato

### 2.2 File di Configurazione Richiesti

- `swarm_config.env`: Configurazione principale per Swarm (creato dal template)
- `config.yml.local`: Configurazione dell'applicazione
- `.env.docker`: Variabili d'ambiente per Docker

---

## 3. Inizializzazione Docker Swarm

Se Docker Swarm non è ancora inizializzato:

```bash
docker swarm init
```

Verifica che Swarm sia attivo:

```bash
docker info | grep Swarm
# Output atteso: Swarm: active
```

---

## 4. Configurazione

### 4.1 Creazione del File di Configurazione

Copia il template di configurazione:

```bash
cp swarm_config.env.template swarm_config.env
```

### 4.2 Modifica di swarm_config.env

Modifica `swarm_config.env` con i tuoi parametri:

```bash
# Nome utente Docker Hub (OBBLIGATORIO)
DOCKER_USERNAME=your-dockerhub-username

# Nome dello stack Swarm
STACK_NAME=thoth

# Versione delle immagini
VERSION=latest

# Porte di esposizione (opzionale, valori default mostrati)
FRONTEND_PORT=3040
BACKEND_PROXY_PORT=8040
SQL_GENERATOR_PORT=8020
QDRANT_PORT=6333
MERMAID_SERVICE_PORT=8003
WEB_PORT=7000
BACKEND_PORT=7002
```

**Nota importante**: Il `DOCKER_USERNAME` deve corrispondere al tuo account Docker Hub dove sono ospitate le immagini ThothAI.

### 4.3 Configurazione Porte

Le porte possono essere personalizzate per evitare conflitti con altri servizi:

| Servizio | Porta Default | Descrizione |
|-----------|---------------|--------------|
| Frontend (Next.js) | 3040 | Interfaccia web principale |
| Backend (via proxy) | 8040 | API Django e Admin Panel |
| SQL Generator | 8020 | API FastAPI per generazione SQL |
| Qdrant | 6333 | Dashboard database vettoriale |
| Mermaid Service | 8003 | Servizio rendering diagrammi |
| Web (Proxy) | 7000 | Proxy Nginx |

---

## 5. Deployment con install-swarm-local

### 5.1 Script Bash (Linux/macOS)

```bash
# Deployment completo (pull immagini + deploy)
./install-swarm-local.sh

# Deployment senza pull immagini (usa cache)
./install-swarm-local.sh --skip-pull

# Deployment senza ricreare secrets
./install-swarm-local.sh --skip-secrets
```

### 5.2 Script PowerShell (Windows)

```powershell
# Deployment completo
.\install-swarm-local.ps1

# Deployment senza pull immagini
.\install-swarm-local.ps1 -SkipPull

# Deployment senza ricreare secrets
.\install-swarm-local.ps1 -SkipSecrets
```

### 5.3 Cosa Fa lo Script

Lo script `install-swarm-local` esegue automaticamente:

1. **Verifica prerequisiti**: Controlla Docker e Swarm
2. **Carica configurazione**: Legge `swarm_config.env`
3. **Pull immagini**: Scarica le immagini da Docker Hub
4. **Prepara stack file**: Crea `docker-stack-swarm.yml` con le porte configurate
5. **Crea secrets/configs**: Crea i secrets e configs necessari
6. **Deploy stack**: Esegue `docker stack deploy`
7. **Attende servizi**: Controlla che tutti i servizi siano avviati
8. **Mostra status**: Visualizza lo stato dei servizi e gli URL di accesso

---

## 6. Verifica dello Stato dei Servizi

### 6.1 Visualizza i Servizi

```bash
docker stack services thoth
```

Output esempio:
```
ID             NAME                MODE        REPLICAS   IMAGE
abc123def456   thoth_frontend      replicated  1/1        username/thoth-frontend:latest
def456ghi789   thoth_backend       replicated  1/1        username/thoth-backend:latest
ghi789jkl012   thoth_sql-generator replicated  1/1        username/thoth-sql-generator:latest
...
```

### 6.2 Visualizza i Task

```bash
docker stack ps thoth
```

### 6.3 Visualizza i Logs

```bash
# Logs del backend
docker service logs thoth_backend --tail 50

# Logs del frontend
docker service logs thoth_frontend --tail 50

# Logs dello SQL Generator
docker service logs thoth_sql-generator --tail 50

# Logs in tempo reale
docker service logs -f thoth_backend
```

---

## 7. Accesso ai Servizi

Dopo il deployment, i servizi saranno accessibili su:

| Servizio | URL Locale |
|----------|-----------|
| Frontend (Next.js) | http://localhost:3040 |
| Backend Admin | http://localhost:8040/admin |
| Backend API | http://localhost:8040/api |
| SQL Generator | http://localhost:8020 |
| Mermaid Service | http://localhost:8003 |
| Qdrant Dashboard | http://localhost:6333/dashboard |
| Web (Proxy) | http://localhost:7000 |

---

## 8. Gestione e Manutenzione

### 8.1 Aggiornamento dello Stack

Per aggiornare i servizi con nuove versioni delle immagini:

```bash
# Modifica VERSION in swarm_config.env
VERSION=new-version

# Riesegui lo script
./install-swarm-local.sh
```

### 8.2 Riavvio dei Servizi

```bash
# Riavvia un servizio specifico
docker service update --force thoth_backend

# Riavvia tutti i servizi
docker service update --force $(docker service ls -q)
```

### 8.3 Scalatura dei Servizi

```bash
# Scala il frontend a 3 repliche
docker service scale thoth_frontend=3

# Scala il backend a 2 repliche
docker service scale thoth_backend=2
```

---

## 9. Rimozione dello Stack

### 9.1 Rimozione Completa

```bash
docker stack rm thoth
```

Questo comando:
- Rimuove tutti i servizi
- Rimuove le reti overlay
- **Mantiene i volumi** per sicurezza

### 9.2 Rimozione dei Volumi (ATTENZIONE)

Per rimuovere anche i volumi (questo eliminerà tutti i dati):

```bash
# Rimuovi lo stack prima
docker stack rm thoth

# Rimuovi i volumi
docker volume rm thoth_thoth-backend-db
docker volume rm thoth_qdrant-data
docker volume rm thoth-data-exchange
docker volume rm thoth-shared-data
docker volume rm thoth-logs
docker volume rm backend-static
docker volume rm backend-media
docker volume rm frontend-cache
```

### 9.3 Rimozione Secrets e Configs

```bash
# Rimuovi secrets
docker secret ls
docker secret rm <secret_name>

# Rimuovi configs
docker config ls
docker config rm <config_name>
```

---

## 10. Troubleshooting

### 10.1 Problema: Le immagini non vengono trovate

**Soluzione**: Verifica che il DOCKER_USERNAME sia corretto:

```bash
# Controlla swarm_config.env
cat swarm_config.env | grep DOCKER_USERNAME

# Verifica che le immagini esistano su Docker Hub
docker pull your-username/thoth-backend:latest
```

### 10.2 Problema: Secrets/Configs non trovati

**Soluzione**: Ricrea i secrets e configs:

```bash
# Rimuovi vecchi secrets/configs
docker secret rm thoth_env_config 2>/dev/null || true
docker secret rm thoth_config_yml 2>/dev/null || true
docker config rm thoth_env_docker 2>/dev/null || true

# Crea nuovi
docker secret create thoth_env_config .env.docker
docker secret create thoth_config_yml config.yml.local
docker config create thoth_env_docker .env.docker
```

### 10.3 Problema: I servizi non partono

**Soluzione**: Controlla i logs dei servizi:

```bash
docker service logs thoth_backend --tail 100
docker service logs thoth_frontend --tail 100
```

### 10.4 Problema: Porte già in uso

**Soluzione**: Modifica le porte in `swarm_config.env`:

```bash
# Modifica le porte conflittuali
FRONTEND_PORT=8080
BACKEND_PROXY_PORT=8081

# Riesegui lo script
./install-swarm-local.sh
```

### 10.5 Problema: Swarm non attivo

**Soluzione**: Inizializza Swarm:

```bash
docker swarm init
```

Se Docker Desktop è in uso, Swarm può essere abilitato dalle impostazioni.

---

## 11. Comandi Utili

### 11.1 Monitoraggio

```bash
# Visualizza tutti i servizi
docker service ls

# Visualizza i nodi Swarm
docker node ls

# Visualizza le reti
docker network ls

# Visualizza i volumi
docker volume ls
```

### 11.2 Debug

```bash
# Esegui un comando in un container
docker exec -it $(docker ps -q -f name=thoth_backend) sh

# Ispeziona un servizio
docker service inspect thoth_backend

# Ispeziona un task
docker inspect <task_id>
```

### 11.3 Pulizia

```bash
# Rimuovi immagini non utilizzate
docker image prune -a

# Rimuovi container fermati
docker container prune

# Rimuovi volumi non utilizzati
docker volume prune

# Rimuovi reti non utilizzate
docker network prune
```

---

## 12. Differenza con Deployment Remoto

| Caratteristica | Locale | Remoto |
|---------------|---------|--------|
| Script | `install-swarm-local.sh` | `install-swarm.sh` |
| Server | Macchina locale | Server remoto via SSH |
| Accesso | localhost | IP/hostname del server |
| Immagini | Da Docker Hub | Da Docker Hub |
| Build locale | Non necessaria | Non necessaria |
| SSH | Non richiesto | Richiesto |

Per il deployment remoto, consulta [`3_DOCKER_SWARM_IT.md`](3_DOCKER_SWARM_IT.md).

---

## 13. Riferimenti

- Documentazione Swarm: [`3_DOCKER_SWARM_IT.md`](3_DOCKER_SWARM_IT.md)
- Installazione Swarm: [`../thothai_install/DOCKER_SWARM_INSTALLATION_IT.md`](../thothai_install/DOCKER_SWARM_INSTALLATION_IT.md)
- Docker Stack: `docker-stack.yml`
- Script di deploy locale: `install-swarm-local.sh`, `install-swarm-local.ps1`
- Script di deploy remoto: `install-swarm.sh`, `install-swarm.ps1`
