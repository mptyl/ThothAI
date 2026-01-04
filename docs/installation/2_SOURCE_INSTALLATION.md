# Source Installation

This mode is designed for **developers**, **contributors**, or anyone needing deep customization of the code or Docker images.

## 1. Prerequisites

Ensure you have installed:
*   **Git**: To clone the repository.
*   **Docker Desktop** (Mac/Windows) or **Docker Engine** (Linux): Active and running.
*   **Python 3.9+** (optional but recommended for utility scripts).
*   **uv** (optional, recommended for Python package management).

### Note for Windows Users
If you are using Windows, ensure **WSL 2** is enabled and configured with Docker Desktop. Shell commands (`.sh`) should be run in WSL, while PowerShell scripts (`.ps1`) can be run directly from Windows PowerShell.

## 2. Cloning the Repository

Download the complete source code:

```bash
git clone https://github.com/mptyl/ThothAI.git
cd ThothAI
```

## 3. Configuration

Before starting, you must create and modify the local configuration file.

1.  Copy the template:
    *   **Mac/Linux:** `cp config.yml config.yml.local`
    *   **Windows:** `Copy-Item config.yml config.yml.local`

2.  Edit `config.yml.local` inserting:
    *   Your **API Keys** (OpenAI, Anthropic, Gemini, etc.).
    *   Any configuration overrides (ports, database, etc.).

> [!IMPORTANT]
> Never commit `config.yml.local` or `.env` files containing secrets!

## 4. Installation and Quick Start

Automatic installation scripts are provided to manage Docker environment creation, image downloading, and startup.

### Mac/Linux
Run the bash script:
```bash
./install.sh
```

### Windows
Run the PowerShell script (from Windows PowerShell):
```powershell
.\install.ps1
```

The script will execute:
1.  Verification of `config.yml.local`.
2.  Generation of environment files (e.g., `.env.docker`).
3.  Pull or Build of images.
4.  Service startup (`docker compose up`).

## 5. Custom Build and Push (Advanced)

If you modified the code and want to distribute your custom images (instead of using the official `tylconsulting` ones), you must build and push to your own registry.

### Push Requirements
*   Docker Hub account (or other registry).
*   Write access to the registry (perform `docker login`).

### Using `push.sh`

The `push.sh` script automates multi-architecture build and push.

```bash
# Syntax: ./push.sh <REGISTRY_URL> <VERSION> [OPTIONS]

# Example: Push to personal Docker Hub (user 'myuser'), version 1.0
./push.sh docker.io/myuser 1.0
```

This will create and upload images (e.g., `docker.io/myuser/thoth-backend:1.0` and `:latest`).

#### Custom Registry Configuration
After the push, update `config.yml.local` to use your new images:

```yaml
docker:
  image_registry: "myuser" # Your registry namespace
  # If it's a private registry, add username/password here
```

Then rerun `./install.sh` to update the running stack.

## 6. Using CLI from Source

The repository includes the source code for `thothai-cli`. You can use it directly without installing via pip, useful for testing changes to the CLI itself.

```bash
# Example: Running 'up' command using uv
uv run thothai up
```

For more details on available commands, see manuals [3_CLI_COMPOSE_INSTALLATION.md](3_CLI_COMPOSE_INSTALLATION.md) and [4_CLI_SWARM_INSTALLATION.md](4_CLI_SWARM_INSTALLATION.md) and [5_CLI_MANAGEMENT.md](5_CLI_MANAGEMENT.md).
