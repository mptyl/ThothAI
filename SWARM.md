# Deploy ThothAI con Docker Swarm (Windows build → Linux server)

Questa guida copre il percorso completo:

1) Windows: aggiornare repo, configurare, buildare le immagini.
2) Windows: push delle immagini sul registry.
3) Linux (server Swarm): deploy dello stack.

## Prerequisiti

- Docker installato su Windows (per build) e su Linux (per Swarm).
- Accesso al registry `registry.uni.com` con credenziali valide.
- File già presenti nel repo: `buildswarm.ps1`, `deployswarm.ps1`, `docker-stack-simple.yml`, `stackswarm.sh`, `.env.docker`, `config.yml.local`.

## Passo 1: Windows – aggiornare e configurare

```powershell
git pull
# aggiorna config.yml.local se necessario
```

## Passo 2: Windows – build immagini

```powershell
.\buildswarm.ps1
# opzionale: senza cache
# .\buildswarm.ps1 -NoCache
```

## Passo 3: Windows – push immagini al registry

```powershell
docker login registry.uni.com

# imposta il tag versione usato in build
$VER="0.1"   # cambia se usi un altro tag
.\deployswarm.ps1 -Version $VER
# opzionale: aggiungi -PushLatest se vuoi pushare anche :latest
```

## Passo 4: Copiare i file sul server Linux

Crea/scegli una cartella sul server (es. `/opt/thoth`) e copia lì:

- `docker-stack-simple.yml`
- `stackswarm.sh`
- `.env.docker`
- `config.yml.local`
- `data_exchange/` (se serve)

## Passo 5: Linux (server Swarm) – deploy

Sul server, dentro la cartella dove hai copiato i file:

```bash
docker login registry.uni.com
chmod +x stackswarm.sh

# variabili di default già nel file; puoi sovrascrivere al volo
export VERSION="0.1"                          # tag pushato
export REGISTRY_URL="registry.uni.com/tylconsulting/thothai"
export FRONTEND_PORT=3040 BACKEND_PORT=8040 SQL_GENERATOR_PORT=8020 WEB_PORT=8040

# se vuoi usare lo stack semplice (env_file .env.docker)
./stackswarm.sh

# se vuoi usare lo stack completo con secrets/config esterni:
# export STACK_FILE="docker-stack.yml"
# ./stackswarm.sh
```

Verifica:

```bash
docker stack services thoth
docker stack ps thoth
```

## Note rapide

- Lo stack “semplice” (`docker-stack-simple.yml`) non richiede secrets/config esterni, ma usa `.env.docker` e `config.yml.local` copiati localmente.
- Per cambiare porte o tag, esporta le variabili prima di lanciare `stackswarm.sh`.
- Assicurati di pushare con lo stesso tag che poi imposti in `VERSION` sul server.

## Volumi e persistenza (Swarm multi-nodo)

Con Docker Swarm su più nodi, la gestione dei volumi è un punto critico: per default **i volumi non “seguono” il container** se un servizio viene riprogrammato su un nodo diverso.

### Tipi di mount nello stack “semplice”

Nel file `docker-stack-simple.yml` sono presenti:

- **Named volumes (driver `local`)**
  - `thoth-backend-db` (SQLite del backend)
  - `qdrant-data` (storage Qdrant)
  - `thoth-shared-data`, `thoth-logs`, `backend-static`, `backend-media`, `frontend-cache`
  - In Swarm, con driver `local`, questi volumi sono **locali al nodo** dove gira il task. Se Swarm sposta il servizio su un altro nodo, verrà usato/creato un volume omonimo **su quel nodo**, che non contiene i dati del nodo precedente.

- **Bind mount (path host `./...`)**
  - `./data_exchange:/app/data_exchange`
  - `./config.yml.local:/app/config.yml.local:ro`
  - `./frontend/public:/app/public:ro`
  - In Swarm, un bind mount funziona solo se **quel path esiste sul nodo** dove viene schedulato il container. Se i file/cartelle non sono presenti su tutti i nodi (o non sono condivisi via NFS), il task può fallire in startup.

### Raccomandazioni per ambienti multi-nodo

- **Vincolare i servizi stateful a un nodo**
  - Per evitare perdita “apparente” dei dati con volumi locali, vincola almeno `backend` e `thoth-qdrant` a un nodo specifico tramite placement constraints (es. label del nodo). In questo modo i loro named volumes restano sempre sullo stesso host.

- **Usare storage condiviso per alta disponibilità**
  - Se vuoi poter rischedulare i servizi stateful su più nodi senza perdere i dati, usa uno storage condiviso (es. NFS/Ceph/Longhorn/Portworx) e configura i volumi (o bind mount verso un mount condiviso) di conseguenza.

- **Gestione `data_exchange/`**
  - Se `data_exchange/` deve essere accessibile da più servizi e/o più nodi, mettilo su storage condiviso (es. NFS) oppure vincola anche i servizi che lo usano allo stesso nodo.

- **Backup**
  - Pianifica backup per:
    - `thoth-backend-db` (SQLite)
    - `qdrant-data`
    - `backend-media` e `thoth-logs` (se ti serve conservarli)
