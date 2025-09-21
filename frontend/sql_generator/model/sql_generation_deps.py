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
Lightweight dependency classes for SQL generation agents.
These classes are designed to be fully pickleable for parallel execution.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any


class SqlGenerationDeps(BaseModel):
    """
    Minimal and pickleable dependencies for SQL generation agents.
    
    This class contains only the essential information needed by SQL generation
    agents and their validators, without any complex non-pickleable objects.
    """
    
    # Read-only database information (simple strings/bool)
    db_type: str
    # The original or translated question (string only, safe for deps)
    question: str = ""
    db_schema_str: str = ""  # Database schema as string for error messages
    treat_empty_result_as_error: bool = False

    # Language context (optional): original question language and DB language
    question_language: str = ""
    db_language: str = ""

    # Mutable fields that validators write to
    last_SQL: str = ""
    last_execution_error: str = ""
    last_generation_success: bool = False
    retry_attempt: int = 0
    retry_history: List[str] = Field(default_factory=list)
    last_failed_tests: List[str] = Field(default_factory=list)
    last_explain_error: str = ""

    # Stateless gating input: evidence-critical tests for this request
    evidence_critical_tests: List[str] = Field(default_factory=list)

    # Telemetry fields captured during validation for downstream logging
    relevance_guard_events: List[Dict[str, Any]] = Field(default_factory=list)
    relevance_guard_summary: Dict[str, Any] = Field(default_factory=dict)
    model_retry_events: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = False  # Ensure only simple types
