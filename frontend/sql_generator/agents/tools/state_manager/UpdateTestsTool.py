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
Tool for updating test units in SystemState during agent execution.
This tool allows test generator agents to save generated test statements.
"""

import logging
from typing import List
from pydantic_ai.tools import RunContext
from model.system_state import SystemState

logger = logging.getLogger(__name__)


def update_tests_tool(
    ctx: RunContext[SystemState],
    thinking: str = None,
    test_units: List[str] = None
) -> str:
    """
    Update SystemState with generated test units and thinking process.
    
    Args:
        ctx: RunContext containing SystemState
        thinking: The reasoning process for test generation
        test_units: List of test statements (e.g., "The generated query should...", "The generated query must not...")
        
    Returns:
        str: Confirmation message about what was updated
    """
    state = ctx.deps
    updates = []
    
    if thinking is not None:
        state.thinking = thinking
        updates.append(f"thinking updated ({len(thinking)} chars)")
    
    if test_units is not None:
        state.test_units = test_units
        updates.append(f"test_units updated ({len(test_units)} tests)")
        
        # Log the test units for debugging
        logger.info(f"Test units saved: {test_units}")
    
    if updates:
        update_message = f"Test generation completed: {'; '.join(updates)}"
        logger.info(update_message)
        return update_message
    else:
        return "No test updates were made to SystemState"