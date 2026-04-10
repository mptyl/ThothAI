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

import os
import json
from django.conf import settings
from django.contrib import messages

# Removed Haystack imports - using LiteLLM instead
from thoth_core.models import SqlTable, SqlColumn, LLMChoices, LanguageCode
from thoth_core.thoth_ai.thoth_workflow.comment_generation_utils import (
    setup_llm_from_env,
)


def _clean_content(generated_content):
    cleaned_content = generated_content.strip()

    # Remove ```json and ``` markers if present
    if cleaned_content.startswith("```json"):
        cleaned_content = cleaned_content[7:]  # Remove ```json
    elif cleaned_content.startswith("```"):
        cleaned_content = cleaned_content[3:]  # Remove ```

    if cleaned_content.endswith("```"):
        cleaned_content = cleaned_content[:-3]  # Remove trailing ```

    # Strip any remaining whitespace
    cleaned_content = cleaned_content.strip()
    return cleaned_content


def _generate_scope_with_llm(llm_client, prompt_variables):
    """Generate scope using the LLM client."""
    template_path = os.path.join(
        settings.BASE_DIR,
        "thoth_core",
        "thoth_ai",
        "thoth_workflow",
        "prompt_templates",
        "generate_scope_prompt.txt",
    )

    with open(template_path, "r") as file:
        prompt_template = file.read()

    # Preprocess template (handles both {{}} syntax and Jinja2 control structures)
    from thoth_core.thoth_ai.thoth_workflow.comment_generation_utils import (
        preprocess_template,
    )

    formatted_prompt = preprocess_template(prompt_template, prompt_variables)

    # If template had Jinja2 control structures, it's already rendered
    # Otherwise, we need to format it
    if "{% " not in prompt_template:
        formatted_prompt = formatted_prompt.format(**prompt_variables)

    # Prepare messages
    messages = []
    if getattr(llm_client, "provider", None) != LLMChoices.GEMINI:
        messages.append(
            {
                "role": "system",
                "content": "You are an expert in relational database management, SQL and database semantics. You will be given a prompt related to database management.",
            }
        )
    messages.append({"role": "user", "content": formatted_prompt})

    # Generate response
    response = llm_client.generate(messages, max_tokens=2000)
    return response


def get_language_description(language_code):
    """Convert language code to full description."""
    for code, description in LanguageCode.choices:
        if code == language_code:
            return description
    return "English"  # fallback


def generate_scope_for_db(sql_db):
    """
    Generate scope for a single SqlDb instance using an AI model.

    Takes a single SqlDb instance, performs the LLM call, and saves the result.
    Returns on success, raises on failure.
    """
    llm = setup_llm_from_env()

    tables = SqlTable.objects.filter(sql_db=sql_db)
    tables_data = []
    for table in tables:
        columns = SqlColumn.objects.filter(sql_table=table)
        columns_data = [
            {
                "original_name": col.original_column_name,
                "description": col.column_description,
                "value_description": col.value_description,
            }
            for col in columns
        ]
        tables_data.append(
            {
                "name": table.name,
                "description": table.description,
                "columns": columns_data,
            }
        )

    language_code = sql_db.language or "en"
    language_description = get_language_description(language_code)
    prompt_variables = {
        "db_name": sql_db.name,
        "tables": tables_data,
        "language": language_description,
    }

    output = _generate_scope_with_llm(llm, prompt_variables)

    if not output or not hasattr(output, "content"):
        raise RuntimeError(f"AI did not return a scope for database '{sql_db.name}'.")

    generated_content = output.content

    try:
        # Clean the content - remove markdown code blocks if present
        cleaned_content = _clean_content(generated_content)

        # Try to parse the output as JSON
        scope_json = json.loads(cleaned_content)

        # Generate Markdown from JSON
        markdown_sections = []
        for key, value in scope_json.items():
            # Convert key to a readable title (e.g., "main_entities" -> "Main Entities")
            title = key.replace("_", " ").title()
            # Add section to markdown with title and content
            markdown_sections.append(f"## {title}\n{value}")

        # Join all sections with double newlines for paragraph separation
        markdown_scope = "\n\n".join(markdown_sections)

        # Save both formats
        sql_db.scope = markdown_scope
        sql_db.scope_json = json.dumps(scope_json, ensure_ascii=False, indent=2)
        sql_db.save()

    except json.JSONDecodeError:
        # If JSON parsing fails, save the raw output to scope and leave scope_json empty
        sql_db.scope = generated_content
        sql_db.scope_json = None
        sql_db.save()


def generate_scope(modeladmin, request, queryset):
    """
    Django admin action: generates a scope description for each selected SqlDb instance.
    """
    for db in queryset:
        try:
            generate_scope_for_db(db)
            modeladmin.message_user(
                request,
                f"Successfully generated scope for database '{db.name}'.",
                messages.SUCCESS,
            )
        except json.JSONDecodeError:
            modeladmin.message_user(
                request,
                f"Warning: AI output was not valid JSON for database '{db.name}'. Saving raw text to scope field.",
                messages.WARNING,
            )
        except Exception as e:
            modeladmin.message_user(
                request,
                f"Error generating scope for database '{db.name}': {str(e)}",
                messages.ERROR,
            )


generate_scope.short_description = "Generate scope (AI assisted - sync)"
