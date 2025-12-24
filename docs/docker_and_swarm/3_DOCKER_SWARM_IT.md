# ThothAI - Guida al Deployment su Docker Swarm

Questo documento guida all'installazione di ThothAI in modalità **Swarm**, sia per test locali che per deploy su server remoti di produzione.

---

## 1. Introduzione a Swarm in ThothAI

Docker Swarm permette di orchestrare i container su più nodi, offrendo funzionalità di scaling, rolling updates e gestione dei secret non disponibili nel semplice Docker Compose.

In ThothAI utilizziamo:
*   **docker-stack.yml**: La definizione dello stack di servizi (simile al compose ma specifico per Swarm).
*   **install-swarm.sh**: Script di automazione per il deploy.

---

## 2. Sezione A: Docker Swarm Locale (Simulazione)

Questa modalità è utile allo **Sviluppatore** per testare come l'applicazione si comporta in un cluster prima del deploy reale, o all'**Utilizzatore** che vuole sfruttare le feature di Swarm sulla propria macchina.

### 2.1 Prerequisiti
*   Docker Desktop attivo.
*   Inizializzazione Swarm: Esegui `docker swarm init` nel tuo terminale. (Se sei già in un cluster, salta questo passaggio).

### 2.2 Procedura per lo Sviluppatore
Lo sviluppatore vuole testare le immagini costruite localmente senza necessariamente pusharle su Hub (anche se Swarm preferisce immagini da registry).

1.  **Build delle immagini**:
    ```bash
    ./install.sh --no-start
    ```
    Questo costruisce le immagini `thoth-backend:latest`, `thoth-frontend:latest` ecc.

2.  **Deploy dello Stack**:
    Per usare immagini locali con Swarm, queste devono essere accessibili. In Docker Desktop (single node swarm), le immagini locali sono visibili.
    
    Prepara le configurazioni (secret/config) ed esegui:
    ```bash
    # Crea configurazioni (esempio manuale per test locale)
    docker config create thoth_env_docker .env.docker
    docker stack deploy -c docker-stack.yml thoth
    ```

### 2.3 Procedura per l'Utilizzatore
L'utilizzatore locale usa Swarm raramente se non per test specifici. Si consiglia l'installazione standard `install.sh` (vedi `DOCKER_LOCAL.md`).

---

## 3. Sezione B: Docker Swarm Remoto (Produzione)

Questa è la modalità standard per il **Deployment di Produzione** su un server VPS o Bare Metal.

### 3.1 Prerequisiti
1.  **Server Remoto**: Una macchina Linux accessibile via SSH (`user@server`).
2.  **Docker Swarm sul Server**:
    *   Collegati: `ssh user@server`
    *   Inizializza: `docker swarm init`
3.  **Docker Hub Account**: Necessario per ospitare le immagini che il server scaricherà.

### 3.2 Configurazione
Sul tuo computer locale (macchina di controllo):

1.  Copia il template di configurazione Swarm:
    ```bash
    cp swarm_config.env.template swarm_config.env
    ```
2.  Modifica `swarm_config.env`:
    *   `DOCKER_USERNAME`: **Obbligatorio**. Il tuo username Docker Hub.
    *   `STACK_NAME`: Nome dello stack (default `thoth`).
    *   Porte (opzionale): Configura su quali porte il server esporrà i servizi.

### 3.3 Procedura per lo Sviluppatore (Deployer)
Chi esegue il deploy agisce come "Sviluppatore/DevOps" che pubblica le immagini.

Usa lo script `install-swarm.sh` (o `.ps1` su Windows). Questo script automatizza l'intero ciclo:

```bash
# Esempio di comando
./install-swarm.sh --server user@192.168.1.100 --key ~/.ssh/id_rsa
```

**Cosa fa lo script:**
1.  **Build**: Compila le immagini localmente.
2.  **Tag & Push**: Tagga le immagini con `DOCKER_USERNAME/image:latest` e le carica su Docker Hub.
3.  **Config**: Genera i file di configurazione necessari.
4.  **Remote Deploy**: Si collega via SSH al server remoto e lancia `docker stack deploy`.

### 3.4 Procedura per l'Utilizzatore (Admin del Server)
Se sei l'amministratore del server e vuoi solo aggiornare o gestire lo stack già deployato senza rieseguire tutto il processo di build:

1.  Collegati al server: `ssh user@server`.
2.  Verifica lo stato:
    ```bash
    docker stack ps thoth
    docker service ls
    ```
3.  Aggiornamento manuale (se nuove immagini sono già su Hub):
    ```bash
    docker service update --image username/thoth-backend:latest thoth_backend --force
    ```

---

## 4. Monitoraggio e Gestione

Una volta deployato su Swarm remoto:

*   **Vedere i servizi attivi**: `docker stack services thoth`
*   **Logs**: `docker service logs -f thoth_backend`
*   **Accesso**:
    *   Frontend: `http://SERVER_IP:FRONTEND_PORT` (default 3040)
    *   Backend Admin: `http://SERVER_IP:BACKEND_PROXY_PORT/admin` (default 8040)

## 5. Pulizia
Per rimuovere lo stack dal server remoto, eseguire questo comando sul **Server Remoto**:
```bash
docker stack rm thoth
```
*Nota: I volumi dati (DB, Qdrant) di solito persistono per sicurezza. Vanno rimossi manualmente con `docker volume rm` se si desidera un reset totale.*

---

## 6. Approfondimento Tecnico: Porte e Volumi

### 6.1 Rimappatura delle Porte
L'applicazione è configurata per permettere la completa rimappatura delle porte esposte sul cluster Swarm, utile se le porte standard (80, 443, 3040, etc.) sono già in uso o se si desidera offuscare i servizi.

Questa configurazione avviene nel file `swarm_config.env` (sul **PC Locale (Sviluppatore)** prima del deploy) o direttamente via variabili d'ambiente.

Le variabili principali definibili in `swarm_config.env` sono:
*   `FRONTEND_PORT`: Porta pubblica per la UI (Default: `3040`).
*   `BACKEND_PROXY_PORT`: Porta pubblica per l'admin backend e API (Default: `8040`).
*   `SQL_GENERATOR_PORT`: Porta pubblica per il servizio SQL (Default: `8020`).
*   `QDRANT_PORT`: Porta pubblica per il DB vettoriale (Default: `6333`).

**Esempio:** Per esporre il frontend sulla porta 8080 invece che 3040:
1.  **[PC Locale]** Modifica `swarm_config.env`.
2.  **[PC Locale]** Riesegui `./install-swarm.sh ...`.

### 6.2 Gestione dei Volumi nel Cluster
I volumi definiti in `docker-stack.yml` sono di tipo **Named Volumes**. Questo garantisce che i dati:
1.  Risiedano all'interno della gestione di Docker Swarm.
2.  Siano persistenti anche se i container vengono riavviati.

**Nota Importante sui Nodi:**
I servizi stateful (Backend, DB, Qdrant) hanno un vincolo di piazzamento (`node.role == manager` o vincoli specifici) per garantire che i dati rimangano accessibili dove il volume è stato creato (driver `local`). In un cluster multi-nodo, assicurarsi che questi servizi non vengano spostati su nodi dove il volume non esiste, oppure utilizzare un driver di storage condiviso (es. NFS, CloudStor).

#### Accesso ai Volumi via CLI
È possibile esplorare e gestire il contenuto dei volumi direttamente da riga di comando sul server, senza dover esporre file system nell'host.

**Da eseguire su: [Server Remoto (via SSH)]**

1.  **Listare i volumi attivi:**
    ```bash
    docker volume ls
    # Troverai volumi come: thoth_thoth-backend-db, thoth_qdrant-data, ecc.
    ```

2.  **Ispezionare il contenuto di un volume:**
    Non è possibile fare semplicemente `ls` su un volume docker. Si usa un container temporaneo "helper":
    ```bash
    # Esempio: vedere il contenuto dei log
    docker run --rm -it -v thoth_thoth-logs:/vol_data alpine ls -la /vol_data
    ```

3.  **Copiare file da/verso un volume (Backup/Restore):**
    ```bash
    # Copiare DB fuori dal volume locale
    docker run --rm -v thoth_thoth-backend-db:/vol_data -v $(pwd):/backup alpine cp /vol_data/db.sqlite3 /backup/db_backup.sqlite3
    ```

---

## 7. Workflow Completo Cross-Platform
Dal momento che lo sviluppo avviene su **macOS** (environment Unix-like) e il deploy può avvenire su **Linux** o **Windows** (se supporta Docker Swarm Mode), ecco il riepilogo dei comandi con il contesto esplicito.

### Fase 1: Preparazione (Sviluppatore)
**Dove: PC Locale (macOS)**

1.  Preparare il codice e testare localmente.
2.  Configurare `swarm_config.env` con i dettagli del server remoto e le porte desiderate.
3.  Assicurarsi di avere accesso SSH al server remoto (chiave privata pronta).

### Fase 2: Deploy (Sviluppatore)
**Dove: PC Locale (macOS)**

Eseguire lo script di deploy che fa da "ponte" verso il server.
```bash
./install-swarm.sh --server admin@192.168.x.x --key /path/to/private_key
```
*Lo script costruirà le immagini su Mac, le invierà al Registry, si collegherà al server Linux/Windows e applicherà lo stack.*

### Fase 3: Verifica (Admin Server)
**Dove: Server Remoto (in SSH)**

Una volta terminato lo script, verificare che tutto giri:
```bash
docker stack ps thoth
```
Verificare che le porte siano aperte come da configurazione scelta.
