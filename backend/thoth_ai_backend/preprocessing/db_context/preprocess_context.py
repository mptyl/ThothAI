# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

import logging

from dotenv import load_dotenv
from typing import Type

# Define DuplicatePolicy locally since we're not using Haystack anymore
from enum import Enum

class DuplicatePolicy(Enum):
    """Policy for handling duplicate documents."""
    OVERWRITE = "overwrite"
    SKIP = "skip"
    FAIL = "fail"

# Import new vector store plugin architecture
from thoth_qdrant import ColumnNameDocument, ThothType
from thoth_ai_backend.utils.progress_tracker import ProgressTracker

from .load_table_description import load_tables_description

load_dotenv(override=True)


def make_db_context_vec_db(document_store, db_params, **kwargs) -> int:
    """
    Creates a context vector database for the specified database directory.

    This function performs the following steps:
    1. Loads table descriptions from the specified database
    2. Deletes any existing column name documents from the vector store
    3. Creates new ColumnNameDocument objects for each column in each table
    4. Uploads the new documents to the vector store

    Args:
        document_store: Vector store instance to store the documents
        db_params (dict): Database parameters containing:
            - db_name (str): Name of the database
        **kwargs: Additional keyword arguments:
            - use_value_description (bool): Whether to include value descriptions (default: True)

    Returns:
        None

    Example:
        db_params = {"db_name": "my_database"}
        make_db_context_vec_db(vector_store, db_params, use_value_description=True)
    """
    db_id = db_params["id"]
    db_name = db_params["name"]

    logging.info(f"Creating context vector database for database: {db_name}")

    # Ensure collection exists before attempting operations
    try:
        document_store.ensure_collection_exists()
    except Exception as e:
        error_msg = f"Failed to ensure collection exists: {str(e)}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    table_description = load_tables_description(
        db_id, use_value_description=kwargs.get("use_value_description", True)
    )

    docs = []

    # First get all existing Column_name documents to delete them
    # Use the interface method instead of the implementation-specific method
    existing_docs = document_store.get_all_column_documents()
    if existing_docs:
        doc_ids = [doc.id for doc in existing_docs]
        document_store.delete_documents(doc_ids)

    # Extract workspace_id from kwargs if provided
    workspace_id = kwargs.get('workspace_id', None)
    
    # Count total columns for progress tracking
    total_columns = sum(len(columns) for columns in table_description.values())
    processed_items = 0
    successful_items = 0
    
    # Get the number of unique values processed previously (from make_db_lsh)
    # This is used as an offset for progress tracking
    from thoth_core.models import SqlDb
    try:
        sql_db = SqlDb.objects.get(id=db_params["id"])
        # Estimate unique values count (we'll use this as offset)
        from thoth_dbmanager import ThothDbFactory
        
        # We don't have the exact count here, so we'll use an estimate or fetch from cache
        processed_items_offset = kwargs.get('processed_items_offset', 0)
    except:
        processed_items_offset = 0
    
    # Then proceed with creating new documents
    for table_name, columns in table_description.items():
        for column_name, column_info in columns.items():
            column_description=ColumnNameDocument(
                table_name=table_name,
                column_name=column_info.get("column_name", ""),
                original_column_name=column_info.get("original_column_name", ""),
                column_description=column_info.get("column_description", ""),
                value_description=column_info.get("value_description", ""),
                text=f"{table_name}.{column_info.get('column_name', '')}: {column_info.get('column_description', '')}"  # Use descriptive text for searching
            )
            docs.append(column_description)
            
            processed_items += 1
            successful_items += 1
            
            # Update progress tracker if workspace_id is provided
            if workspace_id and processed_items % 10 == 0:  # Update every 10 columns
                ProgressTracker.update_progress(
                    workspace_id, 'preprocessing',
                    processed_items_offset + processed_items,
                    processed_items_offset + successful_items,
                    0  # No failed items in this process
                )

    # Upload of documents to the vector store.
    logging.info(
        f"Uploading {len(docs)} nodes with columns_data key in collection {document_store.collection_name} paired with database {db_name}"
    )
    if docs:
        document_store.bulk_add_documents(docs, policy=DuplicatePolicy.OVERWRITE)
    logging.info(f"Context vector database created at {db_name}")
    
    # Final progress update
    if workspace_id:
        ProgressTracker.update_progress(
            workspace_id, 'preprocessing',
            processed_items_offset + processed_items,
            processed_items_offset + successful_items,
            0
        )
    
    return processed_items
