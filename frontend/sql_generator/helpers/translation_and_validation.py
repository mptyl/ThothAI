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

import logging
from helpers.language_utils import resolve_language_name

from .template_preparation import (
    translate_question_template,
    check_question_template,
)
from .dual_logger import log_info, log_error
from model.state_factory import StateFactory


logger = logging.getLogger(__name__)


async def run_question_translation(agents_and_tools, state, workspace) -> None:
    """
    Run the question translation flow if a translator agent is available.
    Mutates the provided state with original/translated question metadata.
    """
    # Get scope and language from workspace
    scope = workspace.get("sql_db", {}).get("scope", "")
    target_language = resolve_language_name(workspace.get("sql_db", {}).get("language", "English"))

    # Prepare the translation template
    translation_template = translate_question_template(
        state.question, target_language, scope
    )

    # Run the translation agent to detect language and translate if needed
    log_info("Running question translation check...")
    
    # Create lightweight dependencies for translation agent
    translation_deps = StateFactory.create_agent_deps(state, "question_translation")
    
    translation_result = await agents_and_tools.question_translator_agent.run(
        translation_template,
        deps=translation_deps,  # Use lightweight TranslationDeps instead of full SystemState
    )

    # Store original question and language in state
    state.original_question = state.question
    state.original_language = translation_result.output.detected_language

    # Update the question in state if translation was needed
    if translation_result.output.translated_question != state.question:
        state.question = translation_result.output.translated_question
        log_info(
            f"Question translated from {state.original_language} -> {target_language}"
        )
        log_info(f"New translated question: {state.question}")
    else:
        # Question was already in target language
        log_info(f"Question already in target language: {target_language}")


async def run_question_validation(agents_and_tools, state, workspace) -> tuple[str, bool]:
    """
    Run the question validation flow if a validator agent is available.
    Returns a tuple: (message_to_stream, is_valid).
    """
    # Get scope and language from workspace
    scope = workspace.get("sql_db", {}).get("scope", "")
    language = resolve_language_name(workspace.get("sql_db", {}).get("language", "English"))

    # Log scope and language used by LLM
    logger.info(f"LLM using scope: '{scope}' and language: '{language}'")
    log_info(f"LLM using scope: '{scope}' and language: '{language}'")

    # Prepare the check question template using the (possibly translated) question from state
    check_template = check_question_template()

    # Add scope and language to state for template dependency injection
    state.scope = scope
    state.language = language

    # Run the question validator agent with lightweight dependencies
    log_info("Running question validity check...")
    
    # Create lightweight dependencies for validation agent
    validation_deps = StateFactory.create_agent_deps(state, "question_validation")
    
    check_result = await agents_and_tools.question_validator_agent.run(
        check_template,
        deps=validation_deps,  # Use lightweight ValidationDeps instead of full SystemState
    )

    # Analyze the result
    outcome = check_result.output.outcome
    reasons = check_result.output.reasons

    # Log outcome and reasons from question check
    logger.info(
        f"Question check result - outcome: '{outcome}', reasons: '{reasons}'"
    )
    log_info(f"Question check result - outcome: '{outcome}', reasons: '{reasons}'")

    log_info(f"Question check outcome: {outcome}")

    if outcome != "OK":
        # Question is not valid, return error message
        error_message = f"## Question Validation Failed\n\n"
        error_message += f"**Status**: {outcome}\n\n"
        error_message += f"**Explanation**: {reasons}\n\n"
        error_message += "### Please try:\n\n"
        error_message += "- Rephrasing your question more clearly\n"
        error_message += "- Ensuring your question relates to the database scope\n"
        error_message += "- Using proper grammar and complete sentences\n"
        error_message += "- Being more specific about what data you want to retrieve\n\n"
        error_message += "### Examples of good questions:\n\n"
        error_message += "- *What is the average salary of employees?*\n"
        error_message += "- *Show me all customers from Italy*\n"
        error_message += "- *How many orders were placed last month?*"

        logger.error(f"Question validation failed: {outcome} - {reasons}")
        log_error(f"Question validation failed: {outcome} - {reasons}")
        return error_message, False

    # Question is valid, continue with workflow
    return "THOTHLOG:Question validation passed, proceeding with keyword extraction", True

