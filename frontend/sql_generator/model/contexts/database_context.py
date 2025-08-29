# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Database context for SystemState decomposition.

Contains database schema information and configuration settings
used throughout the SQL generation process.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, validator

# Import the type definition from centralized types module
from ..types import TableInfo


class DatabaseContext(BaseModel):
    """
    Database configuration and schema context.
    
    This context contains information about the database structure, configuration,
    and rules that guide SQL generation. Most of these fields are populated during
    the initialization phase and remain relatively stable during execution.
    
    Fields are grouped by their purpose:
    - Schema: full_schema (complete database structure)
    - Configuration: directives, treat_empty_result_as_error, db_type
    - Manager: dbmanager (optional for parallel execution)
    """
    
    # Database schema structure
    full_schema: Dict[str, TableInfo] = Field(
        default_factory=dict,
        description="Complete database schema with table descriptions and column information"
    )
    
    # Generation directives and rules
    directives: str = Field(
        default="Use only existing field names and table names",
        description="SQL generation guidelines and constraints from workspace configuration"
    )
    
    # Database configuration
    db_type: str = Field(
        default="postgresql", 
        description="Type of database (postgresql, sqlite, mysql, etc.)"
    )
    
    treat_empty_result_as_error: bool = Field(
        default=True,
        description="Whether to treat empty query results as validation errors"
    )
    
    # Database manager (optional for parallel execution)
    dbmanager: Optional[Any] = Field(
        default=None,
        description="Database manager instance for executing queries (None in parallel execution mode)"
    )
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = True  # Allow dbmanager which is not a Pydantic type
        validate_assignment = True  # Validate on field assignment
        
    @validator('db_type')
    def validate_db_type(cls, v):
        """Validate database type is a supported one"""
        supported_types = {
            'postgresql', 'postgres', 'sqlite', 'mysql', 'mariadb', 
            'mssql', 'sqlserver', 'oracle'
        }
        if v.lower() not in supported_types:
            # Don't raise error, just normalize - some custom types might be valid
            pass
        return v.lower()
        
    @validator('directives')
    def validate_directives_not_empty(cls, v):
        """Ensure directives are not empty"""
        if not v or not v.strip():
            return "Use only existing field names and table names"  # Default fallback
        return v.strip()
        
    def has_schema(self) -> bool:
        """
        Check if database schema has been loaded.
        
        Returns:
            bool: True if schema contains tables, False otherwise
        """
        return len(self.full_schema) > 0
    
    def get_table_names(self) -> list[str]:
        """
        Get list of all table names in the schema.
        
        Returns:
            list[str]: List of table names
        """
        return list(self.full_schema.keys())
    
    def get_table_info(self, table_name: str) -> Optional[TableInfo]:
        """
        Get information for a specific table.
        
        Args:
            table_name: Name of the table to retrieve
            
        Returns:
            TableInfo: Table information if exists, None otherwise
        """
        return self.full_schema.get(table_name)
    
    def has_manager(self) -> bool:
        """
        Check if a database manager is available.
        
        Returns:
            bool: True if dbmanager is available, False if in parallel mode
        """
        return self.dbmanager is not None
    
    def get_schema_summary(self) -> str:
        """
        Get a summary of the database schema for logging/display.
        
        Returns:
            str: Human-readable schema summary
        """
        if not self.has_schema():
            return "No schema loaded"
            
        table_count = len(self.full_schema)
        column_count = sum(
            len(table_info.get('columns', {})) 
            for table_info in self.full_schema.values()
        )
        
        return f"Schema: {table_count} tables, {column_count} total columns ({self.db_type})"