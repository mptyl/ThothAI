# Dependency Environment Merge Plan for Thoth UI

## Executive Summary

This document outlines the strategy for merging the separate dependency environments of the main Thoth UI project and its sql_generator submodule into a single, unified environment managed by UV.

## Current Architecture

### Project Structure
```
thoth_ui/                       # Main Django project
├── .venv/                      # Main virtual environment
├── pyproject.toml              # Main project dependencies
├── uv.lock                     # Main lock file
└── sql_generator/              # FastAPI microservice
    ├── venv/                   # Separate virtual environment
    ├── pyproject.toml          # Separate dependencies
    └── uv.lock                 # Separate lock file
```

### Why Separate Environments Were Created

1. **Microservice Independence**: sql_generator was designed as a standalone FastAPI service
2. **Version Isolation**: Prevented dependency conflicts during development
3. **Deployment Flexibility**: Could be containerized and deployed separately
4. **Development Speed**: Allowed parallel development without dependency coordination

## Dependency Analysis

### Version Conflicts Identified

| Package | Main Project | sql_generator | Resolution Strategy |
|---------|--------------|---------------|-------------------|
| fastapi | >=0.100.0 | >=0.116.1 | Use >=0.116.1 (newer) |
| uvicorn | >=0.20.0 | >=0.35.0 | Use >=0.35.0 (newer) |
| logfire | >=0.60.0 | >=2.7.0 | Use >=2.7.0 (newer major version) |
| httpx | >=0.25.0 | >=0.28.1 | Use >=0.28.1 (newer) |
| pydantic-ai | >=0.7.2 | >=0.0.50 | Use >=0.7.2 (main is newer) |
| thoth-dbmanager | ==0.5.3 | >=0.5.3 | Use >=0.5.3 (flexible) |
| thoth-qdrant | >=0.1.3 | >=0.1.3 | Keep >=0.1.3 (same) |

### Unique sql_generator Dependencies
- `python-multipart>=0.0.20` - Required for FastAPI file uploads
- `annotated-types>=0.6.0` - Pydantic type annotations
- `pathlib>=1.0.1` - Path operations (may be redundant in Python 3.12+)

### Python Version Requirements
- Main project: `>=3.12`
- sql_generator: `>=3.13`
- **Resolution**: Keep `>=3.12` for broader compatibility

## Merge Strategy

### Phase 1: Preparation (Non-destructive)

1. **Backup Current State**
   ```bash
   cp pyproject.toml pyproject.toml.backup
   cp -r sql_generator/pyproject.toml sql_generator/pyproject.toml.backup
   ```

2. **Document Current Working Commands**
   - Main project: `uv run python manage.py runserver`
   - sql_generator: `cd sql_generator && uvicorn main:app --port 8001`

### Phase 2: Dependency Consolidation

1. **Update Main pyproject.toml**
   ```toml
   # Updated versions based on analysis
   dependencies = [
       # ... existing dependencies ...
       
       # API Server (updated versions)
       "fastapi>=0.116.1",     # Updated from 0.100.0
       "uvicorn>=0.35.0",      # Updated from 0.20.0
       
       # Monitoring (check compatibility)
       "logfire>=2.7.0",       # Updated from 0.60.0
       
       # HTTP Client
       "httpx>=0.28.1",        # Updated from 0.25.0
       
       # New additions from sql_generator
       "python-multipart>=0.0.20",
       "annotated-types>=0.6.0",
   ]
   ```

2. **Update Package Discovery**
   ```toml
   [tool.setuptools.packages.find]
   where = ["."]
   include = ["thoth_core*", "thoth_ai_backend*", "Thoth*", "sql_generator*"]
   exclude = ["tests*", "test_*", "node_modules*"]
   ```

### Phase 3: Code Adjustments

1. **Update sql_generator Imports**
   - Change relative imports to absolute imports
   - Example: `from helpers.db_info import ...` → `from sql_generator.helpers.db_info import ...`

2. **Update Launch Scripts**
   ```python
   # New launch method from project root
   # In a new file: run_sql_generator.py
   import uvicorn
   from sql_generator.main import app
   
   if __name__ == "__main__":
       uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
   ```

3. **Environment Variable Paths**
   - Update any hardcoded paths in sql_generator
   - Ensure .env files are read from project root

### Phase 4: Migration Execution

1. **Step-by-step Migration**
   ```bash
   # 1. Update main pyproject.toml with consolidated dependencies
   
   # 2. Remove sql_generator's separate environment
   rm -rf sql_generator/venv
   rm sql_generator/pyproject.toml
   rm sql_generator/uv.lock
   
   # 3. Sync dependencies from project root
   uv sync
   
   # 4. Test imports
   uv run python -c "from sql_generator.main import app; print('✅ Import successful')"
   
   # 5. Test sql_generator launch
   uv run uvicorn sql_generator.main:app --port 8001
   ```

### Phase 5: Verification

1. **Test Suite Execution**
   ```bash
   # Django tests
   uv run python manage.py test
   
   # sql_generator tests
   uv run pytest sql_generator/tests/
   ```

2. **Integration Testing**
   - Verify Django can call sql_generator endpoints
   - Test database connections
   - Verify Qdrant integration

## Benefits of Merged Environment

### Development Benefits
1. **Single dependency update point**: One `pyproject.toml` to maintain
2. **Consistent versions**: No surprise conflicts during integration
3. **Faster CI/CD**: Single environment to build and cache
4. **Simplified debugging**: One virtual environment to inspect

### Operational Benefits
1. **Reduced Docker image size**: Single set of dependencies
2. **Simpler deployment**: One requirements file for production
3. **Better dependency resolution**: UV handles all conflicts at once
4. **Easier onboarding**: New developers need only one setup

## Risk Mitigation

### Potential Issues and Solutions

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Version conflict breaks functionality | Medium | High | Test thoroughly, keep backups |
| Import errors after merge | High | Low | Update imports systematically |
| Performance degradation | Low | Medium | Profile before/after |
| Missing dependencies | Low | Low | Compare pip list outputs |

### Rollback Plan

If issues arise:
1. Restore backup `pyproject.toml` files
2. Recreate sql_generator virtual environment
3. Re-install sql_generator dependencies separately
4. Document specific conflict for future resolution

## Alternative Approaches Considered

### 1. Keep Separate, Use Workspace (Rejected)
- **Pros**: Complete isolation, independent versioning
- **Cons**: Complex dependency coordination, duplicate packages

### 2. Docker Compose Only (Rejected)
- **Pros**: Perfect isolation, production-like
- **Cons**: Slower development cycle, resource intensive

### 3. Monorepo with Multiple pyproject.toml (Rejected)
- **Pros**: Some isolation, shared common deps
- **Cons**: UV doesn't fully support this pattern yet

## Implementation Timeline

### Day 1: Preparation
- [ ] Create backups
- [ ] Document current state
- [ ] Review and update this plan

### Day 2: Execution
- [ ] Update pyproject.toml
- [ ] Remove sql_generator environment
- [ ] Run uv sync
- [ ] Fix import issues

### Day 3: Validation
- [ ] Run all tests
- [ ] Test integration points
- [ ] Performance verification
- [ ] Update documentation

## Success Criteria

The merge is considered successful when:
1. ✅ All tests pass in both Django and sql_generator
2. ✅ sql_generator can be launched with `uv run`
3. ✅ No duplicate dependencies in virtual environment
4. ✅ Django can successfully call sql_generator endpoints
5. ✅ Development workflow is simplified
6. ✅ CI/CD pipeline works with single environment

## Long-term Considerations

### Future Scaling
- If sql_generator grows significantly, consider extracting as separate package
- Monitor dependency conflicts as both projects evolve
- Consider using Python namespace packages for better organization

### Maintenance
- Regular dependency updates with `uv sync`
- Periodic audit of unused dependencies
- Version pinning strategy for production

## Appendix A: Current Dependency Lists

### Main Project Key Dependencies
```
Django>=5.2
djangorestframework>=3.16.0
thoth-dbmanager[postgresql,sqlite]==0.5.3
thoth-qdrant>=0.1.3
pydantic-ai>=0.7.2
fastapi>=0.100.0
uvicorn>=0.20.0
```

### sql_generator Key Dependencies
```
fastapi>=0.116.1
uvicorn>=0.35.0
pydantic-ai>=0.0.50
thoth-dbmanager[postgresql,sqlite]>=0.5.3
thoth-qdrant>=0.1.3
python-multipart>=0.0.20
```

## Appendix B: Testing Checklist

- [ ] Django admin interface loads
- [ ] API endpoints respond
- [ ] sql_generator generates SQL correctly
- [ ] Qdrant connections work
- [ ] Database operations succeed
- [ ] Authentication flows work
- [ ] File uploads work (python-multipart)
- [ ] Logging works correctly
- [ ] Error handling preserved

## Conclusion

Merging the dependency environments will simplify development and deployment while maintaining all functionality. The key is careful version resolution and thorough testing during the migration.

---

*Document Version: 1.0*  
*Date: 2024-01-15*  
*Author: Claude (AI Assistant)*  
*Status: DRAFT - Awaiting Review*