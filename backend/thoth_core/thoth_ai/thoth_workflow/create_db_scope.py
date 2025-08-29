# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

import os
import json
from django.conf import settings
from django.contrib import messages
# Removed Haystack imports - using LiteLLM instead
from thoth_core.models import SqlDb, SqlTable, SqlColumn, Setting, LLMChoices
from thoth_core.thoth_ai.thoth_workflow.comment_generation_utils import setup_default_comment_llm_model

def _clean_content(generated_content):
    cleaned_content = generated_content.strip()
    
    # Remove ```json and ``` markers if present
    if cleaned_content.startswith('```json'):
        cleaned_content = cleaned_content[7:]  # Remove ```json
    elif cleaned_content.startswith('```'):
        cleaned_content = cleaned_content[3:]  # Remove ```
    
    if cleaned_content.endswith('```'):
        cleaned_content = cleaned_content[:-3]  # Remove trailing ```
    
    # Strip any remaining whitespace
    cleaned_content = cleaned_content.strip()
    return cleaned_content


def _generate_scope_with_llm(llm_client, setting, prompt_variables):
    """Generate scope using the LLM client."""
    template_path = os.path.join(
        settings.BASE_DIR,
        'thoth_core',
        'thoth_ai',
        'thoth_workflow',
        'prompt_templates',
        'generate_scope_prompt.txt'
    )
    
    with open(template_path, 'r') as file:
        prompt_template = file.read()
    
    # Preprocess template (handles both {{}} syntax and Jinja2 control structures)
    from thoth_core.thoth_ai.thoth_workflow.comment_generation_utils import preprocess_template
    formatted_prompt = preprocess_template(prompt_template, prompt_variables)
    
    # If template had Jinja2 control structures, it's already rendered
    # Otherwise, we need to format it
    if '{% ' not in prompt_template:
        formatted_prompt = formatted_prompt.format(**prompt_variables)
    
    # Prepare messages
    messages = []
    if setting.comment_model.basic_model.provider != LLMChoices.GEMINI:
        messages.append({
            "role": "system",
            "content": "You are an expert in relational database management, SQL and database semantics. You will be given a prompt related to database management."
        })
    messages.append({"role": "user", "content": formatted_prompt})
    
    # Generate response
    response = llm_client.generate(messages, max_tokens=2000)
    return response


def generate_scope(modeladmin, request, queryset):
    """
    Generates a scope description for each selected SqlDb instance using an AI model.
    """
    try:
        if not hasattr(request, 'current_workspace') or not request.current_workspace:
            modeladmin.message_user(request, "No active workspace found. Please select a workspace.", level=messages.ERROR)
            return
        
        setting = request.current_workspace.setting
        if not setting or not setting.comment_model:
            modeladmin.message_user(request, "AI model for comment generation not configured in settings.", messages.ERROR)
            return

        llm = setup_default_comment_llm_model(setting)
        if llm is None:
            modeladmin.message_user(request, "Failed to set up LLM model.", messages.ERROR)
            return

        for db in queryset:
            tables = SqlTable.objects.filter(sql_db=db)
            tables_data = []
            for table in tables:
                columns = SqlColumn.objects.filter(sql_table=table)
                columns_data = [{
                    'original_name': col.original_column_name,
                    'description': col.column_description,
                    'value_description': col.value_description
                } for col in columns]
                tables_data.append({
                    'name': table.name,
                    'description': table.description,
                    'columns': columns_data
                })

            try:
                language = db.language if db.language else setting.language
                prompt_variables = {
                    "db_name": db.name,
                    "tables": tables_data,
                    "language": language
                }
                
                output = _generate_scope_with_llm(llm, setting, prompt_variables)
                
                if output and hasattr(output, 'content'):
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
                            title = key.replace('_', ' ').title()
                            # Add section to markdown with title and content
                            markdown_sections.append(f"## {title}\n{value}")
                        
                        # Join all sections with double newlines for paragraph separation
                        markdown_scope = "\n\n".join(markdown_sections)
                        
                        # Save both formats
                        db.scope = markdown_scope
                        db.scope_json = json.dumps(scope_json, ensure_ascii=False, indent=2)
                        db.save()
                        
                        modeladmin.message_user(request, f"Successfully generated scope for database '{db.name}'.", messages.SUCCESS)
                    
                    except json.JSONDecodeError:
                        # If JSON parsing fails, save the raw output to scope and leave scope_json empty
                        modeladmin.message_user(request, f"Warning: AI output was not valid JSON for database '{db.name}'. Saving raw text to scope field.", messages.WARNING)
                        db.scope = generated_content
                        db.scope_json = None
                        db.save()
                else:
                    modeladmin.message_user(request, f"AI did not return a scope for database '{db.name}'.", messages.WARNING)

            except Exception as e:
                modeladmin.message_user(request, f"Error generating scope for database '{db.name}': {str(e)}", messages.ERROR)

    except FileNotFoundError:
        modeladmin.message_user(request, "Prompt template file not found.", messages.ERROR)
    except Exception as e:
        modeladmin.message_user(request, f"An unexpected error occurred: {str(e)}", messages.ERROR)

generate_scope.short_description = "Generate scope (AI assisted)"
