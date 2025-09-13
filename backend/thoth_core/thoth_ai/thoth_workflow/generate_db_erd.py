import os
import re

from django.conf import settings
from django.contrib import messages

from thoth_core.models import LLMChoices, Relationship, SqlColumn, SqlTable
from thoth_core.thoth_ai.thoth_workflow.comment_generation_utils import (
    preprocess_template,
    setup_llm_from_env,
)
from thoth_core.thoth_ai.thoth_workflow.generate_db_documentation import (
    extract_mermaid_diagram,
    generate_schema_string_from_models,
)


def generate_db_erd(modeladmin, request, queryset):
    """
    Generate ONLY the ERD (Mermaid) for the selected SqlDb and save it into the
    `erd` field, without producing full documentation artifacts.
    """
    try:
        # Prepare LLM
        try:
            llm = setup_llm_from_env()
        except Exception as e:
            modeladmin.message_user(
                request,
                f"Failed to set up LLM model from environment: {str(e)}",
                messages.ERROR,
            )
            return

        # Process only the first selected DB
        if queryset.count() > 1:
            modeladmin.message_user(
                request,
                "Multiple databases selected. Processing only the first one.",
                messages.WARNING,
            )

        db = queryset.first()
        if not db:
            modeladmin.message_user(request, "No database selected.", messages.ERROR)
            return

        # Load the prompt template used to produce a Mermaid ERD
        template_path = os.path.join(
            settings.BASE_DIR,
            "thoth_core",
            "thoth_ai",
            "thoth_workflow",
            "prompt_templates",
            "generate_db_documentation_prompt.txt",
        )

        with open(template_path, "r") as file:
            prompt_template_text = file.read()

        # Collect DB info: schema string, tables + columns, relationships
        schema_string = generate_schema_string_from_models(db.id)

        tables_data = []
        for table in SqlTable.objects.filter(sql_db=db):
            columns_data = []
            for col in SqlColumn.objects.filter(sql_table=table):
                columns_data.append(
                    {
                        "name": col.original_column_name,
                        "expanded_name": col.column_name or col.original_column_name,
                        "data_type": col.data_format,
                        "description": col.column_description
                        or col.generated_comment
                        or "",
                        "value_description": col.value_description or "",
                        "is_pk": bool(col.pk_field),
                        "is_fk": bool(col.fk_field),
                        "fk_reference": col.fk_field if col.fk_field else "",
                    }
                )

            tables_data.append(
                {
                    "name": table.name,
                    "description": table.description or table.generated_comment or "",
                    "columns": columns_data,
                }
            )

        relationships = Relationship.objects.filter(
            source_table__sql_db=db
        ) | Relationship.objects.filter(target_table__sql_db=db)

        relationships_data = []
        for rel in relationships:
            relationships_data.append(
                {
                    "source_table": rel.source_table.name,
                    "source_column": rel.source_column.original_column_name,
                    "target_table": rel.target_table.name,
                    "target_column": rel.target_column.original_column_name,
                    "name": f"{rel.source_table.name}_{rel.target_table.name}_fk",
                }
            )

        # Build LLM messages
        llm_messages = []
        if getattr(llm, "provider", None) != LLMChoices.GEMINI:
            llm_messages.append(
                {
                    "role": "system",
                    "content": "You are an expert in database schema design. Generate ONLY a Mermaid ERD diagram in mermaid notation.",
                }
            )

        prompt_variables = {
            "db_name": db.name,
            "schema_string": schema_string,
            "tables": tables_data,
            "relationships": relationships_data,
        }

        formatted_prompt = preprocess_template(prompt_template_text, prompt_variables)
        if "{% " not in prompt_template_text:
            formatted_prompt = formatted_prompt.format(**prompt_variables)

        llm_messages.append({"role": "user", "content": formatted_prompt})

        # Call LLM
        output = llm.generate(llm_messages, max_tokens=3000)

        mermaid_diagram = ""
        if output and hasattr(output, "content"):
            llm_response = output.content
            mermaid_diagram = extract_mermaid_diagram(llm_response) or llm_response

        if not mermaid_diagram or not mermaid_diagram.strip():
            modeladmin.message_user(
                request,
                "LLM did not return a Mermaid diagram.",
                messages.ERROR,
            )
            return

        # Persist ERD into the DB and notify
        db.erd = mermaid_diagram.strip()
        db.save(update_fields=["erd"])

        modeladmin.message_user(
            request,
            f"ERD diagram generated and saved for database '{db.name}'.",
            messages.SUCCESS,
        )

    except FileNotFoundError:
        modeladmin.message_user(
            request, "Prompt template file not found.", level=messages.ERROR
        )
    except Exception as e:
        modeladmin.message_user(
            request, f"An unexpected error occurred: {str(e)}", level=messages.ERROR
        )


generate_db_erd.short_description = "Generate ERD diagram only (AI assisted)"

