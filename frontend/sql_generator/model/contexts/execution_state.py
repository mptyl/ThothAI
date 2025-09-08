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
Execution state context for SystemState decomposition.

Contains runtime state information that changes during SQL generation execution,
including error states, execution results, and strategy decisions.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class ExecutionState(BaseModel):
    """
    Runtime execution state and error tracking context.
    
    This context contains mutable state information that changes during
    SQL generation execution. It tracks the current execution status,
    errors encountered, and strategic decisions made during the process.
    
    State is grouped by purpose:
    - SQL Execution: last_SQL, last_execution_error, last_generation_success
    - Error Tracking: sql_generation_failure_message  
    - Strategy Decisions: schema_link_strategy, available_context_tokens, full_schema_tokens_count
    """
    
    # Current SQL execution state
    last_SQL: str = Field(
        default="",
        description="Most recently generated or executed SQL query"
    )
    
    last_execution_error: str = Field(
        default="",
        description="Error message from the last SQL execution attempt"
    )
    
    last_generation_success: bool = Field(
        default=False,
        description="Whether the last SQL generation attempt was successful"
    )
    
    # Generation failure tracking
    sql_generation_failure_message: Optional[str] = Field(
        default=None,
        description="Detailed failure message if SQL generation completely failed"
    )
    
    # Schema linking strategy state
    schema_link_strategy: Optional[str] = Field(
        default=None,
        description="Strategy used for schema linking: 'WITH_SCHEMA_LINK' or 'WITHOUT_SCHEMA_LINK'"
    )
    
    available_context_tokens: Optional[int] = Field(
        default=None,
        description="Available context window size of the LLM model"
    )
    
    full_schema_tokens_count: Optional[int] = Field(
        default=None,
        description="Token count required for the full M-Schema representation"
    )
    
    # Escalation tracking
    escalation_attempts: int = Field(
        default=0,
        description="Number of escalation attempts from BASIC to ADVANCED/EXPERT"
    )
    
    escalation_context: Optional[str] = Field(
        default=None,
        description="Context information from previous escalation attempts"
    )
    
    # Escalation tracking flags
    advanced_escalation: bool = Field(
        default=False,
        description="Flag indicating if escalation to ADVANCED level occurred"
    )
    
    expert_escalation: bool = Field(
        default=False,
        description="Flag indicating if escalation to EXPERT level occurred"
    )
    
    # Timing fields for performance tracking
    sql_generation_start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when SQL generation started"
    )
    
    sql_generation_end_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when SQL generation completed"
    )
    
    sql_generation_duration_ms: float = Field(
        default=0.0,
        description="SQL generation duration in milliseconds"
    )
    
    test_generation_start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when test generation started"
    )
    
    test_generation_end_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when test generation completed"
    )
    
    test_generation_duration_ms: float = Field(
        default=0.0,
        description="Test generation duration in milliseconds"
    )
    
    evaluation_start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when evaluation started"
    )
    
    evaluation_end_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when evaluation completed"
    )
    
    evaluation_duration_ms: float = Field(
        default=0.0,
        description="Evaluation duration in milliseconds"
    )
    
    sql_selection_start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when SQL selection started"
    )
    
    sql_selection_end_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when SQL selection completed"
    )
    
    sql_selection_duration_ms: float = Field(
        default=0.0,
        description="SQL selection duration in milliseconds"
    )
    
    # New timing fields for additional phases
    validation_start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when question validation started"
    )
    
    validation_end_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when question validation completed"
    )
    
    validation_duration_ms: float = Field(
        default=0.0,
        description="Question validation duration in milliseconds"
    )
    
    keyword_generation_start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when keyword generation started"
    )
    
    keyword_generation_end_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when keyword generation completed"
    )
    
    keyword_generation_duration_ms: float = Field(
        default=0.0,
        description="Keyword generation duration in milliseconds"
    )
    
    schema_preparation_start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when schema preparation (LSH + Vector) started"
    )
    
    schema_preparation_end_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when schema preparation completed"
    )
    
    schema_preparation_duration_ms: float = Field(
        default=0.0,
        description="Schema preparation duration in milliseconds"
    )
    
    context_retrieval_start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when context retrieval (evidence + SQL examples) started"
    )
    
    context_retrieval_end_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when context retrieval completed"
    )
    
    context_retrieval_duration_ms: float = Field(
        default=0.0,
        description="Context retrieval duration in milliseconds"
    )
    
    test_reduction_start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when test reduction started (if performed)"
    )
    
    test_reduction_end_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when test reduction completed"
    )
    
    test_reduction_duration_ms: float = Field(
        default=0.0,
        description="Test reduction duration in milliseconds"
    )
    
    process_end_time: Optional[datetime] = Field(
        default=None,
        description="Final timestamp when the entire process completed"
    )
    
    # Belt and Suspenders timing fields
    belt_and_suspenders_start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when Belt and Suspenders selection started (if enabled)"
    )
    
    belt_and_suspenders_end_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when Belt and Suspenders selection completed"
    )
    
    belt_and_suspenders_duration_ms: float = Field(
        default=0.0,
        description="Belt and Suspenders selection duration in milliseconds"
    )
    
    # Evaluation results and status
    evaluation_case: str = Field(
        default="",
        description="Evaluation case: A-GOLD, B-GOLD, A-SILVER, B-SILVER, C-SILVER, D-FAILED"
    )
    
    sql_status: str = Field(
        default="",
        description="SQL status: GOLD, SILVER, FAILED"
    )
    
    evaluation_details: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detailed evaluation results for each SQL"
    )
    
    pass_rates: Dict[str, float] = Field(
        default_factory=dict,
        description="Pass rates for each SQL candidate"
    )
    
    selected_sql_complexity: Optional[float] = Field(
        default=None,
        description="Complexity score of selected SQL (for case B selection)"
    )
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = False  # Only simple types
        validate_assignment = True  # Validate on field assignment
        
    @validator('schema_link_strategy')
    def validate_schema_link_strategy(cls, v):
        """Validate schema link strategy is one of allowed values"""
        if v is not None:
            allowed_strategies = {'WITH_SCHEMA_LINK', 'WITHOUT_SCHEMA_LINK'}
            if v not in allowed_strategies:
                raise ValueError(f'schema_link_strategy must be one of {allowed_strategies}, got: {v}')
        return v
        
    @validator('available_context_tokens', 'full_schema_tokens_count')
    def validate_token_counts(cls, v):
        """Validate token counts are positive if provided"""
        if v is not None and v <= 0:
            raise ValueError('Token counts must be positive integers')
        return v
        
    def has_sql(self) -> bool:
        """
        Check if a SQL query has been generated.
        
        Returns:
            bool: True if last_SQL contains a query
        """
        return bool(self.last_SQL and self.last_SQL.strip())
        
    def has_execution_error(self) -> bool:
        """
        Check if there is a current execution error.
        
        Returns:
            bool: True if execution error exists
        """
        return bool(self.last_execution_error and self.last_execution_error.strip())
        
    def has_generation_failure(self) -> bool:
        """
        Check if generation has completely failed.
        
        Returns:
            bool: True if generation failure message exists
        """
        return (self.sql_generation_failure_message is not None and 
                bool(self.sql_generation_failure_message.strip()))
        
    def has_schema_strategy(self) -> bool:
        """
        Check if schema linking strategy has been decided.
        
        Returns:
            bool: True if strategy is set
        """
        return self.schema_link_strategy is not None
        
    def has_token_analysis(self) -> bool:
        """
        Check if token analysis has been performed.
        
        Returns:
            bool: True if token counts are available
        """
        return (self.available_context_tokens is not None and 
                self.full_schema_tokens_count is not None)
        
    def is_schema_link_enabled(self) -> bool:
        """
        Check if schema linking is enabled based on strategy.
        
        Returns:
            bool: True if schema linking should be used
        """
        return self.schema_link_strategy == 'WITH_SCHEMA_LINK'
        
    def get_execution_status(self) -> str:
        """
        Get current execution status as a string.
        
        Returns:
            str: Current status description
        """
        if self.has_generation_failure():
            return "Generation Failed"
        elif self.has_execution_error():
            return "Execution Error"
        elif self.last_generation_success:
            return "Success"
        elif self.has_sql():
            return "SQL Generated"
        else:
            return "Not Started"
            
    def get_error_summary(self) -> str:
        """
        Get summary of current errors.
        
        Returns:
            str: Error summary or empty string if no errors
        """
        errors = []
        
        if self.has_execution_error():
            errors.append(f"Execution: {self.last_execution_error[:100]}...")
            
        if self.has_generation_failure():
            errors.append(f"Generation: {self.sql_generation_failure_message[:100]}...")
            
        return "; ".join(errors)
        
    def clear_errors(self) -> None:
        """
        Clear all error states.
        """
        self.last_execution_error = ""
        self.sql_generation_failure_message = None
        
    def reset_execution_state(self) -> None:
        """
        Reset execution state for a new attempt.
        """
        self.last_SQL = ""
        self.last_execution_error = ""
        self.last_generation_success = False
        self.sql_generation_failure_message = None
        
    def can_fit_full_schema(self) -> Optional[bool]:
        """
        Check if full schema can fit in available context.
        
        Returns:
            Optional[bool]: True if fits, False if doesn't, None if unknown
        """
        if not self.has_token_analysis():
            return None
            
        return self.full_schema_tokens_count <= self.available_context_tokens
        
    def get_execution_summary(self) -> str:
        """
        Get a summary of execution state for logging/display.
        
        Returns:
            str: Human-readable execution state summary
        """
        status = self.get_execution_status()
        summary_parts = [f"Status: {status}"]
        
        if self.has_schema_strategy():
            strategy = "enabled" if self.is_schema_link_enabled() else "disabled"
            summary_parts.append(f"Schema linking: {strategy}")
            
        if self.has_token_analysis():
            can_fit = self.can_fit_full_schema()
            fit_status = "fits" if can_fit else "exceeds" if can_fit is False else "unknown"
            summary_parts.append(f"Schema size: {fit_status} context")
            
        if self.has_sql():
            sql_preview = self.last_SQL[:50].replace('\n', ' ') + "..." if len(self.last_SQL) > 50 else self.last_SQL
            summary_parts.append(f"Last SQL: {sql_preview}")
            
        error_summary = self.get_error_summary()
        if error_summary:
            summary_parts.append(f"Errors: {error_summary}")
            
        return f"Execution state: {', '.join(summary_parts)}"