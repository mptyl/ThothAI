# Analisi Ipotesi Swarm Production (NFS + Bind Mounts)

Questo documento valuta l'ipotesi descritta in `plans/swarm_production_hypothesis` rispetto all'attuale configurazione architetturale di ThothAI.

## 1. Stato Attuale (`docker-stack.yml` attuale)

L'attuale configurazione di `docker-stack.yml` è progettata per un **Single-Node Swarm** o un ambiente in cui la persistenza è locale al nodo.

*   **Gestione Volumi**: Vengono utilizzati **Named Volumes** con driver predefinito (implicitamente `local`).
    ```yaml
    volumes:
      backend-static:
        driver: local
      # ... altri volumi
    ```
*   **Comportamento in Multi-Nodo**: Se questo stack viene deployato su più nodi, ogni nodo creerà i propri volumi locali.
    *   *Esempio*: Se `backend` gira sul Nodo A e scrive su `backend-media`, e poi viene riavviato sul Nodo B, non troverà i file caricati precedentemente, perché userà il volume `backend-media` locale del Nodo B (che è vuoto o diverso).
*   **Services Configuration**: I servizi riferiscono i volumi per nome (es. `thoth-backend-db:/app/backend_db`).

## 2. Analisi dell'Ipotesi (NFS + Bind Mounts)

L'ipotesi propone di bypassare il meccanismo dei Docker Volumes gestiti per utilizzare **Bind Mounts** diretti a path del file system dell'host, che a loro volta sono mount point NFS.

### Principali Differenze

| Caratteristica | Architettura Attuale | Ipotesi NFS Bind Mounts |
| :--- | :--- | :--- |
| **Tipo di Storage** | Docker Named Volumes (`driver: local`) | Host Filesystem (NFS Mount) |
| **Persistenza Multi-Instance** | Isolato per Nodo (Dati non condivisi) | Condiviso Globalmente (Dati accessibili da tutti i nodi) |
| **Definizione in Stack** | `source: <volume-name>` | `type: bind`, `source: /path/to/nfs/...` |
| **Dipendenza Host** | Nessuna pre-configurazione richiesta | Richiede mount NFS attivo su ogni nodo |
| **Portabilità** | Alta (funziona ovunque ci sia Docker) | Media (richiede infrastruttura NFS sottostante) |

## 3. Adeguamenti Necessari

Per passare dall'architettura attuale all'ipotesi proposta sono necessari i seguenti interventi:

### A. Modifiche Infrastrutturali (Prerequisiti)
Queste azioni sono esterne a ThothAI ma necessarie per il funzionamento:
1.  **Setup Server NFS**: Configurazione di un server storage centrale.
2.  **Configurazione Nodi Swarm**: Su *ogni* nodo del cluster (Manager e Worker) deve essere montata la share NFS allo stesso percorso (es. `/mnt/nfs/thothai`).
3.  **Gestione Utenti (UID/GID)**: Allineamento degli UID dell'utente Docker/Container con quelli del server NFS per evitare errori di `Permission Denied`.

### B. Modifiche a `docker-stack.yml`
È necessario riscrivere le definizioni dei volumi per i servizi stateful (Backend, Frontend, SQL Generator, Qdrant, Proxy).

**Approccio Consigliato**: Mantenere la flessibilità usando variabili d'ambiente per supportare sia volumi locali che path NFS.

Esempio di trasformazione necessaria per un servizio:

**Attuale:**
```yaml
  backend:
    volumes:
      - thoth-backend-db:/app/backend_db
```

**Necessario (secondo ipotesi):**
```yaml
  backend:
    volumes:
      - type: bind
        source: ${THOTH_DATA_PATH:-/mnt/nfs/thothai}/postgres_data  # O sqlite db path
        target: /app/backend_db
```

### C. Volumi Coinvolti
Ecco la mappatura dei volumi attuali che dovranno essere convertiti in path NFS:

1.  `thoth-backend-db` -> `${THOTH_DATA_PATH}/backend_db` (SQLite richiede file locking, **attenzione**: SQLite su NFS è sconsigliato/rischioso per lock issues. Si raccomanda PostgreSQL per produzione Swarm).
2.  `thoth-shared-data` -> `${THOTH_DATA_PATH}/shared`
3.  `thoth-logs` -> `${THOTH_DATA_PATH}/logs`
4.  `backend-static` -> `${THOTH_DATA_PATH}/static`
5.  `backend-media` -> `${THOTH_DATA_PATH}/media`
6.  `thoth-data-exchange` -> `${THOTH_DATA_PATH}/data_exchange`
7.  `thoth-secrets` -> `${THOTH_DATA_PATH}/secrets` (O gestione tramite Docker Configs/Secrets nativi, ma l'ipotesi suggerisce bind mount per semplicità).
8.  `qdrant-data` -> `${THOTH_DATA_PATH}/qdrant_data` (Performance network da valutare).

## 4. Analisi Rischi e Considerazioni

1.  **SQLite su NFS**: L'architettura attuale usa SQLite (`db.sqlite3` in `DB_NAME_DOCKER=/app/backend_db/db.sqlite3`).
    *   ⚠️ **Rischio Critico**: SQLite su NFS ha noti problemi di file locking che possono corrompere il database o causare errori "database is locked".
    *   **Soluzione Necessaria**: Se si passa a Swarm multi-nodo, è **imperativo** migrare da SQLite a PostgreSQL (containerizzato o esterno).
2.  **Network Latency**: Qdrant e Database applicativo potrebbero soffrire latenza se lo storage è remoto.
3.  **Single Point of Failure**: Se il server NFS cade, tutto il cluster si ferma.

## Conclusione

L'ipotesi è **valida e necessaria** per un vero cluster Swarm multi-nodo, ma l'architettura attuale richiede prima:
1.  **Migrazione DB**: Abbandono di SQLite a favore di PostgreSQL (o altro DB client-server).
2.  **Refactoring Stack**: Modifica massiva di `docker-stack.yml` per usare `type: bind` parameterizzati.
