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

"""Schema link strategy decision module."""

import logging
from model.system_state import SystemState
from helpers.token_counter import count_mschema_tokens, estimate_context_usage
from helpers.main_helpers.main_generate_mschema import to_mschema

logger = logging.getLogger(__name__)

async def decide_schema_link_strategy(state: SystemState) -> str:
    """
    Decides the schema link strategy to use based on schema size vs context window
    and the number of columns in the schema.
    
    The decision is based on:
    1. Whether the full schema tokens exceed the max_context_usage_before_linking threshold (from Setting model)
    2. Whether the number of columns exceeds the max_columns_before_schema_linking threshold (from Setting model)
    
    Both thresholds are configurable via the workspace Setting model in Django backend:
    - max_context_usage_before_linking: percentage of context window as integer (0-99, default 50 = 50%)
    - max_columns_before_schema_linking: max number of columns (default 20000)
    
    Args:
        state: System state with question and schema info
        
    Returns:
        str: Either "WITH_SCHEMA_LINK" or "WITHOUT_SCHEMA_LINK"
    """
    try:
        # Step 1: Calculate tokens from full_mschema
        # First, convert full_schema to mschema format
        if not state.full_schema:
            logger.warning("No full_schema available, defaulting to WITHOUT_SCHEMA_LINK")
            return "WITHOUT_SCHEMA_LINK"
        
        # Create enriched schema first to have all the data
        state.create_enriched_schema()
        full_mschema = to_mschema(state.enriched_schema)
        
        # Count tokens in the full mschema
        schema_tokens = count_mschema_tokens(full_mschema)
        state.full_schema_tokens_count = schema_tokens
        
        logger.info(f"Full schema token count: {schema_tokens}")
        logger.info(f"State.full_schema_tokens_count set to: {state.full_schema_tokens_count}")
        
        # Step 2: Compute total columns strictly from full_schema
        total_columns = 0
        for _, table_info in state.full_schema.items():
            columns = table_info.get("columns", {})
            total_columns += len(columns)
        logger.info(f"Total columns computed from full schema: {total_columns}")
        
        # Step 3: Get max_columns_before_schema_linking and max_context_usage_before_linking from workspace setting
        # Defaults: 20000 columns, 0.5 (50%) context usage
        setting = {}
        if isinstance(getattr(state, "workspace", None), dict):
            setting = state.workspace.get("setting", {}) or {}
        
        # Get max columns threshold
        max_columns_threshold = 20000
        if isinstance(setting, dict):
            maybe_threshold = setting.get("max_columns_before_schema_linking")
            if isinstance(maybe_threshold, int) and maybe_threshold > 0:
                max_columns_threshold = maybe_threshold
        
        # Get max context usage percentage threshold (expects integer 0-99 from backend)
        max_context_usage_threshold = 0.5  # Default 50%
        if isinstance(setting, dict):
            maybe_context_usage = setting.get("max_context_usage_before_linking")
            if isinstance(maybe_context_usage, int) and 0 <= maybe_context_usage <= 99:
                # Convert percentage (0-99) to decimal (0.0-0.99)
                max_context_usage_threshold = float(maybe_context_usage) / 100.0
            elif isinstance(maybe_context_usage, float) and 0 <= maybe_context_usage <= 99:
                # Also handle float values from 0-99
                max_context_usage_threshold = float(maybe_context_usage) / 100.0
        
        logger.info(f"Max columns threshold from setting: {max_columns_threshold}")
        logger.info(f"Max context usage threshold from setting: {max_context_usage_threshold:.1%}")
        
        # Step 4: Check if column count exceeds threshold
        if total_columns > max_columns_threshold:
            logger.info(
                f"Column count ({total_columns}) exceeds threshold ({max_columns_threshold}), "
                f"forcing WITH_SCHEMA_LINK strategy"
            )
            return "WITH_SCHEMA_LINK"
        
        # Step 5: Get context window of the starting model
        # The sql_generator parameter from the request determines the starting agent
        # This would be passed through the request and available in state
        context_window = await _get_model_context_window(state)
        state.available_context_tokens = context_window
        
        logger.info(f"Model context window: {context_window} tokens")
        
        # Step 6: Apply the 50% threshold logic for token count
        if context_window <= 0:
            logger.warning("Invalid context window, defaulting to WITHOUT_SCHEMA_LINK")
            return "WITH_SCHEMA_LINK"
        
        needs_schema_link, usage_percentage = estimate_context_usage(
            schema_tokens,
            context_window,
            threshold_percentage=max_context_usage_threshold
        )
        
        strategy = "WITH_SCHEMA_LINK" if needs_schema_link else "WITHOUT_SCHEMA_LINK"
        
        logger.info(
            f"Schema link decision: {strategy} "
            f"(schema uses {usage_percentage:.1%} of context window vs {max_context_usage_threshold:.1%} threshold, "
            f"columns: {total_columns} vs {max_columns_threshold} threshold)"
        )

        return strategy
        
    except Exception as e:
        logger.error(f"Error in decide_schema_link_strategy: {e}")
        # Default to WITHOUT_SCHEMA_LINK on error
        return "WITHOUT_SCHEMA_LINK"


async def _get_model_context_window(state: SystemState) -> int:
    """
    Get the context window size for the model associated with the starting SQL generator.
    
    Args:
        state: System state containing agents_and_tools and other info
        
    Returns:
        int: Context window size in tokens
    """
    # Default context windows for testing
    # These can be overridden by actual model configurations
    DEFAULT_CONTEXT_WINDOWS = {
        "small": 8192,    # 8K for testing
        "medium": 32768,  # 32K for testing
        "large": 100000,  # 100K+ for testing
    }
    
    try:
        # Try to get context window from agent manager
        if hasattr(state, 'agents_and_tools') and state.agents_and_tools:
            agent_manager = state.agents_and_tools
            
            # Check if we have a method to get context window
            if hasattr(agent_manager, 'get_context_window'):
                # Get the starting generator type from workspace or request
                # For now, we'll assume it's available somewhere in state
                sql_generator = getattr(state, 'sql_generator', 'BASIC')
                context_window = agent_manager.get_context_window(sql_generator)
                if context_window and context_window > 0:
                    return context_window
            
            # Try to get from the agent pool configuration
            if hasattr(agent_manager, 'sql_agents_pool') and agent_manager.sql_agents_pool:
                # Get the first agent in the pool (which would be the starting agent)
                first_agent = agent_manager.sql_agents_pool[0]
                
                # Try to extract context window from agent configuration
                if hasattr(first_agent, 'model') and hasattr(first_agent.model, 'context_size'):
                    return first_agent.model.context_size
                
                # Check if there's a config attribute
                if hasattr(first_agent, 'config') and isinstance(first_agent.config, dict):
                    # Try different possible keys for context window
                    for key in ['context_window', 'context_size', 'max_context', 'max_tokens']:
                        if key in first_agent.config:
                            value = first_agent.config[key]
                            if isinstance(value, (int, float)) and value > 0:
                                return int(value)
        
        # If we can't get from agent manager, try from environment or configuration
        # This is where you might read from Django backend configuration
        # For now, return a default medium context window
        logger.warning("Could not determine model context window, using default (32K)")
        return DEFAULT_CONTEXT_WINDOWS["medium"]
        
    except Exception as e:
        logger.error(f"Error getting model context window: {e}")
        # Return a conservative default
        return DEFAULT_CONTEXT_WINDOWS["medium"]