# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

"""
Lightweight dependency classes for SQL generation agents.
These classes are designed to be fully pickleable for parallel execution.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any


class SqlGenerationDeps(BaseModel):
    """
    Minimal and pickleable dependencies for SQL generation agents.
    
    This class contains only the essential information needed by SQL generation
    agents and their validators, without any complex non-pickleable objects.
    """
    
    # Read-only database information (simple strings/bool)
    db_type: str
    db_schema_str: str = ""  # Database schema as string for error messages
    treat_empty_result_as_error: bool = False
    
    # Mutable fields that validators write to
    last_SQL: str = ""
    last_execution_error: str = ""
    last_generation_success: bool = False
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = False  # Ensure only simple types