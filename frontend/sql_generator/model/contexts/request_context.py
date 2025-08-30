# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Request context for SystemState decomposition.

Contains immutable data from the initial user request that doesn't change
throughout the SQL generation workflow.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from tzlocal import get_localzone


class RequestContext(BaseModel):
    """
    Immutable context containing data from the initial user request.
    
    This context holds information that is provided by the user or extracted
    from the request and remains constant throughout the entire SQL generation
    workflow execution.
    
    Fields are grouped by their origin:
    - User-provided: original_question, username, workspace_id, functionality_level
    - Workspace-derived: workspace_name, language, scope
    - System-generated: started_at
    """
    
    # Core request data from UI
    question: str = Field(..., description="The user's natural language question from UI")
    username: str = Field(..., description="Username making the request")
    workspace_id: int = Field(..., description="ID of the workspace containing database configuration")
    workspace_name: str = Field(..., description="Human-readable name of the workspace")
    functionality_level: str = Field(..., description="SQL generator complexity level: BASIC, ADVANCED, or EXPERT")
    
    # Translation support fields
    original_question: Optional[str] = Field(default=None, description="Original question before translation (if applicable)")
    original_language: Optional[str] = Field(default=None, description="Original language of the question (if detected)")
    
    # Localization context
    language: str = Field(default="English", description="Target language for SQL generation and responses")
    scope: str = Field(default="", description="Database scope description from workspace configuration")
    
    # System metadata
    started_at: datetime = Field(default_factory=lambda: datetime.now(get_localzone()), description="Timestamp when request processing started")
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = False  # Ensure only simple, serializable types
        frozen = False  # Allow updates for translation fields
        validate_assignment = True  # Validate on field assignment
        
    @validator('functionality_level')
    def validate_functionality_level(cls, v):
        """Validate functionality level is one of the allowed values"""
        allowed_levels = {'BASIC', 'ADVANCED', 'EXPERT'}
        if v not in allowed_levels:
            raise ValueError(f'functionality_level must be one of {allowed_levels}, got: {v}')
        return v
        
    @validator('workspace_id')
    def validate_workspace_id(cls, v):
        """Validate workspace ID is positive"""
        if v <= 0:
            raise ValueError(f'workspace_id must be positive, got: {v}')
        return v
        
    @validator('question')
    def validate_question_not_empty(cls, v):
        """Validate question is not empty or just whitespace"""
        if not v or not v.strip():
            raise ValueError('question cannot be empty or just whitespace')
        return v.strip()
        
    @validator('username')
    def validate_username_not_empty(cls, v):
        """Validate username is not empty or just whitespace"""
        if not v or not v.strip():
            raise ValueError('username cannot be empty or just whitespace')
        return v.strip()
        
    def was_translated(self) -> bool:
        """
        Check if the question was translated from another language.
        
        Returns:
            bool: True if translation occurred, False otherwise
        """
        return (self.original_question is not None and 
                self.original_language is not None and
                self.original_question != self.question)
    
    def get_processing_language(self) -> str:
        """
        Get the language being used for processing.
        
        For display purposes and logging.
        
        Returns:
            str: The language being used for SQL generation
        """
        return self.language
    
    def get_display_question(self) -> str:
        """
        Get the question being processed for display.
        
        Returns the current (possibly translated) question.
        
        Returns:
            str: The question being processed
        """
        return self.question