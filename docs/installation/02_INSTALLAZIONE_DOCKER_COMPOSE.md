# Guida all'Installazione Docker Compose

Questa guida spiega come distribuire ThothAI utilizzando **Docker Compose**. Questo è il metodo standard per eseguire l'intero stack in un ambiente containerizzato, adatto sia per lo sviluppo che per semplici configurazioni di server di produzione.

## Prerequisiti

- **Docker Desktop** (Mac/Windows) o **Docker Engine** (Linux) installato.
- **Docker Compose V2** abilitato.
- **Git** per clonare la repository.

## 1. Configurazione Iniziale

### Clonare e Preparare
```bash
git clone https://github.com/mptyl/ThothAI.git
cd ThothAI
```

### Configurazione
Tutto è controllato dal file `.env.docker`. Questo file è **ignorato da git** (gitignored) per proteggere i tuoi segreti.

1.  **Creare la Configurazione**:
    ```bash
    cp .env.compose.template .env.docker
    ```

2.  **Modificare le Impostazioni**:
    Apri `.env.docker` e configura:
    - **Chiavi API**: `OPENAI_API_KEY`, ecc.
    - **Modalità di Distribuzione**: Assicurati che `DEPLOYMENT_MODE=compose` (default).
    - **Modalità di Build**:
        - `BUILD_MODE=hub` (Default): Scarica immagini pre-costruite da Docker Hub. Più veloce e stabile.
        - `BUILD_MODE=build`: Costruisce le immagini localmente dal tuo codice sorgente. Usalo se hai modificato il codice.

3.  **Database Esterno Opzionale**:
    Di default viene usato un container PostgreSQL interno (`POSTGRES_INTERNAL=true`).
    Per usare un database esterno (es. Postgres sulla macchina host o Cloud RDS):
    - Imposta `POSTGRES_INTERNAL=false` in `.env.docker`.
    - Configura `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`.
    - (Opzionale) Imposta `AUTO_CREATE_SCHEMA=true` se vuoi che ThothAI crei lo schema automaticamente.

## 2. Distribuzione

Puoi avviare il sistema utilizzando i nostri script di supporto, la CLI o comandi manuali.

### Opzione A: Script di Supporto (Raccomandato)

Forniamo uno script robusto che gestisce automaticamente setup, creazione rete e pulizia.

```bash
./docker-up.sh
```

Per arrestare:
```bash
./docker-down.sh
```

### Opzione B: ThothAI CLI

Se hai inizializzato il progetto con `thothai init`, puoi usare la CLI:

```bash
uv run thothai up
uv run thothai down
```

### Opzione C: Comandi Docker Manuali

Se preferisci gli strumenti Docker standard:

```bash
# Avvia servizi
docker compose up -d

# Visualizza log
docker compose logs -f

# Arresta servizi
docker compose down
```

## 3. Accedere all'Applicazione

Una volta avviato (dai un minuto per l'inizializzazione), accedi ai servizi:

- **Interfaccia Principale**: [http://localhost:8040](http://localhost:8040) (Servita via Nginx Proxy)
- **Frontend Diretto**: [http://localhost:3040](http://localhost:3040)
- **Backend Admin**: [http://localhost:8040/admin](http://localhost:8040/admin)

## 4. Persistenza Volumi e Dati

Docker Compose utilizza volumi con nome per persistere i dati anche quando i container vengono arrestati.

- **`thoth-backend-db`**: Memorizza il database SQLite (se usato) o dati DB persistenti.
- **`qdrant-data`**: Memorizza gli embedding vettoriali.
- **`thoth-data-exchange`**: Un volume condiviso per scambiare file tra i servizi.

### Resettare i Dati
Per cancellare completamente tutti i dati e ricominciare da zero (utile per i test):

```bash
docker compose down -v
```
*Il flag `-v` rimuove i volumi con nome.*

## 5. Risoluzione Problemi

### "Bind for 0.0.0.0:8040 failed: port is already allocated"
Significa che un altro servizio (probabilmente un'istanza locale di ThothAI) sta usando la porta.
**Soluzione**: Ferma le altre istanze o cambia `WEB_PORT` in `.env.docker`.

### "Connection refused" tra container
Assicurati che tutti i servizi siano in esecuzione:
```bash
docker compose ps
```
Se un servizio è `Exited`, controlla i suoi log:
```bash
docker compose logs backend
```
