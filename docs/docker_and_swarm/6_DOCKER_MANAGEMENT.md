# ThothAI - Guida alla Gestione Docker e Swarm

Questo documento fornisce le istruzioni operative per gestire uno stack ThothAI attivo, gestire i dati e aggiungere nuove risorse.

## 1. Gestione Operativa

### 1.1 In Modalità Docker Compose (Locale)
*   **Vedere lo stato**: `docker compose ps`
*   **Vedere i log**: `docker compose logs -f [service_name]` (es. `backend`)
*   **Riavviare un servizio**: `docker compose restart [service_name]`
*   **Spegnere tutto**: `docker compose down`

### 1.2 In Modalità Docker Swarm
*   **Vedere i servizi dello stack**: `docker stack services thothai-swarm`
*   **Vedere i singoli task (container)**: `docker stack ps thothai-swarm`
*   **Vedere i log di un servizio**: `docker service logs -f thothai-swarm_backend`
*   **Aggiornamento forzato**: `docker service update --force thothai-swarm_backend`
*   **Rimuovere lo stack**: `docker stack rm thothai-swarm`

---

## 2. Data Exchange (Import/Export CSV)

ThothAI permette di esportare i risultati delle elaborazioni o importare configurazioni tramite file CSV.

### 2.1 Utilizzo del CLI di Scambio Dati
Il comando principale è `data-exchange-cli.py`, che risiede nel backend. Per utilizzarlo sotto Docker:

```bash
# Eseguire il comando all'interno del container backend
docker exec -it $(docker ps -q -f name=backend) /app/.venv/bin/python data-exchange-cli.py --help
```

### 2.2 Volumi Coinvolti
I file di scambio si trovano nei seguenti volumi:
*   `thoth-data-exchange`: Destinazione per export massivi e documentazione generata.
*   `thoth-shared-data`: Contiene i database sorgente (SQLite).

---

## 3. Caricamento di un Nuovo Database (BIRD)

Per aggiungere un nuovo database (es. scaricato dal benchmark BIRD) in modo che sia visibile a ThothAI "a fianco" del `california_schools` predefinito, segui questa procedura.

### 3.1 Struttura del Volume
Tutti i database devono trovarsi nel volume `thoth-shared-data`, sotto la directory `/app/data/dev_databases/`.

### 3.2 Procedura di Caricamento
Supponiamo di avere un nuovo database chiamato `financial_data`.

1.  **Individua il volume**: Il volume è solitamente gestito dal driver `local` di Docker.
2.  **Copia i file**: Il modo più semplice per caricare i dati è usare un container temporaneo o `docker cp`.
    ```bash
    # Crea la directory di destinazione nel container backend attivo
    docker exec $(docker ps -q -f name=backend) mkdir -p /app/data/dev_databases/financial_data/database_description

    # Copia il file SQLite
    docker cp ./financial_data.sqlite $(docker ps -q -f name=backend):/app/data/dev_databases/financial_data/

    # Copia i CSV di descrizione (se presenti)
    docker cp ./description/. $(docker ps -q -f name=backend):/app/data/dev_databases/financial_data/database_description/
    ```

3.  **Verifica**:
    Assicurati che la struttura sia la seguente:
    ```
    /app/data/dev_databases/
    ├── california_schools/
    │   └── california_schools.sqlite
    └── financial_data/
        ├── financial_data.sqlite
        └── database_description/
            ├── table1.csv
            └── table2.csv
    ```

### 3.3 Attivazione
Una volta caricati i file nel volume, il database è fisicamente presente. Per renderlo utilizzabile nell'interfaccia di ThothAI:
1.  Accedi al **Pannello Admin** (`/admin`).
2.  Aggiungi un nuovo oggetto **Workspace** (o usa quello esistente).
3.  Configura o associa il nuovo database SQLite puntando al path relativo nel volume.

---

## 4. Troubleshooting dei Volumi
Se i dati non appaiono, verifica i permessi e la corretta mappatura del volume:
```bash
docker inspect [container_id] --format '{{ json .Mounts }}'
```
Assicurati che `thoth-shared-data` sia montato correttamente su `/app/data`.
