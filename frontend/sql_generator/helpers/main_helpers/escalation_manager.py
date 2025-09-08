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
Escalation manager for handling Case D: SQL generation failure escalation.

Manages the progression from BASIC → ADVANCED → EXPERT functionality levels
when all SQL candidates fail to achieve acceptable evaluation scores.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

from model.generator_type import GeneratorType

logger = logging.getLogger(__name__)


class EscalationReason(Enum):
    """Reasons for escalating to higher functionality level"""
    ALL_FAILED_EVALUATION = "all_sql_failed_evaluation"  # Case D: all SQLs below threshold
    NO_SQL_GENERATED = "no_sql_generated"  # SQL generation completely failed
    VALIDATION_FAILED = "validation_failed"  # SQL validation issues
    EXECUTION_FAILED = "execution_failed"  # SQL execution problems


class EscalationContext:
    """Context information passed between escalation levels"""
    
    def __init__(
        self,
        reason: EscalationReason,
        current_level: GeneratorType,
        question: str,
        failed_sqls: List[str] = None,
        evaluation_results: Dict[str, Any] = None,
        failure_analysis: str = None,
        previous_attempts: List[Dict[str, Any]] = None
    ):
        self.reason = reason
        self.current_level = current_level
        self.question = question
        self.failed_sqls = failed_sqls or []
        self.evaluation_results = evaluation_results or {}
        self.failure_analysis = failure_analysis or ""
        self.previous_attempts = previous_attempts or []
        
    def to_context_string(self) -> str:
        """Format escalation context for next level prompt"""
        context_parts = [
            f"ESCALATION CONTEXT:",
            f"- Reason: {self.reason.value}",
            f"- Previous Level: {self.current_level.display_name}",
            f"- Question: {self.question}",
        ]
        
        if self.failed_sqls:
            context_parts.append(f"- Failed SQL Count: {len(self.failed_sqls)}")
            context_parts.append("- Failed SQLs:")
            for i, sql in enumerate(self.failed_sqls[:3], 1):  # Limit to first 3
                context_parts.append(f"  {i}. {sql}")
            if len(self.failed_sqls) > 3:
                context_parts.append(f"  ... and {len(self.failed_sqls) - 3} more")
        
        if self.evaluation_results:
            context_parts.append("- Evaluation Summary:")
            for key, value in self.evaluation_results.items():
                context_parts.append(f"  {key}: {value}")
        
        if self.failure_analysis:
            context_parts.append(f"- Failure Analysis: {self.failure_analysis}")
        
        if self.previous_attempts:
            context_parts.append(f"- Previous Attempts: {len(self.previous_attempts)}")
        
        return "\n".join(context_parts)


class EscalationManager:
    """Manages escalation between functionality levels for failed SQL generation"""
    
    # Maximum escalation attempts per level
    MAX_ATTEMPTS_PER_LEVEL = 2
    
    # Escalation chain
    ESCALATION_CHAIN = [GeneratorType.BASIC, GeneratorType.ADVANCED, GeneratorType.EXPERT]
    
    @staticmethod
    def get_next_level(current_level: GeneratorType) -> Optional[GeneratorType]:
        """
        Get the next functionality level in the escalation chain.
        
        Args:
            current_level: Current GeneratorType level
            
        Returns:
            Next GeneratorType level, or None if at maximum level
        """
        try:
            current_index = EscalationManager.ESCALATION_CHAIN.index(current_level)
            if current_index < len(EscalationManager.ESCALATION_CHAIN) - 1:
                return EscalationManager.ESCALATION_CHAIN[current_index + 1]
            return None
        except ValueError:
            logger.error(f"Unknown generator type in escalation: {current_level}")
            return None
    
    @staticmethod
    def should_escalate(
        current_level: GeneratorType,
        evaluation_results: Dict[str, Any],
        attempt_count: int,
        evaluation_threshold: int = 90
    ) -> Tuple[bool, EscalationReason]:
        """
        Determine if escalation is needed based on evaluation results.
        
        Args:
            current_level: Current functionality level
            evaluation_results: Results from evaluation process
            attempt_count: Number of attempts at current level
            evaluation_threshold: Minimum pass rate threshold (0-100)
            
        Returns:
            Tuple of (should_escalate, reason)
        """
        # Check if at maximum level
        if current_level == GeneratorType.EXPERT:
            logger.info("Already at EXPERT level, cannot escalate further")
            return False, None
        
        if attempt_count >= EscalationManager.MAX_ATTEMPTS_PER_LEVEL:
            logger.info(f"Reached maximum attempts ({attempt_count}) at {current_level.display_name} level")
            return True, EscalationReason.ALL_FAILED_EVALUATION
        
        # Analyze evaluation results for escalation triggers
        if not evaluation_results:
            return True, EscalationReason.NO_SQL_GENERATED
        
        # Check for Case D: all SQLs failed evaluation
        status = evaluation_results.get('status')
        if status == 'FAILED':
            best_pass_rate = evaluation_results.get('best_pass_rate', 0.0)
            threshold_ratio = evaluation_threshold / 100.0
            if best_pass_rate < threshold_ratio:
                logger.info(f"All SQLs below {evaluation_threshold}% threshold (best: {best_pass_rate:.1%})")
                return True, EscalationReason.ALL_FAILED_EVALUATION
        
        # Check for SQL generation failures
        generated_sqls = evaluation_results.get('generated_sqls', [])
        if not generated_sqls:
            return True, EscalationReason.NO_SQL_GENERATED
        
        # Default: no escalation needed
        return False, None
    
    @staticmethod
    def create_escalation_context(
        reason: EscalationReason,
        current_level: GeneratorType,
        state: Any,
        evaluation_results: Dict[str, Any] = None
    ) -> EscalationContext:
        """
        Create escalation context from current state and results.
        
        Args:
            reason: Reason for escalation
            current_level: Current functionality level
            state: System state containing question and generation results
            evaluation_results: Results from evaluation process
            
        Returns:
            EscalationContext with relevant information
        """
        failed_sqls = []
        if hasattr(state, 'generated_sqls') and state.generated_sqls:
            failed_sqls = state.generated_sqls
        
        # Extract failure analysis from evaluation
        failure_analysis = ""
        if evaluation_results:
            if 'escalation_context' in evaluation_results:
                failure_analysis = evaluation_results['escalation_context']
            elif 'evaluation_case' in evaluation_results:
                case = evaluation_results['evaluation_case']
                failure_analysis = f"Evaluation Case {case} - insufficient pass rates"
        
        # Build previous attempts info
        previous_attempts = []
        if hasattr(state, 'escalation_history'):
            previous_attempts = state.escalation_history
        
        context = EscalationContext(
            reason=reason,
            current_level=current_level,
            question=state.question,
            failed_sqls=failed_sqls,
            evaluation_results=evaluation_results,
            failure_analysis=failure_analysis,
            previous_attempts=previous_attempts
        )
        
        return context
    
    @staticmethod
    def update_state_for_escalation(
        state: Any,
        next_level: GeneratorType,
        escalation_context: EscalationContext
    ) -> None:
        """
        Update system state for escalation to next level.
        
        Args:
            state: System state to update
            next_level: Next functionality level to escalate to
            escalation_context: Context information for escalation
        """
        # Update functionality level
        state.functionality_level = next_level.display_name
        
        # Set escalation flags based on the level we're escalating to
        if hasattr(state, 'execution'):
            if next_level == GeneratorType.ADVANCED:
                state.execution.advanced_escalation = True
                logger.info("Setting advanced_escalation flag to True")
            elif next_level == GeneratorType.EXPERT:
                state.execution.expert_escalation = True
                logger.info("Setting expert_escalation flag to True")
        
        # Add escalation history
        if not hasattr(state, 'escalation_history'):
            state.escalation_history = []
        
        escalation_record = {
            'from_level': escalation_context.current_level.display_name,
            'to_level': next_level.display_name,
            'reason': escalation_context.reason.value,
            'failed_sqls_count': len(escalation_context.failed_sqls),
            'failure_analysis': escalation_context.failure_analysis
        }
        state.escalation_history.append(escalation_record)
        
        # Add escalation context to state for next level's use
        state.escalation_context = escalation_context.to_context_string()
        
        # Reset generation results for new attempt
        if hasattr(state, 'generated_sqls'):
            state.generated_sqls = []
        if hasattr(state, 'sql_results'):
            state.sql_results = []
        if hasattr(state, 'evaluation_results'):
            state.evaluation_results = None
        
        logger.info(f"Escalated from {escalation_context.current_level.display_name} to {next_level.display_name}")
    
    @staticmethod
    def handle_escalation(
        state: Any,
        current_level: GeneratorType,
        evaluation_results: Dict[str, Any],
        attempt_count: int = 1
    ) -> Tuple[bool, Optional[GeneratorType], Optional[EscalationContext]]:
        """
        Handle complete escalation process from evaluation results.
        
        Args:
            state: System state containing generation and evaluation data
            current_level: Current functionality level
            evaluation_results: Results from evaluation process
            attempt_count: Number of attempts at current level
            
        Returns:
            Tuple of (escalated, new_level, escalation_context)
        """
        # Check if escalation is needed
        should_escalate, reason = EscalationManager.should_escalate(
            current_level, evaluation_results, attempt_count
        )
        
        if not should_escalate:
            return False, None, None
        
        # Get next level
        next_level = EscalationManager.get_next_level(current_level)
        if not next_level:
            logger.warning(f"Cannot escalate beyond {current_level.display_name} level")
            return False, None, None
        
        # Create escalation context
        escalation_context = EscalationManager.create_escalation_context(
            reason, current_level, state, evaluation_results
        )
        
        # Update state for escalation
        EscalationManager.update_state_for_escalation(state, next_level, escalation_context)
        
        return True, next_level, escalation_context