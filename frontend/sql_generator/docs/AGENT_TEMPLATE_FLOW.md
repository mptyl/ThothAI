# Agent Template Flow Documentation

## Overview
This document describes the templates used by each actually implemented agent and the real execution flow of the SQL generator.

## Template Usage by Agent

### 1. **Keyword Extraction Agent**
- **System Template**: `system_templates/system_template_extract_keywords_from_question.txt`
  - Loaded via: `TemplateLoader.load(...)`
  - Used in: `AgentInitializer.create_keyword_extraction_agent()`
- **User Template**: `template_extract_keywords.txt`
  - Loaded via: `TemplateLoader.format('template_extract_keywords.txt', ...)`
  - Used in: `helpers/main_helpers/main_keyword_extraction.py` and `keyword_extraction.py`

### 2. **Question Validator Agent**
- **System Template**: `system_templates/system_template_check_question.txt`
  - Loaded via: `TemplateLoader.load(...)`
  - Used in: `AgentInitializer.create_question_validator_agent()`
- **User Template**: `template_check_question.txt`
  - Prepared via `TemplateLoader` in `helpers/main_helpers/main_translation_validation.py` (functions `run_question_validation` / `run_question_validation_with_translation`)

### 3. **Question Validator with Language Detection**
- **System Template**: Same as Question Validator
- **User Template**: `template_validate_question_with_language.txt`
  - Prepared via `TemplateLoader` in `helpers/main_helpers/main_translation_validation.py`
  - Note: The validator registers the Translator as a tool to perform translation when needed

### 4. **Question Translator Agent**
- **System Template**: `system_templates/system_template_translate_question.txt`
  - Loaded via: `TemplateLoader.load(...)`
  - Used in: `AgentInitializer.create_question_translator_agent()`
- **User Template**: `template_translate_question.txt`
  - Loaded via: `TemplateLoader.format('template_translate_question.txt', ...)`
  - Used in: `helpers/main_helpers/main_translation_validation.py` and `helpers/translation_and_validation.py`

### 5. **SQL Generation Agents** (BASIC, ADVANCED, EXPERT; methods: query_plan, step_by_step, divide_and_conquer)
- **System Template**: `system_templates/system_template_generate_sql.txt` (same for all)
  - Loaded via: `TemplateLoader.load(...)`
  - Used in: `AgentInitializer.create_sql_generation_agent()`
- **User Templates** (applied at runtime by `prepare_user_prompt_with_method`):
  - `template_generate_sql_query_plan.txt`
  - `template_generate_sql_step_by_step.txt`
  - `template_generate_sql_divide_and_conquer.txt`
  - Used in: `helpers/main_helpers/main_sql_generation.py`
- **Notes**:
  - Parallel generation with diverse temperatures
  - Per-call timeout protection via `asyncio.wait_for`

### 6. **Test Generator Agent**
- **System Template**: `system_templates/system_template_test_generator.txt`
  - Loaded via: `TemplateLoader.load(...)`
  - Used in: `AgentInitializer.create_test_generation_agent()`
- **User Template**: `template_generate_unit_tests.txt`
  - Loaded via: `TemplateLoader.format('template_generate_unit_tests.txt', ...)`
  - Used in: `helpers/main_helpers/main_test_generation.py`
- **Notes**: Per-call timeout protection via `asyncio.wait_for`

### 7. **Evaluator Agent**
- **System Template**: `system_templates/system_template_evaluate.txt`
  - Loaded via: `TemplateLoader.load(...)`
  - Used in: `AgentInitializer.create_evaluator_agent()`
- **User Template**: `template_evaluate_single.txt`
  - Loaded via: `TemplateLoader.format('template_evaluate_single.txt', ...)`
  - Used in: `helpers/main_helpers/main_evaluation.py` (function `evaluate_single_sql`)

### 8. **TestReducer Agent** (semantic test deduplication, conditional)
- **System Template**: `system_templates/system_template_test_reducer.txt`
  - Loaded via: `TemplateLoader.load(...)`
  - Used in: `AgentInitializer.create_test_reducer_agent()`
- **User Template**: `template_test_reducer.txt`
  - Loaded via: `TemplateLoader.format('template_test_reducer.txt', ...)`
  - Used in: `agents/test_reducer_agent.py` (function `run_test_reducer`)
- **Activation**: Only when multiple test generators are configured (`number_of_tests_to_generate >= 2`) and there are at least 10 unique tests. See `helpers/main_helpers/main_evaluation.py`.

### 9. **SQL Explanation Agent**
- **System Template**: `system_templates/system_template_explain_generated_sql.txt`
  - Loaded via: `TemplateLoader.load(...)`
  - Used in: `AgentInitializer.create_sql_explanation_agent()`
- **User Template**: `template_explain_generated_sql.txt`
  - Used in: `agents/core/agent_manager.py` (method `explain_generated_sql`)
  - Note: The code calls `TemplateLoader.format('user_sql_explain', ...)`, which maps to this file as per `docs/TEMPLATE_REFACTORING_CHANGES.md`.

### 10. **SqlEvaluator Agent** (Belt and Suspenders selection)
- **System Template**: `system_templates/system_template_sql_selector.txt`
  - Loaded via: `TemplateLoader.load(...)`
  - Used in: `AgentInitializer.create_sql_evaluator_agent()`
- **User Template**: `template_sql_selector.txt`
  - Loaded/Formatted in: `helpers/main_helpers/belt_and_suspenders_selection.py`
- **Role**: Invoked when the evaluation case is borderline (cases B or C) and `belt_and_suspenders` is enabled, to select the best SQL using failed test analysis.

## Flow Sequence

1. **Validation and Optional Translation**
   - Question Validator Agent (with Translator tool for language detection/translation)
2. **Keyword Extraction**
   - Keyword Extraction Agent
3. **Context Retrieval**
   - Vector DB + LSH (no agents; direct operations)
4. **SQL Generation**
   - SQL Generation Agents (BASIC/ADVANCED/EXPERT) run in parallel
   - Methods applied via user templates (query_plan, step_by_step, divide_and_conquer)
   - Each run protected by a timeout
5. **Test Generation**
   - Test Generator Agent (fixed `test_gen_agent_1` repeated with temperature scaling)
   - Each run protected by a timeout
6. **Optional Semantic Test Reduction**
   - TestReducer Agent (only if multiple test generators configured and enough tests)
7. **Evaluation**
   - Evaluator Agent evaluates each SQL with the deduplicated/reduced test set
   - Results aggregated into `SQL #N: OK/KO ...` verdict strings
8. **Optional Belt and Suspenders Selection**
   - SqlEvaluator Agent selects the best SQL for borderline evaluation cases
9. **SQL Explanation**
   - SQL Explanation Agent generates explanation in the user's language

## Template Files Summary

### System Templates (in `templates/system_templates/`)
- `system_template_extract_keywords_from_question.txt`
- `system_template_check_question.txt`
- `system_template_translate_question.txt`
- `system_template_generate_sql.txt`
- `system_template_test_generator.txt`
- `system_template_evaluate.txt`
- `system_template_explain_generated_sql.txt`
- `system_template_test_reducer.txt`
- `system_template_sql_selector.txt`

### User Templates (in `templates/`)
- `template_extract_keywords.txt`
- `template_check_question.txt`
- `template_validate_question_with_language.txt`
- `template_translate_question.txt`
- `template_generate_sql_query_plan.txt`
- `template_generate_sql_step_by_step.txt`
- `template_generate_sql_divide_and_conquer.txt`
- `template_generate_unit_tests.txt`
- `template_evaluate_single.txt`
- `template_explain_generated_sql.txt`
- `template_test_reducer.txt`
- `template_sql_selector.txt`

## Important Notes

1. **SQL Generation Agents**: All three SQL generation agents share the same system template (`system_template_generate_sql.txt`). Differentiation happens at the user prompt level in `helpers/main_helpers/main_sql_generation.py`.
2. **Template Formatting**: All templates are loaded via `TemplateLoader`. Safe formatting is used where JSON blocks are present.
3. **Template Cleaning**: All system templates are processed through `clean_template_for_llm()` before being used.
4. **Language Support**: Translation + enhanced validation flow uses the Translator tool inside the Validator where needed.
5. **Semantic Test Deduplication**: TestReducer runs conditionally only when multiple test generators are configured and the test set is sufficiently large.
6. **Timeouts**: Per-call timeouts are applied to SQL generation and test generation (`asyncio.wait_for`) to prevent hangs.
7. **Agent Wiring**: Agents are created in `agents/core/agent_initializer.py` and configured/wired (validators, tools) in `agents/core/agent_manager.py`. 