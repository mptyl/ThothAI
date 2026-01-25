# Guida all'Installazione Docker Swarm

**Docker Swarm** è la modalità raccomandata per **distribuzioni di produzione** che richiedono alta disponibilità, scalabilità e aggiornamenti progressivi (rolling updates). Questa guida copre la configurazione di un cluster ThothAI.

## 1. Prerequisiti

- Un **Nodo Manager** con Docker installato e inizializzato come Swarm Manager.
- Nodi Worker (opzionali) aggiunti allo swarm.
- **Storage Condiviso** (NFS/GlusterFS/EFS) montato su tutti i nodi (Critico per la persistenza distribuita).
- **Accesso SSH** al nodo manager.

## 2. Inizializzazione Swarm

Sul tuo **Nodo Manager**, inizializza lo swarm se non l'hai già fatto:

```bash
docker swarm init --advertise-addr <IP-MANAGER>
```

## 3. Configurazione

### Variabili d'Ambiente
### Variabili d'Ambiente
1.  Copia `.env.swarm.template` in `.env.swarm`.
2.  Modifica `.env.swarm` per configurare:
    - **Storage Condiviso**: Imposta `THOTH_DATA_PATH` (es. `/mnt/nfs/thothai`).
    - **Database Esterno**: Configura `DB_HOST`, `DB_USER`, `DB_PASSWORD` (Il DB interno non è supportato in Swarm).
    - **Chiavi API**: Configura `OPENAI_API_KEY`, ecc.

### Docker Secrets (Sicurezza)
Swarm utilizza **Docker Secrets** per gestire in modo sicuro i dati sensibili. Invece di passare variabili env in chiaro, `docker-up.sh` (o la CLI) converte automaticamente le variabili rilevanti in secrets.

I Secrets gestiti automaticamente includono:
I Secrets gestiti automaticamente includono:
- `thoth_env_config`: Il contenuto del tuo file `.env.swarm` (passato come secret).

## 4. Storage Condiviso (Critico)

In uno Swarm, i container possono spostarsi tra i nodi. I volumi Docker standard `local` rimangono sulla macchina specifica dove sono stati creati. **Devi usare un filesystem condiviso** se vuoi che i dati (Database, Vector DB, Log) persistano in modo coerente attraverso gli spostamenti dei nodi.

### Esempio Setup NFS

1.  **Monta la tua share NFS** su tutti i nodi (Manager e Worker) allo stesso percorso, es. `/mnt/nfs/thothai`.
2.  **Configura `.env.swarm`**: Imposta `THOTH_DATA_PATH=/mnt/nfs/thothai`.

Tutto qui. `docker-stack.yml` usa questo percorso per montare le directory necessarie (bind mount).



> [!WARNING]
> Senza storage condiviso, se un container database si riavvia su un nodo diverso, si "resetterà" effettivamente a uno stato vuoto o allo stato del volume locale di quel nodo specifico.

## 5. Distribuzione

### Metodo A: Usare Script di Supporto (Raccomandato)

Il nostro script `docker-up.sh` rileva `DEPLOYMENT_MODE=swarm`... in realtà per Swarm raccomandiamo il metodo manuale.

**Metodo Manuale Raccomandato per Swarm:**

```bash
./docker-up.sh
```

Esegue questi passaggi:
1.  Crea la rete overlay `thoth-network` (se mancante).
2.  Crea/Aggiorna i Docker Secrets dai tuoi file di configurazione.
3.  Distribuisce lo stack definito in `docker-stack.yml`.

### Metodo B: Distribuzione Manuale

Se vuoi un controllo manuale completo:

1.  **Crea Rete**:
    ```bash
    docker network create --driver overlay thoth-network
    ```

2.  **Crea Secrets**:
    ```bash
    docker secret create thoth_env_config .env.swarm
    docker config create thoth_env_docker .env.swarm
    ```

3.  **Distribuisci Stack**:
    ```bash
    docker stack deploy -c docker-stack.yml thoth
    ```

## 6. Gestione & Scaling

### Controllo Stato
```bash
docker stack services thoth
docker service ls
```

### Scalare i Servizi
Per eseguire istanze multiple del backend (stateless):

```bash
docker service scale thoth_backend=3
```

### Log
I log di Swarm sono aggregati (se si usa un driver di log) o possono essere visualizzati per servizio:

```bash
docker service logs -f thoth_backend
```

## 7. Aggiornamento & Rollback

Per aggiornare l'applicazione (es. nuova versione immagine):
1.  Aggiorna `IMAGE_VERSION` in `.env.docker`.
2.  Esegui di nuovo `./docker-up.sh`.

Swarm esegue un **rolling update** (default: 1 alla volta, 10s ritardo). Se il nuovo container fallisce l'healthcheck, Swarm esegue automaticamente il **rollback** alla versione stabile precedente.
