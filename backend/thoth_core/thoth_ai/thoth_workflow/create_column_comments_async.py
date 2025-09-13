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

import json
import logging
import pandas as pd
from django.db import transaction
from tabulate import tabulate

from thoth_core.thoth_ai.thoth_workflow.comment_generation_utils import (
    setup_llm_from_env,
    setup_sql_db,
    output_to_json,
    get_table_schema_safe,
)
from thoth_core.models import LLMChoices, SqlColumn, SqlTable
from thoth_core.thoth_ai.prompts.columns_comment_prompt import get_columns_prompt

# Configure logging
logger = logging.getLogger(__name__)


def create_column_comments_async(column_ids: list) -> str:
    """
    Async-compatible function to generate comments for specified columns.

    Args:
        column_ids: List of column IDs to process

    Returns:
        Status message indicating success or failure
    """
    try:
        if not column_ids:
            return "No columns provided"

        # Get columns
        columns = SqlColumn.objects.filter(id__in=column_ids)
        if not columns.exists():
            return "No valid columns found"

        # Group columns by table for efficient processing
        columns_by_table = {}
        for column in columns:
            table_id = column.sql_table.id
            if table_id not in columns_by_table:
                columns_by_table[table_id] = []
            columns_by_table[table_id].append(column)

        # Process each table's columns
        total_processed = 0
        for table_id, table_columns in columns_by_table.items():
            table = SqlTable.objects.get(id=table_id)
            language = table.sql_db.language or "en"

            # Process columns for this table
            result = process_column_chunk_for_table(table, table_columns, language)
            if result == "OK":
                total_processed += len(table_columns)
            else:
                logger.error(
                    f"Error processing columns for table {table.name}: {result}"
                )

        return f"Successfully processed {total_processed} columns"

    except Exception as e:
        logger.error(f"Error in create_column_comments_async: {str(e)}")
        return f"Error: {str(e)}"


@transaction.atomic
def process_column_chunk_for_table(table, columns, language):
    """
    Process a chunk of columns for a specific table.

    Args:
        table: The SqlTable object
        columns: List of SqlColumn objects to process
        setting: The Setting object
        language: Language for comments

    Returns:
        "OK" on success, error message on failure
    """
    try:
        # Setup database
        table_db = table.sql_db
        try:
            db = setup_sql_db(table_db)
        except Exception as e:
            return f"Error setting up SQL database: {str(e)}"

        # Get the table schema/structure using the safe wrapper
        table_schema = get_table_schema_safe(db, table.name)
        all_example_data = db.get_example_data(table.name, 5)

        # Setup LLM model
        llm = setup_llm_from_env()
        if llm is None:
            return "Default LLM model not found"

        # Get column names
        selected_column_names = [col.original_column_name for col in columns]
        tabulated_selected_columns = tabulate(
            [selected_column_names], headers=["Selected Columns"], tablefmt="pipe"
        )

        # Get the table comments
        table_comment = (
            table.description
            if table.description and table.description != ""
            else table.generated_comment
        )
        selected_column_comments = create_filtered_column_comments_dataframe(
            table, selected_column_names
        )

        # Prepare example data for available columns
        available_columns_in_data = set(all_example_data.keys())
        selected_columns_present_in_data = [
            col for col in selected_column_names if col in available_columns_in_data
        ]

        # Create example data table with available columns
        if selected_columns_present_in_data:
            filtered_example_data = {
                col: all_example_data[col] for col in selected_columns_present_in_data
            }
            example_data = tabulate(
                filtered_example_data, headers="keys", tablefmt="pipe", showindex=False
            )
        else:
            example_data = "No example data available for the selected columns."

        # Prepare prompt variables
        prompt_variables = {
            "table_schema": table_schema,
            "table_comment": table_comment,
            "column_list": tabulated_selected_columns,
            "column_comments": selected_column_comments,
            "example_data": example_data,
            "table": table,
            "language": language,
            "max_examples": 10,  # Maximum number of enum values to show in description
        }

        # Format the prompt
        try:
            from thoth_core.thoth_ai.thoth_workflow.comment_generation_utils import (
                preprocess_template,
            )

            prompt_template = get_columns_prompt()
            # Preprocess template to convert {{variable}} to {variable}
            prompt_template = preprocess_template(prompt_template)
            formatted_prompt = prompt_template.format(**prompt_variables)
        except KeyError as e:
            logger.error(f"KeyError during template formatting: {e}")
            logger.error(f"Missing key: {str(e)}")
            logger.error(f"Available keys: {list(prompt_variables.keys())}")
            return f"Error formatting template: missing key {str(e)}"
        except Exception as e:
            logger.error(f"Error formatting prompt template: {e}")
            return f"Error formatting template: {str(e)}"

        # Prepare messages
        messages = []
        if getattr(llm, "provider", None) != LLMChoices.GEMINI:
            messages.append(
                {
                    "role": "system",
                    "content": "You are an expert in relational database management, SQL and database semantics. You will be given a prompt related to database management.",
                }
            )
        messages.append({"role": "user", "content": formatted_prompt})

        # Generate using LLM client
        output = llm.generate(messages, max_tokens=2000)

        try:
            table_comment_json = output_to_json(output)
            if table_comment_json is None:
                # Log the raw output for debugging
                logger.error(
                    f"No JSON found in LLM response. Raw output: {str(output)[:500]}"
                )
                return "Error: No JSON-like content found in the response"
            else:
                logger.info(
                    f"Parsed JSON successfully: {len(table_comment_json)} items"
                )
                return_code = update_column_comments_on_backend(
                    table_comment_json, table
                )
                return return_code
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Raw output: {str(output)[:500]}")
            return "Error: The generated content is not a valid JSON"
        except Exception as e:
            logger.error(f"Unexpected error in column comment generation: {e}")
            logger.error(f"Type of error: {type(e).__name__}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error processing column chunk: {str(e)}"

    except Exception as e:
        return f"Error processing column chunk: {str(e)}"


def update_column_comments(table, column_comments):
    """
    Update the generated_comment field for columns in the given table.

    Args:
        table: The SqlTable object containing the columns to update.
        column_comments: A list of dictionaries, each containing 'name' and 'generated_comment' keys.

    Returns:
        str: "OK" on success, error message on failure
    """
    try:
        for comment in column_comments:
            original_column_name = comment["name"]
            generated_comment = comment["generated_comment"]

            # Get the column object
            column = table.columns.filter(
                original_column_name=original_column_name
            ).first()

            if column:
                # Update the generated_comment field
                column.generated_comment = generated_comment
                column.save()
                logger.info(
                    f"Updated comment for column '{original_column_name}' in table '{table.name}'"
                )
            else:
                return (
                    f"Column '{original_column_name}' not found in table '{table.name}'"
                )
        return "OK"
    except Exception as e:
        logger.error(f"Error updating column comments: {str(e)}", exc_info=True)
        return f"Error updating column comments: {str(e)}"


def update_column_comments_on_backend(columns_comment_json, table):
    """Helper function to update column comments from JSON."""
    if columns_comment_json and isinstance(columns_comment_json, list):
        try:
            column_comments = []
            for i, item in enumerate(columns_comment_json):
                try:
                    if isinstance(item, dict):
                        # Handle both possible key names, being careful with the access
                        column_name = None
                        description = None

                        # Try different key variations
                        for name_key in ["column_name", "name", "column", "col_name"]:
                            if name_key in item:
                                column_name = item[name_key]
                                break

                        for desc_key in [
                            "description",
                            "comment",
                            "desc",
                            "generated_comment",
                        ]:
                            if desc_key in item:
                                description = item[desc_key]
                                break

                        if column_name and description:
                            column_comments.append(
                                {
                                    "name": str(column_name).strip(),
                                    "generated_comment": str(description).strip(),
                                }
                            )
                        else:
                            logger.warning(
                                f"Skipping item {i} with missing data. column_name={column_name}, description={description}"
                            )
                            logger.warning(
                                f"Item keys: {list(item.keys())}, Item: {item}"
                            )
                    else:
                        logger.warning(f"Item {i} is not a dictionary: {type(item)}")
                except Exception as item_error:
                    logger.error(f"Error processing item {i}: {item_error}")
                    logger.error(f"Item content: {item}")

            if column_comments:
                return update_column_comments(table, column_comments)
            else:
                return "No valid column comments found in JSON"

        except Exception as e:
            logger.error(f"Error processing column comments JSON: {e}")
            logger.error(f"JSON type: {type(columns_comment_json)}")
            if columns_comment_json:
                logger.error(
                    f"First item type: {type(columns_comment_json[0]) if columns_comment_json else 'empty'}"
                )
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error processing JSON: {str(e)}"
    else:
        logger.error(
            f"Invalid JSON format. Type: {type(columns_comment_json)}, Content: {columns_comment_json}"
        )
        return "Invalid JSON format"


def create_filtered_column_comments_dataframe(table, selected_names: list):
    """Create filtered column comments dataframe for processing."""
    # Create a DataFrame with column information
    column_comments = pd.DataFrame(
        list(
            table.columns.values(
                "original_column_name",
                "column_name",
                "column_description",
                "generated_comment",
                "value_description",
            )
        )
    )

    # Replace original_comment with generated_comment where original_comment is empty
    column_comments["description"] = column_comments.apply(
        lambda row: row["generated_comment"]
        if pd.isna(row["column_description"]) or row["column_description"] == ""
        else row["column_description"],
        axis=1,
    )
    # Replace original_column_name with name
    column_comments["name"] = column_comments["original_column_name"]
    # Keep only the 'name' and 'comment' columns
    column_comments = column_comments[["name", "description", "value_description"]]

    # Rename columns for clarity
    column_comments = column_comments.rename(
        columns={
            "name": "Column Name",
            "description": "Description",
            "value_description": "Value Description",
        }
    )

    # Remove rows where both Comment and Value Description are empty or null
    column_comments = column_comments[
        (
            column_comments["Description"].notna()
            & (column_comments["Description"] != "")
        )
        | (
            column_comments["Value Description"].notna()
            & (column_comments["Value Description"] != "")
        )
    ]

    # Filter the DataFrame to include only the columns in selected_names
    column_comments = column_comments[
        column_comments["Column Name"].isin(selected_names)
    ]

    return column_comments
