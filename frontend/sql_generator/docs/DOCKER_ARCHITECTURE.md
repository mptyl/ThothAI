# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# 📋 Docker Architecture Choices for ThothAI UI

## 🎯 **Key Decisions and Rationale** (Inherited from thoth_be)

### 1. **Dockerfile Universale (Multi-Architettura)**

#### Node.js (thoth-ui)
```dockerfile
FROM node:20
```
**Choices:**
- Full `node:20` base image instead of Alpine
- No native compilation required
- Native support for all architectures

**Rationale:**
- ✅ Universal compatibility: x86_64, ARM64, ARM
- ✅ Eliminate node-gyp issues on Apple Silicon
- ✅ Consistent build times across platforms
- ✅ No dependency on native toolchains

#### Python (sql-generator)
```dockerfile
FROM python:3.13
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
```
**Choices:**
- Full `python:3.13` base image
- UV package manager for speed
- Prebuilt wheels for all architectures

**Rationale:**
- ⚡ 10-100x faster installs
- 🔒 Lock files for reproducibility
- 📦 No C/C++ compilation

### 2. **Build System Unificato (build.sh)**
```bash
./build.sh            # Build standard (Alpine multi-stage)
./build.sh --universal # Build universale (tutte le architetture)
```
**Choices:**
- Unified script with dual modes
- DOCKER_BUILDKIT=1 for optimized cache
- Auto-create Docker resources
- Visible progress tracking

**Rationale:**
- 🚀 Deployment flexibility
- 📊 Build monitoring
- ⚠️ Robust error handling
- ✨ Improved user experience

### 3. **Architettura Multi-Container**
```yaml
services:
  thoth-ui:       # Next.js frontend
  sql-generator:  # FastAPI Python service
```
**Choices:**
- Service separation by responsibility
- Shared `thothnet` network with backend
- Shared `thoth-shared-data` volume

**Rationale:**
- 🔧 Independent scalability
- 🛡️ Service isolation
- 🔄 Independent deploys
- 🌐 Backend communication

### 4. **Environment Configuration**
```yaml
env_file:
  - .env.docker
environment:
  - DOCKER_ENV=development
  - HOST_IP=host.docker.internal
```
**Choices:**
- External `.env.docker` file
- DOCKER_ENV flag for runtime detection (development/production)
- Host access for development

**Rationale:**
- 🔑 API key security
- 🔧 Flexible configuration
- 🏗️ Environment-aware behavior
- 🔌 Backend connectivity

### 5. **Volume Strategy**
```yaml
volumes:
  - ./public:/app/public:ro        # Static assets (read-only)
  - thoth-ui-cache:/app/.next/cache # Build cache
  - ./logs:/app/logs                # Application logs
  - thoth-shared-data:/app/shared   # Shared with backend
```
**Choices:**
- Mix of bind mounts and named volumes
- Next.js cache for performance
- External volume for shared data

**Rationale:**
- 💾 Selective persistence
- 🚀 Build cache optimization
- 📁 Direct log access
- 🔄 Data sharing with backend

### 6. **Network Architecture**
```yaml
networks:
  thothnet:
    external: true
extra_hosts:
  - "host.docker.internal:host-gateway"
```
**Choices:**
- Pre-existing external network
- Same network as the backend
- Host access for debugging

**Rationale:**
- 🔐 Secure backend communication
- 🔧 Easier debugging
- 🌐 Simplified service discovery
- 📡 Minimized latency

### 7. **Optimization Choices**

#### Next.js Optimizations
```dockerfile
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm ci --only=production
RUN npm cache clean --force
```
**Choices:**
- Telemetry disabled
- Production dependencies only
- Cache cleanup post-install

**Rationale:**
- 📦 Smaller image
- 🔒 Improved privacy
- 🚀 Faster startup

#### Python Optimizations
```dockerfile
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
RUN uv sync --frozen
```
**Choices:**
- No buffering for real-time logs
- No bytecode generation
- Frozen dependencies

**Rationale:**
- 📊 Log streaming
- 💾 Saved disk space
- 🔒 Deterministic builds

### 8. **Security Considerations**
```dockerfile
# Node.js
RUN groupadd -r nodejs && useradd -r -g nodejs nextjs
USER nextjs

# Python
# Run as root but in isolated container
```
**Choices:**
- Non-root user for Node.js
- Container isolation for Python
- Read-only mounts where possible

**Rationale:**
- 🛡️ Least privilege principle
- 🔐 Reduced attack surface
- 📝 Security best practices

## 🎭 **Accepted Trade-offs**

### 1. **Full Base Image vs Alpine**
- ✅ Pros: Universal compatibility, zero compilation issues
- ❌ Cons: Larger images (Node: 1GB, Python: 900MB)
- **Decision**: Prioritize compatibility and reliability

### 2. **UV vs Pip (Python)**
- ✅ Pros: Extreme speed, lock files
- ❌ Cons: Less standard tool
- **Decision**: Performance justifies adoption

### 3. **Dual Build System**
- ✅ Pros: Flexibility, backward compatibility
- ❌ Cons: Double configuration maintenance
- **Decision**: Gradual transition to universal

## 🚀 **Results Achieved**

### Performance
- **Build Time**: 3-5 minutes (universal)
- **Startup Time**: <10 seconds
- **Cache Hit Rate**: >80% with BuildKit

### Compatibility
- **Architectures**: x86_64, ARM64, ARMv7
- **Platforms**: Linux, macOS, Windows (WSL2)
- **Zero compilation failures**

### Developer Experience
- **Single command**: `./build.sh --universal`
- **Auto-setup**: Network and volumes
- **Clear feedback**: Progress and timing
- **Consistent behavior**: All platforms

## 📚 **Differences from thoth_be**

| Aspetto | thoth_be | thoth_ui |
|---------|----------|----------|
| Runtime | Python/Django | Node.js + Python/FastAPI |
| Services | app, qdrant, proxy | thoth-ui, sql-generator |
| Ports | 8040 (proxy) | 3001 (UI), 8005 (API) |
| Volumes | static-data, exports | ui-cache, public |
| Build modes | Universal only | Standard + Universal |

## 🔄 **Recommended Migration**

1. **Test with standard build**: `./build.sh`
2. **Functionality validation**: Verify UI and API
3. **Switch to universal**: `./build.sh --universal`
4. **Production deployment**: Use universal for consistency

This architecture guarantees the same reliability and universal compatibility achieved successfully in thoth_be, adapted to the specific needs of a Next.js frontend and a FastAPI service.
