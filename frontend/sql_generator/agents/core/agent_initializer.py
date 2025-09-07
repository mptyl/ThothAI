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
Agent initialization utilities and factory methods.
"""

from typing import Optional, Dict, Any
from pydantic_ai import Agent

from .agent_ai_model_factory import create_fallback_model
from helpers.template_preparation import TemplateLoader, clean_template_for_llm
from .agent_result_models import (
    AskHumanResult,
    CheckQuestionResult,
    TranslationResult,
    ExtractKeywordsResult,
    TestUnitGeneratorResult,
    EvaluationResult,
    TestReducerResult,
    SqlSelectorResult,
    EvaluatorSupervisorResult,
    SqlResponse
)
from model.sql_generation_deps import SqlGenerationDeps
from model.evaluator_deps import EvaluatorDeps
from model.agent_dependencies import (
    KeywordExtractionDeps,
    ValidationDeps,
    TestGenerationDeps,
    TranslationDeps,
    SqlExplanationDeps,
    AskHumanDeps
)


def get_database_null_handling_rules(db_type: str) -> str:
    """
    Generate database-specific NULL handling rules for SQL generation.
    
    Args:
        db_type: Database type (sqlite, postgresql, mysql, mariadb, oracle, etc.)
    
    Returns:
        String containing database-specific rules for NULL handling
    """
    if db_type == "sqlite":
        return """
## NULL HANDLING FOR SQLite

**INFO**: SQLite 3.30.0+ (October 2019) supports NULLS FIRST/LAST syntax.
- Modern SQLite (3.30.0+) supports NULLS FIRST and NULLS LAST in ORDER BY clauses
- With ASC order: use NULLS LAST to put NULL values at the end (recommended)
- With DESC order: use NULLS FIRST to put NULL values at the beginning (recommended)
- For older SQLite versions (<3.30.0), NULLs behave as:
  - In ASC order: NULLs appear first by default
  - In DESC order: NULLs appear last by default

CORRECT SQLite 3.30.0+ examples:
```sql
SELECT * FROM table ORDER BY column ASC NULLS LAST    -- Recommended
SELECT * FROM table ORDER BY column DESC NULLS FIRST  -- Recommended
SELECT * FROM table ORDER BY column ASC               -- NULLs first (default)
SELECT * FROM table ORDER BY column DESC              -- NULLs last (default)
```
"""
    else:
        # For PostgreSQL, MySQL, MariaDB, Oracle, etc.
        return f"""
## NULL HANDLING FOR {db_type.upper()}

This database supports NULLS FIRST/LAST syntax in ORDER BY clauses.
- With ASC order: use NULLS LAST (recommended)
- With DESC order: use NULLS FIRST (recommended)
- Each column in ORDER BY should have its own NULLS specification

CORRECT {db_type} examples:
```sql
SELECT * FROM table ORDER BY column ASC NULLS LAST
SELECT * FROM table ORDER BY column DESC NULLS FIRST
SELECT * FROM table ORDER BY col1 ASC NULLS LAST, col2 DESC NULLS FIRST
```
"""


def get_test_generation_null_rules(db_type: str) -> str:
    """
    Generate database-specific NULL testing rules for test generation.
    
    Args:
        db_type: Database type (sqlite, postgresql, mysql, mariadb, oracle, etc.)
    
    Returns:
        String containing database-specific rules for NULL testing
    """
    if db_type == "sqlite":
        return """
## TESTING RULES FOR SQLite

- Test NULLS FIRST/LAST clauses for SQLite 3.30.0+ (modern versions support them)
- SQLite handles NULLs automatically, so tests should NOT fail if these clauses are missing
- Focus on testing ORDER BY functionality without NULL position specifiers
"""
    else:
        return f"""
## TESTING RULES FOR {db_type.upper()}

- Test that ORDER BY clauses include appropriate NULLS handling
- Verify: ASC should have NULLS LAST, DESC should have NULLS FIRST
- This is important for consistent NULL handling across queries
"""


class AgentInitializer:
    """
    Factory class for creating and initializing different types of agents.
    """
    
    @staticmethod
    def create_keyword_extraction_agent(agent_config: Dict[str, Any], default_model_config: Dict[str, Any] = None, retries: int = 3, force_default_prompt: bool = False) -> Optional[Agent]:
        """
        Create a keyword extraction agent as preliminary step for SQL generation.
        
        This agent is responsible for:
        - evaluating if the question is relevant to the scope of the database
        - extracting key entities, concepts, and contextual information
        from user queries to help with downstream processing tasks.
        
        Args:
            agent_config: Dictionary containing agent configuration parameters including
                          model settings, name, and optional system prompt
            default_model_config: Configuration for default fallback model from workspace
            retries: Number of retry attempts the agent should make if initial execution fails
            force_default_prompt: If True, use the default keyword extraction prompt regardless
                                  of whether a system_prompt is provided in agent_config
            
        Returns:
            Configured Agent instance ready for keyword extraction tasks, or None if no valid configuration
        """
        # Create model with fallback
        model = create_fallback_model(agent_config, default_model_config)
        if not model:
            return None
        
        # Determina nome agent
        if agent_config:
            agent_name = agent_config['name']
        elif default_model_config:
            agent_name = f"Fallback Keyword - {default_model_config.get('name', 'Default')}"
        else:
            return None
        
        # Determina system prompt
        if force_default_prompt or not (agent_config and agent_config.get('system_prompt')):
            system_prompt = TemplateLoader.load('system_templates/system_template_extract_keywords_from_question.txt')
        else:
            system_prompt = agent_config.get('system_prompt')
            
        agent = Agent(
            model=model,
            name=agent_name,
            system_prompt=clean_template_for_llm(system_prompt),
            output_type=ExtractKeywordsResult,
            deps_type=KeywordExtractionDeps,  # Use lightweight deps instead of SystemState
            retries=retries
        )
        # Store agent type metadata from config, if provided
        agent_type = agent_config.get("agent_type") if agent_config else None
        if agent_type:
            setattr(agent, "agent_type", agent_type)
        return agent
    
    @staticmethod
    def create_sql_generation_agent(agent_config: Dict[str, Any], default_model_config: Dict[str, Any] = None, retries: int = 3, force_default_prompt: bool = False, template_type: str = "query_plan") -> Optional[Agent]:
        """
        Create a SQL generation agent that converts natural language queries into SQL statements.
        
        This agent is responsible for analyzing user queries and database schema information
        to generate appropriate SQL queries that fulfill the user's information needs.
        
        Args:
            agent_config: Dictionary containing agent configuration parameters including
                          model settings, name, and optional system prompt. Must include
                          'name' key and AI model configuration.
            default_model_config: Configuration for default fallback model from workspace
            retries: Number of retry attempts the agent should make if initial SQL generation
                     fails. Default is 3 attempts.
            force_default_prompt: If True, always use the default SQL generator prompt template
                                  regardless of whether a system_prompt is provided in agent_config.
                                  Default is False.
            template_type: Type of SQL generation template to use: "query_plan", "divide_and_conquer", 
                          or "step_by_step". Default is "query_plan".
            
        Returns:
            Configured Agent instance ready for SQL generation tasks, or None if no valid configuration.
        """
        # Create model with fallback
        model = create_fallback_model(agent_config, default_model_config)
        if not model:
            return None
        
        # Determina nome agent
        if agent_config:
            agent_name = agent_config['name']
        elif default_model_config:
            agent_name = f"Fallback SQL Generation - {default_model_config.get('name', 'Default')}"
        else:
            return None
        
        # Determina system prompt - ALWAYS use the same system template
        # The differentiation happens at the USER PROMPT level, not system prompt
        if force_default_prompt or not (agent_config and agent_config.get('system_prompt')):
            # Always use the same SQL generator system template
            system_prompt = TemplateLoader.load('system_templates/system_template_generate_sql.txt')
        else:
            system_prompt = agent_config.get('system_prompt')
        
        # Create agent without tools - SQL execution happens in validators
        agent = Agent(
            model=model,
            name=agent_name,
            system_prompt=clean_template_for_llm(system_prompt),
            output_type=SqlResponse,
            deps_type=SqlGenerationDeps,  # Use lightweight deps instead of SystemState
            retries=retries
        )
        agent_type = agent_config.get("agent_type") if agent_config else None
        if agent_type:
            setattr(agent, "agent_type", agent_type)
        # Store template type as metadata
        setattr(agent, "template_type", template_type)
        return agent
    
    @staticmethod
    def create_test_generation_agent(agent_config: Dict[str, Any], default_model_config: Dict[str, Any] = None, retries: int = 3, force_default_prompt: bool = False) -> Optional[Agent]:
        """
        Create a test generation agent that produces test cases for SQL queries.
        
        This agent is responsible for analyzing the question, the hints and the CoT of the SQL generation process, and generating appropriate
        test cases to validate the correctness and performance of the generated SQL. It uses
        predefined templates or custom prompts to guide the test generation process.
        
        Args:
            agent_config: Dictionary containing agent configuration parameters including
                          model settings, name, and optional system prompt. Must include
                          'name' key and AI model configuration.
            default_model_config: Configuration for default fallback model from workspace
            retries: Number of retry attempts the agent should make if initial test generation
                     fails. Default is 3 attempts.
            force_default_prompt: If True, always use the default test generator prompt template
                                  regardless of whether a system_prompt is provided in agent_config.
                                  Default is False.
            
        Returns:
            Configured Agent instance ready for test generation tasks, or None if no valid configuration.
        """
        # Create model with fallback
        model = create_fallback_model(agent_config, default_model_config)
        if not model:
            return None
        
        # Determina nome agent
        if agent_config:
            agent_name = agent_config['name']
        elif default_model_config:
            agent_name = f"Fallback Test Generation - {default_model_config.get('name', 'Default')}"
        else:
            return None
        
        # Determina system prompt
        if force_default_prompt or not (agent_config and agent_config.get('system_prompt')):
            system_prompt = TemplateLoader.load('system_templates/system_template_test_generator.txt')
        else:
            system_prompt = agent_config.get('system_prompt')
        
        agent = Agent(
            model=model,
            name=agent_name,
            system_prompt=clean_template_for_llm(system_prompt),
            output_type=TestUnitGeneratorResult,
            deps_type=TestGenerationDeps,  # Use lightweight deps for test generation
            retries=retries
        )
        agent_type = agent_config.get("agent_type") if agent_config else None
        if agent_type:
            setattr(agent, "agent_type", agent_type)
        return agent
    
    # Test execution agent removed - no longer used in the workflow
    
    @staticmethod
    def create_evaluator_agent(agent_config: Dict[str, Any], default_model_config: Dict[str, Any] = None, retries: int = 3, force_default_prompt: bool = False) -> Optional[Agent]:
        """
        Create an evaluator agent that evaluates SQL candidates against test units.
        
        This agent is responsible for evaluating SQL queries generated by the SQL generation agents
        against the test units created by the test generation agent. It provides binary pass/fail
        verdicts for each SQL candidate based on the test criteria.
        
        Args:
            agent_config: Dictionary containing agent configuration parameters including
                          model settings, name, and optional system prompt. Typically uses
                          the same configuration as test_gen_agent_1.
            default_model_config: Configuration for default fallback model from workspace
            retries: Number of retry attempts the agent should make if initial evaluation
                     fails. Default is 3 attempts.
            force_default_prompt: If True, always use the default evaluator prompt template
                                  regardless of whether a system_prompt is provided in agent_config.
                                  Default is False.
            
        Returns:
            Configured Agent instance ready for SQL evaluation tasks, or None if no valid configuration.
        """
        # Create model with fallback
        model = create_fallback_model(agent_config, default_model_config)
        if not model:
            return None
        
        # Determine agent name
        if agent_config:
            agent_name = f"Evaluator - {agent_config['name']}"
        elif default_model_config:
            agent_name = f"Fallback Evaluator - {default_model_config.get('name', 'Default')}"
        else:
            return None
        
        # Always use the evaluator system template (not test generator template)
        system_prompt = TemplateLoader.load('system_templates/system_template_evaluate.txt')
        
        # Create validator for evaluator
        from agents.validators.test_validators import TestValidators
        test_validators = TestValidators()
        evaluator_validator = test_validators.create_evaluator_validator()
        
        agent = Agent(
            model=model,
            name=agent_name,
            system_prompt=clean_template_for_llm(system_prompt),
            output_type=EvaluationResult,
            deps_type=EvaluatorDeps,  # Use lightweight deps
            retries=retries
        )
        
        # Add the validator using decorator pattern
        if evaluator_validator:
            agent.output_validator(evaluator_validator)
        agent_type = agent_config.get("agent_type") if agent_config else None
        if agent_type:
            setattr(agent, "agent_type", agent_type)
        return agent
    
    @staticmethod
    def create_ask_human_agent(agent_config: Dict[str, Any], default_model_config: Dict[str, Any] = None, retries: int = 3, force_default_prompt: bool = False) -> Optional[Agent]:
        """
        Create an evaluation agent that can request human assistance when needed.
        
        This agent is responsible for evaluating complex situations or edge cases that
        require human judgment or intervention. It uses a specialized prompt template
        designed to formulate clear requests for human assistance and process the
        responses appropriately.
        
        Args:
            agent_config: Dictionary containing agent configuration parameters including
                          model settings, name, and optional system prompt. Must include
                          'name' key and AI model configuration.
            default_model_config: Configuration for default fallback model from workspace
            retries: Number of retry attempts the agent should make if initial evaluation
                     fails. Default is 3 attempts.
            force_default_prompt: If True, always use the default human assistance prompt
                                  template regardless of whether a system_prompt is provided
                                  in agent_config. Default is False.
            
        Returns:
            Configured Agent instance ready for evaluation and human assistance tasks, or None if no valid configuration.
        """
        # Create model with fallback
        model = create_fallback_model(agent_config, default_model_config)
        if not model:
            return None
        
        # Determina nome agent
        if agent_config:
            agent_name = agent_config['name']
        elif default_model_config:
            agent_name = f"Fallback Ask Human - {default_model_config.get('name', 'Default')}"
        else:
            return None
        
        # Determina system prompt
        if force_default_prompt or not (agent_config and agent_config.get('system_prompt')):
            system_prompt = TemplateLoader.load('system_templates/system_template_ask_human.txt')
        else:
            system_prompt = agent_config.get('system_prompt')
        
        agent = Agent(
            model=model,
            name=agent_name,
            system_prompt=clean_template_for_llm(system_prompt),
            output_type=AskHumanResult,
            deps_type=AskHumanDeps,  # Use lightweight deps for ask human
            retries=retries
        )
        agent_type = agent_config.get("agent_type") if agent_config else None
        if agent_type:
            setattr(agent, "agent_type", agent_type)
        return agent
    
    @staticmethod
    def create_question_validator_agent(agent_config: Dict[str, Any], default_model_config: Dict[str, Any] = None, retries: int = 3, force_default_prompt: bool = False) -> Optional[Agent]:
        """
        Create a question validator agent that validates user questions before processing.
        
        This agent is functionally equivalent to the check_question_agent but follows the
        standard configuration pattern. It is responsible for analyzing user questions to
        determine if they are:
        - Valid and comprehensible
        - Within the scope of the database
        - Suitable for SQL generation
        
        Args:
            agent_config: Dictionary containing agent configuration parameters including
                          model settings, name, and optional system prompt
            default_model_config: Configuration for default fallback model from workspace
            retries: Number of retry attempts the agent should make if initial validation
                     fails. Default is 3 attempts.
            force_default_prompt: If True, use the default check question prompt regardless
                                  of whether a system_prompt is provided in agent_config
            
        Returns:
            Configured Agent instance ready for question validation tasks, or None if no valid configuration.
        """
        # Create model with fallback
        model = create_fallback_model(agent_config, default_model_config)
        if not model:
            return None
        
        # Determina nome agent
        if agent_config:
            agent_name = agent_config['name']
        elif default_model_config:
            agent_name = f"Fallback Question Validator - {default_model_config.get('name', 'Default')}"
        else:
            return None
        
        # Determina system prompt
        if force_default_prompt or not (agent_config and agent_config.get('system_prompt')):
            system_prompt = TemplateLoader.load('system_templates/system_template_check_question.txt')
        else:
            system_prompt = agent_config.get('system_prompt')
        
        agent = Agent(
            model=model,
            name=agent_name,
            system_prompt=clean_template_for_llm(system_prompt),
            output_type=CheckQuestionResult,
            deps_type=ValidationDeps,  # Use lightweight deps instead of SystemState
            retries=retries
        )
        agent_type = agent_config.get("agent_type") if agent_config else None
        if agent_type:
            setattr(agent, "agent_type", agent_type)
        return agent
    
    @staticmethod
    def create_question_translator_agent(agent_config: Dict[str, Any], default_model_config: Dict[str, Any] = None, retries: int = 3, force_default_prompt: bool = False) -> Optional[Agent]:
        """
        Create a question translator agent that translates user questions to the database language.
        
        This agent is responsible for:
        - Detecting the language of the input question
        - Translating the question to the target database language while preserving meaning
        - Maintaining technical terms and proper nouns unchanged
        
        Args:
            agent_config: Dictionary containing agent configuration parameters including
                          model settings, name, and optional system prompt
            default_model_config: Configuration for default fallback model from workspace
            retries: Number of retry attempts the agent should make if initial translation
                     fails. Default is 3 attempts.
            force_default_prompt: If True, use the default translation prompt regardless
                                  of whether a system_prompt is provided in agent_config
            
        Returns:
            Configured Agent instance ready for translation tasks, or None if no valid configuration.
        """
        # Create model with fallback
        model = create_fallback_model(agent_config, default_model_config)
        if not model:
            return None
        
        # Determina nome agent
        if agent_config:
            agent_name = agent_config['name']
        elif default_model_config:
            agent_name = f"Fallback Question Translator - {default_model_config.get('name', 'Default')}"
        else:
            return None
        
        # Determina system prompt
        if force_default_prompt or not (agent_config and agent_config.get('system_prompt')):
            system_prompt = TemplateLoader.load('system_templates/system_template_translate_question.txt')
        else:
            system_prompt = agent_config.get('system_prompt')
        
        agent = Agent(
            model=model,
            name=agent_name,
            system_prompt=clean_template_for_llm(system_prompt),
            output_type=TranslationResult,
            deps_type=TranslationDeps,  # Use lightweight deps instead of SystemState
            retries=retries
        )
        agent_type = agent_config.get("agent_type") if agent_config else None
        if agent_type:
            setattr(agent, "agent_type", agent_type)
        return agent
    
    @staticmethod
    def create_sql_explanation_agent(agent_config: Dict[str, Any], default_model_config: Dict[str, Any] = None, retries: int = 3, force_default_prompt: bool = False) -> Optional[Agent]:
        """
        Create a SQL explanation agent that provides explanations for generated SQL queries.
        
        This agent is responsible for analyzing generated SQL queries and providing clear,
        human-readable explanations of what the query does, how it works, and what results
        it should produce.
        
        Args:
            agent_config: Dictionary containing agent configuration parameters including
                          model settings, name, and optional system prompt. Must include
                          'name' key and AI model configuration.
            default_model_config: Configuration for default fallback model from workspace
            retries: Number of retry attempts the agent should make if initial explanation
                     generation fails. Default is 3 attempts.
            force_default_prompt: If True, always use the default SQL explanation prompt
                                  template regardless of whether a system_prompt is provided
                                  in agent_config. Default is False.
            
        Returns:
            Configured Agent instance ready for SQL explanation tasks, or None if no valid configuration.
        """
        # Create model with fallback
        model = create_fallback_model(agent_config, default_model_config)
        if not model:
            return None
        
        # Determina nome agent
        if agent_config:
            agent_name = agent_config['name']
        elif default_model_config:
            agent_name = f"Fallback SQL Explanation - {default_model_config.get('name', 'Default')}"
        else:
            return None
        
        # Determina system prompt
        if force_default_prompt or not (agent_config and agent_config.get('system_prompt')):
            system_prompt = TemplateLoader.load('system_templates/system_template_explain_generated_sql.txt')
        else:
            system_prompt = agent_config.get('system_prompt')
        
        # Create agent that expects simple string output as per template requirements
        try:
            agent = Agent(
                model=model,
                name=agent_name,
                system_prompt=clean_template_for_llm(system_prompt),
                output_type=str,
                deps_type=SqlExplanationDeps,  # Use lightweight deps for SQL explanation
                retries=retries
            )
            agent_type = agent_config.get("agent_type") if agent_config else None
            if agent_type:
                setattr(agent, "agent_type", agent_type)
            return agent
        except Exception as e:
            # If agent creation fails, try without strict output typing for better compatibility
            from helpers.logging_config import get_logger
            logger = get_logger(__name__)
            logger.warning(f"Failed to create SQL explanation agent with strict typing: {e}")
            logger.info("Attempting to create fallback agent without strict output typing")
            
            try:
                fallback_agent = Agent(
                    model=model,
                    name=f"{agent_name}_fallback",
                    system_prompt=clean_template_for_llm(system_prompt),
                    deps_type=SqlExplanationDeps,  # Use lightweight deps for SQL explanation fallback
                    retries=retries
                    # Note: No output_type for better compatibility with various models
                )
                agent_type = agent_config.get("agent_type") if agent_config else None
                if agent_type:
                    setattr(fallback_agent, "agent_type", agent_type)
                logger.info("Successfully created fallback SQL explanation agent")
                return fallback_agent
            except Exception as fallback_error:
                logger.error(f"Failed to create fallback SQL explanation agent: {fallback_error}")
                return None
    
    @staticmethod
    def create_test_reducer_agent(agent_config: Dict[str, Any], default_model_config: Dict[str, Any] = None, retries: int = 3) -> Optional[Agent]:
        """
        Create a TestReducer agent for semantic test deduplication.
        
        This agent eliminates semantically duplicate test cases to improve evaluation 
        efficiency while maintaining comprehensive test coverage. It uses the same 
        model configuration as the Evaluator for consistency.
        
        Args:
            agent_config: Dictionary containing agent configuration parameters,
                         typically the same as the Evaluator's configuration
            default_model_config: Configuration for default fallback model from workspace
            retries: Number of retry attempts for agent execution. Default is 3.
            
        Returns:
            Configured TestReducer Agent instance, or None if creation fails
        """
        # Create model with fallback
        model = create_fallback_model(agent_config, default_model_config)
        if not model:
            return None
        
        # Determine agent name
        if agent_config:
            agent_name = f"TestReducer - {agent_config['name']}"
        elif default_model_config:
            agent_name = f"Fallback TestReducer - {default_model_config.get('name', 'Default')}"
        else:
            return None
        
        # Always use the TestReducer system template
        system_prompt = TemplateLoader.load('system_templates/system_template_test_reducer.txt')
        
        agent = Agent(
            model=model,
            name=agent_name,
            system_prompt=clean_template_for_llm(system_prompt),
            output_type=TestReducerResult,
            deps_type=EvaluatorDeps,  # Use same deps as Evaluator
            retries=retries
        )
        
        agent_type = agent_config.get("agent_type") if agent_config else None
        if agent_type:
            setattr(agent, "agent_type", agent_type)
        return agent
    
    @staticmethod
    def create_sql_selector_agent(agent_config: Dict[str, Any], default_model_config: Dict[str, Any] = None, retries: int = 3) -> Optional[Agent]:
        """
        Create a SqlSelector agent for choosing the best SQL from equivalent candidates.
        
        This agent handles Case B in the 4-case evaluation system: when multiple 
        SQL candidates have achieved 100% test pass rates, it selects the best one
        based on quality criteria. It uses the same model configuration as the 
        Evaluator for consistency.
        
        Args:
            agent_config: Dictionary containing agent configuration parameters,
                         typically the same as the Evaluator's configuration
            default_model_config: Configuration for default fallback model from workspace
            retries: Number of retry attempts for agent execution. Default is 3.
            
        Returns:
            Configured SqlSelector Agent instance, or None if creation fails
        """
        # Create model with fallback
        model = create_fallback_model(agent_config, default_model_config)
        if not model:
            return None
        
        # Determine agent name
        if agent_config:
            agent_name = f"SqlSelector - {agent_config['name']}"
        elif default_model_config:
            agent_name = f"Fallback SqlSelector - {default_model_config.get('name', 'Default')}"
        else:
            return None
        
        # Always use the SqlSelector system template
        system_prompt = TemplateLoader.load('system_templates/system_template_sql_selector.txt')
        
        agent = Agent(
            model=model,
            name=agent_name,
            system_prompt=clean_template_for_llm(system_prompt),
            output_type=SqlSelectorResult,
            deps_type=EvaluatorDeps,  # Use same deps as Evaluator
            retries=retries
        )
        
        agent_type = agent_config.get("agent_type") if agent_config else None
        if agent_type:
            setattr(agent, "agent_type", agent_type)
        return agent

    @staticmethod
    def create_evaluator_supervisor_agent(agent_config: Dict[str, Any], default_model_config: Dict[str, Any] = None, retries: int = 3) -> Optional[Agent]:
        """
        Create an EvaluatorSupervisor agent for reevaluation of borderline cases.
        
        This agent handles Case C in the 4-case evaluation system: when SQL candidates 
        score 90-99%, it performs careful analysis to make final 
        GOLD/FAILED decisions. It uses the same model configuration as the Evaluator 
        for consistency.
        
        Args:
            agent_config: Dictionary containing agent configuration parameters,
                         typically the same as the Evaluator's configuration
            default_model_config: Configuration for default fallback model from workspace
            retries: Number of retry attempts for agent execution. Default is 3.
            
        Returns:
            Configured EvaluatorSupervisor Agent instance, or None if creation fails
        """
        # Create model with fallback
        model = create_fallback_model(agent_config, default_model_config)
        if not model:
            return None
        
        # Determine agent name
        if agent_config:
            agent_name = f"EvaluatorSupervisor - {agent_config['name']}"
        elif default_model_config:
            agent_name = f"Fallback EvaluatorSupervisor - {default_model_config.get('name', 'Default')}"
        else:
            return None
        
        # Always use the EvaluatorSupervisor system template
        system_prompt = TemplateLoader.load('system_templates/system_template_evaluator_supervisor.txt')
        
        agent = Agent(
            model=model,
            name=agent_name,
            system_prompt=clean_template_for_llm(system_prompt),
            output_type=EvaluatorSupervisorResult,
            deps_type=EvaluatorDeps,  # Use same deps as Evaluator
            retries=retries
        )
        
        agent_type = agent_config.get("agent_type") if agent_config else None
        if agent_type:
            setattr(agent, "agent_type", agent_type)
        return agent
