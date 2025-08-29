# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Code Cleanup Plan - ThothAI UI SQL Generator

## Executive Summary

This document outlines a comprehensive cleanup plan for the ThothAI UI SQL Generator codebase. The analysis has identified multiple categories of code quality issues including duplicate imports, unused code, excessive logging, architectural issues, and configuration problems. The cleanup is organized into four phases, prioritized by risk and impact.

## Issues Identified

### 1. Duplicate Imports and Redundant Code

#### Critical Issues
- **main.py (Lines 19 & 27)**: `asyncio` imported twice - clear duplicate
- **Multiple files**: Repeated patterns in template loading functions
- **logging configuration**: Duplicated logic across multiple files

#### Impact
- Reduced code clarity
- Potential namespace conflicts
- Increased maintenance burden

### 2. Unused Imports and Dead Code

#### Files with Potential Dead Code
- **model/execution.py**: Complex SQL execution logic potentially unused in current workflow
- **model/user.py**: Simple model that may not be actively used
- **model/sql_meta_info.py**: Potentially unused metadata model
- **helpers/setups.py**: Contains migration comments and placeholder functions

#### Impact
- Increased bundle size
- Confusion about actual system functionality
- Maintenance of unused code

### 3. Test/Debug Logging

#### Excessive Logging Found In
- **main.py (Lines 100-150+)**: Extensive debug logging configuration
- **helpers/thoth_log_api.py**: Verbose data logging for backend communication
- **helpers/dual_logger.py**: Defensive fallback logic that may be unnecessary
- **Multiple files**: `logger.info()` calls that appear to be for debugging

#### Impact
- Performance overhead in production
- Log file bloat
- Difficulty finding important log messages

### 4. Architectural Code Smells

#### Major Issues
- **main.py `generate_response()` function**: 400+ lines - violates single responsibility
- **model/system_state.py**: 500+ line class with too many responsibilities
- **helpers/template_preparation.py**: Multiple similar functions with repeated patterns
- **helpers/vectordb_config_utils.py**: Complex nested conditionals

#### Impact
- Poor testability
- Difficult maintenance
- High cognitive load for developers
- Increased bug probability

### 5. Configuration Issues

#### Problems Identified
- **Environment variables**: Loaded multiple times in main.py
- **Logging configuration**: Complex and repeated setup logic
- **Docker vs Local detection**: Brittle environment detection in logging_config.py

#### Impact
- Potential configuration conflicts
- Unpredictable behavior across environments
- Difficult deployment

### 6. Performance Issues

#### Memory Management Problems
- **Global caches in main.py**: `SESSION_CACHE` and `WORKSPACE_STATES` without cleanup
- **services/paginated_query_service.py**: Multiple caching strategies without TTL
- **No cache expiration**: Risk of memory leaks in long-running processes

#### Impact
- Memory leaks
- Degraded performance over time
- Potential OOM errors

## Cleanup Implementation Plan

### Phase 1: Quick Wins (1-2 days, Low Risk)

**Objective**: Remove obvious issues with minimal risk

1. **Remove duplicate imports**
   - Fix asyncio duplicate in main.py
   - Scan all files for other duplicates
   
2. **Clean up obvious dead code**
   - Remove migration comments in setups.py
   - Remove unused imports across all files
   
3. **Standardize headers**
   - Ensure all files have Apache 2.0 license header
   - Fix any remaining MIT references

**Files to modify**:
- `sql_generator/main.py`
- `sql_generator/helpers/setups.py`
- All Python files (import cleanup)

### Phase 2: Logging Optimization (2-3 days, Medium Risk)

**Objective**: Reduce logging overhead while maintaining observability

1. **Consolidate logging configuration**
   - Create single logging configuration module
   - Remove duplicate logging setup code
   
2. **Reduce verbose logging**
   - Convert debug logs to appropriate levels
   - Remove test/debug print statements
   - Implement proper log level filtering
   
3. **Simplify environment detection**
   - Refactor logging_config.py Docker detection
   - Use environment variables consistently

**Files to modify**:
- `sql_generator/main.py` (logging setup)
- `sql_generator/helpers/logging_config.py`
- `sql_generator/helpers/dual_logger.py`
- `sql_generator/helpers/thoth_log_api.py`

### Phase 3: Code Structure Refactoring (3-5 days, Medium-High Risk)

**Objective**: Improve code maintainability and testability

1. **Break down large functions**
   - Split `generate_response()` into logical sub-functions:
     - `validate_question()`
     - `extract_context()`
     - `generate_sql_candidates()`
     - `evaluate_and_select()`
     - `prepare_response()`
   
2. **Refactor template preparation**
   - Create generic template loader
   - Eliminate code duplication
   - Use configuration for template paths
   
3. **Simplify configuration utilities**
   - Reduce nested conditionals in vectordb_config_utils.py
   - Create clear configuration models

**Files to modify**:
- `sql_generator/main.py`
- `sql_generator/helpers/template_preparation.py`
- `sql_generator/helpers/vectordb_config_utils.py`

### Phase 4: Architecture Improvements (5-7 days, High Risk)

**Objective**: Address fundamental architecture issues

1. **Implement proper cache management**
   - Add TTL to all caches
   - Implement cache cleanup routines
   - Add memory monitoring
   
2. **Refactor SystemState class**
   - Split into smaller, focused classes:
     - `QueryState`
     - `SchemaState`
     - `ExecutionState`
     - `ResultState`
   
3. **Clean up unused models**
   - Verify and remove unused models
   - Update imports accordingly
   
4. **Optimize service layer**
   - Review paginated_query_service.py caching
   - Implement proper connection pooling

**Files to modify**:
- `sql_generator/model/system_state.py`
- `sql_generator/model/execution.py`
- `sql_generator/model/user.py`
- `sql_generator/services/paginated_query_service.py`

## Risk Mitigation

### Testing Strategy
1. **Unit tests**: Write tests before refactoring
2. **Integration tests**: Ensure end-to-end functionality
3. **Performance tests**: Measure impact of changes
4. **Regression tests**: Verify no functionality loss

### Rollback Plan
1. Create feature branches for each phase
2. Tag releases before major changes
3. Maintain backward compatibility where possible
4. Document all breaking changes

### Monitoring
1. Track memory usage before/after
2. Monitor response times
3. Log error rates
4. Track code coverage

## Success Metrics

### Code Quality Metrics
- **Cyclomatic complexity**: Reduce by 30%
- **Function length**: No function > 100 lines
- **Class size**: No class > 300 lines
- **Duplicate code**: Reduce by 50%

### Performance Metrics
- **Memory usage**: Reduce by 20%
- **Startup time**: Reduce by 15%
- **Response time**: Maintain or improve
- **Log volume**: Reduce by 40%

### Maintainability Metrics
- **Code coverage**: Increase to 80%
- **Documentation**: 100% of public APIs
- **Type hints**: 100% of function signatures
- **Linting errors**: Zero tolerance

## Timeline

| Phase | Duration | Start Date | End Date | Risk Level |
|-------|----------|------------|----------|------------|
| Phase 1 | 1-2 days | TBD | TBD | Low |
| Phase 2 | 2-3 days | TBD | TBD | Medium |
| Phase 3 | 3-5 days | TBD | TBD | Medium-High |
| Phase 4 | 5-7 days | TBD | TBD | High |

**Total estimated time**: 11-17 days

## Specific File Changes

### High Priority Files
1. `/sql_generator/main.py`
   - Remove duplicate import (line 27)
   - Break down generate_response() function
   - Implement cache cleanup
   - Reduce logging verbosity

2. `/sql_generator/helpers/template_preparation.py`
   - Create generic template loader
   - Remove duplicated functions
   - Centralize template paths

3. `/sql_generator/model/system_state.py`
   - Split into smaller classes
   - Implement proper state management
   - Add validation methods

### Medium Priority Files
1. `/sql_generator/helpers/logging_config.py`
   - Simplify Docker detection
   - Centralize configuration

2. `/sql_generator/helpers/vectordb_config_utils.py`
   - Reduce complexity
   - Create configuration models

3. `/sql_generator/services/paginated_query_service.py`
   - Implement cache TTL
   - Add cleanup routines

### Low Priority Files
1. `/sql_generator/model/user.py`
   - Verify usage and remove if unused

2. `/sql_generator/model/execution.py`
   - Review for dead code
   - Remove unused functions

## Recommendations

### Immediate Actions
1. **Start with Phase 1** - Low risk, immediate benefits
2. **Set up monitoring** - Track metrics before changes
3. **Create test suite** - Ensure safety net for refactoring
4. **Document decisions** - Track why changes were made

### Long-term Improvements
1. **Adopt coding standards** - Enforce via pre-commit hooks
2. **Implement CI/CD** - Automated testing and deployment
3. **Regular code reviews** - Prevent future technical debt
4. **Performance monitoring** - Continuous optimization

### Team Considerations
1. **Knowledge sharing** - Document architectural decisions
2. **Pair programming** - For complex refactoring
3. **Code review process** - Ensure quality standards
4. **Training** - Best practices and new patterns

## Conclusion

The ThothAI UI SQL Generator codebase has accumulated technical debt that impacts maintainability, performance, and reliability. This cleanup plan provides a structured approach to addressing these issues while minimizing risk. By following this phased approach, the team can improve code quality incrementally while maintaining system stability.

The key to success will be:
- Taking an incremental approach
- Maintaining comprehensive tests
- Monitoring impact at each phase
- Being prepared to rollback if needed

With proper execution, this cleanup will result in a more maintainable, performant, and reliable system that will be easier to extend and debug in the future.