# Installazione CLI su Docker Compose (Single Node)

Questa guida spiega come installare ThothAI su un singolo nodo (macchina locale o server remoto) utilizzando la CLI ufficiale e Docker Compose. Questa è la modalità standard per la maggior parte delle installazioni non in cluster.

## 1. Prerequisiti

*   **Python 3.9+** installato.
*   **uv** package manager installato (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
*   **Docker Desktop** (o Docker Engine) attivo sulla macchina di destinazione.

## 2. Installazione della CLI

Create una cartella per il progetto e installate la CLI:

```bash
mkdir my-thothai
cd my-thothai
uv venv
source .venv/bin/activate  # (Su Windows: .venv\Scripts\activate)
uv pip install thothai-cli
```

## 3. Inizializzazione

Inizializzate il progetto per la modalità standard (Compose):

```bash
uv run thothai init
```

Questo comando scaricherà il file `config.yml.local` di base nella directory corrente.

## 4. Configurazione

Modificate `config.yml.local` con le vostre impostazioni:

```yaml
# Esempio parziale di config.yml.local
llm:
  api_key: "sk-..." # Vostra chiave OpenAI

docker:
  network_name: "thoth-network"
  # Opzionale: Configurazione Registry Privato
  # image_registry: "registry.azienda.com"
  # registry_username: "user"
  # registry_password: "password"
```

### Scelta del Registry
*   **Docker Hub (Default)**: Se lasciate commentati i campi registry, le immagini verranno scaricate dal Docker Hub `tylconsulting` pubblico.
*   **Registry Privato**: Se la vostra azienda usa un registry privato (dove avete fatto il push come descritto nel Manuale 2), decommentate e compilate i campi `image_registry`, `registry_username`, e `registry_password`.

## 5. Deploy

La CLI gestisce il deploy sia in locale che in remoto.

### Scenario A: Installazione Locale
Per installare sulla macchina corrente (dove avete eseguito `init`):

```bash
uv run thothai up
```
Il comando configurerà i volumi, la rete e avvierà i container. L'interfaccia sarà disponibile su `http://localhost:3040`.

### Scenario B: Installazione su Server Remoto
Per installare su un server remoto raggiungibile via SSH:

```bash
uv run thothai up --server ssh://user@remote-ip
```

La CLI:
1.  Si connetterà via SSH.
2.  Copierà le configurazioni necessarie.
3.  Eseguirà il `docker login` (se configurato registry privato).
4.  Avvierà l'applicazione sul server remoto.

### Verifica
Dopo il deploy, potete controllare lo stato:

```bash
# Locale
uv run thothai status

# Remoto
uv run thothai status --server ssh://user@remote-ip
```
