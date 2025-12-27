# thoth-data-cli - Developer Manual

## Table of Contents

1. [Development Setup](#development-setup)
2. [ThothAI Backend Setup](#thothai-backend-setup)
3. [Project Structure](#project-structure)
4. [Building the Package](#building-the-package)
5. [Testing Locally](#testing-locally)
6. [Publishing to PyPI](#publishing-to-pypi)
7. [Version Management](#version-management)
8. [Development Workflow](#development-workflow)

---

## Development Setup

### Prerequisites

- Python 3.9+
- `uv` package manager
- Docker (for testing)
- Git

### Clone and Setup

```bash
# Clone the repository
cd /path/to/ThothAI

# Navigate to CLI package
cd cli/thoth-data-cli

# Install dependencies with uv
uv sync

# Verify installation
uv run thoth-data --help
```

---

## ThothAI Backend Setup

To test the CLI, you need a running ThothAI Docker deployment.

### Option 1: Docker Compose (Local Development)

```bash
# From ThothAI root directory
./install.sh
```

This starts ThothAI in Docker Compose mode with:
- Backend on port 8040
- Frontend on port 3040
- SQL Generator on port 8020
- Volumes: `thoth-data-exchange`, `thoth-shared-data`

### Option 2: Docker Swarm (Production-like)

```bash
# From ThothAI root directory
./install-swarm.sh
```

This deploys ThothAI as a Docker Stack with:
- Stack name: `thothai-swarm`
- Services running in Swarm mode
- Named volumes for data persistence

---

## Project Structure

```
cli/thoth-data-cli/
├── pyproject.toml          # Package configuration
├── README.md               # Package readme
├── LICENSE.md              # Apache 2.0 license
├── uv.lock                 # Dependency lock file
├── src/
│   └── thoth_data_cli/
│       ├── __init__.py     # Package metadata
│       ├── cli.py          # Click commands
│       ├── config.py       # YAML config management
│       └── docker_ops.py   # Docker operations
└── docs/
    ├── USER_MANUAL.md      # End-user documentation
    ├── DEVELOPER_MANUAL.md # This file
    └── TESTING_GUIDE.md    # Testing procedures
```

---

## Building the Package

### Build with uv

```bash
cd cli/thoth-data-cli

# Build distribution packages
uv build
```

This creates:
- `dist/thoth_data_cli-1.0.0.tar.gz` (source distribution)
- `dist/thoth_data_cli-1.0.0-py3-none-any.whl` (wheel)

### Verify Build

```bash
# List contents
tar -tzf dist/thoth_data_cli-1.0.0.tar.gz

# Install locally to test
uv pip install dist/thoth_data_cli-1.0.0-py3-none-any.whl
```

---

## Testing Locally

### Development Mode

Run CLI directly from source:

```bash
cd cli/thoth-data-cli

# Run CLI commands
uv run thoth-data csv list
uv run thoth-data config show
uv run thoth-data config test
```

### Install from Wheel

```bash
# Create test environment
mkdir /tmp/test-cli && cd /tmp/test-cli
uv venv
source .venv/bin/activate

# Install from local wheel
uv pip install /path/to/ThothAI/cli/thoth-data-cli/dist/thoth_data_cli-1.0.0-py3-none-any.whl

# Test
thoth-data --help
thoth-data csv list
```

---

## Publishing to PyPI

### Prerequisites

1. **PyPI Account**: Create at https://pypi.org/account/register/
2. **API Token**: Generate at https://pypi.org/manage/account/token/
3. **Configure uv**: Store token in `~/.pypirc` or use environment variable

### Publish to TestPyPI (Recommended First)

```bash
cd cli/thoth-data-cli

# Build
uv build

# Publish to TestPyPI
uv publish --repository testpypi

# Test installation from TestPyPI
uv pip install --index-url https://test.pypi.org/simple/ thoth-data-cli
```

### Publish to PyPI (Production)

```bash
cd cli/thoth-data-cli

# Ensure clean build
rm -rf dist/
uv build

# Publish to PyPI
uv publish

# Verify
uv pip install thoth-data-cli
thoth-data --version
```

### PyPI Credentials

Store credentials in `~/.pypirc`:

```ini
[pypi]
  username = __token__
  password = pypi-your-api-token-here

[testpypi]
  username = __token__
  password = pypi-your-test-api-token-here
```

---

## Version Management

### Update Version

1. **Edit `pyproject.toml`**:
   ```toml
   [project]
   name = "thoth-data-cli"
   version = "1.1.0"  # Update here
   ```

2. **Update `__init__.py`**:
   ```python
   __version__ = "1.1.0"  # Update here
   ```

3. **Commit changes**:
   ```bash
   git add .
   git commit -m "Bump version to 1.1.0"
   git tag v1.1.0
   git push origin main --tags
   ```

### Semantic Versioning

Follow semver (https://semver.org/):

- `1.0.0` → `1.0.1`: Patch (bug fixes)
- `1.0.0` → `1.1.0`: Minor (new features, backward compatible)
- `1.0.0` → `2.0.0`: Major (breaking changes)

---

## Development Workflow

### Adding New Commands

1. **Edit `src/thoth_data_cli/cli.py`**:
   ```python
   @main.command()
   def new_command():
       """New command description."""
       # Implementation
   ```

2. **Add operation in `docker_ops.py`** if needed

3. **Test**:
   ```bash
   uv run thoth-data new-command
   ```

4. **Document** in `USER_MANUAL.md`

### Adding Dependencies

```bash
cd cli/thoth-data-cli

# Add dependency
uv add requests

# This updates pyproject.toml and uv.lock
```

### Code Quality

```bash
# Format code (if using ruff)
uv run ruff format src/

# Lint
uv run ruff check src/

# Type checking (if using mypy)
uv run mypy src/
```

---

## Troubleshooting

### Build fails

**Solution**: Clean build artifacts
```bash
rm -rf dist/ build/ *.egg-info
uv build
```

### Import errors after installation

**Solution**: Check package structure
```bash
# Verify wheel contents
unzip -l dist/thoth_data_cli-1.0.0-py3-none-any.whl
```

### uv publish fails

**Solution**: Check credentials in `~/.pypirc` or use `--username` and `--password` flags

---

## Release Checklist

Before publishing a new version:

- [ ] Update version in `pyproject.toml` and `__init__.py`
- [ ] Update `README.md` if needed
- [ ] Update documentation in `docs/`
- [ ] Test locally with `uv run thoth-data`
- [ ] Test installation from wheel
- [ ] Clean build: `rm -rf dist/ && uv build`
- [ ] Publish to TestPyPI first
- [ ] Test installation from TestPyPI
- [ ] Publish to PyPI
- [ ] Create git tag: `git tag v1.x.x`
- [ ] Push tag: `git push origin --tags`
- [ ] Create GitHub release with changelog
