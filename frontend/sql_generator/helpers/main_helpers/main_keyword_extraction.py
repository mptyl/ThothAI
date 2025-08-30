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
Helper module for keyword extraction phase (Phase 2) of the SQL generation process.
This module handles the extraction of keywords from the user's question.
"""

from typing import List
from ..template_preparation import TemplateLoader
from ..dual_logger import log_debug, log_info, log_error
from model.state_factory import StateFactory


async def extract_keywords(state, question: str, kw_agent) -> List[str]:
    """
    Extracts keywords from the user's question using the specified agent.
    
    This function processes the user's natural language question to identify
    key terms that will be used for SQL generation. It uses an AI agent to
    analyze the question and extract relevant keywords.
    
    Args:
        state: The application state object where extracted keywords will be stored
               and which contains the user's question.
        question: The user's question to extract keywords from.
        kw_agent: The keyword extraction agent that will process the question.
                 This agent should have a 'run' method and a 'name' attribute.
    
    Returns:
        list[str]: The extracted keywords.
    """
    try:
        # Await the agent run call as it's an async operation
        template = TemplateLoader.format('user_keywords', question=question)
        log_debug(f"Keyword extraction template for {kw_agent.name}")
        
        # Create lightweight dependencies for keyword extraction agent
        kw_deps = StateFactory.create_agent_deps(state, "keyword_extraction")
        
        result = await kw_agent.run(
            template,
            deps=kw_deps,  # Use lightweight KeywordExtractionDeps instead of full SystemState
            model_settings={"temperature": 0.2}
        )
        # Result contains keywords list; save to state
        log_info(f"Keywords extracted: {state.keywords}")
        return list(result.output.keywords)
        
    except Exception as e:
        error=f"Keyword extraction failed with {kw_agent.name}: {str(e)}"
        log_error(error)
        
        # Re-raise the exception so the calling function can handle fallback
        raise e