# thothai-cli

**Lightweight installation and management CLI for ThothAI**

Deploy and manage ThothAI without cloning the repository.

## Installation

```bash
# Create virtual environment
mkdir my-thothai && cd my-thothai
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install thothai-cli
uv pip install thothai-cli
```

## Quick Start

```bash
# 1. Initialize project
uv run thothai init

# 2. Configure (edit config.yml.local with your API keys)
nano config.yml.local

# 3. Deploy
uv run thothai up

# 4. Access ThothAI
# http://localhost:8040
```

## Commands

### Deployment

- `thothai init` - Initialize project with configuration files
- `thothai up` - Pull images and start containers
- `thothai down` - Stop containers
- `thothai status` - Show container status
- `thothai logs [SERVICE]` - View logs
- `thothai update` - Update to latest images (manual)

### Configuration

- `thothai config show` - Display current configuration
- `thothai config validate` - Validate configuration
- `thothai config test` - Test Docker connection

### Swarm (Coming Soon)

- `thothai swarm deploy` - Deploy to Docker Swarm
- `thothai swarm status` - Show Swarm services
- `thothai swarm update` - Update Swarm services

### Data Management (Coming Soon)

- `thothai csv list|upload|download|delete` - Manage CSV files
- `thothai db list|insert|remove` - Manage SQLite databases

## Requirements

- Python ≥3.9
- Docker ≥20.0
- uv package manager

## Documentation

- [User Manual](docs/USER_MANUAL.md)
- [Developer Manual](docs/DEVELOPER_MANUAL.md)
- [ThothAI Project](https://github.com/mptyl/ThothAI)

## License

Apache License 2.0 - See LICENSE.md
