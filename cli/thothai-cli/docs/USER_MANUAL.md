# ThothAI User Manual - Lightweight Installation

Guida completa all'installazione lightweight di ThothAI usando `thothai-cli`.

## Prerequisiti

| Requisito | Versione | Installazione |
|-----------|----------|---------------|
| Python | ≥3.9 | https://www.python.org/ |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker | ≥20.0 | https://docs.docker.com/get-docker/ |

## Installazione

### 1. Setup Virtual Environment

```bash
# Crea directory progetto
mkdir my-thothai
cd my-thothai

# Crea virtual environment con uv
uv venv

# Attiva venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate   # Windows PowerShell
```

### 2. Installa thothai-cli

```bash
uv pip install thothai-cli
```

### 3. Inizializza Progetto

```bash
uv run thothai init
```

Questo comando crea:
- `config.yml.local` - Configurazione da editare
- `docker-compose.yml` - Orchestrazione Docker
- `.gitignore` - Esclude file sensibili
- `data_exchange/` - Directory per CSV

### 4. Configura API Keys

Edita `config.yml.local` e inserisci le tue chiavi API:

```yaml
ai_providers:
  openai:
    enabled: true
    api_key: "sk-..."  # La tua chiave OpenAI
  
  gemini:
    enabled: true
    api_key: "AIza..."  # La tua chiave Gemini

embedding:
  provider: "openai"
  model: "text-embedding-3-small"
  api_key: ""  # Usa quella di OpenAI

admin:
  username: "admin"
  password: "change-this-password"  # Min 8 caratteri
```

### 5. Valida Configurazione

```bash
uv run thothai config validate
```

## Deploy Docker Compose

### Primo Avvio

```bash
uv run thothai up
```

Questo comando:
1. Valida la configurazione
2. Genera `.env.docker`
3. Crea volumi e network Docker
4. **Pull immagini da Docker Hub**
5. Avvia i container

### Verifica Stato

```bash
uv run thothai status
```

### Accesso all'Applicazione

- **Applicazione**: http://localhost:8040
- **Admin Panel**: http://localhost:8040/admin
- **Frontend Diretto**: http://localhost:3040

**Credenziali**:
- Username: `admin` (o come configurato)
- Password: come configurato in `config.yml.local`

## Gestione Container

### Visualizza Logs

```bash
# Tutti i servizi
uv run thothai logs

# Servizio specifico
uv run thothai logs backend
uv run thothai logs frontend

# Segui logs in tempo reale
uv run thothai logs -f backend
```

### Stop Container

```bash
uv run thothai down
```

### Aggiornamento (manuale)

```bash
uv run thothai update
```

Questo comando:
1. Pull delle immagini latest
2. Ricrea i container
3. Preserva dati e volumi

> **Nota**: L'aggiornamento è **solo manuale**, non automatico.

## Deploy Docker Swarm

### Inizializza per Swarm

```bash
uv run thothai init --mode swarm
```

Questo crea anche:
- `docker-stack.yml`
- `swarm_config.env`

### Configura Porte Swarm

Edita `swarm_config.env`:

```env
DOCKER_USERNAME=tylconsulting
STACK_NAME=thothai-swarm

WEB_PORT=7010
FRONTEND_PORT=7001
BACKEND_PORT=7002
```

### Deploy

Il `thothai-cli` rileva automaticamente la modalità scelta durante l'`init`.

```bash
# Se inizializzato con --mode swarm, questi comandi gestiscono lo stack Swarm
uv run thothai up
uv run thothai status
uv run thothai down

# Oppure usa i comandi espliciti
uv run thothai swarm deploy
uv run thothai swarm status
uv run thothai swarm down

# Deploy su server remoto via SSH
uv run thothai swarm deploy --server user@my-server.com
```

## Troubleshooting

### Errore: config.yml.local not found

```bash
uv run thothai init
```

### Errore: Docker is not running

```bash
# Verifica Docker
docker info

# Testa connessione
uv run thothai config test
```

### Errore: Failed to pull images

Verifica:
1. Connessione internet
2. Docker Hub accessibile
3. Username Docker corretto in config

### Porta già in uso

Modifica porte in `config.yml.local`:

```yaml
ports:
  frontend: 3050  # Cambia porta
  nginx: 8050
```

Poi rigenera:

```bash
uv run thothai down
uv run thothai up
```

## Comandi Disponibili

| Comando | Descrizione |
|---------|-------------|
| `thothai init` | Inizializza progetto |
| `thothai up` | Avvia container |
| `thothai down` | Ferma container |
| `thothai status` | Mostra stato |
| `thothai logs [SERVICE]` | Visualizza logs |
| `thothai update` | Aggiorna immagini |
| `thothai config show` | Mostra configurazione |
| `thothai config validate` | Valida configurazione |
| `thothai config test` | Testa Docker |
| `thothai swarm deploy` | Deploy stack Swarm |
| `thothai swarm down` | Rimuovi stack Swarm |
| `thothai swarm status` | Stato servizi Swarm |
| `thothai swarm update` | Aggiorna stack Swarm |
| `thothai swarm rollback` | Rollback stack Swarm |

## Best Practices

1. **Mai committare** `config.yml.local` o `.env.docker`
2. **Usa password forti** per admin
3. **Aggiorna regolarmente**: `thothai update`
4. **Backup dati** prima di aggiornamenti maggiori
5. **Testa configurazione** prima del deploy: `thothai config validate`
