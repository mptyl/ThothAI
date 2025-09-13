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
import time
import threading
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import concurrent.futures

import pandas as pd
from django.contrib import messages
from django.db import transaction
from tabulate import tabulate

from thoth_core.thoth_ai.thoth_workflow.comment_generation_utils import (
    setup_llm_from_env,
    setup_sql_db,
    output_to_json,
    get_table_schema_safe,
)
from thoth_core.models import LLMChoices
from thoth_core.thoth_ai.prompts.columns_comment_prompt import get_columns_prompt

# Configure logging
logger = logging.getLogger(__name__)


class PipelineTimeoutError(Exception):
    """Exception raised when pipeline operations timeout"""

    pass


@contextmanager
def pipeline_timeout(seconds: int):
    """Thread-safe context manager for pipeline operation timeouts using concurrent.futures"""

    def run_with_timeout(func, *args, **kwargs):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=seconds)
            except concurrent.futures.TimeoutError:
                raise PipelineTimeoutError(
                    f"Pipeline operation timed out after {seconds} seconds"
                )

    class TimeoutWrapper:
        def __init__(self, timeout_func):
            self.timeout_func = timeout_func

        def __call__(self, func, *args, **kwargs):
            return self.timeout_func(func, *args, **kwargs)

    yield TimeoutWrapper(run_with_timeout)


class CircuitBreaker:
    """Circuit breaker pattern implementation for LLM calls"""

    def __init__(
        self, failure_threshold=3, recovery_timeout=120, expected_exception=Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        with self._lock:
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN - too many failures")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"

    def _on_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"


# Global circuit breaker for LLM calls
llm_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=120)


def create_fresh_llm_client(logger: Optional[logging.Logger] = None):
    """
    Create a fresh LLM client instance for thread-safe operation.

    Args:
        logger: Optional logger for detailed logging

    Returns:
        ThothLLMClient instance or None if creation fails
    """
    if logger:
        logger.info("Creating fresh LLM client for thread")

    # Setup LLM with detailed logging
    llm_client = setup_llm_from_env()
    if llm_client is None:
        if logger:
            logger.error("Failed to create LLM client")
        return None

    if logger:
        logger.info(f"LLM client created: {type(llm_client).__name__}")

    return llm_client


def generate_column_comments_with_llm(llm_client, variables: Dict[str, Any]):
    """
    Generate column comments using the LLM client.

    Args:
        llm_client: ThothLLMClient instance
        setting: Workspace settings
        variables: Dictionary containing prompt variables

    Returns:
        LLM response content
    """
    from thoth_core.thoth_ai.thoth_workflow.comment_generation_utils import (
        preprocess_template,
    )

    # Get the prompt template
    prompt_template = get_columns_prompt()

    # Preprocess template to convert {{variable}} to {variable}
    prompt_template = preprocess_template(prompt_template)

    # Format the prompt with variables
    formatted_prompt = prompt_template.format(**variables)

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


def create_selected_column_comments(modeladmin, request, queryset):
    try:
        chunk_size = 10
        total_columns = queryset.count()

        table = queryset[0].sql_table
        # Get language from table's database, fallback to English
        language = table.sql_db.language or "en"
        # setup database schema
        table_db = table.sql_db
        try:
            db = setup_sql_db(table_db)
        except Exception as e:
            modeladmin.message_user(
                request,
                f"Error setting up SQL database: {str(e)}",
                level=messages.ERROR,
            )
            return

        # Get the table schema using the safe wrapper
        table_schema = get_table_schema_safe(db, table.name)
        all_example_data = db.get_example_data(table.name, 5)

        if total_columns > chunk_size:
            modeladmin.message_user(
                request,
                f"Processing {total_columns} columns in chunks of {chunk_size}.",
                level=messages.INFO,
            )

        for i in range(0, total_columns, chunk_size):
            chunk = queryset[i : i + chunk_size]
            process_column_chunk(
                modeladmin,
                request,
                chunk,
                i // chunk_size + 1,
                table,
                language,
                table_schema,
                all_example_data,
            )

        modeladmin.message_user(
            request,
            f"Finished processing all {total_columns} columns.",
            level=messages.SUCCESS,
        )

    except Exception as e:
        modeladmin.message_user(
            request, f"Failed to create column comments: {str(e)}", level=messages.ERROR
        )
        return


@transaction.atomic
def process_column_chunk(
    modeladmin,
    request,
    chunk,
    chunk_number,
    table,
    language,
    table_schema,
    all_example_data,
):
    try:
        # setup llm model
        llm = setup_llm_from_env()
        if llm is None:
            modeladmin.message_user(
                request, "Default LLM model not found.", level=messages.ERROR
            )
            return

        # identify table to comment
        selected_columns = list(chunk)
        if not selected_columns:
            modeladmin.message_user(
                request, "No columns selected.", level=messages.ERROR
            )
            return
        selected_column_names = [col.original_column_name for col in selected_columns]
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
        available_columns_in_data = set(
            all_example_data.keys()
        )  # Changed from .columns to .keys()
        selected_columns_present_in_data = [
            col for col in selected_column_names if col in available_columns_in_data
        ]

        # Create example data table with available columns and truncation for large content
        if selected_columns_present_in_data:
            # Construct a new dictionary for filtered_example_data with truncation
            filtered_example_data = {}
            truncated_columns = []

            for col in selected_columns_present_in_data:
                col_data = all_example_data[col]
                # Truncate large text content to prevent LLM timeouts
                truncated_data = []
                has_truncation = False

                for item in col_data:
                    if (
                        item is not None
                        and isinstance(item, str)
                        and len(str(item)) > 500
                    ):
                        # For XML and other large text, truncate and add indicator
                        truncated_item = (
                            str(item)[:500] + "... [TRUNCATED - Large content detected]"
                        )
                        truncated_data.append(truncated_item)
                        has_truncation = True
                    else:
                        truncated_data.append(item)

                filtered_example_data[col] = truncated_data
                if has_truncation:
                    truncated_columns.append(col)

            # Log truncation information
            if truncated_columns:
                modeladmin.message_user(
                    request,
                    f"Truncated large content in columns: {', '.join(truncated_columns)}",
                    level=messages.INFO,
                )

            example_data = tabulate(
                filtered_example_data, headers="keys", tablefmt="pipe", showindex=False
            )
        else:
            example_data = "No example data available for the selected columns."
            modeladmin.message_user(
                request,
                "None of the selected columns are present in the example data. Will generate comments based on column names only.",
                level=messages.WARNING,
            )

        # Prepare variables for the prompt
        prompt_variables = {
            "table_schema": table_schema,
            "table_comment": table_comment,
            "column_list": tabulated_selected_columns,
            "column_comments": selected_column_comments,
            "example_data": example_data,
            "table": table.name,  # Pass table name as string, not the model instance
            "language": language,
            "max_examples": 10,  # Maximum number of enum values to show in description
        }

        # Generate column comments using the LLM
        output = generate_column_comments_with_llm(llm, prompt_variables)
        try:
            table_comment_json = output_to_json(output)
            if table_comment_json is None:
                modeladmin.message_user(
                    request,
                    f"Error: No JSON-like content found in the response. Here's the raw content:{output}",
                    level=messages.ERROR,
                )
                return
            else:
                # Save the table comment in JSON format
                return_code = update_column_comments_on_backend(
                    table_comment_json, table
                )
                if return_code == "OK":
                    modeladmin.message_user(request, "Comment created successfully.")
                else:
                    modeladmin.message_user(request, return_code, level=messages.ERROR)
                return
        except json.JSONDecodeError:
            modeladmin.message_user(
                request,
                "Error: The generated content is not a valid JSON. Retry the process",
                level=messages.ERROR,
            )
            return

    except Exception as e:
        modeladmin.message_user(
            request, f"Error processing column chunk: {str(e)}", level=messages.ERROR
        )
        return


def update_column_comments(table, column_comments):
    """
    Update the generated_comment field for columns in the given table.

    Args:
    table (SqlTable): The table object containing the columns to update.
    column_comments (list): A list of dictionaries, each containing 'name' and 'generated_comment' keys.

    Returns:
    bool: True if all updates were successful, False otherwise.
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
    if columns_comment_json and isinstance(columns_comment_json, list):
        try:
            column_comments = []
            for item in columns_comment_json:
                if isinstance(item, dict):
                    # Handle both possible key names
                    column_name = item.get("column_name", item.get("name", ""))
                    description = item.get("description", item.get("comment", ""))

                    if column_name and description:
                        column_comments.append(
                            {"name": column_name, "generated_comment": description}
                        )
                    else:
                        import logging

                        logger = logging.getLogger(__name__)
                        logger.warning(f"Skipping item with missing data: {item}")

            if column_comments:
                return update_column_comments(table, column_comments)
            else:
                return "No valid column comments found in JSON"

        except (KeyError, TypeError) as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error processing column comments JSON: {e}")
            return f"Error processing JSON: {str(e)}"
    return "Invalid JSON format"


def create_filtered_column_comments_dataframe(table, selected_names: list):
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


def create_selected_column_comments_async(
    column_ids: List[int],
    workspace_id: int = None,
    custom_logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Async-compatible function to generate comments for specified columns.

    This function is designed to be called from async contexts without requiring
    Django admin parameters. It processes a list of column IDs and generates
    comments for each column with detailed logging.

    Args:
        column_ids: List of SqlColumn IDs to process
        workspace_id: ID of the workspace to use for settings (optional, will be derived if not provided)
        custom_logger: Optional custom logger for detailed logging

    Returns:
        Dict with processing results including success/failure counts and detailed logs
    """
    from thoth_core.models import SqlColumn
    from django.db import transaction
    import logging

    # Use custom logger if provided, otherwise use default logger
    logger = custom_logger if custom_logger else logging.getLogger(__name__)

    results = {"processed": 0, "failed": 0, "errors": [], "details": []}

    try:
        if custom_logger:
            logger.info(
                f"Starting column comment generation for {len(column_ids)} columns"
            )
        else:
            logger.info(
                f"Starting async column comments generation for {len(column_ids)} columns"
            )

        # Get the columns to process
        columns = SqlColumn.objects.filter(id__in=column_ids).select_related(
            "sql_table", "sql_table__sql_db"
        )
        total_columns = columns.count()

        if total_columns == 0:
            logger.error("No columns found with the provided IDs")
            results["errors"].append("No columns found with the provided IDs")
            return results

        logger.info(f"Found {total_columns} columns to process")

        # Workspace/settings no longer required; proceed with env-based configuration

        # Group columns by table for efficient processing
        columns_by_table = {}
        for column in columns:
            table_id = column.sql_table.id
            if table_id not in columns_by_table:
                columns_by_table[table_id] = {"table": column.sql_table, "columns": []}
            columns_by_table[table_id]["columns"].append(column)

        logger.info(f"Processing columns from {len(columns_by_table)} tables")

        # Process each table's columns with thread-safe pipeline and circuit breaker
        pipeline = None  # Create pipeline once per thread

        for table_id, table_data in columns_by_table.items():
            table = table_data["table"]
            table_columns = table_data["columns"]

            try:
                with transaction.atomic():
                    if custom_logger:
                        logger.info(
                            f"Processing {len(table_columns)} columns from table: {table.name}"
                        )
                    else:
                        logger.info(
                            f"Starting processing columns from table: {table.name} (ID: {table.id})"
                        )

                    # Create fresh LLM client if not exists or if previous attempt failed
                    if pipeline is None:
                        pipeline = create_fresh_llm_client(logger)
                        if pipeline is None:
                            error_msg = "Failed to create LLM client from environment"
                            logger.error(error_msg)
                            results["errors"].append(error_msg)
                            # Mark all columns in this table as failed
                            for column in table_columns:
                                results["failed"] += 1
                                results["details"].append(
                                    {
                                        "column": f"{table.name}.{column.original_column_name}",
                                        "status": "failed",
                                        "message": "Pipeline creation failed",
                                    }
                                )
                            continue

                    # Setup database
                    try:
                        db = setup_sql_db(table.sql_db)
                        if custom_logger:
                            logger.info(
                                f"Setting up database connection for table {table.name}"
                            )
                        else:
                            logger.info(
                                f"Successfully set up database for table {table.name}"
                            )
                    except Exception as e:
                        error_msg = (
                            f"Database setup error for table {table.name}: {str(e)}"
                        )
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                        # Mark all columns in this table as failed
                        for column in table_columns:
                            results["failed"] += 1
                            results["details"].append(
                                {
                                    "column": f"{table.name}.{column.original_column_name}",
                                    "status": "failed",
                                    "message": "Database setup error",
                                }
                            )
                        continue

                    # Get table schema and data using the safe wrapper
                    table_schema = get_table_schema_safe(db, table.name)
                    if custom_logger:
                        logger.info(f"Retrieved table structure for {table.name}")
                    else:
                        logger.info(f"Retrieved schema for table {table.name}")

                    # Get table comment
                    table_comment = (
                        table.description
                        if table.description and table.description.strip()
                        else table.generated_comment
                    )

                    # Get example data
                    try:
                        all_example_data = db.get_example_data(
                            table.name, 5
                        )
                        if all_example_data and any(
                            lst for lst in all_example_data.values() if lst
                        ):
                            available_columns_in_data = set(all_example_data.keys())
                        else:
                            all_example_data = {}
                            available_columns_in_data = set()
                    except Exception as e:
                        if custom_logger:
                            logger.warning(
                                f"Could not retrieve example data for table {table.name}"
                            )
                        else:
                            logger.warning(
                                f"Could not retrieve example data for table {table.name}: {str(e)}"
                            )
                        all_example_data = {}
                        available_columns_in_data = set()

                    # Process columns in chunks to prevent memory issues
                    chunk_size = 10
                    column_chunks = [
                        table_columns[i : i + chunk_size]
                        for i in range(0, len(table_columns), chunk_size)
                    ]

                    for chunk_idx, column_chunk in enumerate(column_chunks):
                        try:
                            if custom_logger:
                                logger.info(
                                    f"Processing chunk {chunk_idx + 1}/{len(column_chunks)} for table {table.name}"
                                )

                            # Prepare data for this chunk
                            selected_column_names = [
                                col.original_column_name for col in column_chunk
                            ]
                            tabulated_selected_columns = tabulate(
                                [selected_column_names],
                                headers=["Selected Columns"],
                                tablefmt="pipe",
                            )

                            # Get column comments for context
                            selected_column_comments = (
                                create_filtered_column_comments_dataframe(
                                    table, selected_column_names
                                )
                            )

                            # Prepare example data for available columns with truncation for large content
                            selected_columns_present_in_data = [
                                col
                                for col in selected_column_names
                                if col in available_columns_in_data
                            ]

                            if selected_columns_present_in_data:
                                filtered_example_data = {}
                                truncated_columns = []

                                for col in selected_columns_present_in_data:
                                    col_data = all_example_data[col]
                                    # Truncate large text content to prevent LLM timeouts
                                    truncated_data = []
                                    has_truncation = False

                                    for item in col_data:
                                        if (
                                            item is not None
                                            and isinstance(item, str)
                                            and len(str(item)) > 500
                                        ):
                                            # For XML and other large text, truncate and add indicator
                                            truncated_item = (
                                                str(item)[:500]
                                                + "... [TRUNCATED - Large content detected]"
                                            )
                                            truncated_data.append(truncated_item)
                                            has_truncation = True
                                        else:
                                            truncated_data.append(item)

                                    filtered_example_data[col] = truncated_data
                                    if has_truncation:
                                        truncated_columns.append(col)

                                # Log truncation information
                                if truncated_columns and custom_logger:
                                    logger.info(
                                        f"Truncated large content in columns: {', '.join(truncated_columns)}"
                                    )

                                example_data = tabulate(
                                    filtered_example_data,
                                    headers="keys",
                                    tablefmt="pipe",
                                    showindex=False,
                                )
                            else:
                                example_data = "No example data available for the selected columns."

                            # Generate comments with timeout and circuit breaker
                            language = table.sql_db.language or "en"

                            def run_llm_generation():
                                with pipeline_timeout(
                                    90
                                ) as timeout_wrapper:  # 90 seconds timeout
                                    prompt_variables = {
                                        "table_schema": table_schema,
                                        "table_comment": table_comment,
                                        "column_list": tabulated_selected_columns,
                                        "column_comments": selected_column_comments,
                                        "example_data": example_data,
                                        "table": table.name,  # Pass table name as string, not the model instance
                                        "language": language,
                                        "max_examples": 10,  # Maximum number of enum values to show in description
                                    }
                                    return timeout_wrapper(
                                        generate_column_comments_with_llm,
                                        pipeline,
                                        prompt_variables,
                                    )

                            try:
                                if custom_logger:
                                    logger.info(
                                        f"Calling LLM for {len(column_chunk)} columns in table: {table.name}"
                                    )
                                else:
                                    logger.info(
                                        f"Generating comments for {len(column_chunk)} columns in table {table.name}"
                                    )

                                # Use circuit breaker for LLM call
                                output = llm_circuit_breaker.call(run_llm_generation)

                                if custom_logger:
                                    logger.info(
                                        f"LLM response received for columns in table: {table.name}"
                                    )

                                columns_comment_json = output_to_json(output)
                                if columns_comment_json:
                                    return_code = update_column_comments_on_backend(
                                        columns_comment_json, table
                                    )
                                    if return_code == "OK":
                                        # Mark all columns in this chunk as successful
                                        for column in column_chunk:
                                            if custom_logger:
                                                logger.info(
                                                    f"✓ Successfully processed column: {table.name}.{column.original_column_name}"
                                                )
                                            else:
                                                logger.info(
                                                    f"Successfully processed column {table.name}.{column.original_column_name}"
                                                )
                                            results["processed"] += 1
                                            results["details"].append(
                                                {
                                                    "column": f"{table.name}.{column.original_column_name}",
                                                    "status": "success",
                                                    "message": "Comment generated successfully",
                                                }
                                            )
                                    else:
                                        error_msg = f"Failed to update comments for columns in {table.name}: {return_code}"
                                        logger.error(error_msg)
                                        results["errors"].append(error_msg)
                                        # Mark all columns in this chunk as failed
                                        for column in column_chunk:
                                            results["failed"] += 1
                                            results["details"].append(
                                                {
                                                    "column": f"{table.name}.{column.original_column_name}",
                                                    "status": "failed",
                                                    "message": "Failed to save comments",
                                                }
                                            )
                                else:
                                    error_msg = f"Failed to generate comments for columns in {table.name}"
                                    logger.error(error_msg)
                                    results["errors"].append(error_msg)
                                    # Mark all columns in this chunk as failed
                                    for column in column_chunk:
                                        results["failed"] += 1
                                        results["details"].append(
                                            {
                                                "column": f"{table.name}.{column.original_column_name}",
                                                "status": "failed",
                                                "message": "AI comment generation failed",
                                            }
                                        )

                            except PipelineTimeoutError as e:
                                error_msg = f"Timeout processing columns in {table.name}: {str(e)}"
                                logger.error(error_msg)
                                results["errors"].append(error_msg)
                                # Mark all columns in this chunk as failed
                                for column in column_chunk:
                                    results["failed"] += 1
                                    results["details"].append(
                                        {
                                            "column": f"{table.name}.{column.original_column_name}",
                                            "status": "failed",
                                            "message": "Pipeline timeout",
                                        }
                                    )
                                # Recreate pipeline for next attempt
                                pipeline = None
                                continue

                            except Exception as e:
                                if "Circuit breaker is OPEN" in str(e):
                                    error_msg = "Circuit breaker activated - stopping processing due to repeated failures"
                                    logger.error(error_msg)
                                    results["errors"].append(error_msg)
                                    # Stop processing all remaining columns
                                    remaining_columns = []
                                    for (
                                        remaining_table_id,
                                        remaining_table_data,
                                    ) in list(columns_by_table.items())[
                                        list(columns_by_table.keys()).index(table_id) :
                                    ]:
                                        if remaining_table_id == table_id:
                                            # Add remaining chunks from current table
                                            for remaining_chunk in column_chunks[
                                                chunk_idx:
                                            ]:
                                                remaining_columns.extend(
                                                    remaining_chunk
                                                )
                                        else:
                                            # Add all columns from remaining tables
                                            remaining_columns.extend(
                                                remaining_table_data["columns"]
                                            )

                                    for remaining_column in remaining_columns:
                                        results["failed"] += 1
                                        results["details"].append(
                                            {
                                                "column": f"{remaining_column.sql_table.name}.{remaining_column.original_column_name}",
                                                "status": "failed",
                                                "message": "Circuit breaker activated",
                                            }
                                        )
                                    return results
                                else:
                                    error_msg = f"Error processing columns in {table.name}: {str(e)}"
                                    logger.error(error_msg)
                                    results["errors"].append(error_msg)
                                    # Mark all columns in this chunk as failed
                                    for column in column_chunk:
                                        results["failed"] += 1
                                        results["details"].append(
                                            {
                                                "column": f"{table.name}.{column.original_column_name}",
                                                "status": "failed",
                                                "message": "Processing error",
                                            }
                                        )
                                    # Recreate pipeline for next attempt
                                    pipeline = None
                                    continue

                        except Exception as e:
                            error_msg = f"Error processing column chunk in {table.name}: {str(e)}"
                            logger.error(error_msg)
                            results["errors"].append(error_msg)
                            # Mark all columns in this chunk as failed
                            for column in column_chunk:
                                results["failed"] += 1
                                results["details"].append(
                                    {
                                        "column": f"{table.name}.{column.original_column_name}",
                                        "status": "failed",
                                        "message": "Processing error",
                                    }
                                )

            except Exception as e:
                error_msg = f"Error processing table {table.name}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                # Mark all columns in this table as failed
                for column in table_columns:
                    results["failed"] += 1
                    results["details"].append(
                        {
                            "column": f"{table.name}.{column.original_column_name}",
                            "status": "failed",
                            "message": "Table processing error",
                        }
                    )

        logger.info(
            f"Completed processing all columns. Processed: {results['processed']}, Failed: {results['failed']}"
        )
        return results

    except Exception as e:
        logger.error(f"Critical error in async column comments: {str(e)}")
        results["errors"].append(f"Critical error: {str(e)}")
        return results
