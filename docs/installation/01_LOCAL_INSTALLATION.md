# Local Installation Guide

This guide details how to install and run ThothAI natively on your local machine (macOS/Linux). This method is ideal for **development**, **debugging**, and **testing**.

> [!NOTE]
> In this mode, the Backend (Django), Frontend (Next.js), and SQL Generator (FastAPI) run directly on your host OS. Infrastructure services like Qdrant (Vector DB) and Mermaid Service still run in Docker for convenience.

## Prerequisites

Ensure your system meets the following requirements:

- **OS**: macOS or Linux
- **Python**: 3.9+ installed
- **Node.js**: v18+ and `npm` installed
- **Docker & Docker Compose**: Required for Qdrant and Mermaid services
- **uv**: Modern Python package manager (highly recommended)

### 1. Install `uv` (Recommended)

ThothAI uses `uv` for ultra-fast Python package management.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Prepare the Environment

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/mptyl/ThothAI.git
    cd ThothAI
    ```

2.  **Initialize Configuration**:
    Copy the template to enable local settings:
    ```bash
    cp .env.local.template .env.local
    ```

3.  **Configure `.env.local`**:
    Open `.env.local` and add your API keys. At a minimum, you need an LLM provider (like OpenAI key) and an Embedding provider.
    ```bash
    nano .env.local
    ```
    > [!IMPORTANT]
    > Do not skip this step! Services will fail to start without valid API keys.

## Method A: Quick Start (Recommended)

We provide a master script `start-all.sh` that automates the entire startup process. It handles:
- Starting dependency storage containers (Qdrant, Mermaid)
- Creating Python virtual environments if missing
- Installing dependencies
- Running database migrations
- Starting Backend, Frontend, and SQL Generator in parallel

### Run the Script

```bash
./start-all.sh
```

The script will output the status of each service. Once ready, you can access:
- **Frontend**: [http://localhost:3040](http://localhost:3040)
- **Backend Admin**: [http://localhost:8040/admin](http://localhost:8040/admin)
- **SQL Generator API**: [http://localhost:8020/docs](http://localhost:8020/docs)

To stop all services, simple press `Ctrl+C`.

---

## Method B: Manual Installation

If you prefer to run services manually (e.g., for individual debugging), follow these steps essentially doing what `start-all.sh` does automatically.

### 1. Infrastructure Services

Start the supporting Docker containers (Qdrant and Mermaid).

```bash
# Start Mermaid Service
docker compose up -d mermaid-service

# Start Local Qdrant
# We run a standalone Qdrant for local dev to avoid conflicts with shared Docker volumes
docker run -d --name thoth-qdrant-local -p 6333:6333 -v $(pwd)/qdrant_storage_local:/qdrant/storage qdrant/qdrant:latest
```

### 2. Backend (Django)

Open a new terminal tab:

```bash
cd backend

# Setup Python environment
uv sync

# Run Migrations
uv run python manage.py migrate
uv run python manage.py createcachetable

# Load Default Data (First time only)
uv run python manage.py load_defaults --source local

# Start Server
uv run python manage.py runserver 8040
```

### 3. SQL Generator (FastAPI)

Open a new terminal tab:

```bash
cd frontend/sql_generator

# Setup environment
uv sync

# Export required variables (aligned with .env.local)
export PORT=8020
export DJANGO_SERVER=http://localhost:8040
export VECTOR_DB_HOST=localhost
export VECTOR_DB_PORT=6333

# Start Service
uv run python main.py
```

### 4. Frontend (Next.js)

Open a new terminal tab:

```bash
cd frontend

# Install Dependencies
npm install

# Export required variables
export PORT=3040
export NEXT_PUBLIC_DJANGO_SERVER=http://localhost:8040
export NEXT_PUBLIC_SQL_GENERATOR_URL=http://localhost:8020

# Start Service
npm run dev
```

## Troubleshooting

- **Port Conflicts**: Ensure ports `8040`, `3040`, `8020`, and `6333` are free.
- **Micro-Frontend Issues**: If the frontend cannot talk to the backend, verify `NEXT_PUBLIC_DJANGO_SERVER` matches the backend URL exactly.
- **Database**: Local development uses SQLite (`backend/db.sqlite3`) by default. To reset it, delete the file and re-run migrations and `load_defaults`.
