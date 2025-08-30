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

# Unless required by applicable law or agreed to in writing, software
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
"""
Agent result models for structured outputs from PydanticAI agents.

This module contains Pydantic models that define the expected output structure
for different types of agents in the SQL Generator service.
"""

from typing import Dict, List, Annotated, TypeAlias, Union, Optional
from enum import Enum

from annotated_types import MinLen
from pydantic import BaseModel, Field


class CheckQuestionResult(BaseModel):
    """Result type for the check question agent"""
    outcome: str
    reasons: str


class TranslationResult(BaseModel):
    """Result type for the question translator agent"""
    detected_language: str
    translated_question: str 
    

class ExtractEntitiesAndContextResult(BaseModel):
    """Result type for the keyword extraction agent"""
    keywords: List[str]

class ExtractKeywordsResult(BaseModel):
    """Result type for the keyword extraction agent (keywords only)."""
    keywords: List[str]


class ColumnSelectionResult(BaseModel):
    """Result type for the column selection agent"""
    chain_of_thought_reasoning: str
    tables: Dict[str, List[str]]


class Success(BaseModel):
    """Response when SQL could be successfully generated."""
    answer: Annotated[str, MinLen(1)]
    explanation: str = Field(
        '', description='Explanation of the SQL query, as markdown'
    )


class InvalidRequest(BaseModel):
    """Response the user input didn't include enough information to generate SQL."""
    error_message: str


SqlResponse: TypeAlias = Union[Success, InvalidRequest]


class TestUnitGeneratorResult(BaseModel):
    """Result type for the test unit generator agent"""
    thinking: str
    answers: List[str]
   

class EvaluationResult(BaseModel):
    """Result type for the evaluator agent that evaluates SQL candidates against test units
    
    Each answer contains a formatted string:
    - "SQL #n: test1_result, test2_result, ..."
    where each test_result is either "OK" or "KO - reason"
    """
    thinking: str
    answers: List[str]  # Each item is formatted as "SQL #n: OK, KO - reason, OK, ..."


class AskHumanResult(BaseModel):
    activity_analysis: str 
    human_help_request: str


class EvaluationStatus(Enum):
    """Status for enhanced evaluation results"""
    GOLD = "GOLD"  # SQL is selected as the best choice (Case A or B outcome)
    FAILED = "FAILED"  # All SQLs failed evaluation (Case D outcome)
    NEEDS_REEVALUATION = "NEEDS_REEVALUATION"  # Borderline case requiring supervisor (Case C)


class EnhancedEvaluationResult(BaseModel):
    """Enhanced evaluation result for the new 4-case evaluation system
    
    Replaces EvaluationResult with status-based outcomes and Gold SQL integration.
    Used by the revised evaluation flow with auxiliary agents.
    """
    # Core evaluation data
    thinking: str
    answers: List[str]  # Backward compatibility: "SQL #n: OK, KO - reason, ..."
    
    # New enhanced fields
    status: EvaluationStatus
    selected_sql_index: Optional[int] = None  # Index of selected SQL (0-based) for GOLD status
    selected_sql: Optional[str] = None  # The actual selected SQL text
    
    # Pass rate analysis
    pass_rates: Dict[str, float] = Field(default_factory=dict)  # "SQL #1": 0.85, "SQL #2": 1.0
    best_pass_rate: float = 0.0
    
    # Gold SQL references (for guidance, not evaluation)
    gold_sql_examples: List[str] = Field(default_factory=list)
    
    # Auxiliary agent results
    reduced_tests: Optional[List[str]] = None  # TestReducer output
    selector_reasoning: Optional[str] = None  # SqlSelector reasoning for Case B
    supervisor_assessment: Optional[str] = None  # EvaluatorSupervisor deep analysis for Case C
    
    # Escalation context
    escalation_context: Optional[str] = None  # Context for next functionality level
    requires_escalation: bool = False
    
    # Metadata
    evaluation_case: Optional[str] = None  # "A", "B", "C", or "D"
    auxiliary_agents_used: List[str] = Field(default_factory=list)
    processing_time_ms: Optional[float] = None


class TestReducerResult(BaseModel):
    """Result from TestReducer agent for semantic test deduplication"""
    thinking: str
    reduced_tests: List[str]
    removed_duplicates: List[str] = Field(default_factory=list)
    reduction_summary: str


class SqlSelectorResult(BaseModel):
    """Result from SqlSelector agent for choosing between equivalent SQLs"""
    thinking: str
    selected_index: int  # 0-based index of selected SQL
    comparison_details: str
    confidence_score: float = 0.0


class EvaluatorSupervisorResult(BaseModel):
    """Result from EvaluatorSupervisor for deep reevaluation of borderline cases"""
    thinking: str  # Extended thinking (8000+ tokens)
    final_decision: EvaluationStatus  # GOLD or FAILED
    confidence_level: str  # "HIGH", "MEDIUM", "LOW"
    detailed_assessment: str
    recommended_sql_index: Optional[int] = None