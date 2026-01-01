# ThothAI Developer Manual - thothai-cli

Guida per sviluppatori su come costruire, testare e pubblicare `thothai-cli` su PyPI.

## Setup Ambiente Sviluppo

### Prerequisiti

- Python ≥3.9
- uv package manager
- Git
- Account PyPI (per pubblicazione)

### Clone e Setup

```bash
# Clone repository ThothAI
git clone https://github.com/mptyl/ThothAI.git
cd ThothAI/cli/thothai-cli

# Crea virtual environment
uv venv
source .venv/bin/activate

# Installa dipendenze sviluppo
uv pip install -e ".[dev]"
```

## Struttura Progetto

```
cli/thothai-cli/
├── src/thothai_cli/
│   ├── __init__.py           # Package info
│   ├── cli.py                # Entry point
│   ├── commands/             # CLI commands
│   │   ├── init.py
│   │   ├── deploy.py
│   │   ├── swarm.py
│   │   ├── data.py
│   │   └── config.py
│   ├── core/                 # Core modules
│   │   ├── config_manager.py
│   │   └── docker_manager.py   # Handles both Compose and Swarm
│   └── templates/            # Embedded templates
│       ├── config.yml
│       ├── docker-compose.yml
│       ├── docker-stack.yml
│       └── swarm_config.env
├── docs/
├── tests/
├── pyproject.toml
└── README.md
```

## Build del Pacchetto

### Build Locale

```bash
# Build distribuzione con uv
uv build

# Output in dist/:
# - thothai_cli-1.0.0-py3-none-any.whl
# - thothai_cli-1.0.0.tar.gz
```

### Test Installazione Locale

```bash
# In un altro directory
mkdir /tmp/test-thothai
cd /tmp/test-thothai
uv venv && source .venv/bin/activate

# Installa da wheel locale
uv pip install /path/to/ThothAI/cli/thothai-cli/dist/thothai_cli-1.0.0-py3-none-any.whl

# Test comandi
uv run thothai --version
uv run thothai init
```

## Testing

### Unit Tests

```bash
cd cli/thothai-cli
uv run pytest tests/ -v
```

### Integration Tests

```bash
# Test completo init → up → down
mkdir /tmp/integration-test
cd /tmp/integration-test

# Init
thothai init

# Edita config.yml.local con API key valida

# Deploy
thothai up

# Verifica
curl http://localhost:8040/admin/login/

# Cleanup
thothai down
```

## Pubblicazione su PyPI

### Setup Account PyPI

1. Crea account su https://pypi.org
2. Verifica email
3. Genera API token: https://pypi.org/manage/account/token/

### Configurazione Credenziali

```bash
# Crea ~/.pypirc
cat > ~/.pypirc << EOF
[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...
EOF

chmod 600 ~/.pypirc
```

### Pubblicazione

### Pubblicazione

#### Opzione A: UV (Raccomandato)

Il metodo più immediato, integrato nel toolchain.

```bash
cd cli/thothai-cli

# 1. Aggiorna versione in pyproject.toml
nano pyproject.toml
# version = "1.0.1"

# 2. Build
uv build

# 3. Upload su PyPI
# Nota: Usa un token con scope "Entire account" se è il primo rilascio del pacchetto
uv publish --token <IL_TUO_TOKEN>
```

#### Opzione B: Twine (Alternativa)

Utile per debug o se preferisci il tool classico.

```bash
# 1. Installa twine
uv pip install twine

# 2. Test upload su TestPyPI (opzionale)
uv run twine upload --repository testpypi dist/*

# 3. Upload su PyPI
uv run twine upload dist/*
```

### Verifica Pubblicazione

```bash
# Dopo pubblicazione
uv pip install thothai-cli==1.0.1

# Test
thothai --version
```

## Versionamento

Segui Semantic Versioning:

- **MAJOR**: Cambiamenti incompatibili API
- **MINOR**: Nuove funzionalità compatibili
- **PATCH**: Bug fixes

Esempio:
- `1.0.0` → Release iniziale
- `1.1.0` → Aggiunto swarm deploy completo
- `1.1.1` → Fix bug in config validation
- `2.0.0` → Cambio architettura CLI

## CI/CD (Futuro)

### GitHub Actions Workflow

```yaml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m pip install build twine
      - name: Build package
        run: python -m build
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

## Logica "Smart Commands"

I comandi principali (`up`, `down`, `status`, `logs`, `update`) implementano una logica di dispatch automatico:

1.  **ConfigManager** legge `docker.deployment_mode` da `config.yml.local`.
2.  **DockerManager** verifica il valore:
    *   Se `compose`: esegue i comandi standard `docker compose`.
    *   Se `swarm`: esegue i metodi `swarm_*` (es. `swarm_up`, `swarm_status`).

Questo permette all'utente di usare la stessa interfaccia di comandi indipendentemente dall'architettura scelta in fase di `init`.

## Aggiornamento Templates

I template embedded devono essere aggiornati quando cambiano i file sorgente:

```bash
# Quando aggiorni config.yml o docker-compose-hub.yml dalla root del progetto
cp ../../config.yml src/thothai_cli/templates/config.yml
cp ../../docker-compose-hub.yml src/thothai_cli/templates/docker-compose.yml
cp ../../docker-stack.yml src/thothai_cli/templates/docker-stack.yml

# IMPORTANTE: Dopo aver copiato config.yml, rimuovere la sezione 'local' 
# e aggiungere 'deployment_mode' nella sezione 'docker' per mantenere
# il template coerente con la filosofia lightweight.
```

## Best Practices

1. **Test prima di pubblicare**: sempre test completo E2E
2. **Mantieni template sincronizzati**: verifica compatibilità immagini Docker
3. **Versionamento chiaro**: documenta breaking changes
4. **Changelog**: mantieni CHANGELOG.md aggiornato
5. **Security**: mai committare credenziali PyPI

## Contatti

- Maintainer: Marco Pancotti
- Email: mp@tylconsulting.it  
- Repository: https://github.com/mptyl/ThothAI
