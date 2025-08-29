# Copyright (c) 2025 Marco Pancotti
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tool for updating SystemState fields during agent execution.
This tool allows agents to modify state fields like question, original_question, and original_language.
"""

import logging
from typing import Any
from pydantic_ai.tools import RunContext
from model.system_state import SystemState

logger = logging.getLogger(__name__)


def update_state_tool(
    ctx: RunContext[SystemState],
    question: str = None,
    original_question: str = None, 
    original_language: str = None
) -> str:
    """
    Update SystemState fields with new values.
    
    Args:
        ctx: RunContext containing SystemState
        question: Updated question (translated if needed)
        original_question: Original question before translation
        original_language: Language of the original question
        
    Returns:
        str: Confirmation message about what was updated
    """
    state = ctx.deps
    updates = []
    
    
    if question is not None:
        old_question = getattr(state, 'question', None)
        state.question = question
        updates.append(f"question: '{old_question}' -> '{question}'")
    
    if original_question is not None:
        old_original = getattr(state, 'original_question', None)
        state.original_question = original_question
        updates.append(f"original_question: '{old_original}' -> '{original_question}'")
        
    if original_language is not None:
        old_language = getattr(state, 'original_language', None)
        state.original_language = original_language
        updates.append(f"original_language: '{old_language}' -> '{original_language}'")
    
    if updates:
        update_message = f"SystemState updated: {'; '.join(updates)}"
        return update_message
    else:
        return "No updates were made to SystemState"