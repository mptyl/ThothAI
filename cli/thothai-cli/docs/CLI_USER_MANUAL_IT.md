# Manuale Utente ThothAI - Installazione Semplificata (CLI)

Guida completa all'installazione e all'uso di ThothAI utilizzando la CLI ufficiale `thothai`. Questa modalità permette di gestire l'intero ciclo di vita dell'applicazione senza la necessità di clonare il repository GitHub.

## 1. Prerequisiti

Assicurati di avere installato i seguenti componenti sul tuo sistema:

| Requisito | Versione | Link / Comando Installazione |
|-----------|----------|------------------------------|
| **Python** | ≥ 3.9 | [python.org](https://www.python.org/) |
| **uv** | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Docker** | ≥ 20.0 | [docs.docker.com](https://docs.docker.com/get-docker/) |

> [!NOTE]
> **Compatibilità**: Le immagini Docker di ThothAI sono multi-piattaforma. Funzionano nativamente sia su sistemi **Windows** (AMD64) tramite WSL2, sia su **macOS** (Intel o Apple Silicon), sia su server **Linux**.

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
3.  **backend_ai_model**: Indica il provider e il modello da utilizzare come motore principale (es. `openai:gpt-4o`).
    - Il modello scelto **deve** appartenere a un provider attivato. Se il provider non è stato configurato nella sezione `ai_providers`, è necessario indicare qui anche l'API Key nel formato `provider:modello:api_key`.
    - **Utilizzo Importante**: Questo modello viene utilizzato durante la prima installazione per generare automaticamente i dati e i metadati relativi al database `california_schools`, che funge da database di test iniziale. Assicurati che il modello scelto sia performante (es. GPT-4o, Claude 3.5 Sonnet o Gemini 1.5 Pro) per garantire una corretta inizializzazione del contesto.

#### Logging con Logfire (Opzionale)
Per un monitoraggio avanzato, puoi inserire un `logfire_token` (totalmente opzionale).
- **Cos'è Logfire**: Uno strumento moderno di osservabilità e debugging per applicazioni AI.
- **Come lo usa ThothAI**: Permette di tracciare le chiamate agli agenti, le prestazioni delle query SQL e facilitare il debug. Se non configurato, ThothAI funzionerà normalmente senza inviare telemetria.

#### Altri Parametri
Tutti gli altri parametri possono essere lasciati ai valori di default. Tuttavia:
- **Verifica le Porte**: Assicurati che le porte configurate (es. `8040`, `3040`) non siano già in uso da altre applicazioni sul tuo sistema.
- **Server Name**: Il parametro `server_name` (opzionale) permette di definire l'hostname pubblico. La CLI lo userà per configurare Nginx e mostrare gli URL di accesso corretti.

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

backend_ai_model:
  ai_provider: "openrouter"   # One of: openai, anthropic, gemini, mistral, deepseek, openrouter, ollama, lm_studio, groq
  ai_model: "mistralai/mistral-large-2512"  # Model identifier for the chosen provider

logfire_token: "tuo-token-logfire" # Opzionale (consigliato per monitoraggio)

admin:
  username: "admin"
  password: "una-password-sicura" # Minimo 8 caratteri
```

### Configurazione Infrastruttura Swarm (`swarm_config.env`)
Se utilizzi la modalità Swarm, puoi personalizzare le porte esposte. **Nota bene: TUTTE le porte utilizzate dallo stack Swarm possono essere modificate editando questo file**, non solo quelle elencate di seguito:

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `WEB_PORT` | `7010` | Gateway Principale (API, Admin, Proxy) |
| `FRONTEND_PORT` | `7001` | Interfaccia Utente |
| `BACKEND_PORT` | `7002` | Backend Django |
| `SQL_GENERATOR_PORT` | `7003` | Servizio Generatore SQL |
| `MERMAID_SERVICE_PORT` | `7004` | Servizio Diagrammi Mermaid |
| `QDRANT_PORT` | `7005` | Vector Database Qdrant |

---

## 4. Gestione Deployment (Matrice Operativa)

La CLI `thothai` è progettata per gestire deployment in quattro scenari principali, combinando la modalità di orchestrazone (Compose o Swarm) con la destinazione (Locale o Remoto).

| Scenario | Docker Compose (Standard) | Docker Swarm (High Availability) |
| :--- | :--- | :--- |
| **Locale** | **Deploy Semplice**<br>Ideale per sviluppo e test rapidi sulla propria macchina.<br><br>`uv run thothai init`<br>`uv run thothai up` | **Test Cluster Locale**<br>Per simulare un ambiente di produzione Swarm sul proprio laptop.<br><br>`uv run thothai init --mode swarm`<br>`uv run thothai swarm deploy` |
| **Remoto (SSH)** | **Server Singolo**<br>Gestione di un server remoto VPS leggero senza cluster.<br><br>`uv run thothai init`<br>`uv run thothai up --server ssh://user@host` | **Cluster di Produzione**<br>Deploy su un cluster Swarm reale gestito da remoto.<br><br>`uv run thothai init --mode swarm`<br>`uv run thothai swarm deploy --server ssh://user@host` |

### Dettaglio Comandi per Scenario

#### 1. Locale + Compose (Default)
L'approccio più semplice. La CLI comunica direttamente con il demone Docker locale.
- **Avvio**: `uv run thothai up`
- **Stop**: `uv run thothai down`
- **Log**: `uv run thothai logs -f`
- **Stato**: `uv run thothai status`

#### 2. Locale + Swarm
Richiede che Docker Desktop (o Engine) abbia lo Swarm attivo (`docker swarm init`).
- **Avvio**: `uv run thothai swarm deploy`
- **Stop**: `uv run thothai swarm down`
- **Log**: `docker service logs -f thothai-swarm_backend` (o tramite visualizzatori esterni)
- **Stato**: `uv run thothai swarm status`

#### 3. Remoto + Compose
La CLI usa il tunneling SSH per inviare comandi al demone Docker remoto.
- **Avvio**: `uv run thothai up --server ssh://user@ip`
- **Stop**: `uv run thothai down --server ssh://user@ip`
- **Pulisci**: `uv run thothai prune --server ssh://user@ip`
- **Nota**: La CLI ora gestisce automaticamente la sincronizzazione dei file di configurazione (`config.yml.local`, `.env.docker`, etc.) verso il server remoto nella directory `/tmp/thothai_generated`, garantendo che i bind mounts funzionino correttamente anche su sistemi remoti.

#### 4. Remoto + Swarm
Gestione professionale di un cluster di produzione.
- **Avvio**: `uv run thothai swarm deploy --server ssh://user@ip`
- **Stop**: `uv run thothai swarm down --server ssh://user@ip`
- **Pulisci**: `uv run thothai swarm prune --server ssh://user@ip`
- **Update**: `uv run thothai swarm update --server ssh://user@ip` (Rolling update senza downtime)
- **Rollback**: `uv run thothai swarm rollback --server ssh://user@ip`

### 4.5 Gestione Avanzata Connessioni SSH

Dall'aggiornamento v1.1, la CLI `thothai` implementa un sistema di **Docker Context** automatico che rende la gestione remota estremamente fluida e sicura.

#### Come funziona
Quando specifichi l'opzione `--server`, la CLI:
1.  **Crea un Docker Context**: Configura automaticamente un context Docker che punta al server remoto via SSH. I context sono persistenti e riutilizzabili tra sessioni.
2.  **Riuso dell'Autenticazione**: Grazie al context, l'autenticazione (password o chiave) avviene **una sola volta** all'inizio dell'operazione. Tutti i comandi successivi riutilizzano lo stesso context istantaneamente.
3.  **Fallback Automatico**: Per versioni Docker precedenti alla 19.03, la CLI utilizza automaticamente un tunnel SSH come metodo alternativo.
4.  **Configurazione Trasparente**: La CLI utilizza il client `ssh` di sistema. Questo significa che rispetta automaticamente il tuo file `~/.ssh/config`, le chiavi caricate in `ssh-agent` e le tue impostazioni di sicurezza abituali.

#### Ottimizzazione con `~/.ssh/config`
Per evitare di scrivere ogni volta `user@ip`, ti consigliamo di aggiungere il server al tuo file di configurazione SSH locale (`~/.ssh/config`):

```text
Host thoth-prod
    HostName srv1198403.hstgr.cloud
    User root
    IdentityFile ~/.ssh/id_rsa
```

Con questa configurazione, i comandi diventano semplicissimi:
```bash
uv run thothai up --server thoth-prod
uv run thothai status --server thoth-prod
uv run thothai prune --server thoth-prod
```

#### Risoluzione Problemi Remoti
Se la connessione fallisce:
- Verifica di poter accedere manualmente: `ssh user@host`.
- Se usi una chiave con passphrase, assicurati che sia caricata: `ssh-add ~/.ssh/id_rsa`.
- In caso di errori "Permission denied", verifica che l'utente specificato abbia i permessi per eseguire comandi Docker sul server (tipicamente deve appartenere al gruppo `docker` o essere `root`).

---

## 5. Accesso all'Applicazione

Al termine dell'avvio, l'applicazione sarà raggiungibile ai seguenti indirizzi (sostituire `localhost` con l'IP del server in caso di deploy remoto):

- **Interfaccia Utente (Frontend)**: `http://localhost:3040` (o `FRONTEND_PORT` configurata)
- **Pannello di Controllo (Admin)**: `http://localhost:8040/admin` (o `WEB_PORT` configurata)

**Credenziali**: Usa lo username e la password definiti in `config.yml.local`.

---

## 6. Comandi Disponibili

### Comandi di Gestione Ciclo di Vita

- **`uv run thothai init`**: Inizializza il tuo spazio di lavoro. Crea i file di configurazione `config.yml.local` e i file Docker necessari. Usa `--mode swarm` se prevedi un deployment su cluster.
- **`uv run thothai up`**: Il comando principale per l'avvio. Valida la configurazione, crea i volumi necessari e avvia tutti i microservizi di ThothAI (Frontend, Backend, AI Generator, Database). Supporta l'opzione `--server ssh://...` per deploy remoti.
- **`uv run thothai down`**: Ferma l'esecuzione e rimuove i container e le reti virtuali. I tuoi dati nei volumi persistenti rimangono intatti.
- **`uv run thothai status`**: Fornisce una panoramica immediata dello stato di salute dei servizi, elencando i container attivi e le porte occupate.
- **`uv run thothai ps [--all]`**: Mostra i servizi attivi con informazioni dettagliate (nome container, immagine, stato, porte). Usa `--all` per includere anche i container fermati. Supporta `--server` per ambienti remoti.
- **`uv run thothai logs [-f]`**: Aggrega i log di tutti i microservizi. Fondamentale per il debugging in fase di configurazione dei provider AI. Use `-f` per seguire i log in tempo reale.
- **`uv run thothai update`**: Sincronizza il tuo sistema con le ultime versioni ufficiali delle immagini Docker di ThothAI, applicando patch e nuove funzionalità.
- **`uv run thothai prune`**: Rimuove tutti gli artefatti Docker (container, network, volumi e immagini) legati al progetto. Supporta l'opzione `--volumes/--no-volumes` e `--images/--no-images`. **Attenzione: la rimozione dei volumi elimina permanentemente tutti i dati (database e CSV).**
- **`uv run thothai config validate`**: Verifica analitica di `config.yml.local`. Assicura che le chiavi API siano formattate correttamente e che i modelli scelti siano supportati dai provider attivi.
- **`uv run thothai config test`**: Verifica la comunicazione con il motore Docker locale o remoto per prevenire errori di avvio dovuti a permessi o conflitti.

### Comandi Dati e Database

- **`uv run thothai csv <command>`**: Gestione completa dei file CSV nel volume di scambio (`list`, `upload`, `download`, `delete`).
- **`uv run thothai db <command>`**: Gestione dei database SQLite dinamici (`list`, `insert`, `remove`).

### Comandi Specifici Swarm
| Comando | Descrizione |
|---------|-------------|
| `uv run thothai swarm deploy` | Deploy dello stack su Swarm |
| `uv run thothai swarm down` | Rimuove lo stack ThothAI da Swarm. Elimina tutti i servizi in esecuzione e pulisce i segreti e le configurazioni associate, mantenendo intatti i volumi con i dati persistenti. |
| `uv run thothai swarm status` | Stato dei servizi nello stack Swarm |
| `uv run thothai swarm ps [-s service]` | Mostra servizi e task dello stack con dettagli. Usa `-s backend` per filtrare un servizio specifico. |
| `uv run thothai swarm prune` | Cleanup completo degli artefatti Swarm (stack, secrets, configs, network e volumi). |
| `uv run thothai swarm update` | Rolling update dei servizi Swarm |
| `uv run thothai swarm rollback` | Ripristina la versione precedente dello stack |
| `uv run thothai swarm logs [service]` | Visualizza i log di un servizio Swarm (default: backend). Opzioni: `-f` (follow), `--tail N`. |

---

## 7. Gestione Dati (CSV e SQLite)

ThothAI utilizza un'architettura a volumi Docker per garantire la persistenza e la condivisione dei dati tra i servizi. La CLI fornisce strumenti avanzati per manipolare questi dati in modo sicuro e veloce.

### 7.1 Gestione File CSV (`uv run thothai csv`)
I file CSV sono fondamentali per l'importazione di dati strutturati e per il recupero dei risultati delle analisi. Tutti i file sono archiviati nel volume Docker `thothai-data-exchange`.

- **`list`**: Fornisce un inventario dettagliato di tutti i file CSV residenti nel volume di scambio `thothai-data-exchange`. Non si limita ad elencare i nomi, ma include metadati vitali come la dimensione del file e l'ultimo timestamp di modifica. Questo è il comando fondamentale per confermare che un'esportazione complessa richiesta dall'interfaccia web sia stata completata con successo sul server prima di procedere al download, o per assicurarsi che un file appena caricato sia nella posizione corretta per essere elaborato dagli agenti AI.
- **`upload <file_locale>`**: Il punto di ingresso primario per i tuoi dati nell'ecosistema ThothAI. Questo comando gestisce in modo intelligente il trasferimento di file strutturati (CSV) dalla tua macchina locale all'infrastruttura Docker, sia che si tratti di un'installazione locale che di un server remoto via SSH. Una volta caricato, il file "alimenta" il sistema, permettendo al backend di mappare le nuove colonne e righe, rendendole immediatamente disponibili per le interrogazioni in linguaggio naturale.
- **`download <nome_file> [-o directory]`**: Rappresenta il canale di uscita ufficiale per i risultati delle tue analisi. Quando ThothAI conclude un'operazione di export o genera un report basato sui tuoi dati, questo comando ti permette di portarlo fuori dal container Docker e salvarlo fisicamente sulla tua macchina. L'opzione `--output` (`-o`) ti offre la flessibilità di organizzare i tuoi file in cartelle dedicate, facilitando la gestione di flussi di lavoro BI o l'archiviazione di report periodici.
- **`delete <nome_file>`**: Svolge un ruolo cruciale nella gestione della privacy e nell'ottimizzazione delle risorse. Consente di rimuovere permanentemente file obsoleti. Supporta il comando `delete all` per rimuovere tutti i file nel volume, oppure una lista separata da virgola (es. `file1.csv,file2.csv`). È uno strumento di governance essenziale per mantenere il volume di scambio ordinato ed evitare l'accumulo di dati non necessari.

### 7.2 Gestione Database SQLite (`uv run thothai db`)
ThothAI permette di interrogare database SQLite aggiuntivi. Questi database devono seguire una struttura specifica nel volume `thoth-shared-data` per essere riconosciuti automaticamente.

- **`list`**: Visualizza la libreria completa dei database SQLite "vivi" all'interno del sistema ThothAI, situati nella directory `dev_databases` del volume condiviso. Mostra i database disponibili per l'AI, escludendo file di sistema come `dev.json`. È lo strumento di monitoraggio principale per capire quali contesti informativi sono attualmente a disposizione.
- **`insert <percorso_file_sqlite>`**: Trasforma un semplice file SQLite in una risorsa attiva e interrogabile. Questo comando posiziona il file database direttamente nella directory `dev_databases` (`/app/data/dev_databases/{nome_file}.sqlite`), rendendolo immediatamente disponibile per le interrogazioni. Assicura che il file non sovrascriva configurazioni protette come `dev.json`. Al termine, il database appare nel selettore della console web.
- **`remove <nome_database>`**: Provvede alla rimozione sicura di una sorgente dati dalla directory `dev_databases`. Elimina il file specificato, impedendo la rimozione accidentale di file di sistema critici. È l'operazione di pulizia per mantenere l'integrità del sistema di conoscenza.

---

## 8. Troubleshooting e Best Practices

- **File mancante `config.yml.local`**: Esegui `uv run thothai init` per generarlo.
- **Docker non attivo**: Verifica con `docker info` e testa con `uv run thothai config test`.
- **Porta già in uso**: Modifica le porte in `config.yml.local` (per Compose) o `swarm_config.env` (per Swarm) e riavvia.
- **Sicurezza**: Non includere mai `config.yml.local`, `.env.docker` o `swarm_config.env` nel controllo di versione (Git).
- **Aggiornamenti**: Esegui regolarmente `uv run thothai update` per ottenere le ultime patch di sicurezza e funzionalità.
