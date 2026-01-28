# Guida all'Installazione Base Docker Swarm

Questa guida descrive come installare **ThothAI** in un cluster **Docker Swarm** utilizzando esclusivamente i comandi nativi di Docker e il file `docker-stack.yml`.

## 1. Preparazione dell'Ambiente di Installazione

Prima di eseguire il deploy, crea una directory dedicata sul tuo nodo manager e copia i seguenti file necessari dal repository:

### Checklist dei File Necessari
Assicurati di avere i seguenti file nella directory di lavoro:
- [ ] `docker-stack.yml`: Definizione dell'infrastruttura Swarm.
- [ ] `.env.swarm.template`: Template per le variabili d'ambiente (da copiare in `.env.swarm`).
- [ ] `swarm_config.env.template`: Template per la configurazione del deployment (porte, registry, ecc.).
- [ ] `.thothai-data.yml.template`: Template per la configurazione di `thothai-data-cli` (da copiare in `.thothai-data.yml`).
- [ ] `setup_csv/`: Directory contenente i dati di inizializzazione base.

## 2. Prerequisiti Infrastrutturali

Assicurarsi di avere:
- Un cluster **Docker Swarm** già inizializzato (`docker swarm init`).
- Un database **PostgreSQL esterno** accessibile dai nodi dello swarm (obbligatorio per la persistenza in Swarm).
- **Storage condiviso** (es. NFS) montato su tutti i nodi nel percorso specificato come `THOTH_DATA_PATH`.
- Le immagini di ThothAI caricate su un registry accessibile o presenti localmente sui nodi.

## 3. Preparazione della Configurazione

1.  Copia i template disponibili:
    ```bash
    cp .env.swarm.template .env.swarm
    cp swarm_config.env.template swarm_config.env
    cp .thothai-data.yml.template .thothai-data.yml
    ```
2.  Modifica `.env.swarm` inserendo le tue chiavi API (OpenAI, Anthropic, ecc.) e le credenziali del database PostgreSQL.
3.  Modifica `swarm_config.env` per configurare le porte dei servizi, il nome dello stack e il registry Docker (se necessario). Questo file viene utilizzato dagli script di deploy e per la gestione delle porte esposte.
4.  Assicurati che `THOTH_DATA_PATH` punti correttamente al tuo storage condiviso.

## 4. Gestione dell'Infrastruttura Swarm

### A. Creazione della Rete Overlay
```bash
docker network create --driver overlay --attachable thothai-swarm_thoth-network
```

### B. Creazione di Secret e Config
```bash
# Crea il secret per la configurazione ambiente
docker secret create thothai-swarm_thoth_env_config .env.swarm

# Crea la config per il file .env.swarm da iniettare nel container
docker config create thothai-swarm_thoth_env_docker .env.swarm
```

## 5. Distribuzione dello Stack

```bash
# Esporta le variabili richieste
export THOTH_DATA_PATH=/mnt/nfs/thothai
export IMAGE_VERSION=latest

# Esegui il deploy
docker stack deploy -c docker-stack.yml thothai-swarm
```

## 6. Inizializzazione dei Dati (`setup_csv`)

> [!IMPORTANT]
> **Nessun dato predefinito nell'immagine**
> Le immagini Docker di ThothAI **non includono dati predefiniti**. Al primo avvio, il database risulterà vuoto.

### Configurazione in Docker Swarm
È necessario mappare la directory `setup_csv` in modo che sia accessibile al servizio backend:

1.  Copia la directory `setup_csv` sullo storage condiviso: `${THOTH_DATA_PATH}/setup_csv`.
2.  Il file `docker-stack.yml` deve includere il seguente volume nel servizio `backend`:
    ```yaml
    volumes:
      - ${THOTH_DATA_PATH}/setup_csv:/setup_csv
    ```

## 7. Gestione Scambio Dati (`data-exchange`)

La directory `data-exchange` gestisce le esportazioni e importazioni CSV tra diversi ambienti.

1.  **Percorso Host**: `${THOTH_DATA_PATH}/data_exchange` sullo storage condiviso.
2.  **Utilizzo**: I file esportati dall'interfaccia appariranno qui automaticamente.

## 8. Utilizzo di `thothai-data-cli`

Il tool `thothai-data-cli` è il modo raccomandato per gestire i dati nello stack Swarm.

### Installazione
Puoi installare la CLI direttamente da PyPI:
```bash
uv pip install thothai-data-cli
```
*Si raccomanda l'uso di un virtual environment.*

### Configurazione iniziale
Al primo avvio, esegui il comando per generare interattivamente la configurazione:
```bash
thothai-data config show
```
Durante la configurazione:
- Scegli `swarm` come modalità.
- Inserisci il nome dello stack (es. `thothai-swarm`).
- Scegli la connessione `local` se esegui il comando dal nodo manager, o `ssh` per gestire lo swarm remotamente.

### Comandi principali
- **Test connessione**: `thothai-data config test`
- **Lista file**: `thothai-data csv list`
- **Upload file**: `thothai-data csv upload mio_file.csv`
- **Download esportazioni**: `thothai-data csv download nome_file.csv`

---

## 9. Comandi Utili di Gestione

### Verificare lo Stato dei Servizi
```bash
docker stack services thothai-swarm
```

### Rimozione dello Stack
```bash
docker stack rm thothai-swarm
docker secret rm thothai-swarm_thoth_env_config
docker config rm thothai-swarm_thoth_env_docker
```
