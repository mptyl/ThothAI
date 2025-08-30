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

import argparse
import logging
import os
import sys
import django
from pathlib import Path
from typing import Dict

# New plugin-based imports
from thoth_dbmanager.core.interfaces import DbPlugin
from dotenv import load_dotenv

# Import new vector store plugin architecture
from thoth_qdrant import VectorStoreFactory
from thoth_qdrant import VectorStoreInterface

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Thoth.settings")
django.setup()

# Now you can import Django models
from thoth_core.models import SqlDb, Setting

from thoth_ai_backend.backend_utils.vectordb_config_utils import get_vectordb_config
from thoth_ai_backend.preprocessing.db_context.preprocess_context import (
    make_db_context_vec_db,
)
from thoth_ai_backend.preprocessing.db_values.preprocess_values import make_db_lsh
from thoth_ai_backend.utils.progress_tracker import ProgressTracker

load_dotenv(override=True)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def preprocess(
    db: DbPlugin,
    document_store: VectorStoreInterface,
    db_params: Dict,
    setting: Dict,
    lsh_root_arg: str = None,
    workspace_id: int = None,
) -> None:
    """
    Preprocesses a database by creating Locality-Sensitive Hashing (LSH) signatures and context vectors.

    This function handles the complete preprocessing workflow for a database, including:
    1. Creating LSH signatures for database elements
    2. Generating context vectors and storing them in the vector database

    Args:
        db (ThothDbManager): Database manager instance for accessing the database
        document_store (VectorStoreInterface): Vector store for saving context vectors
        db_params (Dict): Dictionary containing database configuration parameters including:
            - db_name: Name of the database
            - db_mode: Mode of the database (e.g., 'prod', 'dev')
            - Other database connection parameters
        setting (Dict): Dictionary containing preprocessing configuration parameters:
            - signature_size: Size of LSH signatures
            - n_grams: N-gram size for text processing
            - threshold: Similarity threshold value
            - verbose: Boolean flag for verbose output
            - use_value_description: Boolean flag to include value descriptions
        lsh_root_arg (str, optional): Root directory path for storing LSH data.
            If None, will use DB_ROOT_PATH environment variable. Defaults to None.
        workspace_id (int, optional): Workspace ID for progress tracking.

    Returns:
        None

    Raises:
        ValueError: If no LSH root directory is specified via argument or environment variable
    """
    # preprocess(sql_db, vector_db, sql_db_params, setting)

    signature_size = setting["signature_size"]
    n_gram = setting["n_grams"]
    threshold = setting["threshold"]
    verbose = setting["verbose"]
    use_value_description = setting["use_value_description"]

    db_name = db_params["db_name"]
    db_mode = db_params["db_mode"]

    # Determine LSH root directory: argument > DB_ROOT_PATH env
    lsh_root_path = lsh_root_arg or os.getenv("DB_ROOT_PATH")
    if not lsh_root_path:
        raise ValueError(
            "No LSH root directory specified via --lsh_root or DB_ROOT_PATH environment variable."
        )

    # Create path with db_mode_databases/db_name structure
    db_directory_path = os.path.join(lsh_root_path, f"{db_mode}_databases", db_name)
    os.makedirs(db_directory_path, exist_ok=True)

    # Count total items to process for progress tracking
    if workspace_id:
        try:
            # Get unique values count for LSH processing
            unique_values = db.get_unique_values()
            total_unique_values = sum(
                len(column_values)
                for table_values in unique_values.values()
                for column_values in table_values.values()
            )

            # Get tables and columns count for context vectors
            from thoth_core.models import SqlDb, SqlTable, SqlColumn

            sql_db = SqlDb.objects.get(id=db_params["id"])
            tables_count = SqlTable.objects.filter(sql_db=sql_db).count()
            columns_count = SqlColumn.objects.filter(sql_table__sql_db=sql_db).count()

            # Total items: unique values for LSH + columns for context vectors
            total_items = total_unique_values + columns_count

            logging.info(
                f"Preprocessing will process {total_items} items ({total_unique_values} unique values, {columns_count} columns)"
            )

            # Initialize progress tracking
            ProgressTracker.init_progress(workspace_id, "preprocessing", total_items)
        except Exception as e:
            logging.warning(f"Could not initialize progress tracking: {e}")
            total_items = 0
    else:
        total_items = 0

    logging.info(f"Creating LSH for {db_name} in {db_directory_path}")
    lsh_processed_items = make_db_lsh(
        db,
        db_directory_path,
        db_name,
        signature_size=signature_size,
        n_gram=n_gram,
        threshold=threshold,
        verbose=verbose,
        workspace_id=workspace_id,
    )
    logging.info(
        f"LSH for {db_name} created. Processed {lsh_processed_items} unique values."
    )
    logging.info(f"Creating context vectors for {db_name}")

    columns_processed = make_db_context_vec_db(
        document_store,
        db_params,
        use_value_description=use_value_description,
        workspace_id=workspace_id,
        processed_items_offset=lsh_processed_items,  # Pass the LSH items as offset
    )
    logging.info(
        f"Columns vector points for {db_name} created. Processed {columns_processed} columns."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess database for ThothPydAi")
    parser.add_argument(
        "--db_name", type=str, help="Name of the database to preprocess"
    )
    parser.add_argument(
        "--lsh_root",
        type=str,
        default=None,
        help="Root directory for LSH data (overrides DB_ROOT_PATH)",
    )
    args = parser.parse_args()

    if not args.db_name:
        logging.error("Please provide a database name with --db_name")
        sys.exit(1)

    try:
        # Get database parameters directly from the model
        sql_db_obj = SqlDb.objects.get(name=args.db_name)

        # Convert Django model to dictionary for compatibility with existing code
        sql_db_params = {
            "id": sql_db_obj.id,
            "name": sql_db_obj.name,
            "db_host": sql_db_obj.db_host,
            "db_type": sql_db_obj.db_type,
            "db_name": sql_db_obj.db_name,
            "db_port": sql_db_obj.db_port,
            "schema": sql_db_obj.schema,
            "user_name": sql_db_obj.user_name,
            "password": sql_db_obj.password,
            "db_mode": sql_db_obj.db_mode,
            "language": sql_db_obj.language,
        }

        # Get the associated vector_db
        if sql_db_obj.vector_db:
            vector_db_obj = sql_db_obj.vector_db
            sql_db_params["vector_db"] = {
                "name": vector_db_obj.name,
                "vect_type": vector_db_obj.vect_type,
                "host": vector_db_obj.host,
                "port": vector_db_obj.port,
                "username": vector_db_obj.username,
                "password": vector_db_obj.password,
                "tenant": vector_db_obj.tenant,
            }
        else:
            logging.error(f"No vector database associated with {args.db_name}")
            sys.exit(1)

        # Create the appropriate database manager based on db_type
        if sql_db_params["db_type"] == "PostgreSQL":
            sql_db = ThothPgManager(
                host=sql_db_params["db_host"],
                port=sql_db_params["db_port"],
                schema=sql_db_params["schema"],
                dbname=sql_db_params["db_name"],
                user=sql_db_params["user_name"],
                password=sql_db_params["password"],
                db_root_path=os.getenv("DB_ROOT_PATH"),
                db_mode=sql_db_params["db_mode"],
            )
        elif sql_db_params["db_type"] == "SQLite":
            db_root_path = os.getenv("DB_ROOT_PATH")
            db_mode = sql_db_params["db_mode"]
            db_name = sql_db_params["db_name"]

            # Construct the full path to the database file
            db_directory_path = os.path.join(db_root_path, f"{db_mode}_databases")

            sql_db = ThothSqliteManager(
                db_id=db_name,
                db_root_path=db_directory_path,
                db_mode=db_mode,
            )
        else:
            logging.error(f"Unsupported database type: {sql_db_params['db_type']}")
            sys.exit(1)

        # Get the default setting
        try:
            setting_obj = Setting.objects.get(name="Default")
            setting = {
                "signature_size": setting_obj.signature_size,
                "n_grams": setting_obj.n_grams,
                "threshold": setting_obj.threshold,
                "verbose": setting_obj.verbose,
                "use_value_description": setting_obj.use_value_description,
            }
        except Setting.DoesNotExist:
            logging.error("Default setting not found")
            sys.exit(1)

        # Set up the vector database using VectorStoreFactory
        vector_db_config = get_vectordb_config(sql_db_params)
        try:
            vector_db = VectorStoreFactory.create_vector_store(
                vector_store_type=vector_db_config["vector_db_type"],
                collection_name=vector_db_config.get("collection_name"),
                host=vector_db_config.get("host"),
                port=vector_db_config.get("port"),
            )
        except Exception as e:
            logging.error(f"Failed to create vector store: {e}")
            sys.exit(1)

        # Run the preprocessing
        preprocess(
            sql_db, vector_db, sql_db_params, setting, lsh_root_arg=args.lsh_root
        )
        logging.info("Preprocessing is complete.")

    except SqlDb.DoesNotExist:
        logging.error(f"Database with name '{args.db_name}' not found")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        sys.exit(1)
