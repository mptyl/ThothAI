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

import logging
import os
from django.utils import timezone
from thoth_core.models import Workspace
from .preprocessing.preprocess import preprocess

# New plugin-based imports
from thoth_dbmanager import ThothDbFactory

# Import new vector store plugin architecture
from thoth_qdrant import VectorStoreFactory
from thoth_qdrant import ThothType
from .backend_utils.vectordb_config_utils import get_vectordb_config

logger = logging.getLogger(__name__)


def run_preprocessing_task(workspace_id):
    """
    The actual preprocessing function that will be run in a background thread.
    """
    try:
        workspace = Workspace.objects.get(id=workspace_id)

        # Set status to RUNNING
        workspace.preprocessing_status = Workspace.PreprocessingStatus.RUNNING
        workspace.last_preprocess_log = "Preprocessing started..."
        workspace.save()

        sql_db_obj = workspace.sql_db
        if not sql_db_obj:
            raise ValueError(f"No database associated with workspace: {workspace.name}")

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
            "db_mode": str(sql_db_obj.db_mode),
            "language": sql_db_obj.language,
        }

        if not sql_db_obj.vector_db:
            raise ValueError(f"No vector database associated with {sql_db_obj.name}")

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

        # Use the new ThothDbFactory to create database manager
        db_type_mapping = {
            "PostgreSQL": "postgresql",
            "SQLite": "sqlite",
            "MySQL": "mysql",
            "MariaDB": "mariadb",
            "SQLServer": "sqlserver",
            "Oracle": "oracle",
        }

        plugin_db_type = db_type_mapping.get(sql_db_params["db_type"])
        if not plugin_db_type:
            raise ValueError(f"Unsupported database type: {sql_db_params['db_type']}")

        # Prepare connection parameters
        connection_params = {}
        if plugin_db_type == "sqlite":
            # SQLite uses database_path instead of separate host/port/database
            # Construct path following the same pattern as other database plugins: db_root_path/db_mode_databases/db_name/db_name.sqlite
            db_root_path = os.getenv("DB_ROOT_PATH", "data")
            sqlite_dir = os.path.join(
                db_root_path,
                f"{sql_db_params['db_mode']}_databases",
                sql_db_params["db_name"],
            )
            connection_params["database_path"] = os.path.join(
                sqlite_dir, f"{sql_db_params['db_name']}.sqlite"
            )
        else:
            connection_params.update(
                {
                    "host": sql_db_params["db_host"],
                    "port": sql_db_params["db_port"],
                    "database": sql_db_params["db_name"],
                    "user": sql_db_params["user_name"],
                    "password": sql_db_params["password"],
                }
            )
            if sql_db_params.get("schema"):
                connection_params["schema"] = sql_db_params["schema"]

        # Create manager using new factory
        sql_db = ThothDbFactory.create_manager(
            db_type=plugin_db_type,
            db_root_path=os.getenv("DB_ROOT_PATH", "data"),
            db_mode=str(sql_db_params["db_mode"]),
            **connection_params,
        )

        if not workspace.setting:
            raise ValueError(f"No settings configured for workspace: {workspace.name}")

        setting_obj = workspace.setting
        setting = {
            "signature_size": setting_obj.signature_size,
            "n_grams": setting_obj.n_grams,
            "threshold": setting_obj.threshold,
            "verbose": setting_obj.verbose,
            "use_value_description": setting_obj.use_value_description,
        }

        # Use new VectorStoreFactory to create vector store
        vector_db_config = get_vectordb_config(sql_db_params)

        # Map vector database types to plugin identifiers
        vector_backend_mapping = {
            "Qdrant": "qdrant",
            "Chroma": "chroma",
            "PGVector": "pgvector",
            "Milvus": "milvus",
        }

        backend = vector_backend_mapping.get(vector_db_config["vector_db_type"])
        if not backend:
            raise ValueError(
                f"Unsupported vector database type: {vector_db_config['vector_db_type']}"
            )

        # Prepare vector store parameters
        vector_params = {"collection": vector_db_config.get("collection_name")}

        if backend == "qdrant":
            vector_params.update(
                {
                    "host": vector_db_config["host"],
                    "port": vector_db_config["port"],
                }
            )

        # Create vector store using factory
        vector_db = VectorStoreFactory.create(backend, **vector_params)

        # Delete existing collections before preprocessing to avoid conflicts
        try:
            if hasattr(vector_db, "delete_collection"):
                # Delete all collection types that will be recreated during preprocessing
                vector_db.delete_collection(thoth_type=ThothType.COLUMN_NAME)
                logger.info("Deleted existing COLUMN_NAME collection for preprocessing")
        except Exception as e:
            logger.warning(f"Could not delete existing COLUMN_NAME collection: {e}")

        # Run the actual preprocessing with workspace_id for progress tracking
        preprocess(sql_db, vector_db, sql_db_params, setting, workspace_id=workspace_id)

        # If successful, update status and timestamp
        workspace.preprocessing_status = Workspace.PreprocessingStatus.COMPLETED
        workspace.last_preprocess = timezone.now()
        workspace.last_preprocess_log = "Preprocessing completed successfully."
        workspace.task_id = None  # Clear task ID
        workspace.save()
        logger.info(f"Preprocessing completed for workspace {workspace_id}")

    except Exception as e:
        logger.error(
            f"Error during background preprocessing for workspace {workspace_id}: {e}",
            exc_info=True,
        )
        # Update status to FAILED and save the error message
        if "workspace" in locals():
            workspace.preprocessing_status = Workspace.PreprocessingStatus.FAILED
            workspace.last_preprocess_log = f"Error during preprocessing: {e}"
            workspace.task_id = None  # Clear task ID
            workspace.save()
