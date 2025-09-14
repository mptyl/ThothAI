# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Migration Plan: Centralized Embedding Management

## Objective

Restore library-side embedding management in `thoth-vdbmanager` to resolve Docker issues and ensure architectural consistency across `thoth_be` and `thoth_ui`.

## Target Architecture

### Design Principles

1. **Centralization**: Embeddings are managed entirely by the `thoth-vdbmanager` library
2. **Docker Compatibility**: Robust operation in containerized environments
3. **Performance**: Intelligent caching and lazy model loading
4. **Backward Compatibility**: Transparent transition for existing projects

### Schema Architetturale

```
┌─────────────────────────────────────────┐
│           Client Applications           │
│  ┌─────────────┐    ┌─────────────┐    │
│  │  thoth_be   │    │  thoth_ui   │    │
│  └─────────────┘    └─────────────┘    │
└─────────────┬───────────────────────────┘
              │ Simple API Calls
              ▼
┌─────────────────────────────────────────┐
│         thoth-vdbmanager v2.0           │
│  ┌─────────────────────────────────────┐ │
│  │     Embedding Manager Core         │ │
│  │  ┌─────────────┐ ┌─────────────┐  │ │
│  │  │Model Cache  │ │Environment  │  │ │
│  │  │   Manager   │ │  Detector   │  │ │
│  │  └─────────────┘ └─────────────┘  │ │
│  │  ┌─────────────┐ ┌─────────────┐  │ │
│  │  │SentenceXfmr │ │Error Handler│  │ │
│  │  │   Factory   │ │   & Retry   │  │ │
│  │  └─────────────┘ └─────────────┘  │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Phase 1: Library Design and Implementation

### 1.1 Current State Analysis

#### Task: Version Audit
```bash
# Comparazione delle versioni
pip show thoth-vdbmanager==0.2.24
pip show thoth-vdbmanager==0.4.0

# Analisi delle differenze
git clone https://github.com/mptyl/thoth_vdbmanager
cd thoth_vdbmanager
git diff v0.2.24..v0.4.0 --name-only
```

#### Deliverables
- [ ] **API comparison document** across versions
- [ ] **List of identified breaking changes**
- [ ] **Dependency map** currently used by projects

### 1.2 New Embedding Manager Design

#### Core Components

##### EmbeddingManager Class
```python
# Target architecture pseudocode
class EmbeddingManager:
    """Central manager for all embedding operations."""
    
    def __init__(self, config: EmbeddingConfig):
        self.model_cache = ModelCache()
        self.env_detector = EnvironmentDetector()
        self.error_handler = RetryHandler()
    
    def encode(self, texts: List[str], model: str = "default") -> np.ndarray:
        """Main encoding interface - hides model complexity."""
        
    def get_model(self, model_name: str) -> SentenceTransformer:
        """Lazy loading with intelligent caching."""
        
    def preload_models(self, models: List[str]) -> None:
        """Preload for Docker environments."""
```

##### Environment Detection
```python
class EnvironmentDetector:
    """Detects execution environment and adapts behavior."""
    
    def is_docker(self) -> bool:
        """Detects if running in a Docker container."""
        
    def get_cache_strategy(self) -> CacheStrategy:
        """Cache strategy based on environment."""
        
    def get_download_strategy(self) -> DownloadStrategy:
        """Model download strategy based on environment."""
```

#### Task di Implementazione
- [ ] **Design public interfaces** for the new EmbeddingManager
- [ ] **Implement model caching** with Docker/local strategies
- [ ] **Create a robust retry system** for download failures
- [ ] **Implement automatic environment detection**

### 1.3 Docker Optimization Strategy

#### Problems to Solve
1. **Runtime downloads**: Avoid downloading models at runtime in Docker
2. **Network isolation**: Handle connectivity issues in containers
3. **Memory management**: Optimize memory usage for large models

#### Proposed Solutions

##### Pre-download Strategy
```python
class DockerModelManager:
    """Manager specific to Docker environments."""
    
    def preload_common_models(self) -> None:
        """Preload the most common models during build."""
        common_models = [
            "sentence-transformers/all-MiniLM-L6-v2",
            "paraphrase-multilingual-MiniLM-L12-v2"
        ]
        for model in common_models:
            self._download_and_cache(model)
    
    def get_model_with_fallback(self, model_name: str) -> SentenceTransformer:
        """Fallback strategy for unavailable models."""
```

##### Dockerfile Integration
```dockerfile
# Example of library Dockerfile integration
RUN pip install thoth-vdbmanager[qdrant]==2.0.0
RUN python -c "from thoth_vdbmanager import EmbeddingManager; EmbeddingManager.preload_common_models()"
```

#### Task di Implementazione
- [ ] **Create DockerModelManager** for container-specific handling
- [ ] **Implement pre-download** for common models
- [ ] **Create fallback strategies** for unavailable models
- [ ] **Optimize memory footprint** of loaded models

## Phase 2: Project Migration

### 2.1 thoth_be Migration

#### Current Situation
```python
# Attuale in thoth_be (problematico)
from sentence_transformers import SentenceTransformer
embedding_function = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
embeddings = embedding_function.encode(texts)
```

#### Target Migration
```python
# Target con nuova libreria
from thoth_vdbmanager import EmbeddingManager
embedding_manager = EmbeddingManager.get_instance()
embeddings = embedding_manager.encode(texts, model="multilingual-mini")
```

#### Migration Tasks
- [ ] **Identify all usages** of SentenceTransformer in thoth_be
- [ ] **Create a compatibility wrapper** for gradual transition
- [ ] **Update requirements** and dependency management
- [ ] **Test all existing workflows**

### 2.2 thoth_ui/sql_generator Migration

#### Current Situation
```python
# Attuale in sql_generator (problematico)
from helpers.setups import build_embedding_function
embedding_function = build_embedding_function()
embeddings = embedding_function.encode(to_embed_strings)
```

#### Target Migration
```python
# Target con nuova libreria
from thoth_vdbmanager import EmbeddingManager
embedding_manager = EmbeddingManager.get_instance()
embeddings = embedding_manager.encode(to_embed_strings)
```

#### Migration Tasks
- [ ] **Remove SafeSentenceTransformer** custom class
- [ ] **Update helpers/setups.py** to use the new API
- [ ] **Modify main_schema_extraction_from_lsh.py** for the new handling
- [ ] **Update pyproject.toml** with the new library version
- [ ] **Test the fix** for the Docker hang

### 2.3 Backward Compatibility Strategy

#### Compatibility Layer
```python
# Temporary compatibility for a gradual transition
class LegacyEmbeddingAdapter:
    """Adapter to maintain compatibility with existing APIs."""
    
    def __init__(self, model_name: str):
        self.embedding_manager = EmbeddingManager.get_instance()
        self.model_name = model_name
    
    def encode(self, texts, **kwargs):
        """Preserves the existing interface."""
        return self.embedding_manager.encode(texts, model=self.model_name, **kwargs)
```

## Phase 3: Testing and Validation

### 3.1 Test Strategy

#### Unit Tests
```python
# Tests for the new EmbeddingManager
class TestEmbeddingManager:
    def test_model_caching(self):
        """Verify models are cached correctly."""
        
    def test_docker_environment_detection(self):
        """Verify Docker environment detection."""
        
    def test_fallback_strategies(self):
        """Verify fallback strategies for errors."""
```

#### Integration Tests
```python
# Integration tests with projects
class TestThothAIBeIntegration:
    def test_embedding_workflow_complete(self):
        """Test the complete thoth_be workflow with new embeddings."""
        
class TestThothAIUiIntegration:
    def test_sql_generator_no_hang(self):
        """Verify sql_generator no longer hangs."""
```

#### Docker Tests
```bash
# Script for automated Docker tests
#!/bin/bash
docker-compose build sql-generator
docker-compose up -d sql-generator
# Test API call that previously caused a hang
curl -X POST http://localhost:8005/generate-sql \
  -H "Content-Type: application/json" \
  -d '{"question": "test question", "workspace_id": 4}'
```

### 3.2 Performance Validation

#### Benchmark Setup
- [ ] **Baseline measurements** with current working version
- [ ] **Performance tests** for encoding operations
- [ ] **Memory usage profiling** for loaded models
- [ ] **Startup time comparison** between old and new architectures

## Phase 4: Deployment and Rollout

### 4.1 Staged Rollout Strategy

#### Stage 1: Library Release
1. **Release thoth-vdbmanager v2.0** with the new EmbeddingManager
2. **Backward compatibility** guaranteed via adapter layer
3. **Extensive testing** in staging environments

#### Stage 2: thoth_be Migration
1. **Deploy thoth_be** with the new library to staging
2. **Full validation** of all workflows
3. **Production rollout** with rollback plan

#### Stage 3: thoth_ui Migration  
1. **Deploy sql_generator** with Docker fix
2. **Validate** the hang is resolved
3. **Monitor production** for stability

### 4.2 Rollback Plan

#### Preparation
- [ ] **Backup current working versions**
- [ ] **Automated rollback scripts**
- [ ] **Monitoring alerts** to detect issues quickly

#### Trigger Conditions
- Performance degradation >20%
- Failure rate >5% on critical endpoints  
- Docker hang still present
- Memory usage increase >50%

## Timeline and Milestones

### Milestone 1: Library Foundation (Weeks 1-2)
- [ ] Completed analysis of current versions
- [ ] Approved design of the new EmbeddingManager
- [ ] Core model caching implemented
- [ ] Environment detection working

### Milestone 2: Docker Optimization (Weeks 2-3)
- [ ] DockerModelManager implemented
- [ ] Pre-download strategy tested
- [ ] Memory optimization completed
- [ ] Fallback strategies validated

### Milestone 3: Project Migration (Weeks 3-4)
- [ ] thoth_be migration completed
- [ ] thoth_ui/sql_generator migration completed
- [ ] Backward compatibility layer validated
- [ ] Integration tests passing at 100%

### Milestone 4: Production Ready (Weeks 4-5)
- [ ] Performance validation passed
- [ ] Docker tests fully green
- [ ] Staging deployment successful
- [ ] Monitoring and alerting configured

### Milestone 5: Production Rollout (Week 6)
- [ ] Production deployment completed
- [ ] Hang issue resolved definitively
- [ ] Performance baseline maintained
- [ ] Documentation updated

## Success Metrics

### Technical KPIs
- **Docker hang**: 0 occurrences after deployment
- **Performance impact**: <±5% vs baseline
- **Memory usage**: <+20% for the new caching
- **Test coverage**: >90% for new code

### Operational KPIs  
- **Deployment time**: <30 minutes for full rollout
- **Rollback time**: <5 minutes if needed
- **Zero downtime**: During migration
- **Developer satisfaction**: Positive feedback on new API

## Risk Management

### High Risk: Breaking Changes
- **Mitigation**: Extensive backward compatibility testing
- **Contingency**: Gradual migration with feature flags

### Medium Risk: Performance Degradation
- **Mitigation**: Continuous benchmarking during development
- **Contingency**: Dedicated performance tuning

### Low Risk: Docker Complexity
- **Mitigation**: Docker-specific testing environment
- **Contingency**: Fallback to non-containerized deployment

---

**Plan prepared by**: Claude Code Analysis  
**Date**: 2025-08-10  
**Version**: 1.0  
**Status**: READY FOR REVIEW
