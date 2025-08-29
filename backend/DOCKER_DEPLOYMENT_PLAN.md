# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache 2.0 License.
# See the LICENSE.md file in the project root for full license information.

# Docker Deployment Plan for ThothAI

## Executive Summary

This document outlines the comprehensive plan for dockerizing ThothAI as a production-ready Docker image that can be easily deployed with minimal configuration. The deployment will include a pre-configured California Schools demo database with vector embeddings and an optional BIRD database import feature.

## 1. Docker Image Architecture

### 1.1 Multi-Stage Build Strategy
```dockerfile
# Stage 1: Builder (Python dependencies)
# Stage 2: Node.js builder (if frontend assets needed)
# Stage 3: Runtime image (minimal production image)
```

### 1.2 Image Components
- **Base Image**: `python:3.12-slim` for minimal footprint
- **Pre-installed Services**:
  - Django application (thoth-be)
  - Nginx for reverse proxy
  - Supervisor for process management
  - Health check endpoints
- **Embedded Databases** (for demo):
  - SQLite for California Schools
  - Pre-computed vector embeddings

### 1.3 External Services (via Docker Compose)
- PostgreSQL (production database)
- Qdrant (vector database)
- Redis (caching/queue management)

## 2. Configuration Management

### 2.1 Required Environment Variables
```yaml
# Mandatory at first run
OPENAI_API_KEY: "Required for embeddings"
LLM_PROVIDER: "openai|anthropic|gemini|groq"
LLM_API_KEY: "API key for chosen provider"

# Optional with defaults
DJANGO_SECRET_KEY: "auto-generated if not provided"
POSTGRES_PASSWORD: "auto-generated if not provided"
QDRANT_API_KEY: "auto-generated if not provided"
ADMIN_EMAIL: "admin@example.com"
ADMIN_PASSWORD: "auto-generated and displayed"
```

### 2.2 Configuration Wizard
```bash
# First-time setup with interactive wizard
docker run -it thoth/thoth-ai:latest setup

# Or with environment file
docker run --env-file .env thoth/thoth-ai:latest
```

## 3. California Schools Demo Setup

### 3.1 Pre-configured Components
- **SQL Database**: 
  - Complete California Schools SQLite database
  - Table and column descriptions
  - Example queries and results
  
- **Vector Database**:
  - Pre-computed embeddings for all tables/columns
  - Example question-SQL pairs
  - Semantic hints for query generation
  
- **LSH Indexes**:
  - Pre-built LSH for fast similarity search
  - Optimized for California Schools schema

### 3.2 Data Preparation Pipeline
```python
# Build script to prepare demo data
1. Load California Schools database
2. Generate table/column descriptions
3. Create embeddings using OpenAI
4. Build LSH indexes
5. Export as Docker volume data
```

## 4. BIRD Database Import Feature

### 4.1 Import Mechanism
```bash
# Import BIRD database
docker exec thoth-ai import-bird \
  --sqlite-file /data/bird.db \
  --name "BIRD Database" \
  --create-workspace
```

### 4.2 Automated Setup Process
1. **Database Import**:
   - Validate SQLite file
   - Create PostgreSQL schema
   - Import data with proper typing
   
2. **Metadata Generation**:
   - Extract schema information
   - Generate table descriptions
   - Create column descriptions
   
3. **Vector Setup**:
   - Create Qdrant collection
   - Generate embeddings for metadata
   - Build LSH indexes
   
4. **Workspace Creation**:
   - Create new workspace
   - Link SQL and vector databases
   - Configure AI agents

## 5. Deployment Configurations

### 5.1 Docker Compose Production
```yaml
version: '3.8'

services:
  thoth-ai:
    image: thoth/thoth-ai:latest
    environment:
      - DEPLOYMENT_MODE=production
    volumes:
      - thoth-data:/app/data
      - thoth-media:/app/media
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - postgres
      - qdrant
      - redis

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres-data:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant-data:/qdrant/storage

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
```

### 5.2 Single Container Mode
```bash
# All-in-one container for testing/development
docker run -d \
  -p 8080:80 \
  -v thoth-data:/app/data \
  --env-file .env \
  thoth/thoth-ai:latest --standalone
```

## 6. Build and Release Pipeline

### 6.1 GitHub Actions Workflow
```yaml
name: Build and Push Docker Image

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    steps:
      - Build multi-arch images (amd64, arm64)
      - Run security scanning
      - Push to Docker Hub
      - Update latest tag
```

### 6.2 Version Strategy
- **Tags**: `latest`, `v1.0.0`, `v1.0`, `v1`
- **Development**: `dev`, `nightly`
- **LTS Versions**: `v1.0-lts` with 6-month support

## 7. Installation Documentation

### 7.1 Quick Start Guide
```bash
# 1. Download docker-compose.yml
curl -O https://raw.githubusercontent.com/thoth-ai/thoth/main/docker-compose.yml

# 2. Create configuration
cat > .env << EOF
OPENAI_API_KEY=your-key-here
LLM_PROVIDER=openai
LLM_API_KEY=your-key-here
EOF

# 3. Start services
docker-compose up -d

# 4. Access application
open http://localhost:8080
```

### 7.2 Production Deployment
- SSL/TLS configuration with Let's Encrypt
- Backup and restore procedures
- Monitoring integration (Prometheus/Grafana)
- Log aggregation setup

## 8. Security Considerations

### 8.1 Container Security
- Non-root user execution
- Read-only root filesystem
- Minimal attack surface
- Regular security updates

### 8.2 Secrets Management
- Support for Docker secrets
- HashiCorp Vault integration
- Encrypted environment variables
- API key rotation support

## 9. Health Monitoring

### 9.1 Health Check Endpoints
- `/health/` - Overall system health
- `/health/db/` - Database connectivity
- `/health/vector/` - Vector database status
- `/health/ai/` - AI service availability

### 9.2 Metrics Export
- Prometheus metrics at `/metrics`
- Custom dashboards for Grafana
- Alert rules for common issues

## 10. Migration Path

### 10.1 From Development to Docker
```bash
# Export existing data
python manage.py dumpdata > backup.json

# Import to Docker
docker exec thoth-ai python manage.py loaddata backup.json
```

### 10.2 Version Upgrades
```bash
# Backup before upgrade
docker exec thoth-ai backup --full

# Pull new version
docker-compose pull

# Run migrations
docker-compose run thoth-ai migrate

# Restart services
docker-compose up -d
```

## 11. Implementation Timeline

### Phase 1: Core Dockerization (Week 1-2)
- [ ] Create multi-stage Dockerfile
- [ ] Implement configuration management
- [ ] Set up build pipeline
- [ ] Create docker-compose configurations

### Phase 2: Demo Data Preparation (Week 2-3)
- [ ] Prepare California Schools data
- [ ] Generate embeddings and LSH
- [ ] Package as Docker volumes
- [ ] Create initialization scripts

### Phase 3: Import Features (Week 3-4)
- [ ] Implement BIRD import command
- [ mysteries database import
- [ ] Automated workspace creation
- [ ] Testing and validation

### Phase 4: Production Readiness (Week 4-5)
- [ ] Security hardening
- [ ] Performance optimization
- [ ] Documentation completion
- [ ] Release preparation

### Phase 5: Launch and Support (Week 5-6)
- [ ] Docker Hub publication
- [ ] Community documentation
- [ ] Support channels setup
- [ ] Feedback incorporation

## 12. Testing Strategy

### 12.1 Container Testing
- Unit tests within container
- Integration tests with external services
- Performance benchmarks
- Security scanning

### 12.2 Deployment Testing
- Single container deployment
- Multi-container orchestration
- Kubernetes deployment
- Cloud provider specific tests (AWS, GCP, Azure)

## 13. Documentation Deliverables

### 13.1 User Documentation
- Installation guide
- Configuration reference
- Troubleshooting guide
- FAQ section

### 13.2 Administrator Documentation
- Deployment best practices
- Backup and recovery procedures
- Performance tuning guide
- Security hardening checklist

### 13.3 Developer Documentation
- Build process documentation
- Contributing guidelines
- API documentation
- Plugin development guide

## 14. Support and Maintenance

### 14.1 Support Channels
- GitHub Issues for bug reports
- Discord for community support
- Commercial support options
- Documentation wiki

### 14.2 Update Policy
- Monthly security updates
- Quarterly feature releases
- LTS versions every 6 months
- Breaking changes with major versions only

## 15. Success Metrics

### 15.1 Deployment Metrics
- Time to first query < 5 minutes
- Container size < 500MB
- Memory usage < 512MB (idle)
- Startup time < 30 seconds

### 15.2 User Experience Metrics
- Installation success rate > 95%
- Configuration errors < 5%
- User satisfaction > 4.5/5
- Documentation completeness > 90%

## Conclusion

This comprehensive dockerization plan transforms ThothAI into a production-ready, easily deployable solution. The inclusion of pre-configured demo data (California Schools) and automated import features (BIRD) significantly reduces the barrier to entry while maintaining flexibility for production deployments.

The phased implementation approach ensures quality at each stage while delivering value incrementally. With proper execution, ThothAI will become a turnkey solution for natural language database querying that can be deployed in minutes rather than hours.