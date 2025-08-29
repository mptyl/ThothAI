# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

import json
import logging
import os
import sys
import django
from pathlib import Path
from django.utils import timezone
# Import new vector store plugin architecture
from thoth_qdrant import ThothType, EvidenceDocument
from thoth_qdrant import VectorStoreFactory

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
django.setup()

# Now you can import Django models
from thoth_core.models import Workspace

from thoth_ai_backend.backend_utils.vectordb_config_utils import get_vectordb_config
from thoth_ai_backend.utils.progress_tracker import ProgressTracker

def upload_evidence_to_vectordb(workspace_id=None) -> tuple:
    """
    Uploads evidence from dev.json to the vector database and updates the workspace timestamp.

    This function processes evidence data from a development JSON file and uploads it to the
    appropriate vector database collection associated with the specified workspace. It first
    establishes connections to the workspace's SQL database and vector database, then clears
    any existing evidence documents before uploading new ones. Only evidence with matching db_id
    (corresponding to the collection name) are processed.

    The function workflow:
    1. Creates a QdrantVectorStore for the collection based on workspace's SQL DB
    2. Deletes all existing EVIDENCE documents
    3. Reads evidence from data/dev_databases/dev.json
    4. Creates and uploads EvidenceDocuments for each evidence where db_id matches the workspace's collection
    5. Updates the workspace's last_evidence_load timestamp
    
    Args:
        workspace_id (int, optional): The ID of the workspace to determine the collection name
            and database connections. Must be provided.
        
    Raises:
        ValueError: If workspace_id is not provided, if the workspace doesn't exist,
            if the workspace has no SQL database configured, or if the SQL database
            has no vector database configured.
        NotImplementedError: If the vector database type is not supported (currently only Qdrant).
        IOError: If the dev.json file cannot be read.
    
    Returns:
        tuple: A tuple of (successful_uploads, total_items) for progress tracking.
    """
    # Check if workspace_id is provided
    if not workspace_id:
        error_msg = "Workspace ID is required"
        logging.error(error_msg)
        raise ValueError(error_msg)
    
    # Get workspace and extract configuration
    try:
        workspace = Workspace.objects.get(id=workspace_id)
    except Workspace.DoesNotExist:
        error_msg = f"Workspace with ID {workspace_id} not found"
        logging.error(error_msg)
        raise ValueError(error_msg)
    
    # Check if SQL DB is configured
    if not workspace.sql_db:
        error_msg = f"Workspace {workspace_id} has no SQL database configured"
        logging.error(error_msg)
        raise ValueError(error_msg)
    
    sql_db = workspace.sql_db
    
    # Convert Django model to dictionary for compatibility with existing code
    sql_db_params = {
        "name": sql_db.name,
        "db_host": sql_db.db_host,
        "db_type": sql_db.db_type,
        "db_name": sql_db.db_name,
        "db_port": sql_db.db_port,
        "schema": sql_db.schema,
        "user_name": sql_db.user_name,
        "password": sql_db.password,
        "db_mode": sql_db.db_mode,
        "language": sql_db.language,
    }
    
    # Check if vector DB is configured
    if not sql_db.vector_db:
        error_msg = f"SQL DB {sql_db.name} has no vector database configured"
        logging.error(error_msg)
        raise ValueError(error_msg)
    
    vector_db_obj = sql_db.vector_db
    sql_db_params["vector_db"] = {
        "name": vector_db_obj.name,
        "vect_type": vector_db_obj.vect_type,
        "host": vector_db_obj.host,
        "port": vector_db_obj.port,
        "username": vector_db_obj.username,
        "password": vector_db_obj.password,
        "tenant": vector_db_obj.tenant,
    }
    
    # Get vector database configuration
    vector_db_config = get_vectordb_config(sql_db_params)
    
    # Initialize the appropriate vector store using new plugin factory
    vector_backend_mapping = {
        'Qdrant': 'qdrant',
        'Chroma': 'chroma',
        'PGVector': 'pgvector',
        'Milvus': 'milvus',
    }
    
    backend = vector_backend_mapping.get(vector_db_config["vector_db_type"])
    if not backend:
        error_msg = f"Unsupported vector database type: {vector_db_config['vector_db_type']}"
        logging.error(error_msg)
        raise NotImplementedError(error_msg)
    
    # Create vector store using factory
    vector_params = {'collection': vector_db_config.get('collection_name')}
    if backend == 'qdrant':
        vector_params.update({
            'host': vector_db_config.get('host'),
            'port': vector_db_config.get('port'),
        })
    
    vector_db = VectorStoreFactory.create(backend, **vector_params)
    
    # Delete existing collection before uploading new evidence
    try:
        if hasattr(vector_db, 'delete_collection'):
            vector_db.delete_collection(thoth_type=ThothType.EVIDENCE)
            logging.info(f"Deleted existing EVIDENCE collection for {vector_db_config.get('collection_name')}")
    except Exception as e:
        logging.warning(f"Could not delete existing EVIDENCE collection: {e}")

    logging.info(f"Using vector database: {vector_db_config['vector_db_type']}, "
                 f"collection: {vector_db_config.get('collection_name')}, "
                 f"host: {vector_db_config.get('host')}, "
                 f"port: {vector_db_config.get('port')}")

    # Ensure collection exists before attempting operations
    try:
        logging.info(f"Calling ensure_collection_exists on vector_db: {type(vector_db)}")
        vector_db.ensure_collection_exists()
        logging.info("ensure_collection_exists completed successfully")
    except Exception as e:
        error_msg = f"Failed to ensure collection exists: {str(e)}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    # Delete all existing EVIDENCE documents
    # Use the interface method instead of the implementation-specific method
    existing_evidence = vector_db.get_all_evidence_documents()
    if existing_evidence:
        evidence_ids = [doc.id for doc in existing_evidence]
        vector_db.delete_documents(evidence_ids)
        logging.info(f"Deleted {len(evidence_ids)} existing evidence documents")
    
    # Read dev.json file
    project_root = Path(__file__).resolve().parents[2]
    
    # Check for DB_ROOT_PATH environment variable
    db_root_path_val = os.getenv("DB_ROOT_PATH")
    if not db_root_path_val:
        error_msg = "Environment variable DB_ROOT_PATH is not set."
        logging.error(error_msg)
        raise ValueError(error_msg)
        
    # Check if the base directory specified in DB_ROOT_PATH exists
    db_root_dir = Path(db_root_path_val)
    if not db_root_dir.is_dir():
        error_msg = f"The directory specified by DB_ROOT_PATH does not exist: {db_root_dir}"
        logging.error(error_msg)
        raise ValueError(error_msg)
        
    db_mode_val = sql_db.db_mode
    dev_json_path = db_root_dir / f"{db_mode_val}_databases" / f"{db_mode_val}.json"
    
    # Check if dev_json_path exists and is a file
    if not dev_json_path.is_file():
        error_msg = f"The JSON file specified by dev_json_path does not exist: {dev_json_path}"
        logging.error(error_msg)
        raise ValueError(error_msg)

    try:
        with open(dev_json_path, 'r', encoding='utf-8') as f:
            dev_data = json.load(f)
    except json.JSONDecodeError as e:
        error_msg = f"Failed to decode JSON from {dev_json_path}: {str(e)}"
        logging.error(error_msg)
        raise ValueError(error_msg) # Changed from IOError to ValueError for consistency
    except Exception as e: # Catch other potential IOErrors
        error_msg = f"Failed to read dev.json file at {dev_json_path}: {str(e)}"
        logging.error(error_msg)
        raise IOError(error_msg)
    
    # Use collection name as db_id for filtering
    db_id = sql_db.db_name
    
    # First, count total items to process
    total_items = sum(1 for entry in dev_data if entry.get("db_id") == db_id and entry.get("evidence") and isinstance(entry.get("evidence"), str))
    logging.info(f"Found {total_items} evidence items to process for db_id: {db_id}")
    
    # Update progress tracking with the actual total (it was initialized with 0 in the view)
    progress = ProgressTracker.get_progress(workspace_id, 'evidence')
    if progress:
        # Update the total items count now that we know the actual number
        ProgressTracker.update_progress(workspace_id, 'evidence', 0, 0, 0)
        # Now update with the correct total
        progress = ProgressTracker.get_progress(workspace_id, 'evidence')
        if progress:
            from django.core.cache import cache
            progress['total_items'] = total_items
            cache_key = ProgressTracker.get_cache_key(workspace_id, 'evidence')
            cache.set(cache_key, json.dumps(progress), timeout=3600)
    else:
        # Fallback: initialize if somehow it doesn't exist yet
        ProgressTracker.init_progress(workspace_id, 'evidence', total_items)
    
    successful_uploads = 0
    failed_uploads = 0
    processed_items = 0
    
    # Process each entry, filtering for the specified db_id
    for entry in dev_data:
        if entry.get("db_id") != db_id:
            continue
            
        evidence = entry.get("evidence")
        if not evidence or not isinstance(evidence, str):
            logging.warning(f"Skipping invalid evidence entry: {entry}")
            continue

        evidence_doc = EvidenceDocument(
            evidence=evidence.strip(),
            text=evidence.strip()  # Use evidence as the text for searching
        )

        try:
            vector_db.add_evidence(evidence_doc)
            successful_uploads += 1
            processed_items += 1
            # Update progress tracker
            ProgressTracker.update_progress(workspace_id, 'evidence', processed_items, successful_uploads, failed_uploads)
            progress_percentage = int((processed_items / total_items) * 100) if total_items > 0 else 0
            logging.info(f"Successfully uploaded evidence ({processed_items}/{total_items} - {progress_percentage}%): {evidence[:100]}...")
        except Exception as e:
            failed_uploads += 1
            processed_items += 1
            # Update progress tracker
            ProgressTracker.update_progress(workspace_id, 'evidence', processed_items, successful_uploads, failed_uploads)
            logging.error(f"Failed to upload evidence: {evidence[:100]}... Error: {str(e)}")

    # Clear the cache to ensure fresh data on next retrieval
    #get_cached_training_data.clear(ThothType.EVIDENCE) - sostituire con equivalente streamlit free

    # Update the last_evidence_load timestamp in the workspace
    workspace.last_evidence_load = timezone.now()
    workspace.save()
    logging.info(f"Updated last_evidence_load timestamp for workspace {workspace.name} (ID: {workspace_id})")

    # Log summary
    logging.info(f"Evidence upload complete. Successful: {successful_uploads}, Failed: {failed_uploads}, Total: {total_items}")
    
    # Don't clear progress here - let the check_progress view do it after showing completion
    # The progress view needs the completion status to show the success message
    # ProgressTracker.clear_progress(workspace_id, 'evidence')
    
    return successful_uploads, total_items

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload evidence to vector database")
    parser.add_argument("--workspace_id", type=int, required=True, help="Workspace ID to determine collection name")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        upload_evidence_to_vectordb(workspace_id=args.workspace_id)
    except Exception as e:
        logging.error(f"Error in upload_evidence_to_vectordb: {str(e)}")
        sys.exit(1)
