# Manuale Utente ThothAI - Installazione Semplificata (CLI)

Guida completa all'installazione e all'uso di ThothAI utilizzando la CLI ufficiale `thothai`. Questa modalità permette di gestire l'intero ciclo di vita dell'applicazione senza la necessità di clonare il repository GitHub.

## 1. Prerequisiti

Assicurati di avere installato i seguenti componenti sul tuo sistema:

| Requisito | Versione | Link / Comando Installazione |
|-----------|----------|------------------------------|
| **Python** | ≥ 3.9 | [python.org](https://www.python.org/) |
| **uv** | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Docker** | ≥ 20.0 | [docs.docker.com](https://docs.docker.com/get-docker/) |

### Supporto Docker Swarm
Docker Swarm è consigliato per deploy su server remoti o per alta disponibilità. È possibile inizializzarlo con il comando:
```bash
docker swarm init
```

---

## 2. Procedura di Installazione

### Step 1: Creazione dello spazio di lavoro
Crea una cartella dedicata al progetto ed entra al suo interno:
```bash
mkdir my-thothai && cd my-thothai
```

### Step 2: Configurazione dell'ambiente virtuale
Utilizza `uv` per creare un ambiente isolato:
```bash
uv venv

# Attivazione:
source .venv/bin/activate  # Linux / macOS
.\.venv\Scripts\activate   # Windows (PowerShell)
```

### Step 3: Installazione della CLI
Installa il pacchetto `thothai-cli`:
```bash
uv pip install thothai-cli
```

### Step 4: Inizializzazione del progetto
Prepara i file di configurazione necessari. Puoi scegliere tra la modalità standard (Compose) o Swarm:

```bash
# Modalità Docker Compose (Default)
uv run thothai init

# Modalità Docker Swarm
uv run thothai init --mode swarm
```

Questo comando crea i seguenti file:
- `config.yml.local`: Configurazione applicativa (API key, database, admin).
- `docker-compose.yml` (o `docker-stack.yml`): Orchestrazione dei servizi.
- `swarm_config.env` (**Solo Swarm**): Configurazione porte e infrastruttura Swarm.
- `data_exchange/`: Directory per l'importazione/esportazione di file CSV.

---

## 3. Configurazione

### Configurazione Applicativa (`config.yml.local`)
Questo file contiene i parametri vitali di ThothAI. Segui attentamente queste istruzioni:

#### Provider AI e Modelli
1.  **AI Providers**: Abilita almeno un provider (es. `openai`, `gemini`) e inserisci la relativa `api_key`.
2.  **Embedding**: È fondamentale decommentare almeno un provider di embedding e indicarne l'API key.
    > [!TIP]
    > Se utilizzi lo stesso provider per LLM ed Embedding (es. entrambi OpenAI), puoi usare la stessa chiave in entrambe le sezioni.
3.  **backend_ai_model**: Indica il provider e il modello da utilizzare come motore principale (es. `openai:gpt-4o`). Il modello scelto **deve** appartenere a un provider attivato e configurato con API key nella sezione `ai_providers`.

#### Logging con Logfire (Opzionale)
Per un monitoraggio avanzato, puoi inserire un `logfire_token` (totalmente opzionale).
- **Cos'è Logfire**: Uno strumento moderno di osservabilità e debugging per applicazioni AI.
- **Come lo usa ThothAI**: Permette di tracciare le chiamate agli agenti, le prestazioni delle query SQL e facilitare il debug. Se non configurato, ThothAI funzionerà normalmente senza inviare telemetria.

#### Altri Parametri
Tutti gli altri parametri possono essere lasciati ai valori di default. Tuttavia:
- **Verifica le Porte**: Assicurati che le porte configurate (es. `8040`, `3040`) non siano già in uso da altre applicazioni sul tuo sistema.

```yaml
ai_providers:
  openai:
    enabled: true
    api_key: "tua-chiave-openai"
  gemini:
    enabled: true
    api_key: "tua-chiave-gemini"

embedding:
  provider: "openai"
  model: "text-embedding-3-small"
  api_key: "tua-chiave-openai" # Può essere la stessa di sopra

backend_ai_model: "openai:gpt-4o"

logfire_token: "tuo-token-logfire" # Opzionale (consigliato per monitoraggio)

admin:
  username: "admin"
  password: "una-password-sicura" # Minimo 8 caratteri
```

### Configurazione Infrastruttura Swarm (`swarm_config.env`)
Se utilizzi la modalità Swarm, puoi personalizzare le porte esposte:

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `WEB_PORT` | `7010` | Gateway Principale (API, Admin, Proxy) |
| `FRONTEND_PORT` | `7001` | Interfaccia Utente |
| `BACKEND_PORT` | `7002` | Backend Django |

---

## 4. Avvio di ThothAI

Una volta completata la configurazione, puoi avviare i servizi. La CLI rileva automaticamente la modalità (Compose o Swarm) in base all'inizializzazione.

### Installazione Locale
```bash
uv run thothai up
```

### Installazione Remota (via SSH)
È possibile deployare su un server remoto direttamente dalla macchina locale:
```bash
# Per Docker Compose remoto
uv run thothai up --server ssh://utente@indirizzo-ip

# Per Docker Swarm remoto
uv run thothai swarm deploy --server ssh://utente@indirizzo-ip
```

---

## 5. Accesso all'Applicazione

Al termine dell'avvio, l'applicazione sarà raggiungibile ai seguenti indirizzi (sostituire `localhost` con l'IP del server in caso di deploy remoto):

- **Interfaccia Utente (Frontend)**: `http://localhost:3040` (o `FRONTEND_PORT` configurata)
- **Pannello di Controllo (Admin)**: `http://localhost:8040/admin` (o `WEB_PORT` configurata)

**Credenziali**: Usa lo username e la password definiti in `config.yml.local`.

---

## 6. Comandi Disponibili

| Comando | Descrizione |
|---------|-------------|
| `thothai init` | Inizializza il progetto (usa `--mode swarm` per Swarm) |
| `thothai up` | Avvia i container (supporta `--server` per deploy remoto) |
| `thothai down` | Ferma e rimuove i container/stack |
| `thothai status` | Mostra lo stato dei servizi |
| `thothai logs` | Visualizza i log (usa `-f` per lo streaming) |
| `thothai update` | Aggiorna le immagini all'ultima versione disponibile |
| `thothai config validate` | Verifica la correttezza di `config.yml.local` |
| `thothai config test` | Testa la connessione con Docker |

### Comandi Specifici Swarm
| Comando | Descrizione |
|---------|-------------|
| `thothai swarm deploy` | Deploy dello stack su Swarm |
| `thothai swarm status` | Stato dei servizi nello stack Swarm |
| `thothai swarm update` | Rolling update dei servizi Swarm |
| `thothai swarm rollback` | Ripristina la versione precedente dello stack |

---

## 7. Troubleshooting e Best Practices

- **File mancante `config.yml.local`**: Esegui `uv run thothai init` per generarlo.
- **Docker non attivo**: Verifica con `docker info` e testa con `uv run thothai config test`.
- **Porta già in uso**: Modifica le porte in `config.yml.local` (per Compose) o `swarm_config.env` (per Swarm) e riavvia.
- **Sicurezza**: Non includere mai `config.yml.local`, `.env.docker` o `swarm_config.env` nel controllo di versione (Git).
- **Aggiornamenti**: Esegui regolarmente `uv run thothai update` per ottenere le ultime patch di sicurezza e funzionalità.
