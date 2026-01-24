# Publishing Guide

This document provides instructions for publishing ThothAI components (Docker Images and CLI packages).

---

## 1. Docker Images (Docker Hub)

ThothAI uses a multi-platform build system (Buildx) to support both `amd64` and `arm64` architectures.

### Prerequisites
- Docker Desktop (or Docker Engine with Buildx)
- Docker Hub Account
- Active session: `docker login`

### Configuration
Update your `.env.docker` file with your registry information:
```env
DOCKER_REGISTRY=your_username
IMAGE_VERSION=1.0.0
```

### Publishing Steps
Run the `push.sh` script from the project root. This script builds and pushes all services:
```bash
# Usage: ./push.sh <REGISTRY_NAME> <VERSION>
./push.sh your_username 1.0.0
```

The script will handle:
- `thoth-backend`
- `thoth-frontend`
- `thoth-sql-generator`
- `thoth-proxy`
- `thoth-mermaid-service`
- `thoth-qdrant` (preserved from official image)

---

## 2. CLI Packages (PyPI)

The CLI packages are managed using `uv`. There are three main packages that should be published in order due to dependencies.

### Prerequisites
- `uv` installed
- PyPI account and access token
- Token configured in `~/.pypirc` or via environment variables

### Order of Publication
1. `thothai-cli-core` (Required by both CLIs)
2. `thothai-cli` (Main entry point)
3. `thothai-data-cli` (Data management tool)

### Publishing Procedure

For each package directory under `cli/`:

1. **Update Version**:
   Edit `pyproject.toml` and increment the `version` field.

2. **Build and Publish**:
   ```bash
   cd cli/thothai-cli-core  # Repeat for each package
   
   # Clean previous builds
   rm -rf dist/
   
   # Build the package
   uv build
   
   # Publish to PyPI
   uv publish
   ```

### Quick Commands Summary
```bash
# Core logic
cd cli/thothai-cli-core && uv build && uv publish && cd ../..

# Primary CLI
cd cli/thothai-cli && uv build && uv publish && cd ../..

# Data CLI
cd cli/thothai-data-cli && uv build && uv publish && cd ../..
```

---

## Maintenance Notes
- Always ensure `IMAGE_VERSION` in `.env.docker` matches the version you are pushing.
- For Docker Swarm deployments, ensure nodes have access to the registry where images are hosted.
- Test the CLI packages locally after publication: `uv pip install --upgrade thothai-cli`.
