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
Enhanced evaluation flow implementing the 4-case evaluation system.

This module replaces the original evaluation system with a more sophisticated
approach that reduces false negatives and improves SQL selection accuracy.

Cases:
- Case A: Single SQL with 100% pass rate → Direct GOLD selection
- Case B: Multiple SQLs with 100% pass rate → SqlSelector for best choice  
- Case C: SQLs with 90-99% pass rate → EvaluatorSupervisor for deep analysis
- Case D: All SQLs < 90% pass rate → Escalation to next functionality level
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import time

from agents.core.agent_result_models import EnhancedEvaluationResult, EvaluationStatus
from agents.core.agent_initializer import AgentInitializer
from agents.test_reducer_agent import run_test_reducer
from agents.sql_selector_agent import run_sql_selector  
from agents.evaluator_supervisor_agent import run_evaluator_supervisor
from helpers.main_helpers.escalation_manager import EscalationManager, EscalationReason
from helpers.main_helpers.evaluation_logger import create_evaluation_logger, EvaluationEventType, LogLevel
from model.generator_type import GeneratorType
from model.evaluator_deps import EvaluatorDeps
from helpers.template_preparation import TemplateLoader
from helpers.main_helpers.main_evaluation import evaluate_sql_candidates

logger = logging.getLogger(__name__)


class EnhancedEvaluationFlow:
    """Enhanced evaluation flow with 4-case decision logic and auxiliary agents"""
    
    def __init__(self, agents_and_tools, session_id: str = None):
        self.agents_and_tools = agents_and_tools
        self.auxiliary_agents = {}
        self.processing_start_time = None
        self.eval_logger = create_evaluation_logger(session_id)
        
    async def initialize_auxiliary_agents(self) -> bool:
        """
        Initialize auxiliary agents using the same model config as Evaluator.
        
        Returns:
            bool: True if all auxiliary agents created successfully
        """
        evaluator_agent = getattr(self.agents_and_tools, 'evaluator_agent', None)
        if not evaluator_agent:
            logger.error("No evaluator agent available for auxiliary agent creation")
            return False
            
        # Extract model config from evaluator agent
        evaluator_model_config = {
            'name': getattr(evaluator_agent, 'name', 'Unknown'),
            # Add other model config extraction as needed
        }
        
        try:
            # Create TestReducer agent
            self.auxiliary_agents['test_reducer'] = AgentInitializer.create_test_reducer_agent(
                evaluator_model_config
            )
            
            # Create SqlSelector agent  
            self.auxiliary_agents['sql_selector'] = AgentInitializer.create_sql_selector_agent(
                evaluator_model_config
            )
            
            # Create EvaluatorSupervisor agent
            self.auxiliary_agents['evaluator_supervisor'] = AgentInitializer.create_evaluator_supervisor_agent(
                evaluator_model_config
            )
            
            # Verify all agents created
            missing_agents = []
            for agent_name, agent in self.auxiliary_agents.items():
                if agent is None:
                    missing_agents.append(agent_name)
            
            if missing_agents:
                logger.error(f"Failed to create auxiliary agents: {missing_agents}")
                return False
                
            logger.info(f"Successfully initialized {len(self.auxiliary_agents)} auxiliary agents")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing auxiliary agents: {e}")
            return False
    
    def calculate_pass_rates(self, evaluation_answers: List[str]) -> Dict[str, float]:
        """
        Calculate pass rates for each SQL from evaluation answers.
        
        Args:
            evaluation_answers: List of evaluation answers in format "SQL #n: OK, KO, ..."
            
        Returns:
            Dict mapping SQL identifiers to pass rates
        """
        pass_rates = {}
        
        for answer in evaluation_answers:
            if not answer.startswith("SQL #"):
                continue
                
            # Parse SQL identifier and test results
            parts = answer.split(":", 1)
            if len(parts) != 2:
                continue
                
            sql_id = parts[0].strip()
            test_results = parts[1].strip()
            
            # Count OK vs total tests
            results_list = [r.strip() for r in test_results.split(",")]
            ok_count = sum(1 for result in results_list if result == "OK")
            total_count = len(results_list)
            
            if total_count > 0:
                pass_rate = ok_count / total_count
                pass_rates[sql_id] = pass_rate
                logger.debug(f"{sql_id}: {ok_count}/{total_count} = {pass_rate:.1%}")
        
        return pass_rates
    
    def classify_evaluation_case(self, pass_rates: Dict[str, float]) -> Tuple[str, List[str], List[str], List[str]]:
        """
        Classify evaluation results into Cases A, B, C, or D.
        
        Args:
            pass_rates: Dictionary mapping SQL IDs to pass rates
            
        Returns:
            Tuple of (case, perfect_sqls, borderline_sqls, failed_sqls)
        """
        perfect_sqls = []      # 100% pass rate
        borderline_sqls = []   # 90-99% pass rate  
        failed_sqls = []       # < 90% pass rate
        
        for sql_id, pass_rate in pass_rates.items():
            if pass_rate >= 1.0:
                perfect_sqls.append(sql_id)
            elif pass_rate >= 0.9:
                borderline_sqls.append(sql_id)
            else:
                failed_sqls.append(sql_id)
        
        # Determine case
        if len(perfect_sqls) == 1 and len(borderline_sqls) == 0:
            case = "A"  # Single perfect SQL
        elif len(perfect_sqls) > 1:
            case = "B"  # Multiple perfect SQLs
        elif len(borderline_sqls) > 0:
            case = "C"  # Borderline SQLs (90-99%)
        else:
            case = "D"  # All failed (< 90%)
            
        logger.info(f"Evaluation Case {case}: {len(perfect_sqls)} perfect, {len(borderline_sqls)} borderline, {len(failed_sqls)} failed")
        
        return case, perfect_sqls, borderline_sqls, failed_sqls
    
    async def handle_case_a(self, perfect_sqls: List[str], state: Any) -> EnhancedEvaluationResult:
        """Handle Case A: Single SQL with 100% pass rate"""
        logger.info("Processing Case A: Single perfect SQL → Direct GOLD selection")
        
        sql_index = int(perfect_sqls[0].replace("SQL #", "")) - 1  # Convert to 0-based index
        selected_sql = state.generated_sqls[sql_index] if sql_index < len(state.generated_sqls) else None
        
        result = EnhancedEvaluationResult(
            thinking="Case A: Single SQL achieved perfect score, selected directly",
            answers=[f"SQL #{i+1}: GOLD" if i == sql_index else f"SQL #{i+1}: Not selected" 
                    for i in range(len(state.generated_sqls))],
            status=EvaluationStatus.GOLD,
            selected_sql_index=sql_index,
            selected_sql=selected_sql,
            evaluation_case="A",
            auxiliary_agents_used=[],
            best_pass_rate=1.0
        )
        
        return result
    
    async def handle_case_b(self, perfect_sqls: List[str], state: Any, pass_rates: Dict[str, float]) -> EnhancedEvaluationResult:
        """Handle Case B: Multiple SQLs with 100% pass rate"""
        logger.info(f"Processing Case B: {len(perfect_sqls)} perfect SQLs → SqlSelector")
        
        if not self.auxiliary_agents.get('sql_selector'):
            logger.warning("SqlSelector agent not available, selecting first perfect SQL")
            return await self.handle_case_a([perfect_sqls[0]], state)
        
        # Prepare equivalent SQLs for selection
        equivalent_sqls = []
        for sql_id in perfect_sqls:
            sql_index = int(sql_id.replace("SQL #", "")) - 1
            if sql_index < len(state.generated_sqls):
                equivalent_sqls.append(state.generated_sqls[sql_index])
        
        # Run SqlSelector
        selector_result = await run_sql_selector(
            self.auxiliary_agents['sql_selector'],
            state.question,
            state.used_mschema if hasattr(state, 'used_mschema') else state.full_mschema,
            equivalent_sqls,
            f"All {len(perfect_sqls)} SQLs passed 100% of tests",
            getattr(state, 'gold_sql_examples', [])
        )
        
        if selector_result and selector_result.selected_index < len(equivalent_sqls):
            # Map back to original SQL index
            selected_sql_id = perfect_sqls[selector_result.selected_index]
            sql_index = int(selected_sql_id.replace("SQL #", "")) - 1
            selected_sql = equivalent_sqls[selector_result.selected_index]
            
            result = EnhancedEvaluationResult(
                thinking=f"Case B: SqlSelector chose SQL #{selected_sql_id}",
                answers=[f"SQL #{i+1}: GOLD" if i == sql_index else f"SQL #{i+1}: Not selected"
                        for i in range(len(state.generated_sqls))],
                status=EvaluationStatus.GOLD,
                selected_sql_index=sql_index,
                selected_sql=selected_sql,
                selector_reasoning=selector_result.thinking,
                evaluation_case="B",
                auxiliary_agents_used=["SqlSelector"],
                best_pass_rate=1.0
            )
        else:
            logger.warning("SqlSelector failed, falling back to first perfect SQL")
            result = await self.handle_case_a([perfect_sqls[0]], state)
            
        return result
    
    async def handle_case_c(self, borderline_sqls: List[str], state: Any, evaluation_answers: List[str], evaluation_thinking: str) -> EnhancedEvaluationResult:
        """Handle Case C: SQLs with 90-99% pass rate"""
        logger.info(f"Processing Case C: {len(borderline_sqls)} borderline SQLs → EvaluatorSupervisor")
        
        if not self.auxiliary_agents.get('evaluator_supervisor'):
            logger.warning("EvaluatorSupervisor agent not available, marking as FAILED")
            return EnhancedEvaluationResult(
                thinking="Case C: No supervisor available for borderline cases",
                answers=[f"SQL #{i+1}: FAILED - No supervisor" for i in range(len(state.generated_sqls))],
                status=EvaluationStatus.FAILED,
                evaluation_case="C",
                auxiliary_agents_used=[],
                requires_escalation=True,
                escalation_context="No EvaluatorSupervisor available for borderline analysis"
            )
        
        # Prepare borderline SQLs for supervisor analysis
        borderline_sql_texts = []
        for sql_id in borderline_sqls:
            sql_index = int(sql_id.replace("SQL #", "")) - 1
            if sql_index < len(state.generated_sqls):
                borderline_sql_texts.append(state.generated_sqls[sql_index])
        
        # Run EvaluatorSupervisor
        supervisor_result = await run_evaluator_supervisor(
            self.auxiliary_agents['evaluator_supervisor'],
            state.question,
            state.used_mschema if hasattr(state, 'used_mschema') else state.full_mschema,
            borderline_sql_texts,
            "\n".join(evaluation_answers),
            f"Borderline SQLs: {', '.join(borderline_sqls)}",
            evaluation_thinking,
            getattr(state, 'gold_sql_examples', [])
        )
        
        if supervisor_result:
            if supervisor_result.final_decision == EvaluationStatus.GOLD and supervisor_result.recommended_sql_index is not None:
                # Map back to original SQL index
                original_sql_index = int(borderline_sqls[supervisor_result.recommended_sql_index].replace("SQL #", "")) - 1
                selected_sql = borderline_sql_texts[supervisor_result.recommended_sql_index]
                
                result = EnhancedEvaluationResult(
                    thinking=f"Case C: EvaluatorSupervisor promoted SQL to GOLD",
                    answers=[f"SQL #{i+1}: GOLD" if i == original_sql_index else f"SQL #{i+1}: Not selected"
                            for i in range(len(state.generated_sqls))],
                    status=EvaluationStatus.GOLD,
                    selected_sql_index=original_sql_index,
                    selected_sql=selected_sql,
                    supervisor_assessment=supervisor_result.thinking,
                    evaluation_case="C",
                    auxiliary_agents_used=["EvaluatorSupervisor"]
                )
            else:
                # Supervisor marked as FAILED
                result = EnhancedEvaluationResult(
                    thinking="Case C: EvaluatorSupervisor determined all SQLs inadequate",
                    answers=[f"SQL #{i+1}: FAILED" for i in range(len(state.generated_sqls))],
                    status=EvaluationStatus.FAILED,
                    supervisor_assessment=supervisor_result.thinking,
                    evaluation_case="C",
                    auxiliary_agents_used=["EvaluatorSupervisor"],
                    requires_escalation=True,
                    escalation_context=f"EvaluatorSupervisor analysis: {supervisor_result.detailed_assessment}"
                )
        else:
            logger.error("EvaluatorSupervisor failed to execute")
            result = EnhancedEvaluationResult(
                thinking="Case C: EvaluatorSupervisor execution failed",
                answers=[f"SQL #{i+1}: FAILED - Supervisor error" for i in range(len(state.generated_sqls))],
                status=EvaluationStatus.FAILED,
                evaluation_case="C",
                auxiliary_agents_used=["EvaluatorSupervisor"],
                requires_escalation=True,
                escalation_context="EvaluatorSupervisor execution failed"
            )
            
        return result
    
    async def handle_case_d(self, state: Any, pass_rates: Dict[str, float]) -> EnhancedEvaluationResult:
        """Handle Case D: All SQLs < 90% pass rate"""
        logger.info("Processing Case D: All SQLs failed → Escalation required")
        
        best_pass_rate = max(pass_rates.values()) if pass_rates else 0.0
        
        result = EnhancedEvaluationResult(
            thinking=f"Case D: All SQLs below 90% threshold (best: {best_pass_rate:.1%})",
            answers=[f"SQL #{i+1}: FAILED - Below threshold" for i in range(len(state.generated_sqls))],
            status=EvaluationStatus.FAILED,
            evaluation_case="D",
            auxiliary_agents_used=[],
            best_pass_rate=best_pass_rate,
            requires_escalation=True,
            escalation_context=f"All {len(pass_rates)} SQL candidates failed to meet 90% pass rate threshold"
        )
        
        return result
    
    async def run_enhanced_evaluation(self, state: Any) -> EnhancedEvaluationResult:
        """
        Run the complete enhanced evaluation flow with 4-case logic.
        
        Args:
            state: System state containing generated SQLs and test data
            
        Returns:
            EnhancedEvaluationResult with final decision and metadata
        """
        self.processing_start_time = time.time()
        
        # Initialize logging
        sql_count = len(state.generated_sqls) if hasattr(state, 'generated_sqls') else 0
        test_count = sum(len(answers) for _, answers in state.generated_tests) if hasattr(state, 'generated_tests') else 0
        functionality_level = getattr(state, 'functionality_level', 'BASIC')
        
        self.eval_logger.start_evaluation(
            question=state.question,
            sql_count=sql_count,
            functionality_level=functionality_level,
            test_count=test_count
        )
        
        try:
            # Step 1: Initialize auxiliary agents
            if not await self.initialize_auxiliary_agents():
                logger.error("Failed to initialize auxiliary agents")
                return EnhancedEvaluationResult(
                    thinking="Failed to initialize auxiliary agents",
                    answers=[f"SQL #{i+1}: ERROR" for i in range(len(state.generated_sqls) if hasattr(state, 'generated_sqls') else 0)],
                    status=EvaluationStatus.FAILED,
                    requires_escalation=True,
                    escalation_context="Auxiliary agent initialization failed"
                )
            
            # Step 2: Run TestReducer if available (optional semantic deduplication)
            original_tests = []
            if hasattr(state, 'generated_tests') and state.generated_tests:
                for thinking, answers in state.generated_tests:
                    original_tests.extend(answers)
                
                if self.auxiliary_agents.get('test_reducer') and len(original_tests) > 5:
                    logger.info(f"Running TestReducer on {len(original_tests)} tests")
                    test_thinking = "Combined test generation thinking"  # Simplified for now
                    
                    reducer_result = await run_test_reducer(
                        self.auxiliary_agents['test_reducer'],
                        original_tests,
                        test_thinking,
                        state.question,
                        state.used_mschema if hasattr(state, 'used_mschema') else state.full_mschema
                    )
                    
                    if reducer_result and len(reducer_result.reduced_tests) < len(original_tests):
                        logger.info(f"TestReducer reduced tests from {len(original_tests)} to {len(reducer_result.reduced_tests)}")
                        # Update state with reduced tests
                        state.generated_tests = [(reducer_result.thinking, reducer_result.reduced_tests)]
            
            # Step 3: Run standard evaluation to get baseline results
            logger.info("Running standard evaluation for baseline results")
            evaluation_thinking, evaluation_answers, test_units = await evaluate_sql_candidates(state, self.agents_and_tools)
            
            if not evaluation_answers:
                logger.error("No evaluation answers returned from standard evaluation")
                return EnhancedEvaluationResult(
                    thinking="Standard evaluation failed to produce answers",
                    answers=[],
                    status=EvaluationStatus.FAILED,
                    requires_escalation=True,
                    escalation_context="Standard evaluation produced no answers"
                )
            
            # Step 4: Calculate pass rates and classify case
            pass_rates = self.calculate_pass_rates(evaluation_answers)
            case, perfect_sqls, borderline_sqls, failed_sqls = self.classify_evaluation_case(pass_rates)
            
            # Log case classification
            self.eval_logger.log_case_classification(
                case=case,
                pass_rates=pass_rates,
                perfect_count=len(perfect_sqls),
                borderline_count=len(borderline_sqls),
                failed_count=len(failed_sqls)
            )
            
            # Step 5: Handle the specific case
            result = None
            if case == "A":
                result = await self.handle_case_a(perfect_sqls, state)
            elif case == "B":
                result = await self.handle_case_b(perfect_sqls, state, pass_rates)
            elif case == "C":
                result = await self.handle_case_c(borderline_sqls, state, evaluation_answers, evaluation_thinking)
            elif case == "D":
                result = await self.handle_case_d(state, pass_rates)
            
            # Step 6: Add processing metadata
            if result:
                processing_time = (time.time() - self.processing_start_time) * 1000  # Convert to ms
                result.processing_time_ms = processing_time
                result.pass_rates = {k: v for k, v in pass_rates.items()}
                
                # Preserve Gold SQL examples
                if hasattr(state, 'gold_sql_examples'):
                    result.gold_sql_examples = state.gold_sql_examples
                
                # Log SQL selection if applicable
                if result.selected_sql_index is not None:
                    self.eval_logger.log_sql_selection(
                        case=case,
                        selected_index=result.selected_sql_index,
                        selected_sql=result.selected_sql or "",
                        reasoning=result.selector_reasoning or result.supervisor_assessment or "Direct selection",
                        confidence=getattr(result, 'confidence_score', None)
                    )
                
                # Log escalation if required
                if result.requires_escalation:
                    current_level = getattr(state, 'functionality_level', 'BASIC')
                    next_level = GeneratorType.from_string(current_level).get_next_level()
                    next_level_name = next_level.display_name if next_level else "None"
                    
                    self.eval_logger.log_escalation(
                        reason="evaluation_failure",
                        current_level=current_level,
                        next_level=next_level_name,
                        failure_context=result.escalation_context or "No context provided",
                        failed_sql_count=sql_count
                    )
                
                # Complete evaluation logging
                self.eval_logger.complete_evaluation(result, result.status)
            
            logger.info(f"Enhanced evaluation complete: Case {case}, Status: {result.status.value}, Time: {result.processing_time_ms:.1f}ms")
            return result
            
        except Exception as e:
            # Log the error
            self.eval_logger.log_error(
                error_message=f"Enhanced evaluation flow failed: {str(e)}",
                error_type=type(e).__name__,
                context={"traceback": str(e)}
            )
            
            logger.error(f"Enhanced evaluation flow failed: {e}")
            import traceback
            logger.error(f"Enhanced evaluation traceback: {traceback.format_exc()}")
            
            error_result = EnhancedEvaluationResult(
                thinking=f"Enhanced evaluation flow error: {str(e)}",
                answers=[f"SQL #{i+1}: ERROR" for i in range(len(state.generated_sqls) if hasattr(state, 'generated_sqls') else 0)],
                status=EvaluationStatus.FAILED,
                requires_escalation=True,
                escalation_context=f"Evaluation flow exception: {str(e)}"
            )
            
            # Complete logging even on error
            self.eval_logger.complete_evaluation(error_result, EvaluationStatus.FAILED)
            
            return error_result


async def run_enhanced_evaluation_flow(state: Any, agents_and_tools: Any, session_id: str = None) -> Tuple[EnhancedEvaluationResult, Dict[str, Any]]:
    """
    Entry point for enhanced evaluation flow with comprehensive logging.
    
    Args:
        state: System state containing generated SQLs and test data
        agents_and_tools: Agent manager with evaluator and other agents
        session_id: Optional session identifier for logging
        
    Returns:
        Tuple of (EnhancedEvaluationResult, evaluation_logs_summary)
    """
    flow = EnhancedEvaluationFlow(agents_and_tools, session_id)
    result = await flow.run_enhanced_evaluation(state)
    
    # Return both result and logging summary
    logs_summary = flow.eval_logger.get_evaluation_summary()
    
    return result, logs_summary