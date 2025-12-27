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

L'utilizzatore finale ha l'obiettivo di avviare l'applicazione utilizzando le immagini ufficiali. Per informazioni su come sono costruite le immagini e cosa contengono, consulta la [Guida all'Architettura delle Immagini](./5_DOCKER_BUILD_IMAGES.md).

### 3.1 Setup Iniziale

1.  **Clona il Repository**:
    ```bash
    git clone <repository-url> ThothAI
    cd ThothAI
    ```

2.  **Configurazione**:
    Copia il file di template e configuralo.
    ```bash
    cp config.yml config.yml.local
    ```
    Modifica `config.yml.local` inserendo le tue API Key (OpenAI, Anthropic, Gemini) e le preferenze per il database vettoriale.

### 3.2 Installazione e Avvio

ThothAI fornisce uno script `install.sh` che gestisce tutto il processo di configurazione a **runtime**.

*   **Linux/macOS**:
    ```bash
    ./install.sh
    ```
*   **Windows (PowerShell)**:
    ```powershell
    .\install.ps1
    ```

Lo script eseguirà le seguenti azioni di configurazione e preparazione:
1.  **Validazione**: Controlla la presenza di `config.yml.local`.
2.  **Generazione Ambiente**: Esegue `installer.py` per generare il file `.env.docker` partendo da `config.yml.local`. Questo file contiene tutte le variabili che istruiranno i container a runtime (es. porte, database abilitati via `ENABLED_DATABASES`, etc.).
3.  **Setup Volumi**: Crea i volumi Docker persistenti e i segreti necessari.
4.  **Avvio**: Lancia lo stack con `docker compose up -d` utilizzando le immagini pre-build.

### 3.3 Cosa succede al primo avvio?

Al primo avvio dei container, vengono eseguiti automaticamente degli script di bootstrap:

- **Inizializzazione Dati (`init-shared-data.sh`)**: Se i volumi sono nuovi, i database demo inclusi nell'immagine vengono copiati nel volume persistente `thoth-shared-data`.
- **Inizializzazione Applicazione (`start.sh`)**: Il backend rileva l'assenza di dati precedenti e:
    - Crea gli utenti `admin` e `demo` con le password definite in `config.yml.local`.
    - Inizializza il workspace demo.
    - Se le API Key sono presenti, avvia l'analisi AI (scope, documentazione) e il caricamento nel DB Vettoriale.

---

## 4. Punto di Vista dello Sviluppatore (Producer)

Lo sviluppatore deve poter gestire il ciclo di vita dei container e i dati ad essi associati. Per i dettagli tecnici sulla build delle immagini, fare riferimento al documento [5_DOCKER_BUILD_IMAGES.md](./5_DOCKER_BUILD_IMAGES.md).

### 4.1 Workflow di Sviluppo e Gestione Dati

Per gestire container, volumi e scambio dati, fare riferimento alla guida [6_DOCKER_MANAGEMENT.md](./6_DOCKER_MANAGEMENT.md).

### 4.2 Pulizia e Reset

In caso di necessità di reset completo:
*   **Reset Completo** (Rimuove volumi e container):
    ```bash
    ./install.sh --prune-all
    ```
    *Attenzione: Questo cancella tutti i dati salvati nei volumi persistenti.*

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
