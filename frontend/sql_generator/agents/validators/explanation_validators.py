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
Validators for SQL explanation agents.
"""

from typing import Optional
from pydantic_ai import RunContext, ModelRetry
from pydantic import ValidationError

from model.agent_dependencies import SqlExplanationDeps
from helpers.logging_config import get_logger
from helpers.dual_logger import log_info, log_warning, log_error

logger = get_logger(__name__)


class ExplanationValidators:
    """
    Validators for SQL explanation agents.
    """
    
    def create_explanation_validator(self):
        """
        Create a validator for SQL explanation agents to capture validation failures.
        
        Returns:
            Async validator function
        """
        async def validate_explanation_result(ctx: RunContext[SqlExplanationDeps], response: str):
            logger.info(f"SQL explanation validator started")
            logger.info(f"Response type: {type(response).__name__}")
            logger.info(f"Response content: {str(response)[:200]}...")
            
            try:
                # Response should be a simple string
                if not isinstance(response, str):
                    logger.info(f"Expected string response, got {type(response).__name__} - triggering retry")
                    log_info("SQL EXPLANATION VALIDATION - Wrong response type, retrying")
                    raise ModelRetry('Response must be a simple text string')
                
                explanation = response.strip()
                
                # Check if explanation is empty or too short
                if not explanation or len(explanation) < 10:
                    logger.info(f"Explanation too short or empty: '{explanation}' - triggering retry")
                    log_info("SQL EXPLANATION VALIDATION - Explanation too short, retrying")
                    raise ModelRetry('Explanation must be at least 10 characters long and contain meaningful content')
                
                if len(explanation) > 2000:
                    logger.warning(f"Explanation exceeds 2000 character limit: {len(explanation)} characters")
                    log_warning("SQL EXPLANATION LENGTH WARNING - Exceeds template limit")
                    # Don't truncate, just warn - let the user see the full response
                
                # Basic format validation - should contain bullet points as per template
                if not ('**' in explanation or '•' in explanation or '-' in explanation):
                    logger.warning("Explanation doesn't appear to contain bullet points as required by template")
                    log_warning("SQL EXPLANATION FORMAT WARNING - Missing bullet points")
                
                logger.info("SQL explanation validation passed successfully")
                log_info("SQL EXPLANATION VALIDATION PASSED")
                
                # CRITICAL FIX: Return the validated explanation to ensure it's used by the agent
                return explanation
                
            except ModelRetry:
                # Re-raise ModelRetry exceptions
                raise
            except ValidationError as e:
                logger.info(f"Pydantic validation error: {str(e)} - triggering retry")
                log_info("SQL EXPLANATION PYDANTIC VALIDATION - Validation error, retrying")
                raise ModelRetry(f'Response validation failed: {str(e)}')
            except Exception as e:
                logger.info(f"Unexpected validation error: {str(e)} - triggering retry")
                log_info("SQL EXPLANATION VALIDATION - Unexpected error, retrying")
                raise ModelRetry(f'Unexpected validation error: {str(e)}')
        
        return validate_explanation_result