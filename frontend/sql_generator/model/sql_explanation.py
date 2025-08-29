# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

"""
Models for SQL explanation functionality.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class SqlExplanationRequest(BaseModel):
    """Request model for SQL explanation."""
    workspace_id: int = Field(..., description="The workspace ID")
    question: str = Field(..., description="The original user question")
    keywords: List[str] = Field(default_factory=list, description="Keywords extracted from the question")
    evidence: str = Field(..., description="Evidence/hints used for SQL generation")
    database_schema: str = Field(..., description="Database schema used")
    generated_sql: str = Field(..., description="The SQL query that was generated")
    username: str = Field(..., description="Username of the requester")
    language: str = Field(default="it", description="Language for the explanation (it/en)")
    chain_of_thought: str = Field(default="", description="Chain of thought reasoning used")


class SqlExplanationResponse(BaseModel):
    """Response model for SQL explanation."""
    explanation: str = Field(..., description="The generated explanation")
    execution_time: float = Field(..., description="Time taken to generate explanation in seconds")
    success: bool = Field(..., description="Whether the explanation was generated successfully")
    error: Optional[str] = Field(None, description="Error message if explanation failed")
    agent_used: Optional[str] = Field(None, description="Name of the agent that generated the explanation")