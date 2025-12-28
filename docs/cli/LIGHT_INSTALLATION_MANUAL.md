# ThothAI - Manuale d'Installazione Semplificata (Lightweight)

Questa guida spiega come installare ThothAI nella maniera più semplice e veloce possibile utilizzando la CLI ufficiale `thothai`. Questa modalità **non richiede il clone del repository GitHub** e permette di gestire l'intero ciclo di vita dell'applicazione tramite pochi comandi.

## 1. Prerequisiti

Prima di iniziare, assicurati di avere installato sul tuo sistema:

*   **Docker & Docker Compose**: Fondamentali per far girare i container.
*   **Python (>=3.9)**: Necessario per eseguire la CLI.
*   **uv**: Il gestore di pacchetti Python raccomandato per velocità e consistenza.

> **Installazione rapida di `uv`:**
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

---

## 2. Procedura di Installazione

### Step 1: Creazione dello spazio di lavoro
Crea una cartella dedicata al tuo progetto ThothAI ed entra al suo interno:

```bash
mkdir my-thothai && cd my-thothai
```

### Step 2: Configurazione dell'ambiente virtuale
Crea e attiva un ambiente isolato per la CLI:

```bash
uv venv
source .venv/bin/activate  # Per Linux/macOS
# .venv\Scripts\activate   # Per Windows (PowerShell)
```

### Step 3: Installazione della CLI
Installa il pacchetto `thothai-cli` direttamente tramite `uv`:

```bash
uv pip install thothai-cli
```

### Step 4: Inizializzazione del progetto
Prepara i file di configurazione necessari nella cartella corrente:

```bash
uv run thothai init
```

Questo comando creerà i file template essenziali:
*   `config.yml.local`: Il file principale per la tua configurazione.
*   `docker-compose.yml`: Per l'orchestrazione dei container.
*   `data_exchange/`: Cartella per l'interscambio di dati.

---

## 3. Configurazione

Apri il file `config.yml.local` con il tuo editor preferito (es. VS Code, Notepad, nano) e inserisci le tue chiavi API:

```yaml
ai_providers:
  openai:
    enabled: true
    api_key: "tua-chiave-openai"
  # Abilita altri provider se necessario (gemini, anthropic, etc.)

admin:
  username: "admin"
  password: "una-password-sicura" # Minimo 8 caratteri
```

---

## 4. Avvio di ThothAI

Una volta salvata la configurazione, avvia l'applicazione con un singolo comando:

```bash
uv run thothai up
```

La CLI si occuperà di:
1. Validare la tua configurazione.
2. Scaricare le immagini ufficiali da Docker Hub.
3. Creare i volumi e la rete Docker.
4. Avviare tutti i servizi (Backend, Frontend, SQL Generator, Qdrant).

---

## 5. Accesso all'applicazione

Al termine dell'operazione, la CLI mostrerà i link per accedere:

*   **Pannello di Controllo (Admin)**: [http://localhost:8040/admin](http://localhost:8040/admin)
*   **Interfaccia Utente (Frontend)**: [http://localhost:3040](http://localhost:3040)

Accedi con le credenziali configurate nel file `config.yml.local`.

---

## 6. Comandi di Gestione Base

Ecco i comandi principali per gestire la tua istanza ThothAI:

*   **Vedere lo stato**: `uv run thothai status`
*   **Vedere i log**: `uv run thothai logs -f` (Ctrl+C per uscire)
*   **Aggiornare ThothAI**: `uv run thothai update` (scarica le ultime versioni e riavvia)
*   **Spegnere l'applicazione**: `uv run thothai down`

---

## 7. Installazione su Docker Remoto

Se desideri installare ThothAI su un server remoto tramite SSH, inizializza il progetto in modalità Swarm:

```bash
uv run thothai init --mode swarm
```

Configura il file `swarm_config.env` con i dettagli del tuo server e usa:

```bash
uv run thothai swarm deploy --server ssh://utente@indirizzo-ip
```
