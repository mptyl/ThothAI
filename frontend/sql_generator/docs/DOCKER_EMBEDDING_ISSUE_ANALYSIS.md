# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Docker Issue Analysis: SQL Generator Hung Up

## Executive Summary

The `thoth-sql-generator` service consistently hangs in Docker right after keyword extraction, while it works correctly locally. Analysis identified the root cause as architectural changes in embedding management across `thoth-vdbmanager` versions.

## Problem Description

### Observed Symptoms
- **Ambiente**: Docker container `thoth-sql-generator`
- **When it hangs**: Immediately after keyword extraction
- **Errors in logs**: HTTP 500 with infinite retries while loading the SentenceTransformer model
- **Local environment**: Works correctly without issues

### Key Error Logs
```
INFO:sentence_transformers.SentenceTransformer:Load pretrained SentenceTransformer: paraphrase-multilingual-MiniLM-L12-v2
[2m2025-08-10T21:35:04.219406Z[0m [33m WARN[0m  [33mStatus Code: 500. Retrying..., [1;33mrequest_id[0m[33m: "01K2AYH4XEN3EM91409YS38JQV"[0m
[2m2025-08-10T21:35:04.219482Z[0m [33m WARN[0m  [33mRetry attempt #0. Sleeping 2.750699682s before the next attempt[0m
```

## Identified Root Cause

### Architectural Differences Across Projects

| Project | thoth-vdbmanager Version | Embedding Management | Docker Status |
|----------|--------------------------|-------------------|--------------|
| **thoth_sl** | `v0.2.24` (local dev) | **Library-side** | ✅ Works |
| **thoth_ui/sql_generator** | `>=0.4.0` (PyPI) | **Client-side** | ❌ Hangs |

### Architecture Evolution

1. **Version 0.2.24** (thoth_sl):
   - SentenceTransformer managed internally by the library
   - Models preloaded or managed by the library itself
   - Works in Docker without issues

2. **Version 0.4.0+** (sql_generator):
   - Embedding management moved to the client side
   - Runtime download of SentenceTransformer models
   - Problems in containerized Docker environments

### Technical Failure Point

The hang happens exactly at:
```python
# helpers/main_helpers/main_schema_extraction_from_lsh.py:307
embeddings = embedding_function.encode(to_embed_strings)
```

When the client attempts to download the `paraphrase-multilingual-MiniLM-L12-v2` model inside the Docker container.

## Impact

### Immediate Impacts
- **sql_generator unusable** in Docker
- **Workflow interruptions** for all processes that rely on SQL generation
- **Environment inconsistency** (local works, Docker doesn’t)

### Long-term Impacts
- **Compromised scalability**: cannot deploy to production
- **Complex maintenance**: two different architectures to maintain
- **Degraded developer experience**: different behavior across environments

## Resolution Plan

### Phase 1: Architectural Alignment (Priority: HIGH)

#### Objective
Restore library-side embedding management in `thoth-vdbmanager` to ensure consistency across projects.

#### Project Scope
- **In Scope**: thoth_be, thoth_ui, thoth-vdbmanager library
- **Out of Scope**: thoth_sl (keep as a working reference)

#### Primary Tasks

##### 1.1 thoth-vdbmanager Library Analysis
- [ ] **Version audit**: Compare 0.2.24 vs 0.4.0+ to identify exact changes
- [ ] **Identify API changes**: Document differences in public interfaces
- [ ] **Map dependencies**: Understand how embedding management impacts downstream projects

##### 1.2 Embedding Architecture Redesign
- [ ] **Design pattern**: Define a pattern for centralized embedding management
- [ ] **Backward compatibility**: Ensure changes don’t break existing code
- [ ] **Docker optimization**: Ensure management works properly in containers

##### 1.3 Library Implementation
- [ ] **Core embedding manager**: Create a centralized embedding manager
- [ ] **Model caching**: Implement intelligent caching for SentenceTransformer models
- [ ] **Environment detection**: Automatically handle differences between local/Docker
- [ ] **Error handling**: Robust error handling for model download/load

##### 1.4 Testing and Validation
- [ ] **Unit tests**: Full coverage for the new embedding manager
- [ ] **Integration tests**: Test integration with thoth_be and thoth_ui
- [ ] **Docker tests**: Validate behavior in containers
- [ ] **Performance tests**: Ensure no performance degradation

### Phase 2: Project Migration (Priority: MEDIUM)

#### 2.1 thoth_be Update
- [ ] **Dependency update**: Upgrade to the new thoth-vdbmanager version
- [ ] **Code migration**: Adapt code to use the new API
- [ ] **Configuration**: Update embedding management configuration
- [ ] **Testing**: Validate all existing workflows

#### 2.2 thoth_ui/sql_generator Update
- [ ] **Dependency update**: Update pyproject.toml to the new version
- [ ] **Code refactoring**: Remove client-side embedding management
- [ ] **Docker optimization**: Update the Dockerfile for the new architecture
- [ ] **Testing**: Validate the hung-up issue is fixed

### Phase 3: Stabilization and Monitoring (Priority: LOW)

#### 3.1 Monitoring and Alerting
- [ ] **Health checks**: Implement health checks for embedding management
- [ ] **Logging**: Add detailed logging for debugging
- [ ] **Metrics**: Monitor performance and memory usage

#### 3.2 Documentation
- [ ] **Architecture documentation**: Document the new architecture
- [ ] **Migration guide**: Create a guide for future updates
- [ ] **Best practices**: Document best practices for embedding management

## Time and Resources Estimate

### Estimated Timeline
- **Phase 1**: 2-3 weeks (analysis + library implementation)
- **Phase 2**: 1-2 weeks (project migration)
- **Phase 3**: 1 week (stabilization)

**Total**: 4-6 weeks

### Required Resources
- **Senior developer**: Architecture and core implementation
- **DevOps support**: Docker testing and validation
- **QA testing**: Full workflow validation

## Risks and Mitigations

### Main Risks
1. **Breaking changes**: Library changes may break existing code
2. **Performance degradation**: Centralized management could impact performance
3. **Docker complexity**: Container-specific issues

### Mitigations
1. **Backward compatibility**: Maintain backward-compatible APIs during transition
2. **Performance testing**: Continuous benchmarking during development
3. **Staged rollout**: Gradual deployment to validate each component

## Success Criteria

### Technical Success Criteria
- [ ] **sql_generator runs in Docker** without hanging
- [ ] **Performance maintained** (±5% vs baseline)
- [ ] **Zero breaking changes** for thoth_be and thoth_ui
- [ ] **Test coverage ≥90%** for the new embedding manager

### Operational Success Criteria
- [ ] **Automated deployment** without manual intervention
- [ ] **Active monitoring** across environments
- [ ] **Complete and up-to-date documentation**

## Next Steps

1. **Approval**: Get approval for the plan and prioritization
2. **Resource allocation**: Assign developers and specific timelines
3. **Kick-off**: Start with detailed library analysis
4. **Milestone tracking**: Establish weekly checkpoints to monitor progress

---

**Document prepared by**: Claude Code Analysis  
**Date**: 2025-08-10  
**Version**: 1.0  
**Status**: DRAFT - Pending approval
