# thothai-data-cli - Manuale Sviluppatore

## Indice

1. [Setup Ambiente di Sviluppo](#setup-ambiente-di-sviluppo)
2. [Setup Backend ThothAI](#setup-backend-thothai)
3. [Struttura del Progetto](#struttura-del-progetto)
4. [Build del Pacchetto](#build-del-pacchetto)
5. [Testing Locale](#testing-locale)
6. [Pubblicazione su PyPI](#pubblicazione-su-pypi)
7. [Gestione Versioni](#gestione-versioni)
8. [Workflow di Sviluppo](#workflow-di-sviluppo)

---

## Setup Ambiente di Sviluppo

### Prerequisiti

- Python 3.9+
- `uv` package manager
- Docker (per i test)
- Git

### Clone e Setup

```bash
# Clone del repository
cd /path/to/ThothAI

# Naviga nel pacchetto CLI
cd cli/thothai-data-cli

# Installa dipendenze con uv
uv sync

# Verifica installazione
uv run thothai-data --help
```

---

## Setup Backend ThothAI

Per testare la CLI, hai bisogno di un deployment ThothAI Docker in esecuzione.

### Opzione 1: Docker Compose (Sviluppo Locale)

```bash
# Dalla directory root di ThothAI
./install.sh
```

Questo avvia ThothAI in modalità Docker Compose con:
- Backend sulla porta 8040
- Frontend sulla porta 3040
- SQL Generator sulla porta 8020
- Volumi: `thothai-data-exchange`, `thoth-shared-data`

### Opzione 2: Docker Swarm (Simile a produzione)

```bash
# Dalla directory root di ThothAI
./install-swarm.sh
```

Questo esegue il deploy di ThothAI come Docker Stack con:
- Nome stack: `thothai-swarm`
- Servizi in esecuzione in modalità Swarm
- Volumi named per la persistenza dei dati

---

## Struttura del Progetto

```
cli/
├── thothai_cli_core/       # Pacchetto core condiviso [NUOVO]
│   ├── pyproject.toml
│   └── src/thothai_cli_core/
│       ├── __init__.py
│       └── docker_ops.py   # Logica Docker migrata qui
├── thothai-data-cli/
│   ├── pyproject.toml      # Dipende da thothai-cli-core
│   ├── src/thothai_data_cli/
│   │   ├── cli.py          # Refactorizzato per usare il core
│   │   └── config.py       # Gestione locale directory data-exchange
│   └── docs/
│       ├── DATA_CLI_USER_MANUAL_IT.md
│       ├── DATA_CLI_DEVELOPER_MANUAL_IT.md
│       └── TESTING_GUIDE.md
```

---

## Build del Pacchetto

### Build con uv

```bash
cd cli/thothai-data-cli

# Build pacchetti di distribuzione
uv build
```

Questo crea:
- `dist/thothai_data_cli-1.0.0.tar.gz` (source distribution)
- `dist/thothai_data_cli-1.0.0-py3-none-any.whl` (wheel)

### Verifica Build

```bash
# Elenca contenuti
tar -tzf dist/thothai_data_cli-1.0.0.tar.gz

# Installa localmente per testare
uv pip install dist/thothai_data_cli-1.0.0-py3-none-any.whl
```

---

## Testing Locale

### Modalità Sviluppo

Esegui la CLI direttamente dal sorgente:

```bash
cd cli/thothai-data-cli

# Esegui comandi CLI
uv run thothai-data csv list
uv run thothai-data config show
uv run thothai-data config test
```

### Installazione da Wheel

```bash
# Crea ambiente di test
mkdir /tmp/test-cli && cd /tmp/test-cli
uv venv
source .venv/bin/activate

# Installa da wheel locale
uv pip install /path/to/ThothAI/cli/thothai-data-cli/dist/thothai_data_cli-1.0.0-py3-none-any.whl

# Test
thothai-data --help
thothai-data csv list
```

---

## Pubblicazione su PyPI

### Prerequisiti

1. **Account PyPI**: Crea su https://pypi.org/account/register/
2. **API Token**: Genera su https://pypi.org/manage/account/token/
3. **Configura uv**: Salva il token in `~/.pypirc` o usa variabili d'ambiente

### Pubblica su TestPyPI (Raccomandato prima)

```bash
cd cli/thothai-data-cli

# Build
uv build

# Pubblica su TestPyPI
uv publish --repository testpypi

# Test installazione da TestPyPI
uv pip install --index-url https://test.pypi.org/simple/ thothai-data-cli
```

### Pubblica su PyPI (Produzione)

```bash
cd cli/thothai-data-cli

# Assicura build pulita
rm -rf dist/
uv build

# Pubblica su PyPI
uv publish

# Verifica
uv pip install thothai-data-cli
thothai-data --version
```

### Credenziali PyPI

Salva le credenziali in `~/.pypirc`:

```ini
[pypi]
  username = __token__
  password = pypi-your-api-token-here

[testpypi]
  username = __token__
  password = pypi-your-test-api-token-here
```

---

## Gestione Versioni

### Aggiornamento Versione

1. **Modifica `pyproject.toml`**:
   ```toml
   [project]
   name = "thothai-data-cli"
   version = "1.1.0"  # Aggiorna qui
   ```

2. **Aggiorna `__init__.py`**:
   ```python
   __version__ = "1.1.0"  # Aggiorna qui
   ```

3. **Invia modifiche**:
   ```bash
   git add .
   git commit -m "Bump version to 1.1.0"
   git tag v1.1.0
   git push origin main --tags
   ```

### Semantic Versioning

Segui semver (https://semver.org/):

- `1.0.0` → `1.0.1`: Patch (bug fixes)
- `1.0.0` → `1.1.0`: Minor (nuove funzionalità, retrocompatibile)
- `1.0.0` → `2.0.0`: Major (breaking changes)

---

## Workflow di Sviluppo

### Aggiunta Nuovi Comandi

1. **Modifica `src/thothai_data_cli/cli.py`**:
   ```python
   @main.command()
   def new_command():
       """New command description."""
       # Implementation
   ```

2. **Aggiungi operazione in `docker_ops.py`** se necessario

3. **Test**:
   ```bash
   uv run thothai-data new-command
   ```

4. **Documenta** in `DATA_CLI_USER_MANUAL_IT.md`

### Aggiunta Dipendenze

```bash
cd cli/thothai-data-cli

# Aggiungi dipendenza
uv add requests

# Questo aggiorna pyproject.toml e uv.lock
```

### Qualità del Codice

```bash
# Formatta codice (se usi ruff)
uv run ruff format src/

# Lint
uv run ruff check src/

# Type checking (se usi mypy)
uv run mypy src/
```

---

## Risoluzione dei Problemi

### Build fallita

**Soluzione**: Pulisci artefatti di build
```bash
rm -rf dist/ build/ *.egg-info
uv build
```

### Errori di import dopo installazione

**Soluzione**: Controlla struttura pacchetto
```bash
# Verifica contenuti wheel
unzip -l dist/thothai_data_cli-1.0.0-py3-none-any.whl
```

### uv publish fallisce

**Soluzione**: Controlla credenziali in `~/.pypirc` o usa flag `--username` e `--password`

---

## Checklist di Rilascio

Prima di pubblicare una nuova versione:

- [ ] Aggiorna versione in `pyproject.toml` e `__init__.py`
- [ ] Aggiorna `README.md` se necessario
- [ ] Aggiorna documentazione in `docs/`
- [ ] Test locale con `uv run thothai-data`
- [ ] Test installazione da wheel
- [ ] Build pulita: `rm -rf dist/ && uv build`
- [ ] Pubblica su TestPyPI prima
- [ ] Test installazione da TestPyPI
- [ ] Pubblica su PyPI
- [ ] Crea git tag: `git tag v1.x.x`
- [ ] Push tag: `git push origin --tags`
- [ ] Crea release GitHub con changelog
