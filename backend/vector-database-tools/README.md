# Thoth Vector Database Tools

Simple Docker Compose setup for testing and development with multiple vector databases. All containers are part of the `thoth-test-virtualdbs` network group.

## 🎯 Overview

This environment provides ready-to-use vector database containers for development and testing:

- **Qdrant**: Vector database with web dashboard
- **Milvus**: High-performance vector database with Attu web UI
- **Chroma**: Simple vector database for embeddings
- **pgvector**: PostgreSQL with vector extension

## 📋 Prerequisites

- **Docker** and **Docker Compose**
- Available ports: 5436, 6334-6335, 8000, 8082, 9000-9001, 9091, 19530, 3002

## 🚀 Quick Start

```bash
# Navigate to vector database tools
cd vector-database-tools

# Start all vector databases
docker-compose -f vector-databases.yml up -d

# Check status
docker ps

# View logs
docker-compose -f vector-databases.yml logs
```

## 🗄️ Vector Database Services

### Qdrant
- **Port**: 6334 (HTTP), 6335 (gRPC)
- **Container**: `thoth-test-qdrant`
- **Dashboard**: http://localhost:6334/dashboard
- **API**: http://localhost:6334
- **Features**: REST API, gRPC, web dashboard
- **Storage**: Persistent volume `qdrant_data`

 

### Milvus
- **Port**: 19530 (server), 9091 (web admin)
- **Container**: `thoth-test-milvus`
- **Web UI (Attu)**: http://localhost:3002
- **API**: localhost:19530
- **Features**: High-performance, scalable, Attu web interface
- **Dependencies**: Includes etcd and MinIO containers
- **Storage**: Persistent volume `milvus_data`

### Chroma
- **Port**: 8000
- **Container**: `thoth-test-chroma`
- **API**: http://localhost:8000
- **Features**: Simple REST API, lightweight
- **Storage**: Persistent volume `chroma_data`

### pgvector
- **Port**: 5436
- **Container**: `thoth-test-pgvector`
- **Database**: `vector_db`
- **Credentials**: `vector_user` / `vector_password`
- **pgAdmin**: http://localhost:8082 (`admin@thoth.local` / `admin_password`)
- **Features**: PostgreSQL with vector operations, SQL interface
- **Storage**: Persistent volume `pgvector_data`

## 🔐 Connection Details

### Qdrant
```python
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6334)
```

 

### Milvus
```python
from pymilvus import connections

connections.connect("default", host="localhost", port="19530")
```

### Chroma
```python
import chromadb

client = chromadb.HttpClient(host="localhost", port=8000)
```

### pgvector
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5436,
    database="vector_db",
    user="vector_user",
    password="vector_password"
)
```

## 📊 Web Interfaces

| Service | URL | Description |
|---------|-----|-------------|
| Qdrant Dashboard | http://localhost:6334/dashboard | Vector database management |
| Milvus Attu | http://localhost:3002 | Milvus web interface |
| pgAdmin | http://localhost:8082 | PostgreSQL management |
| MinIO Console | http://localhost:9001 | Milvus object storage (minioadmin/minioadmin) |

## 🔧 Service Management

### Start Individual Services

```bash
# Start only Qdrant
docker-compose -f vector-databases.yml up -d qdrant

 

# Start only Chroma
docker-compose -f vector-databases.yml up -d chroma

# Start only pgvector
docker-compose -f vector-databases.yml up -d pgvector pgadmin

# Start Milvus (includes dependencies)
docker-compose -f vector-databases.yml up -d milvus-standalone milvus-attu
```

### Stop Services

```bash
# Stop all services
docker-compose -f vector-databases.yml down

# Stop specific service
docker-compose -f vector-databases.yml stop qdrant

# Stop and remove volumes (WARNING: deletes all data)
docker-compose -f vector-databases.yml down -v
```

## 📈 Health Checks

All services include health checks. View status:

```bash
# Check all containers
docker ps

# Check specific service health
docker inspect thoth-test-qdrant | grep -A 5 Health
 
docker inspect thoth-test-milvus | grep -A 5 Health
docker inspect thoth-test-chroma | grep -A 5 Health
docker inspect thoth-test-pgvector | grep -A 5 Health
```

## 🔄 Network Configuration

All services are connected to the `thoth-test-virtualdbs` network, allowing inter-service communication:

```bash
# Services can communicate using container names:
# - thoth-test-qdrant:6333
# - thoth-test-milvus:19530
# - thoth-test-chroma:8000
# - thoth-test-pgvector:5432
```

## 📂 Data Persistence

All vector databases use persistent Docker volumes:

- `qdrant_data`: Qdrant collections and metadata
 
- `milvus_data`: Milvus collections and indexes
- `chroma_data`: Chroma collections and embeddings
- `pgvector_data`: PostgreSQL database with vectors

## 🛠️ Configuration

Optional configuration files can be placed in respective directories:

- `qdrant/config/`: Qdrant configuration files
 
- `milvus/config/`: Milvus configuration files
- `chroma/config/`: Chroma configuration files
- `pgvector/init/`: PostgreSQL initialization scripts

## 📋 Example Usage

### Quick Vector Operations Test

```python
# Test all databases with simple operations
import numpy as np

# Generate test vectors
vectors = np.random.rand(10, 128).tolist()

# Test Qdrant
from qdrant_client import QdrantClient
qdrant = QdrantClient(host="localhost", port=6334)
qdrant.recreate_collection("test", vectors_config={"size": 128, "distance": "Cosine"})

 

# Test Milvus
from pymilvus import connections, Collection
connections.connect("default", host="localhost", port="19530")

# Test Chroma
import chromadb
chroma = chromadb.HttpClient(host="localhost", port=8000)
collection = chroma.create_collection("test")

# Test pgvector
import psycopg2
conn = psycopg2.connect(
    host="localhost", port=5436, database="vector_db",
    user="vector_user", password="vector_password"
)
```

## 🔍 Troubleshooting

### Port Conflicts
```bash
# Check if ports are already in use
netstat -tulpn | grep :6334
netstat -tulpn | grep :19530
netstat -tulpn | grep :8000
netstat -tulpn | grep :5436
```

### Service Not Starting
```bash
# Check logs for specific service
docker-compose -f vector-databases.yml logs qdrant
docker-compose -f vector-databases.yml logs milvus-standalone
docker-compose -f vector-databases.yml logs chroma
docker-compose -f vector-databases.yml logs pgvector
```

### Reset Everything
```bash
# Stop and remove all containers and volumes
docker-compose -f vector-databases.yml down -v
docker system prune -f

# Restart fresh
docker-compose -f vector-databases.yml up -d
```

## 💡 Best Practices

1. **Start one database at a time** if testing specific features
2. **Monitor resource usage** with `docker stats`
3. **Use health checks** to ensure services are ready before connecting
4. **Backup volumes** before major changes
5. **Check logs** if services fail to start properly

## 🚀 Quick Start Checklist

- [ ] Docker and Docker Compose installed
- [ ] Ports 5436, 6334-6335, 8000-8082, 9000-9001, 9091, 19530, 3002 available
- [ ] Repository cloned and in `vector-database-tools` directory
- [ ] All services started: `docker-compose -f vector-databases.yml up -d`
- [ ] Web interfaces accessible
- [ ] Test connections with your preferred client libraries

**Ready for vector database development and testing!** 🎯