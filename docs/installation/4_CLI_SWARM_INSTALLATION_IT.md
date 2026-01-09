# Installazione CLI su Docker Swarm (Cluster)

Questa guida spiega come installare ThothAI su un cluster **Docker Swarm**. Questa è la modalità consigliata per produzione, alta affidabilità e scalabilità.

## 0. Installazione Locale della CLI

Prima di poter gestire il cluster Swarm, è necessario configurare l'ambiente locale con la CLI di ThothAI.

### 0.1 Installazione di `uv`

Il progetto utilizza `uv` per la gestione rapida delle dipendenze Python.

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 0.2 Creazione dell'ambiente virtuale

Posizionarsi nella root del progetto e creare un virtual environment:

```bash
uv venv
```

Attivare l'ambiente:

*   **macOS / Linux:** `source .venv/bin/activate`
*   **Windows:** `.venv\Scripts\activate`

### 0.3 Installazione della CLI

Installare le dipendenze e il pacchetto CLI in modalità editabile:

```bash
uv pip install -e cli/thothai-cli
```

Verificare l'installazione:

```bash
thothai --help
```

## 1. Prerequisiti

*   **Cluster Swarm**: Server di destinazione con Docker Engine inizializzato come Swarm Manager (`docker swarm init`).
*   **Python 3.9+** e **uv** installati sulla macchina di gestione (da cui lancerete i comandi).
*   **Accesso SSH** al nodo manager del cluster.

## 2. Inizializzazione Swarm

Nella vostra cartella di progetto, inizializzate la configurazione per Swarm:

```bash
uv run thothai init --mode swarm
```

Questo genererà:
*   `config.yml.local`: Configurazione principale.
*   `swarm_config.env`: Variabili specifiche per lo stack Swarm.
*   `.env.docker`: File environment autogenerato.

## 3. Configurazione

Modificate `config.yml.local`. La sezione `docker` è cruciale per dire al cluster da dove scaricare le immagini.

```yaml
docker:
  network_name: "thoth-network"
  # Default: Docker Hub pubblico (tylconsulting)
  # image_registry: "tylconsulting" 
  
  # Opzionale: Registry Privato (Decommentare se necessario)
  # image_registry: "registry.azienda.com/mia-azienda"
  # registry_username: "user"
  # registry_password: "password"
```

## 4. Deploy su Swarm

Il comando `swarm deploy` si occupa di trasferire configurazioni e avviare lo stack. Solitamente si opera verso un server remoto (il manager del cluster).

```bash
uv run thothai swarm deploy --server ssh://manager-node-user@ip
```

### Cosa avviene durante il deploy
1.  **Connessione**: La CLI si connette via SSH al nodo manager.
2.  **Autenticazione**: Se configurato un registry privato, esegue il login su tutti i nodi (o gestisce l'autenticazione tramite `--with-registry-auth`).
3.  **Configurazione**: Crea/aggiorna Secret e Config di Docker.
4.  **Avvio**: Esegue `docker stack deploy`.

## 5. Verifica

Verificate che i servizi siano distribuiti e attivi:

```bash
uv run thothai swarm status --server ssh://manager-node-user@ip
```

Dovreste vedere una lista di servizi con repliche `1/1` (o più se scalati).

## 6. Aggiornamento

Per aggiornare il cluster (es. dopo aver cambiato versione nel `config.yml` o dopo un nuovo push delle immagini):

```bash
uv run thothai swarm deploy --server ssh://manager-node-user@ip
```

Il comando è idempotente: aggiornerà solo i servizi necessari.
