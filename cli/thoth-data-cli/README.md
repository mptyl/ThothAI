# thoth-data-cli

CLI tool for managing CSV files and SQLite databases in ThothAI Docker deployments.

## Features

- **CSV Management**: Upload, download, list, and delete CSV files in the `thoth-data-exchange` volume
- **SQLite Database Management**: Insert and remove SQLite databases in the `thoth-shared-data` volume
- **Flexible Deployment Support**:
  - Local Docker or remote (SSH)
  - Docker Compose or Docker Swarm
- **Interactive Configuration**: Automatic config file creation on first use

## Installation

```bash
# Create virtual environment
mkdir thoth-data && cd thoth-data
uv venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install CLI
uv pip install thoth-data-cli
```

## Quick Start

```bash
# First usage creates config interactively
thoth-data csv list

# Upload CSV file
thoth-data csv upload data.csv

# Insert SQLite database
thoth-data db insert mydb.sqlite

# Test Docker connection
thoth-data config test
```

## Documentation

- [User Manual](docs/USER_MANUAL.md) - Installation and usage guide
- [Developer Manual](docs/DEVELOPER_MANUAL.md) - Build and publish instructions
- [Testing Guide](docs/TESTING_GUIDE.md) - Test procedures

## License

Apache License 2.0 - See [LICENSE.md](LICENSE.md) for details.

## Author

Marco Pancotti - ThothAI Project
