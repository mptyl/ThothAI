# Logging Standardization Guide for SQL Generator

## Overview

This document defines the standardized logging architecture for the SQL Generator service, ensuring consistent, maintainable, and performant logging across all components.

## Architecture Components

### 1. Centralized Configuration (`config/logging_config.py`)

The logging configuration is centralized and environment-driven, providing flexibility without code changes.

```python
import os
import logging.config
from typing import Dict, Any

def get_logging_config() -> Dict[str, Any]:
    """
    Unified logging configuration based on environment variables.
    
    Returns:
        Dict containing the logging configuration for Python's logging.config
    """
    
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_format = os.getenv('LOG_FORMAT', 'standard')
    
    # Available format templates
    formats = {
        'standard': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'detailed': '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
        'json': '{"time":"%(asctime)s","logger":"%(name)s","level":"%(levelname)s","file":"%(filename)s","line":%(lineno)d,"msg":"%(message)s"}'
    }
    
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': formats.get(log_format, formats['standard']),
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'default',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'default',
                'filename': os.getenv('LOG_FILE', 'logs/sql_generator.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            }
        },
        'loggers': {
            'sql_generator': {
                'level': log_level,
                'handlers': ['console', 'file'] if os.getenv('LOG_TO_FILE', 'false').lower() == 'true' else ['console'],
                'propagate': False
            },
            'agents': {
                'level': os.getenv('AGENTS_LOG_LEVEL', log_level),
                'handlers': ['console'],
                'propagate': False
            },
            'helpers': {
                'level': os.getenv('HELPERS_LOG_LEVEL', log_level),
                'handlers': ['console'],
                'propagate': False
            },
            'validators': {
                'level': os.getenv('VALIDATORS_LOG_LEVEL', log_level),
                'handlers': ['console'],
                'propagate': False
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['console']
        }
    }
```

### 2. Logger Factory Pattern (`utils/logger_factory.py`)

A factory pattern ensures consistent logger creation and caching for performance.

```python
import logging
from functools import lru_cache
from typing import Optional

@lru_cache(maxsize=128)
def get_logger(name: str, component: Optional[str] = None) -> logging.Logger:
    """
    Factory to obtain consistently configured loggers.
    
    Args:
        name: Module name (typically __name__)
        component: Optional component for categorization
        
    Returns:
        Configured logger instance
        
    Example:
        logger = get_logger(__name__, 'agents')
    """
    if component:
        logger_name = f"{component}.{name}"
    else:
        # Extract component from module path
        parts = name.split('.')
        if len(parts) > 1 and parts[0] in ['agents', 'helpers', 'validators']:
            logger_name = name
        else:
            logger_name = f"sql_generator.{name}"
    
    return logging.getLogger(logger_name)

def get_child_logger(parent_logger: logging.Logger, child_name: str) -> logging.Logger:
    """
    Create a child logger from a parent logger.
    
    Args:
        parent_logger: The parent logger instance
        child_name: Name for the child logger
        
    Returns:
        Child logger instance
    """
    return parent_logger.getChild(child_name)
```

### 3. Logging Context Manager (`utils/logging_context.py`)

Context managers for automatic operation timing and structured logging.

```python
import logging
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any
import json

@contextmanager
def log_operation(operation: str, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
    """
    Context manager for logging operations with automatic timing.
    
    Args:
        operation: Name of the operation being performed
        logger: Logger instance to use
        extra: Additional context information
        
    Usage:
        with log_operation("SQL generation", logger, {"workspace_id": 123}):
            # operation code here
            pass
    """
    start_time = time.time()
    extra_str = f" with {json.dumps(extra)}" if extra else ""
    
    logger.info(f"Starting {operation}{extra_str}")
    try:
        yield
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Failed {operation} after {duration:.2f}s: {e}",
            exc_info=True,
            extra={'duration': duration, 'operation': operation, **(extra or {})}
        )
        raise
    else:
        duration = time.time() - start_time
        logger.info(
            f"Completed {operation} in {duration:.2f}s",
            extra={'duration': duration, 'operation': operation, **(extra or {})}
        )

@contextmanager
def log_performance(operation: str, logger: logging.Logger, threshold_ms: float = 1000):
    """
    Context manager for performance monitoring with threshold alerts.
    
    Args:
        operation: Name of the operation
        logger: Logger instance
        threshold_ms: Performance threshold in milliseconds
        
    Usage:
        with log_performance("database_query", logger, threshold_ms=500):
            # perform database query
            pass
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        if duration_ms > threshold_ms:
            logger.warning(
                f"Performance threshold exceeded for {operation}: {duration_ms:.2f}ms > {threshold_ms}ms",
                extra={'duration_ms': duration_ms, 'threshold_ms': threshold_ms, 'operation': operation}
            )
        else:
            logger.debug(
                f"Performance metric for {operation}: {duration_ms:.2f}ms",
                extra={'duration_ms': duration_ms, 'operation': operation}
            )
```

### 4. Security and Sanitization (`utils/log_sanitizer.py`)

Utilities for sanitizing sensitive data in logs.

```python
import re
from typing import Any, Dict, List
import hashlib

class LogSanitizer:
    """Sanitizes sensitive information from log messages."""
    
    # Patterns for sensitive data
    PATTERNS = {
        'api_key': re.compile(r'(api[_-]?key|apikey|api_secret)[\s"\'=:]+([A-Za-z0-9+/=_-]{20,})', re.IGNORECASE),
        'password': re.compile(r'(password|passwd|pwd)[\s"\'=:]+([^\s"\']+)', re.IGNORECASE),
        'token': re.compile(r'(token|bearer|auth)[\s"\'=:]+([A-Za-z0-9+/=_-]{20,})', re.IGNORECASE),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    }
    
    @classmethod
    def sanitize(cls, message: str, truncate_sql: bool = True) -> str:
        """
        Sanitize sensitive information from log messages.
        
        Args:
            message: The log message to sanitize
            truncate_sql: Whether to truncate long SQL queries
            
        Returns:
            Sanitized message
        """
        # Replace sensitive patterns
        for pattern_name, pattern in cls.PATTERNS.items():
            if pattern_name in ['email']:
                # Hash emails to maintain uniqueness for debugging
                message = pattern.sub(lambda m: cls._hash_value(m.group()), message)
            else:
                message = pattern.sub(lambda m: f"{m.group(1)}=***REDACTED***", message)
        
        # Truncate SQL queries if needed
        if truncate_sql and 'SELECT' in message.upper():
            sql_start = message.upper().find('SELECT')
            if sql_start != -1 and len(message[sql_start:]) > 500:
                message = message[:sql_start + 500] + '... [TRUNCATED]'
        
        return message
    
    @staticmethod
    def _hash_value(value: str) -> str:
        """Hash a value for consistent redaction."""
        return f"***{hashlib.md5(value.encode()).hexdigest()[:8]}***"

def safe_log(logger: logging.Logger, level: str, message: str, *args, **kwargs):
    """
    Safely log a message with automatic sanitization.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Message to log
        *args: Additional arguments for the logger
        **kwargs: Additional keyword arguments for the logger
    """
    sanitized_message = LogSanitizer.sanitize(message)
    getattr(logger, level.lower())(sanitized_message, *args, **kwargs)
```

## Logging Levels and Conventions

### Level Guidelines

| Level | Usage | Example |
|-------|-------|---------|
| **DEBUG** | Technical details, variable values, generated SQL | `logger.debug(f"Generated SQL: {sql[:200]}...")` |
| **INFO** | Significant events, operation start/end | `logger.info(f"Processing question for workspace {workspace_id}")` |
| **WARNING** | Anomalous but recoverable situations | `logger.warning(f"Retry attempt {retry} for agent {agent}")` |
| **ERROR** | Errors preventing operation completion | `logger.error(f"Database connection failed: {e}", exc_info=True)` |
| **CRITICAL** | Severe system errors | `logger.critical("Critical system failure: out of memory")` |

### Structured Logging Examples

```python
# Good: Structured with context
logger.info("SQL generation completed", extra={
    'workspace_id': workspace_id,
    'duration_ms': duration_ms,
    'sql_length': len(sql),
    'agent_type': agent_type
})

# Good: Error with full context
logger.error("Agent execution failed", extra={
    'agent': agent_name,
    'retry_count': retry_count,
    'error_type': type(e).__name__
}, exc_info=True)

# Bad: Unstructured string concatenation
logger.info(f"Completed {operation} for {user} in {time}ms with {result}")
```

## Environment Configuration

### Development Environment
```bash
# .env.development
LOG_LEVEL=DEBUG
AGENTS_LOG_LEVEL=DEBUG
HELPERS_LOG_LEVEL=INFO
VALIDATORS_LOG_LEVEL=DEBUG
LOG_FORMAT=detailed
LOG_TO_FILE=true
LOG_FILE=logs/dev_sql_generator.log
```

### Production Environment
```bash
# .env.production
LOG_LEVEL=INFO
AGENTS_LOG_LEVEL=WARNING
HELPERS_LOG_LEVEL=WARNING
VALIDATORS_LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_TO_FILE=true
LOG_FILE=/var/log/sql_generator/app.log
```

### Docker Configuration
```yaml
# docker-compose.yml
services:
  sql-generator:
    environment:
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - LOG_FORMAT=${LOG_FORMAT:-json}
      - LOG_TO_FILE=true
      - LOG_FILE=/app/logs/sql_generator.log
    volumes:
      - ./logs:/app/logs
```

## Implementation in Code

### Application Initialization (`main.py`)
```python
import logging.config
from config.logging_config import get_logging_config
from utils.logger_factory import get_logger

# Initialize logging at application startup
logging.config.dictConfig(get_logging_config())

# Get logger for main module
logger = get_logger(__name__)

def main():
    logger.info("Starting SQL Generator service")
    # ... application code
```

### Module Usage Example
```python
# agents/core/agent_manager.py
from utils.logger_factory import get_logger
from utils.logging_context import log_operation

logger = get_logger(__name__)

class AgentManager:
    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)
    
    async def execute_agent(self, agent_name: str, input_data: dict):
        with log_operation(f"agent_execution_{agent_name}", self.logger, 
                         {'agent': agent_name, 'input_size': len(str(input_data))}):
            # Agent execution logic
            result = await self._run_agent(agent_name, input_data)
            self.logger.debug(f"Agent {agent_name} returned: {result[:100]}...")
            return result
```

## Migration Strategy

### Phase 1: Setup (Immediate)
1. Create logging configuration module
2. Implement logger factory
3. Add context managers and sanitizer

### Phase 2: Migration (1 week)
1. Replace all `print()` statements with appropriate logger calls
2. Update all modules to use logger factory
3. Add context managers to key operations

### Phase 3: Enhancement (2 weeks)
1. Implement structured logging with extra fields
2. Add performance monitoring
3. Set up log aggregation for production

## Performance Considerations

- **Logger Caching**: LRU cache prevents repeated logger creation
- **Lazy Formatting**: Use `logger.debug("msg %s", value)` not `f"msg {value}"`
- **Level Checking**: Logger checks level before formatting
- **Async Handlers**: Consider async handlers for high-volume production

## Security Best Practices

1. **Never log sensitive data**: Passwords, API keys, tokens
2. **Truncate large payloads**: SQL queries, request bodies
3. **Hash identifiable information**: Emails, user IDs for correlation
4. **Use structured logging**: Easier to filter and analyze
5. **Rotate log files**: Prevent disk space issues

## Monitoring and Analysis

### Log Analysis Queries

```python
# Parse JSON logs for performance analysis
import json
from datetime import datetime

def analyze_performance_logs(log_file):
    slow_operations = []
    with open(log_file) as f:
        for line in f:
            try:
                log = json.loads(line)
                if 'duration_ms' in log and log['duration_ms'] > 1000:
                    slow_operations.append(log)
            except json.JSONDecodeError:
                continue
    return slow_operations
```

### Metrics to Track
- Operation duration percentiles (p50, p95, p99)
- Error rates by component
- Retry attempts and success rates
- Resource usage correlation

## Conclusion

This standardized logging architecture provides:
- **Consistency**: Uniform logging across all components
- **Flexibility**: Environment-based configuration
- **Performance**: Optimized with caching and lazy evaluation
- **Security**: Built-in sanitization and truncation
- **Maintainability**: Centralized configuration and patterns

By following these standards, the SQL Generator service will have professional-grade logging suitable for production environments while maintaining developer-friendly output for debugging.