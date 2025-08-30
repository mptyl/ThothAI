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
from tabulate import tabulate

from thoth_core.thoth_ai.thoth_workflow.comment_generation_utils import setup_default_comment_llm_model, setup_sql_db, output_to_json, get_table_schema_safe
from thoth_core.thoth_ai.prompts.table_comment_prompt import get_table_prompt
from thoth_core.models import Setting, LLMChoices # Added LLMChoices
from django.db import transaction # Added transaction


class LLMTimeoutError(Exception):
    """Exception raised when LLM operations timeout"""
    pass


@contextmanager
def llm_timeout(seconds: int):
    """Thread-safe context manager for LLM operation timeouts using concurrent.futures"""
    def run_with_timeout(func, *args, **kwargs):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=seconds)
            except concurrent.futures.TimeoutError:
                raise LLMTimeoutError(f"LLM operation timed out after {seconds} seconds")
    
    class TimeoutWrapper:
        def __init__(self, timeout_func):
            self.timeout_func = timeout_func
            
        def __call__(self, func, *args, **kwargs):
            return self.timeout_func(func, *args, **kwargs)
    
    yield TimeoutWrapper(run_with_timeout)


class CircuitBreaker:
    """Circuit breaker pattern implementation for LLM calls"""
    
    def __init__(self, failure_threshold=3, recovery_timeout=120, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def call(self, func, *args, **kwargs):
        with self._lock:
            if self.state == 'OPEN':
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = 'HALF_OPEN'
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
            self.state = 'CLOSED'
    
    def _on_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'


# Global circuit breaker for LLM calls
llm_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=120)


def create_fresh_llm_client(setting, logger: Optional[logging.Logger] = None):
    """
    Create a fresh LLM client instance for thread-safe operation.
    
    Args:
        setting: Workspace setting containing LLM configuration
        logger: Optional logger for detailed logging
        
    Returns:
        LLM client instance or None if creation fails
    """
    if logger:
        logger.info("Creating fresh LLM client for thread")
    
    # Setup LLM with detailed logging
    llm_client = setup_default_comment_llm_model(setting)
    if llm_client is None:
        if logger:
            logger.error("Failed to create LLM client")
        return None
    
    if logger:
        logger.info(f"LLM client created: {type(llm_client).__name__}")
    
    return llm_client

def generate_table_comments_with_llm(llm_client, setting, prompt_variables: Dict[str, Any]):
    """
    Generate table comments using the LLM client.
    
    Args:
        llm_client: ThothLLMClient instance
        setting: Workspace settings
        prompt_variables: Dictionary containing prompt variables
        
    Returns:
        LLM response
    """
    # Get the prompt template
    from thoth_core.thoth_ai.thoth_workflow.comment_generation_utils import preprocess_template
    prompt_template = get_table_prompt()
    
    # Preprocess template to convert {{variable}} to {variable}
    prompt_template = preprocess_template(prompt_template)
    
    # Format the prompt with variables
    formatted_prompt = prompt_template.format(**prompt_variables)
    
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


def create_table_comments(modeladmin, request, queryset): # Renamed function
    """
    Django admin action to generate comments for selected tables.

    This function processes a queryset of database tables, dividing them into
    chunks for efficient handling. For each table, it invokes the
    `process_table_chunk` function, which is responsible for generating
    descriptive comments using a Language Model (LLM).

    The function handles the following aspects:
    - Checks for an active workspace and its settings.
    - Verifies if any tables have been selected.
    - Splits the processing into chunks if the number of tables is large.
    - Provides feedback to the admin user via messages regarding the
      processing status and any errors encountered.

    Args:
        modeladmin: The ModelAdmin instance invoking the action.
        request: The current HttpRequest object.
        queryset: A Django QuerySet containing the table model instances
                  for which to generate comments.
    """
    try:
        chunk_size = 10
        total_tables = queryset.count()

        if not hasattr(request, 'current_workspace') or not request.current_workspace:
            modeladmin.message_user(request, "No active workspace found. Please select a workspace.", level=messages.ERROR)
            return
        
        setting = request.current_workspace.setting
        if not setting:
            modeladmin.message_user(request, "No settings configured for the current workspace.", level=messages.ERROR)
            return

        if total_tables == 0:
            modeladmin.message_user(request, "No tables selected.", level=messages.WARNING)
            return

        if total_tables > chunk_size:
            modeladmin.message_user(request, f"Processing {total_tables} tables in chunks of {chunk_size}.", level=messages.INFO)
        
        for i in range(0, total_tables, chunk_size):
            chunk = queryset[i:i+chunk_size]
            process_table_chunk(modeladmin, request, chunk, i//chunk_size + 1, setting)

        modeladmin.message_user(request, f"Finished processing all {total_tables} tables.", level=messages.SUCCESS)
    
    except Exception as e:
        modeladmin.message_user(request, f"Failed to create table comments: {str(e)}", level=messages.ERROR)
        return

@transaction.atomic
def process_table_chunk(modeladmin, request, chunk, chunk_number, setting):

    for table in chunk:
        modeladmin.message_user(request, f"Processing table: {table.name}", level=messages.INFO)

        # setup llm model
        llm = setup_default_comment_llm_model(setting)
        if llm is None:
            modeladmin.message_user(request, f"Default LLM model not found for table {table.name} in workspace {request.current_workspace.name}. Skipping this table.", level=messages.ERROR)
            continue

        # setup language
        table_db = table.sql_db
        language = table_db.language if table_db.language else setting.language

        #define number of example rows for comment
        example_rows_for_comment=setting.example_rows_for_comment

        # setup database schema
        try:
            db = setup_sql_db(table_db)
        except Exception as e:
            modeladmin.message_user(request, f"Error setting up SQL database for table {table.name}: {str(e)}. Skipping this table.", level=messages.ERROR)
            continue # Skip to the next table in the chunk

        # Get the table schema/structure using the safe wrapper
        table_schema = get_table_schema_safe(db, table.name)

        # Get the table comments
        table_current_comment_val = table.description if table.description and table.description.strip() else table.generated_comment
        table_current_comment_str = table_current_comment_val if table_current_comment_val and table_current_comment_val.strip() else ""

        # Get column comments
        column_comments_df = create_column_comments_dataframe(table) # Returns a DataFrame
        if not column_comments_df.empty:
            # Convert DataFrame to markdown string for the prompt
            column_comments_str = column_comments_df.to_markdown(index=False)
        else:
            column_comments_str = ""
        
        try:
            examples_data_result = db.get_example_data(table.name, example_rows_for_comment) # type: Dict[str, List[Any]]
            
            # Check if dict has keys and any list has content
            if examples_data_result and any(lst for lst in examples_data_result.values() if lst): 
                example_data_str = tabulate(examples_data_result, headers="keys", tablefmt='pipe', showindex=False)
            else: # Handles None, empty dict, or dict with all empty lists
                example_data_str = "" # Default to empty string for LLM
                if examples_data_result is None:
                    modeladmin.message_user(request, f"Info for table {table.name}: No example data returned (None). LLM will receive empty string.", level=messages.INFO)
                else:
                    modeladmin.message_user(request, f"Info for table {table.name}: No example data found (empty). LLM will receive empty string.", level=messages.INFO)
        except Exception as e:
            example_data_str = "" # Default to empty string for LLM on error
            modeladmin.message_user(request, f"Warning for table {table.name}: Could not retrieve example data: {str(e)}. LLM will receive empty string.", level=messages.WARNING)


        # Prepare prompt variables
        prompt_variables = {
            "database_schema": table_schema,
            "table_comment": table_current_comment_str,
            "column_comments": column_comments_str,
            "example_data": example_data_str,
            "table": table.name,  # Pass table name as string, not the model instance
            "language": language,
        }
        
        try:
            # Generate table comments using the LLM
            output = generate_table_comments_with_llm(llm, setting, prompt_variables)
            table_comment_json = output_to_json(output)
            if table_comment_json is None:
                raw_output_preview = str(output)[:200] # Show a preview of raw output
                modeladmin.message_user(request, f"Error for table {table.name}: No JSON-like content found in the LLM response. Raw output preview: {raw_output_preview}...", level=messages.ERROR)
                continue # Skip to the next table
            else:
                # Save the table comment in JSON format
                return_code=update_table_comments_on_backend(table_comment_json, table)
                if return_code=="OK":
                    modeladmin.message_user(request, f"Comment created successfully for table {table.name}.")
                else:
                    modeladmin.message_user(request, f"Error updating comment for table {table.name}: {return_code}",level=messages.ERROR)
        except Exception as e:
            modeladmin.message_user(request, f"Error during pipeline execution or comment update for table {table.name}: {str(e)}", level=messages.ERROR)
            continue # Skip to the next table

def update_table_comments_on_backend(table_comment_json, table):
    """
    Update the generated comment for a given table in the backend.

    This function takes a JSON-like structure containing table comments and updates
    the 'generated_comment' field of the provided table object. It checks for the
    validity of the input and updates the table only if a valid comment is found.

    Parameters:
    table_comment_json (list): A list containing a dictionary with table comments.
                               Expected to have at least one item with a 'description' key.
    table (object): The table object to be updated. Must have 'generated_comment'
                    attribute and a 'save' method.

    Returns:
    str: A status message indicating the result of the operation.
         "OK" if the comment was successfully updated.
         "No valid comment found in the generated output" if no valid comment was found.
         "No valid output found in the generated output" if the input is invalid.
    """
    if table_comment_json and isinstance(table_comment_json, list) and len(table_comment_json) > 0:
        comment = table_comment_json[0].get('description')
        if comment:
            table.generated_comment = comment
            table.save()
            return "OK"
        else:
            return "No valid comment found in the generated output"
    else:
        return "No valid output found in the generated output"

def create_column_comments_dataframe(table):
    # Create a DataFrame with column information
    column_comments = pd.DataFrame(list(table.columns.values('original_column_name', 'column_description', 'generated_comment', 'value_description')))

    # Replace original_comment with generated_comment where original_comment is empty
    column_comments['comment'] = column_comments.apply(
        lambda row: row['generated_comment'] if pd.isna(row['column_description']) or row['column_description'] == '' else row['column_description'],
        axis=1
    )

    # Keep only the 'name' and 'comment' columns
    column_comments = column_comments[['original_column_name', 'column_description','value_description']]

    # Rename columns for clarity
    column_comments = column_comments.rename(columns={"original_column_name": "Column Name", "column_description": "Comment", "value_description": "Value Description"})

    # Remove rows where both Comment and Value Description are empty or null
    column_comments = column_comments[
        (column_comments['Comment'].notna() & (column_comments['Comment'] != '')) |
        (column_comments['Value Description'].notna() & (column_comments['Value Description'] != ''))
    ]
    
    return column_comments

def create_table_comments_async(table_ids: List[int], workspace_id: int = None, custom_logger: logging.Logger = None) -> Dict[str, Any]:
    """
    Async-compatible function to generate comments for specified tables.
    
    This function is designed to be called from async contexts without requiring
    Django admin parameters. It processes a list of table IDs and generates
    comments for each table with detailed logging.
    
    Args:
        table_ids: List of SqlTable IDs to process
        workspace_id: ID of the workspace to use for settings (optional, will be derived if not provided)
        
    Returns:
        Dict with processing results including success/failure counts and detailed logs
    """
    from thoth_core.models import SqlTable, Workspace
    from django.db import transaction
    import logging
    
    # Use custom logger if provided, otherwise use default logger
    logger = custom_logger if custom_logger else logging.getLogger(__name__)
    
    results = {
        'processed': 0,
        'failed': 0,
        'errors': [],
        'details': []
    }
    
    try:
        if custom_logger:
            logger.info(f"Starting table comment generation for {len(table_ids)} tables")
        else:
            logger.info(f"Starting async table comments generation for {len(table_ids)} tables")
        
        # Get the tables to process
        tables = SqlTable.objects.filter(id__in=table_ids).select_related('sql_db')
        total_tables = tables.count()
        
        if total_tables == 0:
            logger.error("No tables found with the provided IDs")
            results['errors'].append("No tables found with the provided IDs")
            return results
        
        logger.info(f"Found {total_tables} tables to process")
        
        # Get workspace and settings
        if workspace_id:
            try:
                workspace = Workspace.objects.get(id=workspace_id)
                logger.info(f"Using provided workspace: {workspace.name} (ID: {workspace_id})")
            except Workspace.DoesNotExist:
                logger.error(f"Workspace with ID {workspace_id} not found")
                results['errors'].append(f"Workspace with ID {workspace_id} not found")
                return results
        else:
            # Fallback: try to find workspace by database
            first_table = tables.first()
            if not first_table or not first_table.sql_db:
                logger.error("Cannot determine workspace settings")
                results['errors'].append("Cannot determine workspace settings")
                return results
                
            workspace = Workspace.objects.filter(sql_db=first_table.sql_db).first()
            if not workspace:
                logger.error(f"No workspace found for database {first_table.sql_db.name}")
                results['errors'].append(f"No workspace found for database {first_table.sql_db.name}")
                return results
            logger.info(f"Found workspace by database: {workspace.name}")
            
        setting = workspace.setting
        
        if not setting:
            logger.error("No settings configured for workspace")
            results['errors'].append("No settings configured for workspace")
            return results
        
        logger.info(f"Processing tables with workspace: {workspace.name}")
        
        # Process each table with thread-safe pipeline and circuit breaker
        table_count = 0
        pipeline = None  # Create pipeline once per thread
        
        for table in tables:
            table_count += 1
            try:
                with transaction.atomic():
                    if custom_logger:
                        logger.info(f"Processing table {table_count}/{total_tables}: {table.name}")
                    else:
                        logger.info(f"Starting processing table: {table.name} (ID: {table.id})")
                    
                    # Create fresh LLM client if not exists or if previous attempt failed
                    if pipeline is None:
                        pipeline = create_fresh_llm_client(setting, logger)
                        if pipeline is None:
                            error_msg = f"Failed to create LLM client for workspace {workspace.name}"
                            logger.error(error_msg)
                            results['errors'].append(error_msg)
                            results['failed'] += 1
                            results['details'].append({
                                'table': table.name,
                                'status': 'failed',
                                'message': 'Pipeline creation failed'
                            })
                            continue
                    
                    # Setup database
                    try:
                        db = setup_sql_db(table.sql_db)
                        if custom_logger:
                            logger.info(f"Setting up database connection for {table.name}")
                        else:
                            logger.info(f"Successfully set up database for table {table.name}")
                    except Exception as e:
                        error_msg = f"Database setup error for {table.name}: {str(e)}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                        results['failed'] += 1
                        results['details'].append({
                            'table': table.name,
                            'status': 'failed',
                            'message': 'Database setup error'
                        })
                        continue
                    
                    # Get table schema/structure and data (without logging sensitive details)
                    table_schema = get_table_schema_safe(db, table.name)
                    if custom_logger:
                        logger.info(f"Retrieved table structure for {table.name}")
                    else:
                        logger.info(f"Retrieved schema for table {table.name}")
                    
                    # Get current comment
                    table_current_comment_str = table.description if table.description and table.description.strip() else ""
                    
                    # Get column comments
                    column_comments_df = create_column_comments_dataframe(table)
                    column_comments_str = column_comments_df.to_markdown(index=False) if not column_comments_df.empty else ""
                    
                    # Get example data
                    try:
                        examples_data_result = db.get_example_data(table.name, setting.example_rows_for_comment)
                        if examples_data_result and any(lst for lst in examples_data_result.values() if lst):
                            example_data_str = tabulate(examples_data_result, headers="keys", tablefmt='pipe', showindex=False)
                        else:
                            example_data_str = ""
                    except Exception as e:
                        if custom_logger:
                            logger.warning(f"Could not retrieve example data for {table.name}")
                        else:
                            logger.warning(f"Could not retrieve example data for {table.name}: {str(e)}")
                        example_data_str = ""
                    
                    # Generate comment with timeout and circuit breaker
                    language = table.sql_db.language if table.sql_db.language else setting.language
                    
                    def run_llm_generation():
                        with llm_timeout(30) as timeout_wrapper:  # 30 seconds timeout - if LLM doesn't respond, something is wrong
                            prompt_variables = {
                                "database_schema": table_schema,
                                "table_comment": table_current_comment_str,
                                "column_comments": column_comments_str,
                                "example_data": example_data_str,
                                "table": table.name,  # Pass table name as string, not the model instance
                                "language": language,
                            }
                            return timeout_wrapper(
                                generate_table_comments_with_llm,
                                pipeline, setting, prompt_variables
                            )
                    
                    try:
                        if custom_logger:
                            logger.info(f"Calling LLM for table: {table.name}")
                        else:
                            logger.info(f"Generating comment for table {table.name}")
                        
                        # Use circuit breaker for LLM call
                        output = llm_circuit_breaker.call(run_llm_generation)
                        
                        if custom_logger:
                            logger.info(f"LLM response received for table: {table.name}")
                        
                        table_comment_json = output_to_json(output)
                        if table_comment_json:
                            return_code = update_table_comments_on_backend(table_comment_json, table)
                            if return_code == "OK":
                                if custom_logger:
                                    logger.info(f"✓ Successfully processed table: {table.name}")
                                else:
                                    logger.info(f"Successfully processed table {table.name}")
                                results['processed'] += 1
                                results['details'].append({
                                    'table': table.name,
                                    'status': 'success',
                                    'message': 'Comment generated successfully'
                                })
                            else:
                                error_msg = f"Failed to update comment for {table.name}: {return_code}"
                                logger.error(error_msg)
                                results['errors'].append(error_msg)
                                results['failed'] += 1
                                results['details'].append({
                                    'table': table.name,
                                    'status': 'failed',
                                    'message': 'Failed to save comment'
                                })
                        else:
                            error_msg = f"Failed to generate comment for {table.name}"
                            logger.error(error_msg)
                            results['errors'].append(error_msg)
                            results['failed'] += 1
                            results['details'].append({
                                'table': table.name,
                                'status': 'failed',
                                'message': 'AI comment generation failed'
                            })
                            
                    except LLMTimeoutError as e:
                        error_msg = f"Timeout processing {table.name}: {str(e)}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                        results['failed'] += 1
                        results['details'].append({
                            'table': table.name,
                            'status': 'failed',
                            'message': 'Pipeline timeout'
                        })
                        # Recreate pipeline for next attempt
                        pipeline = None
                        continue
                        
                    except Exception as e:
                        if "Circuit breaker is OPEN" in str(e):
                            error_msg = f"Circuit breaker activated - stopping processing due to repeated failures"
                            logger.error(error_msg)
                            results['errors'].append(error_msg)
                            # Stop processing all remaining tables
                            remaining_tables = total_tables - table_count
                            results['failed'] += remaining_tables
                            for remaining_table in tables[table_count:]:
                                results['details'].append({
                                    'table': remaining_table.name,
                                    'status': 'failed',
                                    'message': 'Circuit breaker activated'
                                })
                            break
                        else:
                            error_msg = f"Error processing {table.name}: {str(e)}"
                            logger.error(error_msg)
                            results['errors'].append(error_msg)
                            results['failed'] += 1
                            results['details'].append({
                                'table': table.name,
                                'status': 'failed',
                                'message': 'Processing error'
                            })
                            # Recreate pipeline for next attempt
                            pipeline = None
                            continue
                        
            except Exception as e:
                error_msg = f"Error processing {table.name}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                results['failed'] += 1
                results['details'].append({
                    'table': table.name,
                    'status': 'failed',
                    'message': 'Processing error'
                })
        
        logger.info(f"Completed processing all tables. Processed: {results['processed']}, Failed: {results['failed']}")
        return results
        
    except Exception as e:
        logger.error(f"Critical error in async table comments: {str(e)}")
        results['errors'].append(f"Critical error: {str(e)}")
        return results
