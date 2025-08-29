# Agent Template Flow Documentation

## Overview
This document describes exactly which system and user templates are used by each agent during the SQL generation flow.

## Template Usage by Agent

### 1. **Keyword Extraction Agent**
- **System Template**: `system_template_extract_keywords_from_question.txt`
  - Loaded via: `keywords_default_system_template()`
  - Used in: `AgentInitializer.create_keyword_extraction_agent()`
- **User Template**: `template_extract_keywords.txt`
  - Loaded via: `keywords_template(question)`
  - Used in: `keyword_extraction.py` line 31

### 2. **Question Validator Agent**
- **System Template**: `system_template_check_question.txt`
  - Loaded via: `check_question_system_template()`
  - Used in: `AgentInitializer.create_question_validator_agent()`
- **User Template**: `template_check_question.txt`
  - Loaded via: `check_question_template()`
  - Used in: `model/system_state.py` line 924

### 3. **Question Validator with Language Detection**
- **System Template**: Same as Question Validator
- **User Template**: `template_validate_question_with_language.txt`
  - Loaded via: `validate_question_with_language_template(question, scope, language)`
  - Used in: `model/system_state.py` line 808

### 4. **Question Translator Agent**
- **System Template**: `system_template_translate_question.txt`
  - Loaded via: `question_translator_system_template()`
  - Used in: `AgentInitializer.create_question_translator_agent()`
- **User Template**: `template_translate_question.txt`
  - Loaded via: `translate_question_template(question, target_language, scope)`
  - Used in: Multiple places for translation

### 5. **SQL Generation Agents** (query_plan, divide_and_conquer, step_by_step)
- **System Template**: `system_template_generate_sql.txt` (SAME FOR ALL)
  - Loaded via: `sql_generator_system_template()`
  - Used in: `AgentInitializer.create_sql_generation_agent()`
  - Note: All SQL generators use the same system template
- **User Template**: Different based on template_type parameter:
  - `template_generate_sql_query_plan.txt`
  - `template_generate_sql_divide_and_conquer.txt`
  - `template_generate_sql_step_by_step.txt`
  - Used in: `main_sql_generation.py`

### 6. **Test Generator Agent**
- **System Template**: `system_template_test_generator.txt`
  - Loaded via: `test_generator_system_template()`
  - Used in: `AgentInitializer.create_test_generation_agent()`
- **User Template**: `template_generate_unit_tests.txt`
  - Loaded via: `test_generator_template(directives, dbmanager, ...)`
  - Used in: `main_test_generation.py` line 92

### 7. **Evaluator Agent**
- **System Template**: `system_template_evaluate.txt`
  - Loaded via: `evaluator_system_template()`
  - Used in: `AgentInitializer.create_evaluation_agent()`
- **User Template**: `template_evaluate.txt`
  - Loaded via: `evaluator_template(question, test_thinking, ...)`
  - Used in: `main_evaluation.py` line 111
  - Also used in: `test_generator_with_evaluator.py` line 78

### 8. **SQL Explanation Agent**
- **System Template**: `system_template_explain_generated_sql.txt`
  - Loaded via: `sql_explanation_system_template()`
  - Used in: `AgentInitializer.create_sql_explanation_agent()`
- **User Template**: `template_explain_generated_sql.txt`
  - Loaded via: `sql_explanation_template(generated_sql, question, ...)`
  - Used in: `agent_manager.py` line 529

### 9. **Ask Human Agent**
- **System Template**: `system_template_ask_human.txt`
  - Loaded via: `ask_human_system_template()`
  - Used in: `AgentInitializer.create_ask_human_agent()`
- **User Template**: None (uses direct input)

## Flow Sequence

1. **Question Validation Phase**
   - Question Validator Agent (with language detection if enabled)
   - Question Translator Agent (if translation needed)

2. **Keyword Extraction Phase**
   - Keyword Extraction Agent

3. **Context Retrieval Phase**
   - No agents involved (direct vector DB operations)

4. **SQL Generation Phase**
   - SQL Generation Agents (multiple in parallel)
   - Each uses the same system template but different user templates

5. **Test Generation Phase**
   - Test Generator Agent

6. **Evaluation Phase**
   - Evaluator Agent

7. **SQL Explanation Phase**
   - SQL Explanation Agent (generates explanation in user's language)

## Template Files Summary

### System Templates (in `templates/system_templates/`)
- `system_template_extract_keywords_from_question.txt`
- `system_template_check_question.txt`
- `system_template_translate_question.txt`
- `system_template_generate_sql.txt`
- `system_template_test_generator.txt`
- `system_template_evaluate.txt`
- `system_template_explain_generated_sql.txt`
- `system_template_ask_human.txt`

### User Templates (in `templates/`)
- `template_extract_keywords.txt`
- `template_check_question.txt`
- `template_validate_question_with_language.txt`
- `template_translate_question.txt`
- `template_generate_sql_query_plan.txt`
- `template_generate_sql_divide_and_conquer.txt`
- `template_generate_sql_step_by_step.txt`
- `template_generate_unit_tests.txt`
- `template_evaluate.txt`
- `template_explain_generated_sql.txt`

## Important Notes

1. **SQL Generation Agents**: All three SQL generation strategies (query_plan, divide_and_conquer, step_by_step) use the SAME system template (`system_template_generate_sql.txt`). The differentiation happens at the user prompt level.

2. **Template Formatting**: Many templates use the `_format_template_safe()` function to handle JSON content with braces that need escaping.

3. **Clean Template**: All system templates are processed through `clean_template_for_llm()` before being used.

4. **Language Support**: The SQL Explanation Agent and Question Translator Agent support multiple languages, specified via the `language` parameter.

5. **Fallback Behavior**: If an agent's configuration doesn't specify a system_prompt, the default template is used (when `force_default_prompt=True` or no custom prompt provided).