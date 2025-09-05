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
- Case C: SQLs with borderline pass rate → EvaluatorSupervisor for deep analysis
- Case D: All SQLs below threshold → Escalation to next functionality level
"""

import logging
from typing import Dict, Any, List, Tuple
import time
import json

from agents.core.agent_result_models import EnhancedEvaluationResult, EvaluationStatus
from agents.core.agent_initializer import AgentInitializer
from agents.test_reducer_agent import run_test_reducer
from agents.sql_selector_agent import run_sql_selector  
from agents.evaluator_supervisor_agent import run_evaluator_supervisor
from helpers.main_helpers.evaluation_logger import create_evaluation_logger
from helpers.sql_complexity_analyzer import SQLComplexityAnalyzer
from model.generator_type import GeneratorType
from helpers.main_helpers.main_evaluation import evaluate_sql_candidates

logger = logging.getLogger(__name__)


class EnhancedEvaluationFlow:
    """Enhanced evaluation flow with 4-case decision logic and auxiliary agents"""
    
    def __init__(self, agents_and_tools, session_id: str = None, evaluation_threshold: int = 90):
        self.agents_and_tools = agents_and_tools
        self.auxiliary_agents = {}
        self.processing_start_time = None
        self.eval_logger = create_evaluation_logger(session_id)
        self.evaluation_threshold = evaluation_threshold
        self.threshold_ratio = evaluation_threshold / 100.0
        
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
            
        # Get evaluator config from agents_and_tools if available
        evaluator_model_config = None
        
        # First try to get evaluator_config directly from agents_and_tools
        if hasattr(self.agents_and_tools, 'evaluator_config'):
            evaluator_model_config = self.agents_and_tools.evaluator_config
        # Then try to get from workspace config stored in agents_and_tools
        elif hasattr(self.agents_and_tools, 'workspace') and self.agents_and_tools.workspace:
            workspace = self.agents_and_tools.workspace
            evaluator_model_config = workspace.get('test_evaluator_agent')
            if not evaluator_model_config:
                # Fallback to test_gen_agent_1 for backward compatibility
                evaluator_model_config = workspace.get('test_gen_agent_1')
        
        # If still no config, try to extract from the agent itself
        if not evaluator_model_config:
            if hasattr(evaluator_agent, 'agent_config'):
                evaluator_model_config = evaluator_agent.agent_config
            elif hasattr(evaluator_agent, 'model_config'):
                evaluator_model_config = evaluator_agent.model_config
            else:
                logger.error("Could not extract model config for auxiliary agents - no configuration available")
                return False
        
        try:
            # Create TestReducer agent
            self.auxiliary_agents['test_reducer'] = AgentInitializer.create_test_reducer_agent(
                evaluator_model_config,
                default_model_config=None
            )
            
            # Create SqlSelector agent  
            self.auxiliary_agents['sql_selector'] = AgentInitializer.create_sql_selector_agent(
                evaluator_model_config,
                default_model_config=None
            )
            
            # Create EvaluatorSupervisor agent
            self.auxiliary_agents['evaluator_supervisor'] = AgentInitializer.create_evaluator_supervisor_agent(
                evaluator_model_config,
                default_model_config=None
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
    
    def select_simplest_sql(self, sql_ids: List[str], sql_texts: List[str], state: Any) -> Tuple[str, float]:
        """
        Select the simplest SQL from a list using complexity analysis.
        
        Args:
            sql_ids: List of SQL IDs (e.g., ["SQL #1", "SQL #2"])
            sql_texts: List of SQL text strings
            state: System state for logging
            
        Returns:
            Tuple of (selected_sql_id, complexity_score)
        """
        analyzer = SQLComplexityAnalyzer()
        min_complexity = float('inf')
        selected_sql_id = sql_ids[0]  # Default to first
        selected_complexity = 0.0
        
        for i, sql_text in enumerate(sql_texts):
            try:
                metrics = analyzer.analyze_query(sql_text)
                complexity = analyzer.calculate_complexity_score(metrics)
                
                logger.debug(f"{sql_ids[i]} complexity: {complexity} (tokens: {metrics.get('tokens', 0)}, joins: {metrics.get('joins', 0)})")
                
                if complexity < min_complexity:
                    min_complexity = complexity
                    selected_sql_id = sql_ids[i]
                    selected_complexity = complexity
                    
            except Exception as e:
                # Fallback: use character length if sqlparse fails
                complexity = len(sql_text)
                logger.warning(f"Failed to analyze {sql_ids[i]} with sqlparse, using length: {complexity}. Error: {e}")
                
                if complexity < min_complexity:
                    min_complexity = complexity
                    selected_sql_id = sql_ids[i]
                    selected_complexity = complexity
        
        logger.info(f"Selected {selected_sql_id} as simplest with complexity score: {selected_complexity}")
        return selected_sql_id, selected_complexity
    
    def determine_evaluation_case(self, pass_rates: Dict[str, float]) -> Tuple[str, str, str, List[str]]:
        """
        Determine evaluation case using new Python logic (no LLM).
        
        Args:
            pass_rates: Dictionary mapping SQL IDs to pass rates
            
        Returns:
            Tuple of (case, sql_status, selected_sql_id_or_message, candidate_sql_ids)
        """
        perfect_sqls = [sql_id for sql_id, rate in pass_rates.items() if rate == 1.0]
        above_threshold = [sql_id for sql_id, rate in pass_rates.items() if rate >= self.threshold_ratio]
        
        if len(perfect_sqls) == 1:
            # Case A-GOLD: One SQL with 100%
            return "A-GOLD", "GOLD", perfect_sqls[0], perfect_sqls
        elif len(perfect_sqls) > 1:
            # Case B-GOLD: Multiple SQLs with 100%  
            return "B-GOLD", "GOLD", "MULTIPLE_PERFECT", perfect_sqls
        elif len(above_threshold) == 1:
            # Case A-SILVER: One SQL above threshold but not 100%
            return "A-SILVER", "SILVER", above_threshold[0], above_threshold
        elif len(above_threshold) > 1:
            # Find the best pass rate among above-threshold SQLs
            best_rate = max(pass_rates[sql_id] for sql_id in above_threshold)
            best_sqls = [sql_id for sql_id in above_threshold if pass_rates[sql_id] == best_rate]
            
            if len(best_sqls) == 1:
                # Case C-SILVER: One SQL with highest rate above threshold
                return "C-SILVER", "SILVER", best_sqls[0], best_sqls
            else:
                # Case B-SILVER: Multiple SQLs with same best rate above threshold
                return "B-SILVER", "SILVER", "MULTIPLE_BEST", best_sqls
        else:
            # Case D-FAILED: All below threshold
            return "D-FAILED", "FAILED", "ALL_FAILED", list(pass_rates.keys())
    
    def classify_evaluation_case(self, pass_rates: Dict[str, float]) -> Tuple[str, List[str], List[str], List[str]]:
        """
        Classify evaluation results into Cases A, B, C, or D.
        
        Args:
            pass_rates: Dictionary mapping SQL IDs to pass rates
            
        Returns:
            Tuple of (case, perfect_sqls, borderline_sqls, failed_sqls)
        """
        perfect_sqls = []      # 100% pass rate
        borderline_sqls = []   # threshold% to 99% pass rate  
        failed_sqls = []       # < threshold% pass rate
        
        for sql_id, pass_rate in pass_rates.items():
            if pass_rate >= 1.0:
                perfect_sqls.append(sql_id)
            elif pass_rate >= self.threshold_ratio:
                borderline_sqls.append(sql_id)
            else:
                failed_sqls.append(sql_id)
        
        # Determine case
        if len(perfect_sqls) == 1 and len(borderline_sqls) == 0:
            case = "A"  # Single perfect SQL
        elif len(perfect_sqls) > 1:
            case = "B"  # Multiple perfect SQLs
        elif len(borderline_sqls) > 0:
            case = "C"  # Borderline SQLs (threshold% to 99%)
        else:
            case = "D"  # All failed (< threshold%)
            
        logger.info(f"Evaluation Case {case}: {len(perfect_sqls)} perfect, {len(borderline_sqls)} borderline, {len(failed_sqls)} failed (threshold: {self.evaluation_threshold}%)")
        
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
        f"""Handle Case C: SQLs with {self.evaluation_threshold}-99% pass rate"""
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
            getattr(state, 'gold_sql_examples', []),
            evaluation_threshold=self.evaluation_threshold
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
        f"""Handle Case D: All SQLs < {self.evaluation_threshold}% pass rate"""
        logger.info(f"Processing Case D: All SQLs failed → Escalation required (threshold: {self.evaluation_threshold}%)")
        
        best_pass_rate = max(pass_rates.values()) if pass_rates else 0.0
        
        result = EnhancedEvaluationResult(
            thinking=f"Case D: All SQLs below {self.evaluation_threshold}% threshold (best: {best_pass_rate:.1%})",
            answers=[f"SQL #{i+1}: FAILED - Below threshold" for i in range(len(state.generated_sqls))],
            status=EvaluationStatus.FAILED,
            evaluation_case="D",
            auxiliary_agents_used=[],
            best_pass_rate=best_pass_rate,
            requires_escalation=True,
            escalation_context=f"All {len(pass_rates)} SQL candidates failed to meet {self.evaluation_threshold}% pass rate threshold"
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
                    answers=[f"SQL #{i+1}: KO - Failed to initialize evaluation agents for testing" for i in range(len(state.generated_sqls) if hasattr(state, 'generated_sqls') else 0)],
                    status=EvaluationStatus.FAILED,
                    requires_escalation=True,
                    escalation_context="Auxiliary agent initialization failed"
                )
            
            # Step 2: Run TestReducer if available (optional semantic deduplication)
            original_tests = []
            if hasattr(state, 'generated_tests') and state.generated_tests:
                for thinking, answers in state.generated_tests:
                    original_tests.extend(answers)
                
                # Determine if multiple test generators are active
                multiple_test_generators_active = False
                try:
                    pools = getattr(self.agents_and_tools, 'agent_pools', None)
                    if pools:
                        test_pool = getattr(pools, 'test_unit_generation_agents_pool', []) or []
                        multiple_test_generators_active = len([a for a in test_pool if a is not None]) > 1
                except Exception as e:
                    logger.debug(f"Could not determine test generator pool size in enhanced flow: {e}")
                
                if (
                    multiple_test_generators_active
                    and self.auxiliary_agents.get('test_reducer')
                    and len(original_tests) > 5
                ):
                    logger.info(f"Running TestReducer on {len(original_tests)} tests (multiple test generators active)")
                    test_thinking = "Combined test generation thinking"  # Simplified for now
                    
                    reducer_result = await run_test_reducer(
                        self.auxiliary_agents['test_reducer'],
                        original_tests,
                        test_thinking,
                        state.question,
                        state.used_mschema if hasattr(state, 'used_mschema') else state.full_mschema
                    )
                    
                    if reducer_result and len(reducer_result.reduced_tests) < len(original_tests):
                        logger.info(
                            f"TestReducer reduced tests from {len(original_tests)} to {len(reducer_result.reduced_tests)}"
                        )
                        # Update state with reduced tests as single list format
                        state.generated_tests_json = json.dumps(
                            reducer_result.reduced_tests, ensure_ascii=False
                        )
                else:
                    # Log why semantic filtering was skipped in enhanced flow
                    if not multiple_test_generators_active:
                        logger.info("Skipping TestReducer in enhanced flow: only one test generator active")
                    elif len(original_tests) <= 5:
                        logger.debug("Skipping TestReducer in enhanced flow: not enough tests to benefit")
            
            # Step 3: Run new parallel evaluation to get baseline results
            logger.info("Running parallel SQL evaluation for baseline results")
            evaluation_results = await evaluate_sql_candidates(state, self.agents_and_tools)
            
            # Extract thinking and answers from the results
            if evaluation_results and len(evaluation_results) > 0:
                evaluation_thinking, evaluation_answers = evaluation_results[0]
                # Get test units from state if available
                test_units = getattr(state, 'filtered_tests', getattr(state, 'test_answers', []))
            else:
                evaluation_thinking = "No evaluation results"
                evaluation_answers = []
                test_units = []
            
            if not evaluation_answers:
                logger.error("No evaluation answers returned from standard evaluation")
                return EnhancedEvaluationResult(
                    thinking="Standard evaluation failed to produce answers",
                    answers=[],
                    status=EvaluationStatus.FAILED,
                    requires_escalation=True,
                    escalation_context="Standard evaluation produced no answers"
                )
            
            # Step 4: Calculate pass rates and determine case with new Python logic
            from datetime import datetime
            state.execution.evaluation_start_time = state.execution.evaluation_start_time or datetime.now()
            
            pass_rates = self.calculate_pass_rates(evaluation_answers)
            evaluation_case, sql_status, selected_info, candidate_sqls = self.determine_evaluation_case(pass_rates)
            
            # Update state with evaluation results
            state.execution.evaluation_case = evaluation_case
            state.execution.sql_status = sql_status
            state.execution.evaluation_details = evaluation_answers
            state.execution.pass_rates = pass_rates
            
            # Log case classification
            self.eval_logger.log_case_classification(
                case=evaluation_case,
                pass_rates=pass_rates,
                perfect_count=len([sql for sql, rate in pass_rates.items() if rate == 1.0]),
                borderline_count=len([sql for sql, rate in pass_rates.items() if 1.0 > rate >= self.threshold_ratio]),
                failed_count=len([sql for sql, rate in pass_rates.items() if rate < self.threshold_ratio])
            )
            
            logger.info(f"Evaluation Case {evaluation_case}: Status {sql_status}")
            
            # Step 5: Handle the specific case with new logic
            result = None
            selected_sql_index = None
            selected_sql = None
            
            if selected_info in ["MULTIPLE_PERFECT", "MULTIPLE_BEST"]:
                # Case B: Multiple SQLs need selection via complexity analysis  
                state.execution.sql_selection_start_time = datetime.now()
                
                # Get SQL texts for complexity analysis
                sql_texts = []
                for sql_id in candidate_sqls:
                    sql_idx = int(sql_id.replace("SQL #", "")) - 1
                    if sql_idx < len(state.generated_sqls):
                        sql_texts.append(state.generated_sqls[sql_idx])
                
                # Select simplest SQL using complexity analysis
                selected_sql_id, complexity_score = self.select_simplest_sql(candidate_sqls, sql_texts, state)
                selected_sql_index = int(selected_sql_id.replace("SQL #", "")) - 1
                selected_sql = state.generated_sqls[selected_sql_index] if selected_sql_index < len(state.generated_sqls) else None
                
                # Store complexity score
                state.execution.selected_sql_complexity = complexity_score
                state.execution.sql_selection_end_time = datetime.now()
                if state.execution.sql_selection_start_time and state.execution.sql_selection_end_time:
                    duration = (state.execution.sql_selection_end_time - state.execution.sql_selection_start_time).total_seconds() * 1000
                    state.execution.sql_selection_duration_ms = duration
                
                thinking = f"Case {evaluation_case}: Selected {selected_sql_id} via complexity analysis (score: {complexity_score})"
                
            elif selected_info not in ["ALL_FAILED"]:
                # Case A or C: Single SQL selection
                selected_sql_index = int(selected_info.replace("SQL #", "")) - 1
                selected_sql = state.generated_sqls[selected_sql_index] if selected_sql_index < len(state.generated_sqls) else None
                thinking = f"Case {evaluation_case}: Direct selection of {selected_info}"
                
            else:
                # Case D: All failed
                thinking = f"Case {evaluation_case}: All SQLs below threshold"
            
            # Create result
            if selected_sql_index is not None and selected_sql:
                # Success case
                if sql_status == "GOLD":
                    status = EvaluationStatus.GOLD
                elif sql_status == "SILVER":
                    status = EvaluationStatus.SILVER
                else:
                    status = EvaluationStatus.FAILED
                
                result = EnhancedEvaluationResult(
                    thinking=thinking,
                    answers=[f"SQL #{i+1}: {sql_status}" if i == selected_sql_index else f"SQL #{i+1}: Not selected" 
                            for i in range(len(state.generated_sqls))],
                    status=status,
                    selected_sql_index=selected_sql_index,
                    selected_sql=selected_sql,
                    evaluation_case=evaluation_case,
                    auxiliary_agents_used=[], 
                    best_pass_rate=max(pass_rates.values()) if pass_rates else 0.0
                )
            else:
                # Failed case
                result = EnhancedEvaluationResult(
                    thinking=thinking,
                    answers=[f"SQL #{i+1}: FAILED - Below threshold" for i in range(len(state.generated_sqls))],
                    status=EvaluationStatus.FAILED,
                    evaluation_case=evaluation_case,
                    auxiliary_agents_used=[],
                    best_pass_rate=max(pass_rates.values()) if pass_rates else 0.0,
                    requires_escalation=True,
                    escalation_context=f"All SQL candidates failed to meet {self.evaluation_threshold}% pass rate threshold"
                )
            
            # Complete evaluation timing
            state.execution.evaluation_end_time = datetime.now()
            if state.execution.evaluation_start_time and state.execution.evaluation_end_time:
                duration = (state.execution.evaluation_end_time - state.execution.evaluation_start_time).total_seconds() * 1000
                state.execution.evaluation_duration_ms = duration
            
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
                        case=evaluation_case,
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
                answers=[f"SQL #{i+1}: KO - Evaluation system error: {str(e)}" for i in range(len(state.generated_sqls) if hasattr(state, 'generated_sqls') else 0)],
                status=EvaluationStatus.FAILED,
                requires_escalation=True,
                escalation_context=f"Evaluation flow exception: {str(e)}"
            )
            
            # Complete logging even on error
            self.eval_logger.complete_evaluation(error_result, EvaluationStatus.FAILED)
            
            return error_result


async def run_enhanced_evaluation_flow(state: Any, agents_and_tools: Any, session_id: str = None, evaluation_threshold: int = None) -> Tuple[EnhancedEvaluationResult, Dict[str, Any]]:
    """
    Entry point for enhanced evaluation flow with comprehensive logging.
    
    Args:
        state: System state containing generated SQLs and test data
        agents_and_tools: Agent manager with evaluator and other agents
        session_id: Optional session identifier for logging
        evaluation_threshold: Minimum percentage threshold for SQL evaluation (0-100)
        
    Returns:
        Tuple of (EnhancedEvaluationResult, evaluation_logs_summary)
    """
    # Get evaluation threshold from state.workspace if not provided
    if evaluation_threshold is None:
        evaluation_threshold = getattr(state, 'workspace', {}).get('evaluation_threshold', 90)
    
    flow = EnhancedEvaluationFlow(agents_and_tools, session_id, evaluation_threshold)
    result = await flow.run_enhanced_evaluation(state)
    
    # Return both result and logging summary
    logs_summary = flow.eval_logger.get_evaluation_summary()
    
    return result, logs_summary