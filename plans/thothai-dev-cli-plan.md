# ThothAI Development CLI Implementation Plan

## Overview

Creare una CLI di sviluppo unificata (`thothai-dev`) per gestire tutte le operazioni di build, push, deploy e management dell'applicazione. L'obiettivo finale è rimuovere tutti gli script .sh e .ps1 dalla root directory, mantenendo solo i file essenziali.

## Analisi degli Script Esistenti

### Script da Consolidare

| Script | Funzione | Comandi CLI Proposti |
|--------|----------|---------------------|
| `push.sh` / `push.ps1` | Build e push immagini Docker | `thothai-dev build`, `thothai-dev push` |
| `install.sh` / `install.ps1` | Installazione Docker Compose | `thothai-dev compose install` |
| `install-swarm.sh` / `install-swarm.ps1` | Deploy su Docker Swarm | `thothai-dev swarm install` |
| `manage-swarm.sh` / `manage-swarm.ps1` | Gestione stack Swarm | `thothai-dev swarm [status\|update\|rollback\|logs]` |
| `start-all.sh` / `start-all.ps1` | Avvio sviluppo locale | `thothai-dev dev start` |

### Struttura Root Attuale (38 file, 24 cartelle)
```
/ThothAI/
├── *.sh (5 file)           # Da rimuovere
├── *.ps1 (5 file)          # Da rimuovere
├── *.md (README, CHANGELOG, etc.)  # Mantenere
├── config.yml*             # Mantenere
├── docker-compose*.yml     # Spostare in docker/
├── docker-stack.yml        # Spostare in docker/
├── swarm_config.env*       # Spostare in docker/
├── backend/                # Mantenere
├── frontend/               # Mantenere
├── cli/                    # Mantenere (aggiungere thothai-dev)
├── docker/                 # Mantenere (aggiungere compose files)
├── docs/                   # Mantenere
├── scripts/                # Mantenere
└── ...
```

---

## Decisioni da Prendere

> [!IMPORTANT]
> **Spostamento file Docker**: Propongo di spostare `docker-compose*.yml`, `docker-stack.yml` e `swarm_config.env*` dalla root a `docker/`. Questo richiederà aggiornamenti ai percorsi nei comandi.

> [!IMPORTANT]
> **Docker SDK vs subprocess**: La CLI dovrebbe usare il Docker SDK Python (come `thothai-cli`) o invocare `docker` via subprocess (più fedele agli script esistenti)?

> [!IMPORTANT]
> **Timeline**: Implementazione completa in un'unica fase o incrementale (prima build/push, poi compose, poi swarm, infine dev)?

---

## Proposed Changes

### CLI Package

#### [NEW] cli/thothai-dev/
Nuovo package CLI per operazioni di sviluppo.

```
cli/thothai-dev/
├── pyproject.toml          # Package configuration
├── README.md               # Developer documentation
├── LICENSE.md              # Apache 2.0
├── src/
│   └── thothai_dev/
│       ├── __init__.py
│       ├── cli.py          # Main CLI entry point
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── build.py    # Build images command
│       │   ├── push.py     # Push to registry
│       │   ├── compose.py  # Docker Compose commands
│       │   ├── swarm.py    # Docker Swarm commands
│       │   └── dev.py      # Local development commands
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── docker.py   # Docker utilities
│       │   ├── config.py   # Configuration loader
│       │   └── console.py  # Rich console output
│       └── config/
│           └── images.py   # Image definitions
└── tests/
    └── test_cli.py
```

#### CLI Command Structure

```
thothai-dev
├── build                   # Build Docker images
│   ├── --all              # Build all images
│   ├── --image NAME       # Build specific image
│   ├── --no-cache         # Build without cache
│   └── --version VERSION  # Tag version
│
├── push                    # Push images to registry
│   ├── --registry URL     # Registry URL
│   ├── --version VERSION  # Image version
│   └── --push-only        # Skip build, push only
│
├── compose                 # Docker Compose operations
│   ├── install            # Install via Compose
│   │   ├── --build        # Build locally
│   │   ├── --pull         # Pull from Hub
│   │   └── --prune        # Remove all resources
│   ├── up                  # Start services
│   ├── down                # Stop services
│   └── logs                # View logs
│
├── swarm                   # Docker Swarm operations
│   ├── install             # Deploy to Swarm
│   │   ├── --server HOST  # Remote server
│   │   └── --prune        # Remove before deploy
│   ├── status              # Show stack status
│   ├── update              # Rolling update
│   ├── rollback            # Rollback deployment
│   ├── logs                # View service logs
│   └── backup              # Backup volumes
│
├── dev                     # Local development
│   ├── start               # Start all services
│   ├── stop                # Stop all services
│   ├── restart             # Restart services
│   └── status              # Show service status
│
└── config                  # Configuration management
    ├── validate            # Validate config.yml.local
    ├── generate            # Generate .env files
    └── show                # Show current config
```

---

### Docker Directory Restructure

#### [MODIFY] docker/
Spostare i file Docker Compose nella cartella `docker/`.

**File da spostare:**
- `docker-compose.yml` → `docker/compose.yml`
- `docker-compose-hub.yml` → `docker/compose-hub.yml`
- `docker-compose-local.yml` → `docker/compose-local.yml`
- `docker-stack.yml` → `docker/stack.yml`
- `swarm_config.env` → `docker/swarm_config.env`
- `swarm_config.env.template` → `docker/swarm_config.env.template`

---

### Root Directory Cleanup

#### [DELETE] Script Files
Dopo il completamento della CLI, eliminare:
- `push.sh`, `push.ps1`
- `install.sh`, `install.ps1`
- `install-swarm.sh`, `install-swarm.ps1`
- `manage-swarm.sh`, `manage-swarm.ps1`
- `start-all.sh`, `start-all.ps1`

---

### Final Root Structure

```
/ThothAI/
├── .agent/                     # Agent configuration
├── .claude/                    # Claude configuration
├── AGENTS.md                   # Agent instructions (Codex, Cline, etc.)
├── CHANGELOG.md                # Version history
├── CLAUDE.md                   # Claude-specific context
├── GEMINI.md                   # Gemini-specific context
├── LICENSE.md                  # Apache 2.0 license
├── PLANNING.md                 # Development roadmap
├── README.md                   # Project overview
├── config.yml                  # Configuration template
├── config.yml.local            # Local configuration (gitignored)
├── .env.local                  # Generated env (gitignored)
├── .env.docker                 # Generated env (gitignored)
│
├── backend/                    # Django backend
├── cli/                        # CLI packages
│   ├── thothai-cli/           # Installation CLI
│   ├── thothai-data-cli/      # Data management CLI
│   └── thothai-dev/           # Development CLI (NEW)
├── data/                       # Test databases
├── data_exchange/              # CSV exchange
├── docker/                     # Docker configuration
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   ├── sql-generator.Dockerfile
│   ├── proxy.Dockerfile
│   ├── mermaid-service/
│   ├── compose.yml            # (moved from root)
│   ├── compose-hub.yml         # (moved from root)
│   ├── compose-local.yml       # (moved from root)
│   ├── stack.yml               # (moved from root)
│   ├── swarm_config.env        # (moved from root)
│   └── swarm_config.env.template
├── docs/                       # Documentation
├── frontend/                   # Next.js frontend
├── scripts/                    # Helper scripts
├── setup_csv/                  # CSV setup data
└── vendor/                     # Vendored dependencies
```

---

## Verification Plan

### Automated Tests

#### 1. CLI Unit Tests
```bash
cd cli/thothai-dev
uv run pytest tests/ -v
```

#### 2. CLI Help Validation
```bash
# Verifica che tutti i comandi siano registrati
uv run thothai-dev --help
uv run thothai-dev build --help
uv run thothai-dev push --help
uv run thothai-dev compose --help
uv run thothai-dev swarm --help
uv run thothai-dev dev --help
```

### Manual Verification

#### Test 1: Build Command
```bash
cd /Users/mp/ThothAI
uv run --project cli/thothai-dev thothai-dev build --all --version test
# Verificare che le immagini siano create con docker images | grep thoth
```

#### Test 2: Local Development
```bash
cd /Users/mp/ThothAI
uv run --project cli/thothai-dev thothai-dev dev start
# Verificare che i servizi siano accessibili:
# - Backend: http://localhost:8200
# - Frontend: http://localhost:3200
# - Qdrant: http://localhost:6334
```

#### Test 3: Docker Compose Install
```bash
cd /Users/mp/ThothAI
uv run --project cli/thothai-dev thothai-dev compose install --build
# Verificare con docker compose -f docker/compose.yml ps
```

---

## Execution Timeline

### Phase 1: CLI Foundation (Priority)
1. Creare struttura package `cli/thothai-dev/`
2. Implementare comandi `build` e `push`
3. Testare equivalenza funzionale con `push.sh`

### Phase 2: Docker Operations
4. Implementare comandi `compose`
5. Implementare comandi `swarm`
6. Spostare file Docker Compose

### Phase 3: Local Development
7. Implementare comando `dev start` (più complesso)
8. Implementare altri comandi `dev`

### Phase 4: Cleanup
9. Aggiornare documentazione
10. Rimuovere script shell dalla root
11. Aggiornare GEMINI.md con nuovi comandi

---

## Notes

- La CLI usa **Click** per il parsing dei comandi (consistente con `thothai-cli`)
- Output con **Rich** per feedback colorato e formattato
- Le funzioni helper esistenti in `scripts/` vengono riutilizzate dove possibile
- La CLI non viene pubblicata su PyPI (solo uso interno per sviluppo)
