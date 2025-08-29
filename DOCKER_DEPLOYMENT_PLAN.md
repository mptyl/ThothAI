# Docker Deployment Plan - Progetto Thoth

## Executive Summary
Piano operativo per la creazione di un sistema di deployment Docker professionale per Thoth, seguendo le best practices dei progetti enterprise open source.

**Obiettivo**: Pubblicare un'immagine Docker ottimizzata su Docker Hub con sistema di configurazione user-friendly.

**Approccio**: Multi-stage build, configurazione via environment, deployment con Docker Compose.

---

## Fase 1: Ottimizzazione Docker Image
**Timeline**: 2-3 ore  
**Priorità**: ALTA

### 1.1 Dockerfile Multi-Stage Build
- [ ] Creare Dockerfile ottimizzato con build multi-stage
- [ ] Implementare non-root user per sicurezza
- [ ] Aggiungere health check endpoint
- [ ] Configurare layer caching ottimale

```dockerfile
# Esempio struttura
FROM python:3.11-slim as builder
# Build dependencies

FROM python:3.11-slim as runtime
# Runtime minimal
USER thoth
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8000/health || exit 1
```

### 1.2 Riduzione Dimensioni
- [ ] Analizzare dimensione attuale con `docker images`
- [ ] Rimuovere dipendenze non necessarie
- [ ] Utilizzare alpine images dove possibile
- [ ] Target: < 500MB per immagine finale

### 1.3 Security Hardening
- [ ] Scan vulnerabilità con `docker scout`
- [ ] Implementare `.dockerignore` completo
- [ ] Configurare security policies
- [ ] Non esporre secrets in layers

---

## Fase 2: Sistema di Configurazione
**Timeline**: 2 ore  
**Priorità**: ALTA

### 2.1 Docker Compose Setup
- [ ] Creare `docker-compose.yml` production-ready
- [ ] Configurare networking isolato
- [ ] Implementare volume management
- [ ] Definire restart policies

```yaml
# Struttura base
version: '3.8'
services:
  thoth:
    image: marcopancotti/thoth:latest
    env_file: .env
    volumes:
      - thoth_data:/app/data
    restart: unless-stopped
    networks:
      - thoth_network
```

### 2.2 Environment Variables
- [ ] Creare `.env.example` con tutte le variabili
- [ ] Documentare ogni variabile
- [ ] Implementare validazione al startup
- [ ] Supportare default values sensati

```bash
# .env.example
# OpenAI Configuration
OPENAI_API_KEY=sk-...

# Anthropic Configuration  
ANTHROPIC_API_KEY=sk-ant-...

# Google Configuration
GOOGLE_API_KEY=...

# Application Settings
LOG_LEVEL=INFO
PORT=8000
```

### 2.3 Secrets Management
- [ ] Implementare Docker secrets per produzione
- [ ] Creare script per inizializzazione secrets
- [ ] Documentare best practices
- [ ] Opzionale: supporto per HashiCorp Vault

---

## Fase 3: Scripts di Deployment
**Timeline**: 3 ore  
**Priorità**: MEDIA

### 3.1 Install Script Linux/Mac
- [ ] Creare `scripts/install.sh`
- [ ] Verificare prerequisiti (Docker, Docker Compose)
- [ ] Configurazione guidata interattiva
- [ ] Validazione API keys

```bash
#!/bin/bash
# Struttura base
check_prerequisites() {
    command -v docker >/dev/null 2>&1 || { echo "Docker required"; exit 1; }
}

configure_environment() {
    read -p "Enter OpenAI API Key: " OPENAI_KEY
    # Validate and save
}

deploy_application() {
    docker compose up -d
}
```

### 3.2 Install Script Windows
- [ ] Creare `scripts/install.bat`
- [ ] Adattare logica per PowerShell
- [ ] Gestire permessi amministratore
- [ ] Test su Windows 10/11

### 3.3 Update/Rollback Scripts
- [ ] Script per aggiornamenti `update.sh`
- [ ] Meccanismo di rollback automatico
- [ ] Backup configurazione prima di update
- [ ] Logging dettagliato operazioni

---

## Fase 4: Pubblicazione Docker Hub
**Timeline**: 2 ore  
**Priorità**: ALTA

### 4.1 Docker Hub Setup
- [ ] Creare repository `marcopancotti/thoth`
- [ ] Configurare description e README
- [ ] Setup automated builds
- [ ] Configurare webhooks

### 4.2 GitHub Actions CI/CD
- [ ] Creare `.github/workflows/docker-publish.yml`
- [ ] Build multi-architettura (amd64, arm64)
- [ ] Semantic versioning automatico
- [ ] Security scanning pre-push

```yaml
# Workflow structure
name: Docker Build and Push
on:
  push:
    tags: ['v*']
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: docker/setup-buildx-action@v2
      - uses: docker/build-push-action@v4
        with:
          platforms: linux/amd64,linux/arm64
          tags: marcopancotti/thoth:latest
```

### 4.3 Versioning Strategy
- [ ] Implementare semantic versioning
- [ ] Tag: `latest`, `v1.0.0`, `v1.0`, `v1`
- [ ] Changelog automatico
- [ ] Release notes generation

---

## Fase 5: Documentazione
**Timeline**: 2 ore  
**Priorità**: MEDIA

### 5.1 README Docker Hub
- [ ] Quick start guide
- [ ] Configuration reference
- [ ] Troubleshooting section
- [ ] Examples e use cases

### 5.2 Deployment Guide
- [ ] `docs/DEPLOYMENT.md` dettagliato
- [ ] Video tutorial (opzionale)
- [ ] FAQ section
- [ ] Migration guide da versioni precedenti

### 5.3 API Documentation
- [ ] Documentare tutti gli endpoints
- [ ] Swagger/OpenAPI spec
- [ ] Postman collection
- [ ] Rate limiting info

---

## Testing Checklist

### Pre-Release Tests
- [ ] Fresh install su Ubuntu 22.04
- [ ] Fresh install su macOS
- [ ] Fresh install su Windows 11
- [ ] Upgrade da versione precedente
- [ ] Rollback test
- [ ] Performance benchmark
- [ ] Security scan completo
- [ ] Multi-arch compatibility (arm64)

### Validation Criteria
- [ ] Startup time < 30 secondi
- [ ] Memory usage < 512MB idle
- [ ] Tutte le API keys validate correttamente
- [ ] Health check risponde 200 OK
- [ ] Logs strutturati funzionanti
- [ ] Volumes persistenti verificati

---

## Timeline Complessiva

| Fase | Durata | Priorità | Dipendenze |
|------|--------|----------|------------|
| Ottimizzazione Docker | 3h | ALTA | - |
| Configurazione | 2h | ALTA | Fase 1 |
| Scripts Deployment | 3h | MEDIA | Fase 2 |
| Pubblicazione | 2h | ALTA | Fase 1,2 |
| Documentazione | 2h | MEDIA | Tutte |
| Testing | 2h | ALTA | Tutte |

**Tempo totale stimato**: 14 ore

---

## Security Considerations

1. **Secrets Management**
   - Mai committare API keys
   - Usare .gitignore appropriato
   - Rotazione keys periodica

2. **Container Security**
   - Non-root user sempre
   - Minimal base images
   - Regular security updates

3. **Network Security**
   - Isolamento network Docker
   - Rate limiting APIs
   - HTTPS only in produzione

---

## Rollback Plan

In caso di problemi durante deployment:

1. **Backup Current State**
   ```bash
   docker compose down
   cp -r ./data ./data.backup
   cp .env .env.backup
   ```

2. **Restore Previous Version**
   ```bash
   docker pull marcopancotti/thoth:previous-version
   docker compose up -d
   ```

3. **Verify Restoration**
   ```bash
   docker compose ps
   docker compose logs --tail=50
   ```

---

## Next Steps

1. **Domani mattina**: Iniziare con Fase 1 (Dockerfile optimization)
2. **Review**: Code review dopo ogni fase
3. **Test**: Testing continuo durante sviluppo
4. **Deploy**: Prima release su Docker Hub entro 2 giorni

---

## Commands Reference

```bash
# Build locale
docker build -t thoth:local .

# Run con compose
docker compose up -d

# Check logs
docker compose logs -f

# Update image
docker compose pull
docker compose up -d

# Cleanup
docker system prune -a
```

---

## Notes

- Mantenere compatibilità con architetture ARM per Raspberry Pi
- Considerare Kubernetes manifest per future espansioni
- Valutare integrazione con cloud providers (AWS, GCP, Azure)

---

*Last Updated: 2025-08-29*  
*Author: Marco Pancotti*  
*Project: Thoth*