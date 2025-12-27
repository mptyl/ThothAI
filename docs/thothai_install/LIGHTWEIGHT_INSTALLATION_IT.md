# Installazione Lightweight di ThothAI

Installazione rapida di ThothAI senza clonare il repository.

## Prerequisiti

- Python ≥3.9
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker ≥20.0

## Procedura

### 1. Setup

```bash
mkdir my-thothai && cd my-thothai
uv venv && source .venv/bin/activate
uv pip install thothai-cli
```

### 2. Inizializzazione

```bash
uv run thothai init
```

### 3. Configurazione

Edita `config.yml.local` con le tue API keys.

### 4. Deploy

```bash
uv run thothai up
```

### 5. Accesso

- **Applicazione**: http://localhost:8040
- **Admin**: http://localhost:8040/admin

## Documentazione Completa

Vedi [cli/thothai-cli/docs/USER_MANUAL.md](../../cli/thothai-cli/docs/USER_MANUAL.md)
