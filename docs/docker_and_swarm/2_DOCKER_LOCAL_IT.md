# ThothAI - Guida all'Installazione Docker Locale

## 1. Introduzione

Questo documento spiega come installare ed eseguire ThothAI in locale utilizzando Docker Compose. La guida è divisa in due sezioni principali:
*   **Per l'Utilizzatore**: Chi vuole semplicemente scaricare ed eseguire l'applicazione senza modificarne il codice.
*   **Per lo Sviluppatore**: Chi vuole modificare il codice sorgente, ricostruire le immagini e contribuire al progetto.

---

## 2. Prerequisiti Comuni

Indipendentemente dal ruolo, il tuo sistema deve avere:
*   **Docker Desktop** (con Docker Compose V2) installato e avviato.
*   **Git** (per clonare il repository).
*   **Python 3.9+** (richiesto dallo script di installazione per validare la configurazione).
*   **Risorse di sistema**: Almeno 8GB di RAM e 4 CPU consigliati per eseguire l'intero stack (LLM + Vector DB + App).

---

## 3. Punto di Vista dell'Utilizzatore (Consumer)

L'utilizzatore finale ha l'obiettivo di avviare l'applicazione il più velocemente possibile, utilizzando immagini stabili o costruendole automaticamente tramite gli script forniti.

### 3.1 Setup Iniziale

1.  **Clona il Repository**:
    ```bash
    git clone <repository-url> ThothAI
    cd ThothAI
    ```

2.  **Configurazione**:
    Copia il file di template e configuraslo.
    ```bash
    cp config.yml config.yml.local
    ```
    Modifica `config.yml.local` inserendo le tue API Key (OpenAI, Anthropic, Gemini) e le preferenze per il database vettoriale.
    > **Nota**: `config.yml.local` è il tuo file personale e non verrà tracciato da Git.

### 3.2 Installazione e Avvio

ThothAI fornisce uno script `install.sh` (interattivo) che gestisce tutto il processo.

*   **Linux/macOS**:
    ```bash
    ./install.sh
    ```
*   **Windows (PowerShell)**:
    ```powershell
    .\install.ps1
    ```

Lo script eseguirà:
1.  **Stop dei servizi locali**: Arresta eventuali servizi di sviluppo (`docker-compose-local.yml`) per evitare conflitti di porta.
2.  **Validazione Configurazione**: Controlla la presenza di `config.yml.local`.
3.  **Scelta Build/Pull**: Ti chiederà se vuoi scaricare le immagini da Docker Hub (default) o costruirle localmente (utile se hai modificato il codice ma vuoi testare in full-docker).
4.  **Setup Ambiente**: Genera `.env.docker` e crea i volumi necessari (es. `thoth-secrets`).
5.  **Avvio**: Lancia lo stack con `docker compose up -d` (usando `docker-compose-hub.yml` o `docker-compose.yml` a seconda della scelta).

> **Nota per Sviluppatori (Hybrid Mode)**: Se vuoi sviluppare con codice nativo su host (hot-reload) e servizi di supporto su Docker, NON usare `install.sh`. Usa invece `start-all.sh`. Vedi la guida [LOCAL_INSTALLATION_DEV_IT](../thothai_install/LOCAL_INSTALLATION_DEV_IT.md).

### 3.3 Accesso all'Applicazione

Una volta terminato lo script, i servizi sono attivi su:

| Servizio | URL | Descrizione |
|----------|-----|-------------|
| **Frontend** | `http://localhost:3040` | L'interfaccia principale dell'applicazione. |
| **Backend API** | `http://localhost:8040` | API Rest accessibili tramite Proxy. |
| **Admin Panel** | `http://localhost:8040/admin` | Pannello di amministrazione Django. |
| **Qdrant** | `http://localhost:6333/dashboard` | Dashboard del DB vettoriale. |

---

## 4. Punto di Vista dello Sviluppatore (Producer)

Lo sviluppatore deve poter modificare il codice, testare le modifiche rapidamente e preparare le immagini per la distribuzione (Docker Hub).

### 4.1 Workflow di Sviluppo Locale con Docker

Se stai sviluppando una nuova feature e vuoi testarla in un ambiente containerizzato simile alla produzione:

1.  **Applica le modifiche** al codice in `backend/` o `frontend/`.
2.  **Ricostruisci i container** interessati. Non è necessario reinstallare tutto da zero.
    ```bash
    # Ricostruisce e riavvia solo il backend
    docker compose up -d --build backend
    
    # Ricostruisce e riavvia solo il frontend
    docker compose up -d --build frontend
    ```
3.  **Logs**: Monitora i log per debuggare.
    ```bash
    docker compose logs -f backend
    ```

### 4.2 Pulizia e Reset

Durante lo sviluppo potresti aver bisogno di pulire l'ambiente:

*   **Pulizia Cache Build**:
    ```bash
    ./install.sh --clean-cache
    ```
*   **Reset Completo** (Rimuove volumi, immagini e container Thoth):
    ```bash
    ./install.sh --prune-all
    ```
    *Attenzione: Questo cancella anche i dati nel DB locale.*

### 4.3 Pubblicazione su Docker Hub

Quando una feature è stabile e vuoi distribuirla (es. per il deploy su Swarm), devi creare le immagini e pusharle sul Registry.

Prerequisiti:
*   Account su Docker Hub.
*   Login effettuato: `docker login`.

Procedura:
1.  Verifica che il file `swarm_config.env` abbia il tuo `DOCKER_USERNAME` corretto.
2.  Usa lo script di deploy che include la fase di push (oppure pusha manualmente).
    *Vedi `DOCKER_SWARM.md` per i dettagli sul push e deploy remoto.*

Se vuoi pushare manualmente le immagini locali taggate:
```bash
# Esempio manuale
docker tag thoth-backend:latest tuo-user/thoth-backend:latest
docker push tuo-user/thoth-backend:latest
```

---

## 5. Dettagli Tecnici dello Stack

Il file `docker-compose.yml` orchestra i seguenti servizi:

*   **proxy (Nginx)**: Entrypoint unico. Gestisce routing verso frontend, backend e servizi ausiliari. Porta esposta: `8040`.
*   **frontend (Next.js)**: Applicazione React. Porta: `3040`.
*   **backend (Django)**: Core logic. Non esposto direttamente all'host in produzione, ma raggiungibile via proxy.
*   **sql-generator (FastAPI)**: Microservizio per generazione SQL con AI.
*   **thoth-qdrant**: Database vettoriale persistente.
*   **mermaid-service**: Rendering grafici.

### Gestione Dati e Volumi
I dati persistenti risiedono nei volumi Docker:
*   `thoth-backend-db`: Database SQLite (se usato).
*   `thoth-qdrant-data`: Vettori e collezioni Qdrant.
*   `thoth-secrets`: Chiavi e file sensibili generati all'installazione.
*   `thoth-shared-data`: Dati condivisi tra i container.
