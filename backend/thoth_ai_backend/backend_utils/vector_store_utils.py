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

from django.core.exceptions import ValidationError

# Import new vector store plugin architecture
from thoth_qdrant import VectorStoreFactory
from thoth_qdrant import (
    EvidenceDocument, ColumnNameDocument, SqlDocument, ThothType
)

from thoth_core.models import VectorDbChoices
from .session_utils import get_current_workspace

import csv
import io
import os
import logging

logger = logging.getLogger(__name__)

def get_csv_export_path(request):
    """
    Determine the CSV export/import path based on IO_DIR environment variable
    and the vector database type and name.
    
    Args:
        request: The HTTP request object containing the session
        
    Returns:
        str: The path for CSV files in format {IO_DIR}/{vect_type}/{name}/
        
    Raises:
        ValueError: If workspace or vector database configuration is invalid
    """
    # Get IO_DIR from environment variable with fallback to 'exports'
    io_dir = os.environ.get('IO_DIR', 'exports')
    
    try:
        # Get current workspace
        workspace = get_current_workspace(request)
        
        if not workspace.sql_db:
            raise ValueError("No SQL database associated with the current workspace")
        
        if not workspace.sql_db.vector_db:
            raise ValueError("No vector database associated with the SQL database")
        
        vector_db = workspace.sql_db.vector_db
        
        # Build hierarchical directory structure: vect_type/name
        vect_type = vector_db.vect_type if vector_db.vect_type else "Unknown"
        vdb_name = vector_db.name if vector_db.name else "default"
        
        # Sanitize the vector type for directory creation
        sanitized_vect_type = "".join(c if c.isalnum() or c in ['_', '-'] else "_" for c in vect_type).strip('_')
        if not sanitized_vect_type:
            sanitized_vect_type = "Unknown"
            logger.warning("Vector database type resulted in empty string after sanitization, using 'Unknown'")
        
        # Sanitize the vector database name for directory creation
        sanitized_vdb_name = "".join(c if c.isalnum() or c in ['_', '-'] else "_" for c in vdb_name).strip('_')
        if not sanitized_vdb_name:
            sanitized_vdb_name = "default"
            logger.warning("Vector database name resulted in empty string after sanitization, using 'default'")
        
        # Create hierarchical path: IO_DIR/vect_type/name
        export_path = os.path.join(io_dir, sanitized_vect_type, sanitized_vdb_name)
        logger.info(f"CSV export path resolved to: {export_path}")
        
        return export_path
        
    except Exception as e:
        logger.error(f"Error resolving CSV export path: {e}")
        # Fallback to old behavior in case of error
        fallback_path = os.path.join(os.environ.get('IO_DIR', 'exports'), 'default')
        logger.warning(f"Using fallback path: {fallback_path}")
        return fallback_path

def get_vector_store(request):
    """
    Get the vector store for the current workspace using the new plugin architecture.
    
    Args:
        request: The HTTP request object containing the session
        
    Returns:
        VectorStoreInterface: The vector store for the current workspace
        
    Raises:
        ValueError: If no workspace is found in the session or if configuration is invalid
    """
    workspace = get_current_workspace(request)
    
    if not workspace.sql_db:
        raise ValueError("No SQL database associated with the current workspace")
    
    if not workspace.sql_db.vector_db:
        raise ValueError("No vector database associated with the SQL database")
    
    vector_db = workspace.sql_db.vector_db
    
    try:
        # Map Django VectorDbChoices to plugin backend identifiers
        backend_mapping = {
            VectorDbChoices.QDRANT: 'qdrant',
            VectorDbChoices.CHROMA: 'chroma',
            VectorDbChoices.PGVECTOR: 'pgvector',
            VectorDbChoices.MILVUS: 'milvus',
        }
        
        backend = backend_mapping.get(vector_db.vect_type)
        if not backend:
            raise ValueError(f"Vector database type {vector_db.vect_type} is not supported")
        
        # Prepare connection parameters based on backend type
        params = {'collection': vector_db.name}
        
        if backend == 'qdrant':
            params.update({
                'host': vector_db.host or 'localhost',
                'port': vector_db.port or 6333,
            })
                
        elif backend == 'chroma':
            if vector_db.path:
                params['path'] = vector_db.path
            else:
                params.update({
                    'host': vector_db.host or 'localhost',
                    'port': vector_db.port or 8000,
                })
                
        elif backend == 'pgvector':
            params.update({
                'host': vector_db.host or 'localhost',
                'port': vector_db.port or 5432,
                'database': vector_db.name or 'postgres',
                'user': vector_db.username,
                'password': vector_db.password,
            })
            
        elif backend == 'milvus':
            params.update({
                'host': vector_db.host or 'localhost',
                'port': vector_db.port or 19530,
            })
            if vector_db.username:
                params['user'] = vector_db.username
            if vector_db.password:
                params['password'] = vector_db.password
                
        
        # Prepare embedding configuration with fallback to environment variables
        # This provides backward compatibility for existing VectorDb records
        embedding_provider = vector_db.embedding_provider or os.environ.get('EMBEDDING_PROVIDER')
        embedding_model = vector_db.embedding_model or os.environ.get('EMBEDDING_MODEL')
        
        # Get API key from environment variables
        embedding_api_key = None
        # Try provider-specific environment variables
        if embedding_provider == 'openai':
            embedding_api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('OPENAI_KEY')
        elif embedding_provider == 'cohere':
            embedding_api_key = os.environ.get('COHERE_API_KEY') or os.environ.get('COHERE_KEY')
        elif embedding_provider == 'mistral':
            embedding_api_key = os.environ.get('MISTRAL_API_KEY') or os.environ.get('MISTRAL_KEY')
        elif embedding_provider == 'huggingface':
            embedding_api_key = os.environ.get('HUGGINGFACE_API_KEY') or os.environ.get('HF_API_KEY') or os.environ.get('HUGGINGFACE_TOKEN')
        elif embedding_provider == 'anthropic':
            embedding_api_key = os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('CLAUDE_API_KEY')
        
        # Fall back to generic EMBEDDING_API_KEY if provider-specific not found
        if not embedding_api_key:
            embedding_api_key = os.environ.get('EMBEDDING_API_KEY')
        
        # Validate embedding configuration (now with fallback values)
        if not all([embedding_provider, embedding_api_key, embedding_model]):
            raise ValueError(f"Incomplete embedding configuration for {vector_db.name}. "
                           f"Provider: {embedding_provider}, "
                           f"API Key: {'set' if embedding_api_key else 'missing'}, "
                           f"Model: {embedding_model}. "
                           f"Please configure embedding settings in database or environment variables.")
        
        # Add embedding parameters to params for the adapter
        # Note: thoth-vdbmanager v0.6.0 expects individual parameters for external embeddings
        params['embedding_provider'] = embedding_provider
        params['embedding_model'] = embedding_model
        
        # Configure embedding dimensions based on provider and model
        if embedding_provider == 'openai':
            if 'text-embedding-3-small' in embedding_model:
                params['embedding_dim'] = 1536
            elif 'text-embedding-3-large' in embedding_model:
                params['embedding_dim'] = 3072
            else:
                params['embedding_dim'] = 1536  # default for OpenAI
        elif embedding_provider == 'cohere':
            params['embedding_dim'] = 1024  # Cohere embed-multilingual-v3.0
        elif embedding_provider == 'mistral':
            params['embedding_dim'] = 1024  # Mistral embed
        else:
            params['embedding_dim'] = 384   # default/fallback
        
        # Create vector store using factory with individual parameters
        vector_store = VectorStoreFactory.create(
            backend=backend, 
            **params
        )
        
        # Log embedding configuration source for debugging
        config_source = "environment variables"
        
        logger.info(f"Successfully created {backend} vector store for collection {vector_db.name} "
                   f"with {embedding_provider} embeddings ({embedding_model}) "
                   f"from {config_source}")
        return vector_store
        
    except Exception as e:
        logger.error(f"Failed to create vector store for {vector_db.name}: {e}")
        raise

def export_evidence_to_csv_file(vector_store, request=None):
    """
    Exports all evidence from the given vector_store to a CSV file.

    Args:
        vector_store: An instance of a vector store from thoth-qdrant.
        request: The HTTP request object (optional, for new path resolution)

    Returns:
        A tuple (filepath, csv_content_string) if successful,
        otherwise raises an exception.
    """
    try:
        evidence_documents = vector_store.get_all_evidence_documents()

        # Use new path resolution if request is provided
        if request is not None:
            try:
                export_dir = get_csv_export_path(request)
            except Exception as e:
                logger.warning(f"Failed to get new CSV export path: {e}. Falling back to old method.")
                request = None  # Fall back to old method
        
        # Fallback to old method if request not provided or new method failed
        if request is None:
            # Use qdrant as the folder name for Qdrant-based vector stores
            vector_db_type_folder = "qdrant"

            # Sanitize the folder name to ensure it's valid for directory creation
            # Replace non-alphanumeric characters (except underscore) with an underscore
            vector_db_type_folder = "".join(c if c.isalnum() else "_" for c in vector_db_type_folder).strip('_')
            if not vector_db_type_folder: # If sanitization results in an empty string
                vector_db_type_folder = "default_vdb_type"

            export_base_dir = "exports"
            export_dir = os.path.join(export_base_dir, vector_db_type_folder)
        
        # Create directories if they don't exist
        os.makedirs(export_dir, exist_ok=True)

        csv_filename = "evidence_export.csv" # No timestamp, overwrite
        filepath = os.path.join(export_dir, csv_filename)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['id', 'evidence']) # CSV Headers

        for doc in evidence_documents:
            if isinstance(doc, EvidenceDocument): # Ensure it's the correct document type
                writer.writerow([getattr(doc, 'id', ''), getattr(doc, 'evidence', '')])
            else:
                logger.warning(f"Skipping document of type {type(doc)} during evidence export, expected EvidenceDocument.")

        csv_content_string = output.getvalue()
        output.close()

        # Save the file to the server, overwriting if it exists
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_content_string)
        
        logger.info(f"Evidence CSV successfully saved to {filepath}")
        return filepath, csv_content_string

    except Exception as e:
        logger.error(f"Error during evidence CSV export process: {e}", exc_info=True)
        raise # Re-raise the exception to be handled by the calling view

# --- DELETE ALL FUNCTIONS ---

def delete_all_evidence_from_vector_store(vector_store):
    """
    Deletes all EvidenceDocuments from the vector store using delete_collection.
    """
    try:
        # Ensure vector_store has delete_collection method.
        # The vector_store is an instance from thoth-qdrant library where delete_collection is defined.
        if not hasattr(vector_store, 'delete_collection'):
            logger.error("Vector store object does not have a 'delete_collection' method.")
            raise NotImplementedError("Vector store 'delete_collection' method not found.")

        vector_store.delete_collection(thoth_type=ThothType.EVIDENCE)
        logger.info("Successfully called delete_collection for evidence (ThothType.EVIDENCE).")
    except Exception as e:
        logger.error(f"Error deleting all evidence using delete_collection: {e}", exc_info=True)
        raise

def delete_all_columns_from_vector_store(vector_store):
    """
    Deletes all ColumnNameDocuments from the vector store using delete_collection.
    """
    try:
        if not hasattr(vector_store, 'delete_collection'):
            logger.error("Vector store object does not have a 'delete_collection' method.")
            raise NotImplementedError("Vector store 'delete_collection' method not found.")

        vector_store.delete_collection(thoth_type=ThothType.COLUMN_NAME) # Assuming ThothType.COLUMN_NAME
        logger.info("Successfully called delete_collection for columns (ThothType.COLUMN_NAME).")
    except Exception as e:
        logger.error(f"Error deleting all columns using delete_collection: {e}", exc_info=True)
        raise


def delete_all_questions_from_vector_store(vector_store):
    """
    Deletes all SqlDocuments (questions) from the vector store using delete_collection.
    """
    try:
        if not hasattr(vector_store, 'delete_collection'):
            logger.error("Vector store object does not have a 'delete_collection' method.")
            raise NotImplementedError("Vector store 'delete_collection' method not found.")

        vector_store.delete_collection(thoth_type=ThothType.SQL) # Assuming ThothType.SQL
        logger.info("Successfully called delete_collection for questions (ThothType.SQL).")
    except Exception as e:
        logger.error(f"Error deleting all questions using delete_collection: {e}", exc_info=True)
        raise

# --- IMPORT FUNCTIONS ---

def _get_csv_file_path(vector_store, filename_suffix, request=None):
    """
    Helper function to determine the CSV file path for import.
    
    Args:
        vector_store: The vector store instance
        filename_suffix: The filename suffix (e.g., 'evidence', 'columns', 'questions')
        request: The HTTP request object (optional, for new path resolution)
    
    Returns:
        str: The full path to the CSV file
    """
    # Use new path resolution if request is provided
    if request is not None:
        try:
            export_dir = get_csv_export_path(request)
        except Exception as e:
            logger.warning(f"Failed to get new CSV export path: {e}. Falling back to old method.")
            request = None  # Fall back to old method
    
    # Fallback to old method if request not provided or new method failed
    if request is None:
        # Use qdrant as the folder name for Qdrant-based vector stores
        vector_db_type_folder = "qdrant"

        vector_db_type_folder = "".join(c if c.isalnum() else "_" for c in vector_db_type_folder).strip('_')
        if not vector_db_type_folder:
            vector_db_type_folder = "default_vdb_type"

        export_base_dir = "exports"
        export_dir = os.path.join(export_base_dir, vector_db_type_folder)
    
    csv_filename = f"{filename_suffix}_export.csv" # Assumes export files are named like 'evidence_export.csv'
    filepath = os.path.join(export_dir, csv_filename)
    return filepath

def import_evidence_from_csv_file(vector_store, request=None):
    """
    Imports evidence from a CSV file into the vector store.
    Assumes CSV has 'id' and 'evidence' columns.
    Uses the ID from CSV for potential overwrites based on vector_store's DuplicatePolicy.

    Args:
        vector_store: The vector store instance
        request: The HTTP request object (optional, for new path resolution)
    """
    filepath = _get_csv_file_path(vector_store, "evidence", request)
    imported_count = 0
    error_count = 0
    messages = []

    if not os.path.exists(filepath):
        messages.append(f"Error: File not found at {filepath}")
        logger.error(f"Evidence import CSV file not found: {filepath}")
        return {"imported_count": 0, "error_count": 1, "messages": messages}

    try:
        with open(filepath, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if 'id' not in reader.fieldnames or 'evidence' not in reader.fieldnames:
                msg = "Error: CSV file for evidence must contain 'id' and 'evidence' columns."
                messages.append(msg)
                logger.error(msg + f" File: {filepath}")
                return {"imported_count": 0, "error_count": 1, "messages": messages}

            for row in reader:
                try:
                    evidence_id = row.get('id')
                    evidence_text = row.get('evidence')
                    if not evidence_id or evidence_text is None: # evidence_text can be empty string
                        logger.warning(f"Skipping evidence row due to missing id or evidence key: {row}")
                        error_count += 1
                        messages.append(f"Skipped evidence row: missing id or evidence data - ID: {evidence_id if evidence_id else 'N/A'}")
                        continue

                    evidence_doc = EvidenceDocument(id=evidence_id, evidence=evidence_text)
                    vector_store.add_evidence(evidence_doc)
                    imported_count += 1
                except Exception as e_row:
                    logger.error(f"Error importing evidence row (ID: {evidence_id}): {e_row}")
                    error_count += 1
                    messages.append(f"Error for evidence ID {evidence_id}: {e_row}")
        if error_count > 0:
            messages.insert(0, f"Import process completed with {error_count} errors.")
        messages.insert(0, f"Successfully imported {imported_count} evidence items.")
        logger.info(f"Evidence import complete. Imported: {imported_count}, Errors: {error_count} from {filepath}")
    except Exception as e_file:
        logger.error(f"Error processing CSV file {filepath} for evidence: {e_file}")
        error_count += 1 # This might double count if an error also happened per row
        messages.append(f"Failed to process CSV file {filepath}: {e_file}")
        
    return {"imported_count": imported_count, "error_count": error_count, "messages": messages}

def import_columns_from_csv_file(vector_store, request=None):
    """
    Imports column documents from a CSV file into the vector store.
    Uses IDs from CSV for potential overwrites.
    
    Args:
        vector_store: The vector store instance
        request: The HTTP request object (optional, for new path resolution)
    """
    filepath = _get_csv_file_path(vector_store, "columns", request)
    imported_count = 0
    error_count = 0
    messages = []

    if not os.path.exists(filepath):
        messages.append(f"Error: File not found at {filepath}")
        logger.error(f"Columns import CSV file not found: {filepath}")
        return {"imported_count": 0, "error_count": 1, "messages": messages}

    try:
        with open(filepath, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            expected_headers = ['id', 'table_name', 'original_column_name', 'column_description', 'value_description']
            if not all(header in reader.fieldnames for header in expected_headers):
                msg = f"Error: CSV file for columns must contain all expected columns: {', '.join(expected_headers)}."
                messages.append(msg)
                logger.error(msg + f" File: {filepath}")
                return {"imported_count": 0, "error_count": 1, "messages": messages}

            for row in reader:
                try:
                    col_id = row.get('id')
                    if not col_id:
                        logger.warning(f"Skipping column row due to missing id: {row}")
                        error_count += 1
                        messages.append(f"Skipped column row: missing id - Name: {row.get('original_column_name', 'N/A')}")
                        continue
                    
                    table_name_val = row.get('table_name')
                    original_column_name_val = row.get('original_column_name')
                    column_description_val = row.get('column_description')
                    value_description_val = row.get('value_description')

                    # Ensure required string fields get strings, not None.
                    # This addresses potential string_type errors and the "missing" error if it was due to None for a required string.
                    csv_original_col_name = original_column_name_val if original_column_name_val is not None else ""
                    csv_value_desc = value_description_val if value_description_val is not None else ""

                    column_doc = ColumnNameDocument(
                        id=col_id,
                        table_name=table_name_val if table_name_val else '',
                        column_name=csv_original_col_name, # Fed from CSV's original_column_name
                        original_column_name=csv_original_col_name, # Fed from CSV's original_column_name
                        column_description=column_description_val if column_description_val else '',
                        value_description=csv_value_desc
                    )
                    vector_store.add_column_description(column_doc)
                    imported_count += 1
                except Exception as e_row:
                    logger.error(f"Error importing column row (ID: {col_id}): {e_row}")
                    error_count += 1
                    messages.append(f"Error for column ID {col_id}: {e_row}")
        if error_count > 0:
            messages.insert(0, f"Import process completed with {error_count} errors.")
        messages.insert(0, f"Successfully imported {imported_count} columns.")
        logger.info(f"Column import complete. Imported: {imported_count}, Errors: {error_count} from {filepath}")
    except Exception as e_file:
        logger.error(f"Error processing CSV file {filepath} for columns: {e_file}")
        messages.append(f"Failed to process CSV file {filepath}: {e_file}")

    return {"imported_count": imported_count, "error_count": error_count, "messages": messages}


def import_questions_from_csv_file(vector_store, request=None):
    """
    Imports SQL documents (questions) from a CSV file into the vector store.
    Uses IDs from CSV for potential overwrites.
    
    Args:
        vector_store: The vector store instance
        request: The HTTP request object (optional, for new path resolution)
    """
    filepath = _get_csv_file_path(vector_store, "questions", request)
    imported_count = 0
    error_count = 0
    messages = []

    if not os.path.exists(filepath):
        messages.append(f"Error: File not found at {filepath}")
        logger.error(f"Questions import CSV file not found: {filepath}")
        return {"imported_count": 0, "error_count": 1, "messages": messages}

    try:
        with open(filepath, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            expected_headers = ['id', 'question', 'sql']
            if not all(header in reader.fieldnames for header in expected_headers):
                msg = f"Error: CSV file for questions must contain all expected columns: {', '.join(expected_headers)}."
                messages.append(msg)
                logger.error(msg + f" File: {filepath}")
                return {"imported_count": 0, "error_count": 1, "messages": messages}

            for row in reader:
                try:
                    q_id = row.get('id')
                    q_text = row.get('question')
                    q_sql = row.get('sql')
                    if not q_id or q_text is None or q_sql is None: # question and sql can be empty strings
                        logger.warning(f"Skipping question row due to missing id, question key, or sql key: {row}")
                        error_count += 1
                        messages.append(f"Skipped question row: missing id, question or sql data - ID: {q_id if q_id else 'N/A'}")
                        continue
                        
                    question_doc = SqlDocument(id=q_id, question=q_text, sql=q_sql)
                    vector_store.add_sql(question_doc) 
                    imported_count += 1
                except Exception as e_row:
                    logger.error(f"Error importing question row (ID: {q_id}): {e_row}")
                    error_count += 1
                    messages.append(f"Error for question ID {q_id}: {e_row}")
        if error_count > 0:
            messages.insert(0, f"Import process completed with {error_count} errors.")
        messages.insert(0, f"Successfully imported {imported_count} questions.")
        logger.info(f"Questions import complete. Imported: {imported_count}, Errors: {error_count} from {filepath}")
    except Exception as e_file:
        logger.error(f"Error processing CSV file {filepath} for questions: {e_file}")
        messages.append(f"Failed to process CSV file {filepath}: {e_file}")

    return {"imported_count": imported_count, "error_count": error_count, "messages": messages}

def export_columns_to_csv_file(vector_store, request=None):
    """
    Exports all column documents from the given vector_store to a CSV file.

    Args:
        vector_store: An instance of a vector store from thoth-qdrant.
        request: The HTTP request object (optional, for new path resolution)

    Returns:
        A tuple (filepath, csv_content_string) if successful,
        otherwise raises an exception.
    """
    try:
        column_documents = vector_store.get_all_column_documents()

        # Use new path resolution if request is provided
        if request is not None:
            try:
                export_dir = get_csv_export_path(request)
            except Exception as e:
                logger.warning(f"Failed to get new CSV export path: {e}. Falling back to old method.")
                request = None  # Fall back to old method
        
        # Fallback to old method if request not provided or new method failed
        if request is None:
            # Use qdrant as the folder name for Qdrant-based vector stores
            vector_db_type_folder = "qdrant"

            vector_db_type_folder = "".join(c if c.isalnum() else "_" for c in vector_db_type_folder).strip('_')
            if not vector_db_type_folder:
                vector_db_type_folder = "default_vdb_type"

            export_base_dir = "exports"
            export_dir = os.path.join(export_base_dir, vector_db_type_folder)
        
        os.makedirs(export_dir, exist_ok=True)

        csv_filename = "columns_export.csv"
        filepath = os.path.join(export_dir, csv_filename)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['id', 'table_name', 'original_column_name', 'column_description', 'value_description']) # CSV Headers

        for doc in column_documents:
            if isinstance(doc, ColumnNameDocument):
                writer.writerow([
                    getattr(doc, 'id', ''),
                    getattr(doc, 'table_name', ''),
                    getattr(doc, 'column_name', ''),
                    getattr(doc, 'column_description', ''),
                    getattr(doc, 'value_description', '')
                ])
            else:
                logger.warning(f"Skipping document of type {type(doc)} during column export, expected ColumnNameDocument.")

        csv_content_string = output.getvalue()
        output.close()

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_content_string)
        
        logger.info(f"Columns CSV successfully saved to {filepath}")
        return filepath, csv_content_string

    except Exception as e:
        logger.error(f"Error during columns CSV export process: {e}", exc_info=True)
        raise


def export_questions_to_csv_file(vector_store, request=None):
    """
    Exports all SQL documents (questions) from the given vector_store to a CSV file.

    Args:
        vector_store: An instance of a vector store from thoth-qdrant.
        request: The HTTP request object (optional, for new path resolution)

    Returns:
        A tuple (filepath, csv_content_string) if successful,
        otherwise raises an exception.
    """
    try:
        sql_documents = vector_store.get_all_sql_documents()

        # Use new path resolution if request is provided
        if request is not None:
            try:
                export_dir = get_csv_export_path(request)
            except Exception as e:
                logger.warning(f"Failed to get new CSV export path: {e}. Falling back to old method.")
                request = None  # Fall back to old method
        
        # Fallback to old method if request not provided or new method failed
        if request is None:
            # Use qdrant as the folder name for Qdrant-based vector stores
            vector_db_type_folder = "qdrant"

            vector_db_type_folder = "".join(c if c.isalnum() else "_" for c in vector_db_type_folder).strip('_')
            if not vector_db_type_folder:
                vector_db_type_folder = "default_vdb_type"

            export_base_dir = "exports"
            export_dir = os.path.join(export_base_dir, vector_db_type_folder)
        
        os.makedirs(export_dir, exist_ok=True)

        csv_filename = "questions_export.csv"
        filepath = os.path.join(export_dir, csv_filename)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['id', 'question', 'sql', 'evidence']) # CSV Headers

        for doc in sql_documents:
            if isinstance(doc, SqlDocument):
                writer.writerow([
                    getattr(doc, 'id', ''),
                    getattr(doc, 'question', ''),
                    getattr(doc, 'sql', ''),
                    getattr(doc, 'evidence', '')
                ])
            else:
                logger.warning(f"Skipping document of type {type(doc)} during questions export, expected SqlDocument.")

        csv_content_string = output.getvalue()
        output.close()

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_content_string)
        
        logger.info(f"Questions CSV successfully saved to {filepath}")
        return filepath, csv_content_string

    except Exception as e:
        logger.error(f"Error during questions CSV export process: {e}", exc_info=True)
        raise
