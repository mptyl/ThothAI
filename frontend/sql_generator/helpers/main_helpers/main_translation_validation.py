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
Helper module for question translation and validation phase (Phase 1) of the SQL generation process.
This module implements a multi-agent system where:
1. Validator agent detects if question is in wrong language and calls translator
2. Translator agent translates and updates SystemState via UpdateStateTool
3. Validator agent then validates the (possibly translated) question
"""

import logging
from dataclasses import dataclass
from typing import Optional, NamedTuple

from ..template_preparation import (
    translate_question_template,
    check_question_template,
)
from ..dual_logger import log_info, log_error
from model.system_state import SystemState
from model.state_factory import StateFactory


@dataclass
class QuestionValidationDeps:
    """Dependencies for question validation containing the necessary data for template injection."""
    question: str
    scope: str
    language: str


@dataclass 
class TranslationDeps:
    """Dependencies for question translation containing the necessary data for template injection."""
    question: str
    target_language: str
    scope: str


class TranslationResult(NamedTuple):
    """Result of translation operation with explicit data."""
    translated_question: str
    original_question: str
    original_language: str
    was_translated: bool


class ValidationResult(NamedTuple):
    """Complete result of validation operation."""
    message: str
    is_valid: bool
    question: str
    original_question: Optional[str] = None
    original_language: Optional[str] = None


logger = logging.getLogger(__name__)


async def run_question_translation(agents_and_tools, state, workspace) -> None:
    """
    Run the question translation flow if a translator agent is available.
    Mutates the provided state with original/translated question metadata.
    """
    # Get scope and language from workspace
    scope = workspace.get("sql_db", {}).get("scope", "")
    target_language = workspace.get("sql_db", {}).get("language", "English")

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


async def run_question_validation_with_translation(agents_and_tools, state, workspace) -> ValidationResult:
    """
    Run the enhanced question validation flow with language detection and translation coordination.
    This function implements a multi-agent system where the validator can call the translator.
    Returns ValidationResult with all necessary data.
    """
    # Get scope and language from workspace
    state.scope = workspace.get("sql_db", {}).get("scope", "")
    state.language = workspace.get("sql_db", {}).get("language", "English")

    log_info(f"Starting question validation - Target language: {state.language}")

    # Create a combined agent that has both validator and translator capabilities
    # The validator agent gets access to the translator agent as a tool
    if not hasattr(agents_and_tools, 'question_validator_agent') or not hasattr(agents_and_tools, 'question_translator_agent'):
        # Fallback to simple validation due to error
        log_info("Falling back to simple validation due to error")
        simple_result = await run_question_validation(agents_and_tools, state, workspace)
        return ValidationResult(
            message=simple_result[0],
            is_valid=simple_result[1],
            question=state.question
        )

    # Add the translator as a tool to the validator agent
    validator_agent = agents_and_tools.question_validator_agent
    translator_agent = agents_and_tools.question_translator_agent

    # Store translation result to return explicitly
    translation_result = None
    
    # Check if translator_tool is already registered to prevent duplicate registration
    existing_tool_names = [tool.name for tool in validator_agent._function_toolset.tools]
    
    if "translator_tool" not in existing_tool_names:
        # Register the translator agent as a tool for the validator (without state updates)
        @validator_agent.tool
        async def translator_tool(question_to_translate: str, target_language: str, scope: str) -> str:
            """Translate a question to the target language and return translation info."""
            nonlocal translation_result
            try:
                # Validate inputs
                if not question_to_translate or not question_to_translate.strip():
                    return "Translation failed: Empty question provided"
                
                if not target_language or not target_language.strip():
                    return "Translation failed: No target language specified"
                
                # Create translation dependencies
                translation_deps = TranslationDeps(
                    question=question_to_translate.strip(),
                    target_language=target_language.strip(),
                    scope=scope or ""
                )
                
                # Get the translation template and run the translator agent
                translation_template = translate_question_template(
                    question_to_translate.strip(), target_language.strip(), scope or ""
                )
                translation_agent_result = await translator_agent.run(
                    translation_template,
                    deps=translation_deps,
                )
                
                # Validate translation result
                if not translation_agent_result:
                    return "Translation failed: Invalid translation result"
                
                # Store translation result for explicit return
                translation_result = TranslationResult(
                    translated_question=translation_agent_result.output.translated_question,
                    original_question=question_to_translate,
                    original_language=translation_agent_result.output.detected_language,
                    was_translated=translation_agent_result.output.translated_question != question_to_translate
                )
                
                log_info(f"Translation completed: {question_to_translate} -> {translation_result.translated_question}")
                return f"Translation successful. Question translated from {translation_result.original_language} to {target_language}"
                
            except Exception as e:
                error_msg = f"Translation failed: {str(e)}"
                logger.error(error_msg)
                log_error(error_msg)
                return error_msg

    # Prepare the enhanced validation template with language detection
    from ..template_preparation import validate_question_with_language_template
    validation_template = validate_question_with_language_template()

    # Run the enhanced validator agent with translator access
    log_info("Running enhanced question validation with language detection...")
    
    # Create lightweight dependencies for validation agent
    validation_deps = StateFactory.create_agent_deps(state, "question_validation")
    
    try:
        check_result = await validator_agent.run(
            validation_template,
            deps=validation_deps,  # Use lightweight ValidationDeps instead of full SystemState
        )

        logger.info(f"Validator agent execution completed")
        
        # Check if we got a valid result
        if not check_result or not hasattr(check_result, 'data'):
            log_error("Validator agent returned invalid result")
            simple_result = await run_question_validation(agents_and_tools, state, workspace)
            return ValidationResult(
                message=simple_result[0],
                is_valid=simple_result[1],
                question=state.question
            )
        
        # Analyze the result
        outcome = check_result.output.outcome
        reasons = check_result.output.reasons
        detected_language = getattr(check_result.output, 'detected_language', 'unknown')
        translation_needed = getattr(check_result.output, 'translation_needed', False)
        
        # Log the detection results
        log_info(f"Language detection: {detected_language}, Translation needed: {translation_needed}")
        
    except Exception as e:
        error_msg = f"Enhanced validation failed: {str(e)}"
        logger.error(error_msg)
        log_error(error_msg)
        # Fallback to simple validation
        log_info("Falling back to simple validation due to error")
        simple_result = await run_question_validation(agents_and_tools, state, workspace)
        return simple_result[0], simple_result[1], None

    if outcome != "OK":
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

        log_error(f"Question validation failed: {outcome} - {reasons}")
        return ValidationResult(
            message=error_message,
            is_valid=False,
            question=state.question,
            original_question=translation_result.original_question if translation_result else None,
            original_language=translation_result.original_language if translation_result else None
        )
   
    success_msg = "THOTHLOG:Question validation passed"
    if translation_needed:
        success_msg += f" (translated from {detected_language} to {state.language})"
    success_msg += ", proceeding with keyword extraction"
    log_info(f"Enhanced validation completed successfully - {success_msg}")
    
    return ValidationResult(
        message=success_msg,
        is_valid=True,
        question=translation_result.translated_question if translation_result else state.question,
        original_question=translation_result.original_question if translation_result else None,
        original_language=translation_result.original_language if translation_result else None
    )


async def run_question_validation(agents_and_tools, state, workspace) -> tuple[str, bool]:
    """
    Run the original question validation flow (fallback version).
    Returns a tuple: (message_to_stream, is_valid).
    """
    # Get scope and language from workspace
    scope = workspace.get("sql_db", {}).get("scope", "")
    language = workspace.get("sql_db", {}).get("language", "English")

    # Log scope and language used by LLM
    logger.info(f"LLM using scope: '{scope}' and language: '{language}'")
    log_info(f"LLM using scope: '{scope}' and language: '{language}'")

    # Prepare the check question template (now without parameters - it uses dependency injection)
    check_template = check_question_template()
    
    # Create validation dependencies with the data needed for template injection
    validation_deps = QuestionValidationDeps(
        question=state.question,
        scope=scope,
        language=language
    )

    # Run the question validator agent with lightweight dependencies  
    log_info("Running question validity check...")
    
    # Create lightweight dependencies for validation agent
    state_validation_deps = StateFactory.create_agent_deps(state, "question_validation")
    
    check_result = await agents_and_tools.question_validator_agent.run(
        check_template,
        deps=state_validation_deps,  # Use lightweight ValidationDeps instead of full SystemState
    )

    # Analyze the result - in PydanticAI 0.7.0, access via .output
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