# ThothAI - Guida al Deployment su Docker Swarm

Questo documento guida all'installazione di ThothAI in modalità **Swarm**, con due percorsi distinti: deployment locale e deployment remoto.

**⚠️ IMPORTANTE**: Entrambi i percorsi utilizzano esclusivamente le immagini pre-compilate da Docker Hub. Non è richiesta alcuna build locale.

---

## 1. Introduzione a Swarm in ThothAI

Docker Swarm permette di orchestrare i container su più nodi, offrendo funzionalità di scaling, rolling updates e gestione dei secret non disponibili nel semplice Docker Compose.

In ThothAI utilizziamo:
*   **docker-stack.yml**: La definizione dello stack di servizi (simile al compose ma specifico per Swarm).
*   **install-swarm-local.sh/ps1**: Script per deployment locale.
*   **manage-swarm.sh/ps1**: Script per gestione di uno stack già esistente (aggiornamento, rollback, backup, ecc.).

---

## 2. Due Percorsi di Deployment

ThothAI offre due percorsi distinti per il deployment su Swarm:

### 2.1 Deployment Locale

**Script**: [`install-swarm-local.sh`](../../install-swarm-local.sh) (Linux/macOS) o [`install-swarm-local.ps1`](../../install-swarm-local.ps1) (Windows)

**Caratteristiche**:
- Deployment sulla macchina locale
- Immagini prelevate da Docker Hub
- Nessuna build locale richiesta
- Ideale per sviluppo e test

**Per maggiori dettagli** (per sviluppatori), consulta: [`../developer/DOCKER_SWARM_LOCAL_BUILD_IT.md`](../developer/DOCKER_SWARM_LOCAL_BUILD_IT.md)

### 2.2 Deployment Remoto

**Script**: [`install-swarm.sh`](../../install-swarm.sh) (Linux/macOS) o [`install-swarm.ps1`](../../install-swarm.ps1) (Windows)

**Caratteristiche**:
- Deployment su server remoto via SSH
- Gestione automatica della connessione SSH
- Immagini prelevate da Docker Hub
- Nessuna build locale richiesta
- Ideale per produzione

---

## 3. Sezione A: Deployment Locale

Questa modalità è utile allo **Sviluppatore** per testare come l'applicazione si comporta in un cluster locale, o all'**Utilizzatore** che vuole sfruttare le feature di Swarm sulla propria macchina.

### 3.1 Prerequisiti
*   Docker Desktop attivo.
*   Inizializzazione Swarm: Esegui `docker swarm init` nel tuo terminale.
*   File `swarm_config.env` configurato con il tuo Docker Hub username.

### 3.2 Configurazione

1.  Copia il template di configurazione:
    ```bash
    cp swarm_config.env.template swarm_config.env
    ```

2.  Modifica `swarm_config.env`:
    *   `DOCKER_USERNAME`: **Obbligatorio**. Il tuo username Docker Hub.
    *   `STACK_NAME`: Nome dello stack (default `thoth`).
    *   Porte (opzionale): Configura su quali porte i servizi saranno esposti.

### 3.3 Esecuzione del Deployment

**Linux/macOS:**
```bash
# Deployment completo
./install-swarm-local.sh

# Deployment senza pull immagini
./install-swarm-local.sh --skip-pull

# Deployment senza ricreare secrets
./install-swarm-local.sh --skip-secrets
```

**Windows (PowerShell):**
```powershell
# Deployment completo
.\install-swarm-local.ps1

# Deployment senza pull immagini
.\install-swarm-local.ps1 -SkipPull

# Deployment senza ricreare secrets
.\install-swarm-local.ps1 -SkipSecrets
```

### 3.4 Accesso ai Servizi

Dopo il deployment, i servizi saranno accessibili su:
- **Frontend**: http://localhost:3040
- **Backend Admin**: http://localhost:8040/admin
- **Backend API**: http://localhost:8040/api
- **SQL Generator**: http://localhost:8020
- **Qdrant Dashboard**: http://localhost:6333/dashboard

**Per istruzioni complete** (per sviluppatori), consulta: [`../developer/DOCKER_SWARM_LOCAL_BUILD_IT.md`](../developer/DOCKER_SWARM_LOCAL_BUILD_IT.md)

---

## 4. Sezione B: Deployment Remoto

Questa è la modalità standard per il **Deployment di Produzione** su un server VPS o Bare Metal.

### 4.1 Prerequisiti
1.  **Server Remoto**: Una macchina Linux accessibile via SSH (`user@server`).
2.  **Docker Swarm sul Server**:
    *   Collegati: `ssh user@server`
    *   Inizializza: `docker swarm init`
3.  **Docker Hub Account**: Necessario per ospitare le immagini che il server scaricherà.

### 4.2 Configurazione

Sul tuo computer locale (macchina di controllo):

1.  Copia il template di configurazione:
    ```bash
    cp swarm_config.env.template swarm_config.env
    ```

2.  Modifica `swarm_config.env`:
    *   `DOCKER_USERNAME`: **Obbligatorio**. Il tuo username Docker Hub.
    *   `STACK_NAME`: Nome dello stack (default `thoth`).
    *   Porte (opzionale): Configura su quali porte il server esporrà i servizi.

### 4.3 Esecuzione del Deployment

**Linux/macOS:**
```bash
# Deployment con server specificato
./install-swarm.sh --server user@192.168.1.100

# Deployment con porta SSH personalizzata
./install-swarm.sh --server user@swarm.example.com --port 2222

# Deployment con chiave SSH personalizzata
./install-swarm.sh --server user@192.168.1.100 --key ~/.ssh/custom_key

# Deployment senza pull immagini
./install-swarm.sh --server user@192.168.1.100 --skip-pull

# Deployment senza ricreare secrets
./install-swarm.sh --server user@192.168.1.100 --skip-secrets
```

**Windows (PowerShell):**
```powershell
# Deployment con server specificato
.\install-swarm.ps1 -Server user@192.168.1.100

# Deployment con porta SSH personalizzata
.\install-swarm.ps1 -Server user@swarm.example.com -Port 2222

# Deployment con chiave SSH personalizzata
.\install-swarm.ps1 -Server user@192.168.1.100 -Key C:\Users\user\.ssh\custom_key

# Deployment senza pull immagini
.\install-swarm.ps1 -Server user@192.168.1.100 -SkipPull

# Deployment senza ricreare secrets
.\install-swarm.ps1 -Server user@192.168.1.100 -SkipSecrets
```

### 4.4 Gestione dell'Accesso SSH

Lo script di deployment remoto gestisce automaticamente:

1. **Prompt interattivo**: Se il server non viene specificato, lo script chiederà di inserire la stringa di connessione SSH.
2. **Test connessione**: Prima del deploy, lo script verifica che la connessione SSH funzioni.
3. **Configurazione DOCKER_HOST**: Imposta automaticamente `DOCKER_HOST=ssh://user@server:port` per comunicare con il Docker del server remoto.
4. **Gestione chiavi SSH**: Supporta chiavi SSH personalizzate e verifica che siano accessibili.

### 4.5 Cosa Fa lo Script Remoto

Lo script `install-swarm` (remoto) esegue automaticamente:

1. **Verifica prerequisiti**: Controlla Docker, SSH e Swarm
2. **Test connessione SSH**: Verifica che il server sia raggiungibile
3. **Carica configurazione**: Legge `swarm_config.env`
4. **Pull immagini**: Scarica le immagini da Docker Hub (localmente, poi il server le scaricherà)
5. **Prepara stack file**: Crea `docker-stack-swarm.yml` con le porte configurate
6. **Crea secrets/configs**: Crea i secrets e configs sul server remoto
7. **Deploy stack**: Esegue `docker stack deploy` sul server remoto
8. **Attende servizi**: Controlla che tutti i servizi siano avviati
9. **Mostra status**: Visualizza lo stato dei servizi e gli URL di accesso

### 4.6 Accesso ai Servizi

Dopo il deployment, i servizi saranno accessibili sul server remoto:
- **Frontend**: http://SERVER_IP:3040
- **Backend Admin**: http://SERVER_IP:8040/admin
- **Backend API**: http://SERVER_IP:8040/api
- **SQL Generator**: http://SERVER_IP:8020
- **Qdrant Dashboard**: http://SERVER_IP:6333/dashboard

### 4.7 Procedura per l'Utilizzatore (Admin del Server)

Se sei l'amministratore del server e vuoi solo aggiornare o gestire lo stack già deployato:

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

## 5. Monitoraggio e Gestione

Una volta deployato su Swarm (locale o remoto):

*   **Vedere i servizi attivi**: `docker stack services thoth`
*   **Logs**: `docker service logs -f thoth_backend`
*   **Visualizzare i task**: `docker stack ps thoth`
*   **Visualizzare i nodi**: `docker node ls`

### 5.1 Comuni per Entrambi i Percorsi

```bash
# Visualizza i servizi
docker stack services thoth

# Visualizza i task
docker stack ps thoth

# Visualizza i logs di un servizio
docker service logs thoth_backend --tail 100

# Visualizza i logs in tempo reale
docker service logs -f thoth_backend

# Rimuovi lo stack
docker stack rm thoth
```

---

## 6. Pulizia

Per rimuovere lo stack:

```bash
docker stack rm thoth
```

*Nota: I volumi dati (DB, Qdrant) di solito persistono per sicurezza. Vanno rimossi manualmente con `docker volume rm` se si desidera un reset totale.*

### 6.1 Rimozione dei Volumi

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

---

## 7. Approfondimento Tecnico: Porte e Volumi

### 7.1 Rimappatura delle Porte

L'applicazione è configurata per permettere la completa rimappatura delle porte esposte sul cluster Swarm, utile se le porte standard sono già in uso.

Questa configurazione avviene nel file `swarm_config.env` (sul **PC Locale** prima del deploy).

Le variabili principali definibili in `swarm_config.env` sono:
*   `FRONTEND_PORT`: Porta pubblica per la UI (Default: `3040`).
*   `BACKEND_PROXY_PORT`: Porta pubblica per l'admin backend e API (Default: `8040`).
*   `SQL_GENERATOR_PORT`: Porta pubblica per il servizio SQL (Default: `8020`).
*   `QDRANT_PORT`: Porta pubblica per il DB vettoriale (Default: `6333`).

**Esempio:** Per esporre il frontend sulla porta 8080 invece che 3040:
1.  **[PC Locale]** Modifica `swarm_config.env`.
2.  **[PC Locale]** Riesegui lo script di deployment appropriato.

### 7.2 Gestione dei Volumi nel Cluster

I volumi definiti in `docker-stack.yml` sono di tipo **Named Volumes**. Questo garantisce che i dati:
1.  Risiedano all'interno della gestione di Docker Swarm.
2.  Siano persistenti anche se i container vengono riavviati.

**Nota Importante sui Nodi:**
I servizi stateful (Backend, DB, Qdrant) hanno un vincolo di piazzamento (`node.role == manager` o vincoli specifici) per garantire che i dati rimangano accessibili dove il volume è stato creato (driver `local`). In un cluster multi-nodo, assicurarsi che questi servizi non vengano spostati su nodi dove il volume non esiste, oppure utilizzare un driver di storage condiviso (es. NFS, CloudStor).

#### Accesso ai Volumi via CLI

È possibile esplorare e gestire il contenuto dei volumi direttamente da riga di comando, senza dover esporre file system nell'host.

**Da eseguire su: [Server Remoto (via SSH) o Locale]**

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

## 8. Workflow Completo Cross-Platform

Dal momento che lo sviluppo avviene su **macOS** (environment Unix-like) e il deploy può avvenire su **Linux** o **Windows** (se supporta Docker Swarm Mode), ecco il riepilogo dei comandi con il contesto esplicito.

### 8.1 Fase 1: Preparazione (Sviluppatore)
**Dove: PC Locale (macOS)**

1.  Preparare il codice e testare localmente.
2.  Configurare `swarm_config.env` con i dettagli del server remoto e le porte desiderate.
3.  Assicurarsi di avere accesso SSH al server remoto (chiave privata pronta).

### 8.2 Fase 2: Deployment Locale (Sviluppatore)
**Dove: PC Locale (macOS)**

Eseguire lo script di deployment locale:
```bash
./install-swarm-local.sh
```

### 8.3 Fase 3: Deployment Remoto (Sviluppatore)
**Dove: PC Locale (macOS)**

Eseguire lo script di deploy remoto che fa da "ponte" verso il server:
```bash
./install-swarm.sh --server admin@192.168.x.x --key /path/to/private_key
```

*Lo script scaricherà le immagini da Docker Hub, si collegherà al server Linux/Windows e applicherà lo stack.*

### 8.4 Fase 4: Verifica (Admin Server)
**Dove: Server Remoto (in SSH)**

Una volta terminato lo script, verificare che tutto giri:
```bash
docker stack ps thoth
```
Verificare che le porte siano aperte come da configurazione scelta.

---

## 9. Confronto dei Percorsi

| Caratteristica | Locale | Remoto |
|---------------|---------|--------|
| Script | `install-swarm-local.sh/ps1` | `install-swarm.sh/ps1` |
| Target | Macchina locale | Server remoto via SSH |
| Accesso | localhost | IP/hostname del server |
| SSH | Non richiesto | Richiesto e gestito |
| Immagini | Da Docker Hub | Da Docker Hub |
| Build locale | Non necessaria | Non necessaria |
| Uso | Sviluppo, test | Produzione |
| Prompt server | No | Sì, se non specificato |

---

## 10. Troubleshooting Comune

### 10.1 Problema: Connessione SSH Fallita

**Soluzione**:
- Verifica che l'indirizzo IP/hostname sia corretto
- Verifica che la porta SSH sia corretta (default 22)
- Verifica che la chiave SSH sia accessibile
- Verifica che il server sia raggiungibile: `ping server_ip`

### 10.2 Problema: Swarm Non Attivo

**Soluzione**:
```bash
# Inizializza Swarm
docker swarm init
```

### 10.3 Problema: Immagini Non Trovate

**Soluzione**:
- Verifica che `DOCKER_USERNAME` sia corretto in `swarm_config.env`
- Verifica che le immagini esistano su Docker Hub:
  ```bash
  docker pull your-username/thoth-backend:latest
  ```

### 10.4 Problema: Servizi Non Partono

**Soluzione**:
- Controlla i logs dei servizi:
  ```bash
  docker service logs thoth_backend --tail 100
  ```
- Verifica che i secrets/configs siano stati creati correttamente:
  ```bash
  docker secret ls
  docker config ls
  ```

---

## 11. Riferimenti

- **Deployment Locale** (per sviluppatori): [`../developer/DOCKER_SWARM_LOCAL_BUILD_IT.md`](../developer/DOCKER_SWARM_LOCAL_BUILD_IT.md)
- **Gestione Stack** (aggiornamento/rollback): [`../developer/MANAGE_SWARM_IT.md`](../developer/MANAGE_SWARM_IT.md)
- **Installazione Swarm**: [`../thothai_install/DOCKER_SWARM_INSTALLATION_IT.md`](../thothai_install/DOCKER_SWARM_INSTALLATION_IT.md)
- **Docker Stack**: `docker-stack.yml`
- **Script deploy locale**: `install-swarm-local.sh`, `install-swarm-local.ps1`
- **Script deploy remoto**: `install-swarm.sh`, `install-swarm.ps1`
- **Script gestione**: `deploy-swarm.sh`, `deploy-swarm.ps1`
