# Guida all'Installazione Docker Swarm

**Docker Swarm** è la modalità raccomandata per **distribuzioni di produzione** che richiedono alta disponibilità, scalabilità e aggiornamenti progressivi (rolling updates). Questa guida copre la configurazione di un cluster ThothAI.

## 1. Prerequisiti

- Un **Nodo Manager** con Docker installato e inizializzato come Swarm Manager.
- Nodi Worker (opzionali) aggiunti allo swarm.
- **Storage Condiviso** (NFS/GlusterFS/EFS) montato su tutti i nodi (Critico per la persistenza distribuita).
- **Accesso SSH** al nodo manager.

> [!TIP]
> **Test Locale su Mac/Windows**: È possibile testare Swarm localmente anche senza NFS. In questo caso, usa un percorso locale assoluto per `THOTH_DATA_PATH` (es. `/Users/nome/thoth_data`). Nota che questo funzionerà solo in configurazione single-node.

## 2. Inizializzazione Swarm

Sul tuo **Nodo Manager**, inizializza lo swarm se non l'hai già fatto:

```bash
docker swarm init --advertise-addr <IP-MANAGER>
```

### Configurazione Ambiente

Le impostazioni di Swarm sono divise in due file:

1.  **`.env.swarm`**: Configurazione dell'applicazione (API keys, DB, ecc.).
    - Copia `.env.swarm.template` in `.env.swarm`.
    - Imposta `THOTH_DATA_PATH` (es. `/mnt/nfs/thothai` o un path locale per test).
    - Configura il Database Esterno (PostgreSQL).

2.  **`swarm_config.env`**: Configurazione dell'infrastruttura Swarm (Porte, Stack Name).
    - Copia `swarm_config.env.template` in `swarm_config.env`.
    - **Rimappatura Porte**: Qui puoi cambiare le porte pubbliche (es. `WEB_PORT`, `FRONTEND_PORT`) se quelle di default (serie 7000) sono occupate.
    - Definisci lo `STACK_NAME` (default: `thothai-swarm`).

### Docker Secrets (Sicurezza)
Swarm utilizza **Docker Secrets** per gestire in modo sicuro i dati sensibili. Invece di passare variabili env in chiaro, `docker-up.sh` (o la CLI) converte automaticamente le variabili rilevanti in secrets.

I Secrets gestiti automaticamente includono:
- `thoth_env_config`: Il contenuto del tuo file `.env.swarm` (passato come secret).

> [!NOTE]
> **Persistenza della Configurazione**: A differenza dei dati variabili (che risiedono nei volumi condivisi), i Secret e le Config sono memorizzati e replicati dai nodi manager del cluster. Questo permette di ricreare i container senza perdere le impostazioni, poiché Swarm inietta automaticamente i segreti in ogni nuova istanza del servizio.

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

Per semplificare il processo di distribuzione (gestendo automaticamente rete, segreti e configurazioni):

```bash
./docker-swarm-up.sh
```

Per resettare l'ambiente al "Giorno 0" (incluso il reset dello schema DB):
```bash
./clean-docker-swarm.sh
```

### Metodo B: Distribuzione Manuale

Se desideri un controllo manuale completo, ecco i passaggi eseguiti dallo script:

1.  **Inizializza Swarm**:
    ```bash
    docker swarm init
    ```

2.  **Crea Rete**:
    ```bash
    docker network create --driver overlay --attachable thothai-swarm_thoth-network
    ```

3.  **Crea Secrets & Configs**:
    ```bash
    docker secret create thothai-swarm_thoth_env_config .env.docker
    docker config create thothai-swarm_thoth_env_docker .env.docker
    ```

4.  **Distribuisci Stack**:
    ```bash
    docker stack deploy -c docker-stack.yml thothai-swarm
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

## 8. Troubleshooting Comuni

### Errore di Sintassi `SECRET_KEY`
Se ricevi errori bash durante il deploy (es. `syntax error near unexpected token`), verifica che la tua `SECRET_KEY` in `.env.swarm` non contenga caratteri speciali non escapati (come `(`, `)`, `&`).
**Soluzione**: Usa lo script `./generate-keys.sh` per generare chiavi sicure e compatibili con bash.

### Connessione Database Fallita (Locale)
Se i container non riescono a connettersi a un database locale (es. Supabase su Mac) con errore `Connection refused` usando `localhost`:
**Soluzione**: Imposta `DB_HOST=host.docker.internal` in `.env.swarm`. Questo permette ai container di raggiungere i servizi sulla macchina host.

### Errore Auhtenticazione Supabase (Pooler)
Se usi Supabase locale con pooler (es. Supavisor) e ricevi `Tenant or user not found`:
**Soluzione**: Verifica il formato dell'utente. Spesso con il pooler è necessario usare il formato `postgres.<tenant_id>` (es. `postgres.athena`) invece del semplice `postgres`.
