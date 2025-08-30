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
Generation results context for SystemState decomposition.

Contains all the results from SQL generation, test generation, evaluation,
and final selection processes.
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, validator
from frozenlist import FrozenList


class GenerationResults(BaseModel):
    """
    Results from SQL generation and evaluation processes.
    
    This context contains the outputs of various generation phases including
    test generation, SQL candidate creation, evaluation, and final selection.
    Most fields are populated progressively as the generation pipeline executes.
    
    Results are grouped by generation phase:
    - Test Generation: generated_tests, generated_tests_json
    - SQL Generation: generated_sqls, generated_sqls_json  
    - Evaluation: evaluation_results, evaluation_results_json, final_evaluation
    - Selection: generated_sql, successful_agent_name, selection_metrics
    - Explanation: sql_explanation
    - Compatibility: test_results (maintained for backward compatibility)
    """
    
    # Test generation results
    generated_tests: List[Tuple[str, List[str]]] = Field(
        default_factory=list,
        description="Generated test cases as tuples of (thinking, answers)"
    )
    
    generated_tests_json: str = Field(
        default="",
        description="JSON string representation of generated_tests for storage"
    )
    
    # SQL generation results  
    generated_sqls: List[str] = Field(
        default_factory=list,
        description="List of generated SQL candidate queries"
    )
    
    generated_sqls_json: str = Field(
        default="",
        description="JSON string representation of generated_sqls for storage"
    )
    
    # Evaluation results
    evaluation_results: List[Tuple[str, List[str]]] = Field(
        default_factory=list,
        description="Results from autonomous evaluators as tuples of (thinking, scores/feedback)"
    )
    
    evaluation_results_json: str = Field(
        default="",
        description="JSON string representation of evaluation_results for storage"  
    )
    
    final_evaluation: bool = Field(
        default=False,
        description="Whether final evaluation phase has been completed"
    )
    
    # Selection and final results
    generated_sql: Optional[str] = Field(
        default=None,
        description="Final selected SQL query after evaluation and selection"
    )
    
    successful_agent_name: Optional[str] = Field(
        default=None,
        description="Name of the agent that generated the successful SQL"
    )
    
    selection_metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metrics and scores from the SQL selection process"
    )
    
    selection_metrics_json: str = Field(
        default="",
        description="JSON string representation of selection_metrics for storage"
    )
    
    # SQL explanation
    sql_explanation: Optional[str] = Field(
        default=None,
        description="Human-readable explanation of the generated SQL query"
    )
    
    # Compatibility field for backward compatibility
    test_results: List[str] = Field(
        default_factory=lambda: FrozenList([]),
        description="Test results field maintained for backward compatibility"
    )
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = True  # Allow FrozenList and complex types
        validate_assignment = True  # Validate on field assignment
        
    @validator('generated_tests')
    def validate_generated_tests(cls, v):
        """Validate generated tests structure"""
        if v is None:
            return []
        validated = []
        for test in v:
            if isinstance(test, tuple) and len(test) == 2:
                thinking, answers = test
                if isinstance(answers, list):
                    validated.append((str(thinking), answers))
        return validated
        
    @validator('generated_sqls')
    def validate_generated_sqls(cls, v):
        """Validate generated SQLs list"""
        if v is None:
            return []
        # Filter out empty or whitespace-only SQL statements
        return [sql.strip() for sql in v if sql and sql.strip()]
        
    @validator('evaluation_results')
    def validate_evaluation_results(cls, v):
        """Validate evaluation results structure"""
        if v is None:
            return []
        validated = []
        for result in v:
            if isinstance(result, tuple) and len(result) == 2:
                thinking, feedback = result
                if isinstance(feedback, list):
                    validated.append((str(thinking), feedback))
        return validated
        
    @validator('test_results')
    def validate_test_results(cls, v):
        """Validate test results for backward compatibility"""
        if v is None:
            return FrozenList([])
        return FrozenList([str(result) for result in v if result])
        
    def has_tests(self) -> bool:
        """
        Check if tests have been generated.
        
        Returns:
            bool: True if tests exist
        """
        return len(self.generated_tests) > 0
        
    def has_sql_candidates(self) -> bool:
        """
        Check if SQL candidates have been generated.
        
        Returns:
            bool: True if SQL candidates exist
        """
        return len(self.generated_sqls) > 0
        
    def has_evaluations(self) -> bool:
        """
        Check if evaluations have been performed.
        
        Returns:
            bool: True if evaluation results exist
        """
        return len(self.evaluation_results) > 0
        
    def has_final_sql(self) -> bool:
        """
        Check if final SQL has been selected.
        
        Returns:
            bool: True if final SQL exists
        """
        return self.generated_sql is not None and bool(self.generated_sql.strip())
        
    def has_explanation(self) -> bool:
        """
        Check if SQL explanation has been generated.
        
        Returns:
            bool: True if explanation exists
        """
        return self.sql_explanation is not None and bool(self.sql_explanation.strip())
        
    def has_selection_metrics(self) -> bool:
        """
        Check if selection metrics are available.
        
        Returns:
            bool: True if selection metrics exist
        """
        return self.selection_metrics is not None and len(self.selection_metrics) > 0
        
    def get_test_count(self) -> int:
        """
        Get number of generated tests.
        
        Returns:
            int: Number of generated tests
        """
        return len(self.generated_tests)
        
    def get_sql_candidate_count(self) -> int:
        """
        Get number of generated SQL candidates.
        
        Returns:
            int: Number of SQL candidates
        """
        return len(self.generated_sqls)
        
    def get_evaluation_count(self) -> int:
        """
        Get number of evaluations performed.
        
        Returns:
            int: Number of evaluations
        """
        return len(self.evaluation_results)
        
    def get_successful_agent(self) -> str:
        """
        Get name of successful agent or default.
        
        Returns:
            str: Agent name or 'Unknown' if not available
        """
        return self.successful_agent_name if self.successful_agent_name else "Unknown"
        
    def is_generation_complete(self) -> bool:
        """
        Check if generation pipeline is complete.
        
        Returns:
            bool: True if final SQL and evaluation are complete
        """
        return self.has_final_sql() and self.final_evaluation
        
    def get_generation_summary(self) -> str:
        """
        Get a summary of generation results for logging/display.
        
        Returns:
            str: Human-readable generation summary
        """
        summary_parts = []
        
        if self.has_tests():
            summary_parts.append(f"{self.get_test_count()} tests")
            
        if self.has_sql_candidates():
            summary_parts.append(f"{self.get_sql_candidate_count()} SQL candidates")
            
        if self.has_evaluations():
            summary_parts.append(f"{self.get_evaluation_count()} evaluations")
            
        if self.has_final_sql():
            agent_info = f" by {self.get_successful_agent()}" if self.successful_agent_name else ""
            summary_parts.append(f"final SQL{agent_info}")
            
        if self.has_explanation():
            summary_parts.append("explanation")
            
        if not summary_parts:
            return "No generation results available"
            
        status = "complete" if self.is_generation_complete() else "in progress"
        return f"Generation results ({status}): {', '.join(summary_parts)}"