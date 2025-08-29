# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Custom exception classes for the SystemState and related components.

This module provides specific exception types to replace generic Exception
handling throughout the codebase, improving error handling and debugging.
"""


class SystemStateError(Exception):
    """
    Base exception for all SystemState-related errors.
    
    This is the parent class for all SystemState exceptions, allowing
    for broad exception handling when needed while still providing
    specific exception types for detailed error handling.
    """
    pass


class SchemaProcessingError(SystemStateError):
    """
    Exception raised during schema processing operations.
    
    Used for errors in:
    - Schema enrichment
    - Schema filtering 
    - Schema validation
    - Vector database schema operations
    """
    
    def __init__(self, message: str, schema_name: str = None, operation: str = None):
        self.schema_name = schema_name
        self.operation = operation
        
        if schema_name and operation:
            message = f"Schema processing error in {operation} for '{schema_name}': {message}"
        elif operation:
            message = f"Schema processing error in {operation}: {message}"
        
        super().__init__(message)


class ValidationError(SystemStateError):
    """
    Exception raised during data validation operations.
    
    Used for errors in:
    - Agent dependency validation
    - Context validation
    - Input parameter validation
    """
    
    def __init__(self, message: str, field_name: str = None, field_value = None):
        self.field_name = field_name
        self.field_value = field_value
        
        if field_name:
            message = f"Validation error for field '{field_name}': {message}"
            if field_value is not None:
                message += f" (value: {field_value})"
        
        super().__init__(message)


class VectorDatabaseError(SystemStateError):
    """
    Exception raised during vector database operations.
    
    Used for errors in:
    - Vector similarity searches
    - Vector database connections
    - Vector database queries
    """
    
    def __init__(self, message: str, operation: str = None, query: str = None):
        self.operation = operation
        self.query = query
        
        if operation:
            message = f"Vector database error in {operation}: {message}"
            if query:
                message += f" (query: {query[:100]}...)" if len(query) > 100 else f" (query: {query})"
        
        super().__init__(message)


class DatabaseConnectionError(SystemStateError):
    """
    Exception raised during database connection operations.
    
    Used for errors in:
    - Database connections
    - Database queries
    - Database configuration
    """
    
    def __init__(self, message: str, db_type: str = None, connection_string: str = None):
        self.db_type = db_type
        self.connection_string = connection_string
        
        if db_type:
            message = f"Database connection error ({db_type}): {message}"
        
        super().__init__(message)


class AgentExecutionError(SystemStateError):
    """
    Exception raised during agent execution.
    
    Used for errors in:
    - Agent initialization
    - Agent execution
    - Agent dependency creation
    """
    
    def __init__(self, message: str, agent_type: str = None, agent_name: str = None):
        self.agent_type = agent_type
        self.agent_name = agent_name
        
        if agent_type:
            agent_info = f"{agent_type}"
            if agent_name:
                agent_info += f" ({agent_name})"
            message = f"Agent execution error [{agent_info}]: {message}"
        
        super().__init__(message)


class ConfigurationError(SystemStateError):
    """
    Exception raised for configuration-related errors.
    
    Used for errors in:
    - Missing configuration values
    - Invalid configuration values
    - Configuration file parsing
    """
    
    def __init__(self, message: str, config_key: str = None, config_file: str = None):
        self.config_key = config_key
        self.config_file = config_file
        
        if config_key:
            message = f"Configuration error for '{config_key}': {message}"
            if config_file:
                message += f" (file: {config_file})"
        
        super().__init__(message)


class StateFactoryError(SystemStateError):
    """
    Exception raised during StateFactory operations.
    
    Used for errors in:
    - SystemState creation
    - Agent dependency creation
    - State updates and modifications
    """
    
    def __init__(self, message: str, factory_method: str = None, target_type: str = None):
        self.factory_method = factory_method
        self.target_type = target_type
        
        if factory_method:
            message = f"StateFactory error in {factory_method}: {message}"
            if target_type:
                message += f" (target: {target_type})"
        
        super().__init__(message)


# Convenience function for creating validation errors
def validation_error(message: str, field_name: str = None, field_value = None) -> ValidationError:
    """Create a ValidationError with standardized formatting."""
    return ValidationError(message, field_name, field_value)


# Convenience function for creating schema processing errors  
def schema_error(message: str, schema_name: str = None, operation: str = None) -> SchemaProcessingError:
    """Create a SchemaProcessingError with standardized formatting."""
    return SchemaProcessingError(message, schema_name, operation)