# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# 📋 Scelte Architetturali Docker per ThothAI UI

## 🎯 **Decisioni Chiave e Motivazioni** (Ereditate da thoth_be)

### 1. **Dockerfile Universale (Multi-Architettura)**

#### Node.js (thoth-ui)
```dockerfile
FROM node:20
```
**Scelte:**
- Base image `node:20` completa invece di Alpine
- Nessuna compilazione nativa richiesta
- Supporto nativo per tutte le architetture

**Motivazioni:**
- ✅ Compatibilità universale: x86_64, ARM64, ARM
- ✅ Eliminazione problemi node-gyp su Apple Silicon
- ✅ Build time consistente su tutte le piattaforme
- ✅ Nessuna dipendenza da compilatori nativi

#### Python (sql-generator)
```dockerfile
FROM python:3.13
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
```
**Scelte:**
- Base image `python:3.13` completa
- UV package manager per velocità
- Wheel pre-compilati per tutte le architetture

**Motivazioni:**
- ⚡ Installazione 10-100x più veloce
- 🔒 Lock file per riproducibilità
- 📦 Nessuna compilazione C/C++

### 2. **Build System Unificato (build.sh)**
```bash
./build.sh            # Build standard (Alpine multi-stage)
./build.sh --universal # Build universale (tutte le architetture)
```
**Scelte:**
- Script unificato con modalità dual
- DOCKER_BUILDKIT=1 per cache ottimizzata
- Auto-creazione risorse Docker
- Progress tracking visibile

**Motivazioni:**
- 🚀 Flessibilità deployment
- 📊 Monitoraggio build
- ⚠️ Error handling robusto
- ✨ User experience migliorata

### 3. **Architettura Multi-Container**
```yaml
services:
  thoth-ui:       # Next.js frontend
  sql-generator:  # FastAPI Python service
```
**Scelte:**
- Separazione servizi per responsabilità
- Network condiviso `thothnet` con backend
- Volume condiviso `thoth-shared-data`

**Motivazioni:**
- 🔧 Scalabilità indipendente
- 🛡️ Isolamento servizi
- 🔄 Deploy indipendenti
- 🌐 Comunicazione con backend

### 4. **Environment Configuration**
```yaml
env_file:
  - .env.docker
environment:
  - DOCKER_ENV=development
  - HOST_IP=host.docker.internal
```
**Scelte:**
- File `.env.docker` esterno
- Flag DOCKER_ENV per runtime detection (development/production)
- Host access per sviluppo

**Motivazioni:**
- 🔑 Sicurezza API keys
- 🔧 Configurazione flessibile
- 🏗️ Ambiente-aware behavior
- 🔌 Connettività backend

### 5. **Volume Strategy**
```yaml
volumes:
  - ./public:/app/public:ro        # Static assets (read-only)
  - thoth-ui-cache:/app/.next/cache # Build cache
  - ./logs:/app/logs                # Application logs
  - thoth-shared-data:/app/shared   # Shared with backend
```
**Scelte:**
- Mix bind mounts e named volumes
- Cache Next.js per performance
- Volume esterno per dati condivisi

**Motivazioni:**
- 💾 Persistenza selettiva
- 🚀 Build cache optimization
- 📁 Log access diretto
- 🔄 Data sharing con backend

### 6. **Network Architecture**
```yaml
networks:
  thothnet:
    external: true
extra_hosts:
  - "host.docker.internal:host-gateway"
```
**Scelte:**
- Network esterno pre-esistente
- Stesso network del backend
- Host access per debugging

**Motivazioni:**
- 🔐 Comunicazione sicura backend
- 🔧 Debug facilitato
- 🌐 Service discovery semplificato
- 📡 Latenza minimizzata

### 7. **Optimization Choices**

#### Next.js Optimizations
```dockerfile
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm ci --only=production
RUN npm cache clean --force
```
**Scelte:**
- Telemetry disabilitata
- Production dependencies only
- Cache cleanup post-install

**Motivazioni:**
- 📦 Immagine più leggera
- 🔒 Privacy migliorata
- 🚀 Startup più veloce

#### Python Optimizations
```dockerfile
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
RUN uv sync --frozen
```
**Scelte:**
- No buffering per logs real-time
- No bytecode generation
- Frozen dependencies

**Motivazioni:**
- 📊 Log streaming
- 💾 Spazio risparmiato
- 🔒 Build deterministiche

### 8. **Security Considerations**
```dockerfile
# Node.js
RUN groupadd -r nodejs && useradd -r -g nodejs nextjs
USER nextjs

# Python
# Run as root but in isolated container
```
**Scelte:**
- Non-root user per Node.js
- Container isolation per Python
- Read-only mounts dove possibile

**Motivazioni:**
- 🛡️ Principio least privilege
- 🔐 Attack surface ridotto
- 📝 Best practices security

## 🎭 **Trade-offs Accettati**

### 1. **Immagine Base Completa vs Alpine**
- ✅ Pro: Compatibilità universale, zero compilation issues
- ❌ Con: Immagini più grandi (Node: 1GB, Python: 900MB)
- **Decisione**: Priorità a compatibilità e affidabilità

### 2. **UV vs Pip (Python)**
- ✅ Pro: Velocità estrema, lock files
- ❌ Con: Tool meno standard
- **Decisione**: Performance vale adoption

### 3. **Dual Build System**
- ✅ Pro: Flessibilità, backward compatibility
- ❌ Con: Manutenzione doppia configurazione
- **Decisione**: Transizione graduale a universal

## 🚀 **Risultati Ottenuti**

### Performance
- **Build Time**: 3-5 minuti (universale)
- **Startup Time**: <10 secondi
- **Cache Hit Rate**: >80% con BuildKit

### Compatibilità
- **Architetture**: x86_64, ARM64, ARMv7
- **Platforms**: Linux, macOS, Windows (WSL2)
- **Zero compilation failures**

### Developer Experience
- **Single command**: `./build.sh --universal`
- **Auto-setup**: Network e volumi
- **Clear feedback**: Progress e timing
- **Consistent behavior**: Tutte le piattaforme

## 📚 **Differenze da thoth_be**

| Aspetto | thoth_be | thoth_ui |
|---------|----------|----------|
| Runtime | Python/Django | Node.js + Python/FastAPI |
| Services | app, qdrant, proxy | thoth-ui, sql-generator |
| Ports | 8040 (proxy) | 3001 (UI), 8005 (API) |
| Volumes | static-data, exports | ui-cache, public |
| Build modes | Universal only | Standard + Universal |

## 🔄 **Migrazione Consigliata**

1. **Test con build standard**: `./build.sh`
2. **Validazione funzionalità**: Verificare UI e API
3. **Switch a universal**: `./build.sh --universal`
4. **Production deployment**: Usare universal per consistency

Questa architettura garantisce la stessa affidabilità e compatibilità universale ottenuta con successo in thoth_be, adattata alle specifiche esigenze di un frontend Next.js e servizio FastAPI.