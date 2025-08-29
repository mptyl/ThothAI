# ThothAI Backend Documentation

This repository contains the documentation for the ThothAI Backend system.

## Installation

This project uses `uv` for dependency management. To get started:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run the development server
uv run mkdocs serve
```

The documentation will be available at http://127.0.0.1:8050

## Building the Documentation

To build the static documentation site:

```bash
uv run mkdocs build
```

The built site will be in the `site/` directory.

## Development

To add new dependencies:

```bash
# Add a production dependency
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>
```

## License

Copyright (c) 2025 Marco Pancotti
This project is released under the MIT License.