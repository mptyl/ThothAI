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
Main factory for creating and configuring all types of agents.
"""

from typing import Dict, Any, Optional
from pydantic_ai import Agent
from helpers.logging_config import get_logger

from .base_agent_manager import BaseAgentManager
from .agent_initializer import AgentInitializer
from ..validators.sql_validators import SqlValidators
from ..validators.test_validators import TestValidators
from .agent_pools import AgentPools

logger = get_logger(__name__)

class ThothAgentManager(BaseAgentManager):
    """
    Factory class for creating and managing all agent types with their validators and pools.
    """

    def __init__(self, workspace: Dict[str, Any], dbmanager=None, agent_pool_config=None):
        super().__init__(workspace)
        self.dbmanager = dbmanager
        self.agent_pool_config = agent_pool_config  # Store pool config for dynamic initialization
        
        # Initialize individual agents - only the ones we currently need
        self.question_validator_agent: Optional[Agent] = None
        self.question_translator_agent: Optional[Agent] = None
        self.keyword_extraction_agent: Optional[Agent] = None
        self.test_gen_agent_1: Optional[Agent] = None
        self.test_gen_agent_2: Optional[Agent] = None
        self.test_gen_agent_3: Optional[Agent] = None
        # test_exec_agent removed - no longer used in the workflow
        self.evaluator_agent: Optional[Agent] = None
        
        # Comment out agents we don't need yet
        # self.select_columns_agent_1: Optional[Agent] = None
        # self.select_columns_agent_2: Optional[Agent] = None
        self.sql_basic_agent: Optional[Agent] = None
        self.sql_advanced_agent: Optional[Agent] = None
        self.sql_expert_agent: Optional[Agent] = None
        # NOTE: ask_human_agent is currently not used but maintained for future implementation
        # self.ask_human_agent: Optional[Agent] = None
        self.sql_explainer_agent: Optional[Agent] = None
        
        # Initialize agent pools
        self.agent_pools = AgentPools()
        
        # Initialize validators - only the ones we need for now
        self.sql_validators = None  # Will be initialized when SQL agents are activated
        self.test_validators = TestValidators()
        # self.explanation_validators = ExplanationValidators()  # Not needed yet
    
    def initialize(self):
        """
        Initialize all agents and configure their tools and validators.
        """
        # Only initialize the agents we currently need
        self._create_question_validator_agent()
        self._create_question_translator_agent()
        self._create_keyword_extraction_agent()
        self._create_test_agents()  # Only test generation agents for now
        
        # Comment out agents we don't need yet
        # self._create_column_selection_agents()
        self._create_sql_generation_agents()
        # NOTE: ask_human_agent creation is currently not used but maintained for future implementation
        # self._create_ask_humans_agent()
        self._create_sql_explainer_agent()
        
        # Only initialize validators we need
        self.sql_validators = SqlValidators(None, self.dbmanager)  # Enable SQL validators with dbmanager (test_exec_agent no longer used)
        
        self._populate_agent_pools()
        self._configure_tools_and_validators()  # Enable tools and validators
        
        return self
    
    def _create_question_validator_agent(self):
        """
        Create the question validator agent.
        
        This agent uses the question_validator configuration from the workspace.
        No fallback to default_agent.
        """
        # Use specific question_validator agent
        question_validator_config = self.workspace.get("question_validator")
        default_model_config = self.workspace.get("default_model")
        use_default = question_validator_config is None
        # No fallback to default_agent - if no question_validator, agent will be None
        
        # Create the question validator agent with standard configuration
        self.question_validator_agent = AgentInitializer.create_question_validator_agent(
            question_validator_config,
            default_model_config,
            self.get_retries(question_validator_config),
            force_default_prompt=use_default
        )
    
    def _create_question_translator_agent(self):
        """
        Create the question translator agent.
        
        This agent translates user questions from any language to the database language.
        It uses the same model as the question validator for consistency.
        """
        # Use the same configuration as the question validator agent
        translator_config = self.workspace.get("question_validator")
        default_model_config = self.workspace.get("default_model")
        # No fallback to default_agent - use question_validator config for translation
        
        # Create the question translator agent with standard configuration
        self.question_translator_agent = AgentInitializer.create_question_translator_agent(
            translator_config,
            default_model_config,
            self.get_retries(translator_config),
            force_default_prompt=True  # Always use default template for translation
        )
    
    def _create_keyword_extraction_agent(self):
        """Create a single keyword extraction agent (no pool)."""
        kw_agent_config = self.workspace.get("kw_sel_agent")
        default_model_config = self.workspace.get("default_model")
        use_default = self.workspace.get("kw_sel_agent") is None
        self.keyword_extraction_agent = AgentInitializer.create_keyword_extraction_agent(
            kw_agent_config,
            default_model_config,
            self.get_retries(kw_agent_config),
            force_default_prompt=use_default
        )
    
    def _create_column_selection_agents(self):
        """Create column selection agents."""
        # Use specific agents only, no fallback to default agent
        sel_agent_1_config = self.workspace.get("sel_columns_agent_1")
        sel_agent_2_config = self.workspace.get("sel_columns_agent_2")
        default_model_config = self.workspace.get("default_model")
        use_default_1 = sel_agent_1_config is None
        use_default_2 = sel_agent_2_config is None
        # No fallback to default_agent - if no specific agent, agent will be None
        
        self.select_columns_agent_1 = AgentInitializer.create_column_selection_agent(
            sel_agent_1_config,
            default_model_config,
            self.get_retries(sel_agent_1_config),
            force_default_prompt=use_default_1
        )
        
        self.select_columns_agent_2 = AgentInitializer.create_column_selection_agent(
            sel_agent_2_config,
            default_model_config,
            self.get_retries(sel_agent_2_config),
            force_default_prompt=use_default_2
        )
    
    def _create_sql_generation_agents(self):
        """Create SQL generation agents - one for each functionality level (BASIC, ADVANCED, EXPERT)."""
        # Get configs for all levels
        sql_basic_config = self.workspace.get("sql_basic_agent")
        sql_advanced_config = self.workspace.get("sql_advanced_agent")
        sql_expert_config = self.workspace.get("sql_expert_agent")
        default_model_config = self.workspace.get("default_model")
        use_default_basic = sql_basic_config is None
        use_default_advanced = sql_advanced_config is None
        use_default_expert = sql_expert_config is None
        
        # NO MORE POOL - Create only single agents, one for each level
        # Each agent uses a simplified system prompt
        self.sql_basic_agent = AgentInitializer.create_sql_generation_agent(
            sql_basic_config,
            default_model_config,
            self.get_retries(sql_basic_config),
            force_default_prompt=use_default_basic,
            template_type="simplified"  # Use new simplified template
        )
        
        self.sql_advanced_agent = AgentInitializer.create_sql_generation_agent(
            sql_advanced_config,
            default_model_config,
            self.get_retries(sql_advanced_config),
            force_default_prompt=use_default_advanced,
            template_type="simplified"  # Use new simplified template
        )
        
        self.sql_expert_agent = AgentInitializer.create_sql_generation_agent(
            sql_expert_config,
            default_model_config,
            self.get_retries(sql_expert_config),
            force_default_prompt=use_default_expert,
            template_type="simplified"  # Use new simplified template
        )
        
        logger.info(f"Created 3 SQL generation agents (BASIC, ADVANCED, EXPERT) with simplified prompts")
    
    
    def _create_test_agents(self):
        """Create test generation and execution agents."""
        # Use specific agents only, no fallback to default agent
        test_gen_1_config = self.workspace.get("test_gen_agent_1")
        test_gen_2_config = self.workspace.get("test_gen_agent_2")
        test_gen_3_config = self.workspace.get("test_gen_agent_3")
        # test_exec_agent removed - no longer used in workflow
        default_model_config = self.workspace.get("default_model")
        use_default_gen_1 = test_gen_1_config is None
        use_default_gen_2 = test_gen_2_config is None
        use_default_gen_3 = test_gen_3_config is None
        # No fallback to default_agent - if no specific agent, agent will be None
        
        self.test_gen_agent_1 = AgentInitializer.create_test_generation_agent(
            test_gen_1_config,
            default_model_config,
            self.get_retries(test_gen_1_config),
            force_default_prompt=use_default_gen_1
        )
        
        self.test_gen_agent_2 = AgentInitializer.create_test_generation_agent(
            test_gen_2_config,
            default_model_config,
            self.get_retries(test_gen_2_config),
            force_default_prompt=use_default_gen_2
        )
        
        self.test_gen_agent_3 = AgentInitializer.create_test_generation_agent(
            test_gen_3_config,
            default_model_config,
            self.get_retries(test_gen_3_config),
            force_default_prompt=use_default_gen_3
        )
        
        # test_exec_agent creation removed - no longer used in workflow
        
        # Create evaluator agent using dedicated test_evaluator_agent config from workspace
        test_evaluator_config = self.workspace.get("test_evaluator_agent")
        use_default_evaluator = test_evaluator_config is None
        
        # If no test_evaluator_agent configured, fallback to test_gen_agent_1 config for backward compatibility
        if not test_evaluator_config:
            test_evaluator_config = test_gen_1_config
            if test_evaluator_config:
                logger.info("No test_evaluator_agent configured, using test_gen_agent_1 config for backward compatibility")
        
        self.evaluator_agent = AgentInitializer.create_evaluator_agent(
            test_evaluator_config,
            default_model_config,
            self.get_retries(test_evaluator_config),
            force_default_prompt=use_default_evaluator  # Use default if no specific config
        )
        
        # Store the evaluator config for auxiliary agents to use
        self.evaluator_config = test_evaluator_config
    
    def _create_ask_humans_agent(self):
        """Create ask human agent."""
        # NOTE: This method creates the ask_human_agent but is currently not used in the system.
        # The agent configuration is maintained for future implementation.
        # Use specific agent only, no fallback to default agent
        ask_human_agent_config = self.workspace.get("ask_human_help_agent")
        default_model_config = self.workspace.get("default_model")
        use_default_eval = ask_human_agent_config is None
        # No fallback to default_agent - if no specific agent, agent will be None
        
        # NOTE: Currently assigning to evaluate_agent instead of ask_human_agent for future compatibility
        self.evaluate_agent = AgentInitializer.create_ask_human_agent(
            ask_human_agent_config,
            default_model_config,
            self.get_retries(ask_human_agent_config),
            force_default_prompt=use_default_eval
        )
    
    def _create_sql_explainer_agent(self):
        """Create SQL explainer agent."""
        # Use specific explain_sql_agent only
        sql_explainer_config = self.workspace.get("explain_sql_agent")
        default_model_config = self.workspace.get("default_model")
        use_default = sql_explainer_config is None
        # No fallback to default_agent - if no explain_sql_agent, agent will be None
        
        self.sql_explainer_agent = AgentInitializer.create_sql_explanation_agent(
            sql_explainer_config,
            default_model_config,
            self.get_retries(sql_explainer_config),
            force_default_prompt=use_default
        )
    
    def _populate_agent_pools(self):
        """Populate agent pools with created agents - supports both legacy and dynamic pools."""
        
        # Check if we have dynamic pool configuration
        if self.agent_pool_config:
            self._populate_pools_from_config()
        else:
            # Fall back to legacy pool population
            self._populate_legacy_pools()
    
    def _populate_legacy_pools(self):
        """Legacy method to populate pools from workspace-specific agents."""
        # Test generation agents pool
        self.agent_pools.add_to_test_generation_pool(self.test_gen_agent_1)
        self.agent_pools.add_to_test_generation_pool(self.test_gen_agent_2)
        self.agent_pools.add_to_test_generation_pool(self.test_gen_agent_3)
        
        # SQL generation agents pool
        self.agent_pools.add_to_sql_generation_pool(self.sql_basic_agent)
        self.agent_pools.add_to_sql_generation_pool(self.sql_advanced_agent)
        self.agent_pools.add_to_sql_generation_pool(self.sql_expert_agent)
    
    def _populate_pools_from_config(self):
        """
        Populate agent pools from dynamic configuration.
        Creates agents based on the pool configuration received from Django backend.
        """
        if not self.agent_pool_config:
            logger.warning("No agent pool configuration available, falling back to legacy pools")
            self._populate_legacy_pools()
            return
        
        # Import AgentPoolConfig for type checking
        from model.agent_pool_config import AgentPoolConfig
        
        if not isinstance(self.agent_pool_config, AgentPoolConfig):
            # Convert dict to AgentPoolConfig if needed
            self.agent_pool_config = AgentPoolConfig(**self.agent_pool_config)
        
        # Create and add SQL generator agents
        for level in ['basic', 'advanced', 'expert']:
            agents = self.agent_pool_config.get_sql_agents_by_level(level)
            logger.info(f"Creating {len(agents)} SQL agents for {level} level from pool config")
            for i, agent_config in enumerate(agents):
                # Create agent from configuration
                logger.info(f"Creating SQL {level} agent {i+1}/{len(agents)}: {agent_config.name} ({agent_config.ai_model.specific_model if agent_config.ai_model else 'no model'})")
                agent = self._create_agent_from_config(agent_config, 'sql_generation')
                if agent:
                    self.agent_pools.add_sql_agent(agent, level)
                    logger.info(f"Successfully added SQL {level} agent to pool")
                else:
                    logger.warning(f"Failed to create SQL {level} agent from config: {agent_config.name}")
        
        # Create and add test generator agents
        for level in ['basic', 'advanced', 'expert']:
            agents = self.agent_pool_config.get_test_agents_by_level(level)
            for agent_config in agents:
                # Create agent from configuration
                agent = self._create_agent_from_config(agent_config, 'test_generation')
                if agent:
                    self.agent_pools.add_test_agent(agent, level)
        
        # Log pool statistics
        stats = self.agent_pools.get_pool_stats()
        logger.info(f"Agent pools populated - SQL: {stats['sql']}, Test: {stats['test']}")
    
    def _create_agent_from_config(self, agent_config, agent_type: str):
        """
        Create an agent from configuration data using agent_ai_model_factory.
        
        Args:
            agent_config: AgentConfig object with agent parameters
            agent_type: Type of agent ('sql_generation' or 'test_generation')
            
        Returns:
            Configured Agent instance or None if creation fails
        """
        try:
            # Build the config dict in the format expected by AgentInitializer
            # which uses agent_ai_model_factory.get_agent_llm_model
            
            # The agent_ai_model_factory expects:
            # {
            #     'name': agent_name,
            #     'ai_model': {
            #         'basic_model': {'provider': 'OPENROUTER'},
            #         'specific_model': 'model-name',
            #         'url': optional_url
            #     }
            # }
            
            # Convert basic_model to provider format
            provider = None
            if agent_config.ai_model and agent_config.ai_model.basic_model:
                # First try to get provider directly from basic_model if available
                provider = agent_config.ai_model.basic_model.get('provider')
                
                # If provider field not present, fallback to name-based detection
                if not provider:
                    basic_model_name = agent_config.ai_model.basic_model.get('name', '').upper()
                    # Map basic_model names to provider constants
                    if 'OPENROUTER' in basic_model_name:
                        provider = 'OPENROUTER'
                    elif 'OPENAI' in basic_model_name or 'GPT' in basic_model_name:
                        provider = 'OPENAI'
                    elif 'ANTHROPIC' in basic_model_name or 'CLAUDE' in basic_model_name:
                        provider = 'ANTHROPIC'
                    elif 'MISTRAL' in basic_model_name:
                        provider = 'MISTRAL'
                    elif 'CODESTRAL' in basic_model_name:
                        provider = 'CODESTRAL'
                    elif 'GEMINI' in basic_model_name:
                        provider = 'GEMINI'
                    elif 'GROQ' in basic_model_name:
                        provider = 'GROQ'
                    elif 'DEEPSEEK' in basic_model_name:
                        provider = 'DEEPSEEK'
                    elif 'OLLAMA' in basic_model_name:
                        provider = 'OLLAMA'
                    elif 'LMSTUDIO' in basic_model_name or 'LM_STUDIO' in basic_model_name:
                        provider = 'LMSTUDIO'
                    else:
                        provider = 'OPENROUTER'  # Default fallback
            
            # Build the config in the expected format
            config_dict = {
                'name': agent_config.name,
                'agent_type': agent_config.agent_type,
                'ai_model': {
                    'basic_model': {
                        'provider': provider
                    },
                    'specific_model': agent_config.ai_model.specific_model if agent_config.ai_model else None,
                    # Add url if available (currently not in the pool config but might be added)
                    'url': getattr(agent_config.ai_model, 'url', None) if agent_config.ai_model else None
                }
            }
            
            # Log the config for debugging
            logger.info(f"Creating {agent_type} agent '{agent_config.name}' with provider={provider}, model={config_dict['ai_model']['specific_model']}")
            print(f"DEBUG: Agent config being passed: {config_dict}", flush=True)
            
            # Map agent type to creation method
            if agent_type == 'sql_generation':
                agent = AgentInitializer.create_sql_generation_agent(
                    config_dict,
                    self.workspace.get("default_model"),
                    agent_config.retries,
                    force_default_prompt=False
                )
            elif agent_type == 'test_generation':
                agent = AgentInitializer.create_test_generation_agent(
                    config_dict,
                    self.workspace.get("default_model"),
                    agent_config.retries,
                    force_default_prompt=False
                )
            else:
                logger.warning(f"Unknown agent type: {agent_type}")
                return None
            
            # Log the created agent's model info
            if agent:
                model_info = "unknown"
                if hasattr(agent, '_model') and agent._model:
                    model_info = str(agent._model)
                elif hasattr(agent, 'model') and agent.model:
                    model_info = str(agent.model)
                logger.info(f"Successfully created {agent_type} agent '{config_dict.get('name')}' with model: {model_info}")
            
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent from config: {e}", exc_info=True)
            return None

    
    def _configure_tools_and_validators(self):
        """Configure tools and validators for the agents."""
        self._configure_sql_validators()
        self._configure_test_validators()
        self._configure_explanation_validators()
    

    
    def _configure_sql_validators(self):
        """Configure validators for SQL generation agents."""
        if self.sql_validators:
            sql_validator = self.sql_validators.create_sql_validator()
            
            # Apply validators to all SQL agents
            if self.sql_basic_agent:
                print(f"DEBUG: Attaching validator to sql_basic_agent, dbmanager={self.dbmanager is not None}", flush=True)
                self.sql_basic_agent.output_validator(sql_validator)
            if self.sql_advanced_agent:
                print(f"DEBUG: Attaching validator to sql_advanced_agent, dbmanager={self.dbmanager is not None}", flush=True)
                self.sql_advanced_agent.output_validator(sql_validator)
            if self.sql_expert_agent:
                print(f"DEBUG: Attaching validator to sql_expert_agent, dbmanager={self.dbmanager is not None}", flush=True)
                self.sql_expert_agent.output_validator(sql_validator)
    
    def _configure_test_validators(self):
        """Configure validators for test generation and execution agents."""
        # Validators disabled for test generation agents - we handle output directly
        # Previously created but unused - removed:
        # test_gen_validator = self.test_validators.create_test_gen_validator()
        # test_exec_validator = self.test_validators.create_test_exec_validator()
        # if self.test_gen_agent_1:
        #     self.test_gen_agent_1.output_validator(test_gen_validator)
        # if self.test_gen_agent_2:
        #     self.test_gen_agent_2.output_validator(test_gen_validator)
        # if self.test_gen_agent_3:
        #     self.test_gen_agent_3.output_validator(test_gen_validator)
        
        # test_exec_agent validator application removed - agent no longer exists
    
    def _configure_explanation_validators(self):
        """Configure validators for SQL explanation agents."""
        # explanation_validator = self.explanation_validators.create_explanation_validator()
        
        # # Apply validator to SQL explainer agent
        # if self.sql_explainer_agent:
        #     self.sql_explainer_agent.output_validator(explanation_validator)
        pass
    
    async def explain_generated_sql(
        self,
        question: str,
        generated_sql: str,
        database_schema: str,
        hints: str = "",
        chain_of_thought: str = "",
        language: str = "it"
    ) -> Optional[str]:
        """
        Generate an explanation for the SQL query.
        
        Args:
            question: The original user question
            generated_sql: The SQL query that was generated
            database_schema: The database schema used
            hints: Any hints or evidence used in generation
            chain_of_thought: The reasoning process used
            language: Language for the explanation (default: Italian)
            
        Returns:
            Explanation string or None if generation fails
        """
        if not self.sql_explainer_agent:
            logger.warning("SQL explainer agent is not initialized")
            return None
        
        try:
            # Prepare the prompt with all context
            from helpers.template_preparation import TemplateLoader
            
            prompt = TemplateLoader.format(
                'user_sql_explain',
                GENERATED_SQL=generated_sql,
                QUESTION=question,
                DATABASE_SCHEMA=database_schema,
                HINTS=hints,
                COT=chain_of_thought,
                LANGUAGE=language.upper()
            )
            
            # Run the explainer agent - no state needed for explanation
            result = await self.sql_explainer_agent.run(prompt)
            
            # The result object has different structure - could be result.output or result.data
            if hasattr(result, 'output') and result.output:
                # If output is a string, return it directly
                if isinstance(result.output, str):
                    return result.output
                # If output is an object with an explanation attribute
                elif hasattr(result.output, 'explanation'):
                    return result.output.explanation
                else:
                    return str(result.output)
            else:
                logger.warning("SQL explanation agent returned empty result")
                return None
                
        except Exception as e:
            logger.error(f"Error generating SQL explanation: {e}")
            return None
    
    def get_context_window(self, sql_generator: str) -> Optional[int]:
        """
        Get the context window size for a specific SQL generator.
        
        Args:
            sql_generator: The SQL generator type (BASIC, ADVANCED, EXPERT)
            
        Returns:
            Optional[int]: Context window size in tokens, or None if not found
        """
        try:
            # Map generator type directly to config key
            generator_to_config_key = {
                "BASIC": "sql_basic_agent",
                "Basic": "sql_basic_agent",
                "ADVANCED": "sql_advanced_agent",
                "Advanced": "sql_advanced_agent",
                "EXPERT": "sql_expert_agent",
                "Expert": "sql_expert_agent",
            }
            
            config_key = generator_to_config_key.get(sql_generator)
            if not config_key:
                logger.warning(f"Unknown SQL generator type: {sql_generator}")
                return None
            
            # Get the agent configuration
            agent_config = self.workspace.get(config_key)
            if not agent_config:
                # No fallback - return None if specific agent config not found
                return None
            
            if agent_config and "ai_model" in agent_config:
                ai_model = agent_config["ai_model"]
                # Check for context_size in the ai_model configuration
                if "context_size" in ai_model:
                    return int(ai_model["context_size"])
                
                # Check for other possible keys
                for key in ["context_window", "max_context", "max_tokens"]:
                    if key in ai_model:
                        return int(ai_model[key])
            
            # If we can't find it in config, return None
            logger.warning(f"Could not find context window for {sql_generator}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting context window for {sql_generator}: {e}")
            return None
