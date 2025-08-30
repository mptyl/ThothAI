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