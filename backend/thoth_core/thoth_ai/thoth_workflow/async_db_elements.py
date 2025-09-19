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

"""
Async task functions for creating database elements (tables, columns, relationships).
This module provides background processing capabilities to prevent timeouts
when processing large databases, using simple logging to console and file.
"""

import logging
import threading
from typing import List, Dict, Any
from django.utils import timezone

from thoth_core.models import SqlDb, SqlTable, SqlColumn, Relationship
from thoth_core.dbmanagement import (
    get_table_names_and_comments,
    create_sql_tables,
    get_column_names_and_comments,
    create_sql_columns,
    get_db_manager,
)
from thoth_core.thoth_ai.thoth_workflow.simple_logger import get_db_elements_logger

logger = logging.getLogger(__name__)


class AsyncDbElementsTask:
    """Handles async processing of database elements creation with simple logging."""

    @staticmethod
    def process_db_elements(
        workspace_id: int, sqldb_ids: List[int], user_id: int = None
    ) -> Dict[str, Any]:
        """
        Async task to create tables, columns, and relationships for specified databases.
        Uses simple logging to console and file only.
        """
        try:
            total_databases = len(sqldb_ids)
            total_success = 0
            total_failed = 0
            failed_databases = []

            for sqldb_id in sqldb_ids:
                try:
                    sql_db = SqlDb.objects.get(id=sqldb_id)
                    
                    # Initialize DB-scoped status (no log field)
                    sql_db.db_elements_status = "RUNNING"
                    sql_db.db_elements_task_id = f"db_elements_db_{sql_db.id}_{timezone.now().timestamp()}"
                    sql_db.db_elements_start_time = timezone.now()
                    sql_db.db_elements_end_time = None
                    sql_db.save(update_fields=[
                        "db_elements_status", "db_elements_task_id", 
                        "db_elements_start_time", "db_elements_end_time"
                    ])

                    # Get simple logger
                    task_logger = get_db_elements_logger(sql_db.id, workspace_id)
                    
                    task_logger.info(f"Starting database elements creation for DB '{sql_db.name}' (ID: {sql_db.id})")
                    task_logger.info(f"Workspace ID: {workspace_id}, User ID: {user_id}")

                    # Step 1: Create tables
                    task_logger.info("Step 1: Creating tables")
                    try:
                        table_info = get_table_names_and_comments(sql_db)
                        if not table_info:
                            raise Exception("Failed to retrieve table information")

                        created_tables, skipped_tables = create_sql_tables(sql_db, table_info)
                        
                        task_logger.info(f"Tables created: {len(created_tables)}")
                        task_logger.info(f"Tables skipped: {len(skipped_tables)}")
                        
                        for table, comment in created_tables:
                            task_logger.info(f"  - Created table: {table} (Comment: {comment or 'None'})")
                            
                    except Exception as e:
                        task_logger.error(f"Error creating tables: {str(e)}")
                        raise Exception(f"Error creating tables: {str(e)}")

                    # Step 2: Create columns for each table
                    task_logger.info("Step 2: Creating columns for each table")
                    tables_processed = 0
                    tables_failed = 0
                    
                    all_tables = list(SqlTable.objects.filter(sql_db=sql_db))
                    total_tables = len(all_tables)
                    
                    for i, sql_table in enumerate(all_tables):
                        try:
                            task_logger.info(f"Processing table {i+1}/{total_tables}: {sql_table.name}")
                            column_info = get_column_names_and_comments(sql_db, sql_table.name)
                            if not column_info:
                                task_logger.warning(f"No columns found for table {sql_table.name}")
                                continue

                            created_columns, skipped_columns = create_sql_columns(
                                sql_table, column_info
                            )
                            tables_processed += 1
                            
                            task_logger.info(
                                f"  Columns created: {len(created_columns)}, "
                                f"skipped: {len(skipped_columns)}"
                            )
                            
                            # Log some sample columns
                            for j, (col, dtype, comment) in enumerate(created_columns[:3]):
                                task_logger.info(f"    - Column {j+1}: {col} ({dtype})")
                            if len(created_columns) > 3:
                                task_logger.info(f"    ... and {len(created_columns) - 3} more columns")
                                
                        except Exception as e:
                            task_logger.error(f"Error processing table {sql_table.name}: {str(e)}")
                            tables_failed += 1

                    task_logger.info(f"Tables processing completed: {tables_processed} successful, {tables_failed} failed")

                    # Step 3: Create foreign key relationships
                    task_logger.info("Step 3: Creating foreign key relationships")
                    try:
                        db_manager = get_db_manager(sql_db)
                        adapter = getattr(db_manager, "adapter", None)
                        if adapter and hasattr(adapter, "get_foreign_keys_as_documents"):
                            fk_docs = adapter.get_foreign_keys_as_documents()
                            relationships_info = [
                                {
                                    "source_table_name": d.source_table_name,
                                    "source_column_name": d.source_column_name,
                                    "target_table_name": d.target_table_name,
                                    "target_column_name": d.target_column_name,
                                }
                                for d in fk_docs
                            ]
                        else:
                            relationships_info = db_manager.get_foreign_keys()

                        # Limit to relationships whose tables exist in our catalog
                        existing_tables = set(
                            SqlTable.objects.filter(sql_db=sql_db).values_list("name", flat=True)
                        )
                        relationships_info = [
                            r
                            for r in relationships_info
                            if r.get("source_table_name") in existing_tables
                            and r.get("target_table_name") in existing_tables
                        ]

                        relationships_created = 0
                        for rel_data in relationships_info:
                            source_table_name = rel_data["source_table_name"]
                            source_column_name = rel_data["source_column_name"]
                            target_table_name = rel_data["target_table_name"]
                            target_column_name = rel_data["target_column_name"]

                            try:
                                source_table = SqlTable.objects.get(
                                    name=source_table_name, sql_db=sql_db
                                )
                                target_table = SqlTable.objects.get(
                                    name=target_table_name, sql_db=sql_db
                                )
                                
                                # Ensure columns exist; create on-the-fly if missing
                                try:
                                    source_column = SqlColumn.objects.get(
                                        original_column_name=source_column_name,
                                        sql_table=source_table,
                                    )
                                except SqlColumn.DoesNotExist:
                                    try:
                                        col_info = get_column_names_and_comments(
                                            sql_db, source_table.name
                                        )
                                        create_sql_columns(source_table, col_info)
                                        source_column = SqlColumn.objects.get(
                                            original_column_name=source_column_name,
                                            sql_table=source_table,
                                        )
                                    except Exception:
                                        raise
                                try:
                                    target_column = SqlColumn.objects.get(
                                        original_column_name=target_column_name,
                                        sql_table=target_table,
                                    )
                                except SqlColumn.DoesNotExist:
                                    try:
                                        col_info = get_column_names_and_comments(
                                            sql_db, target_table.name
                                        )
                                        create_sql_columns(target_table, col_info)
                                        target_column = SqlColumn.objects.get(
                                            original_column_name=target_column_name,
                                            sql_table=target_table,
                                        )
                                    except Exception:
                                        raise

                                relationship, created = Relationship.objects.get_or_create(
                                    source_table=source_table,
                                    target_table=target_table,
                                    source_column=source_column,
                                    target_column=target_column,
                                )
                                if created:
                                    relationships_created += 1
                                    task_logger.info(
                                        f"  Created relationship: "
                                        f"{source_table_name}.{source_column_name} -> "
                                        f"{target_table_name}.{target_column_name}"
                                    )
                            except Exception as e:
                                task_logger.warning(f"Error creating relationship: {str(e)}")

                        Relationship.update_pk_fk_fields()
                        task_logger.info(f"Relationships created: {relationships_created}")
                        
                    except Exception as e:
                        task_logger.error(f"Error creating relationships: {str(e)}")
                        raise Exception(f"Error creating relationships: {str(e)}")

                    # Finalize task
                    sql_db.db_elements_end_time = timezone.now()
                    sql_db.db_elements_status = "COMPLETED"
                    sql_db.save(update_fields=[
                        "db_elements_status", "db_elements_end_time"
                    ])
                    
                    task_logger.info(
                        f"Successfully processed database '{sql_db.name}': "
                        f"{len(created_tables)} tables, {tables_processed} tables with columns, "
                        f"{relationships_created} relationships"
                    )
                    
                    total_success += 1

                except Exception as e:
                    error_msg = f"Failed to process database '{sql_db.name}': {str(e)}"
                    task_logger.error(error_msg)
                    
                    # Update status to failed
                    sql_db.db_elements_end_time = timezone.now()
                    sql_db.db_elements_status = "FAILED"
                    sql_db.save(update_fields=[
                        "db_elements_status", "db_elements_end_time"
                    ])
                    
                    failed_databases.append((sql_db.name, str(e)))
                    total_failed += 1

            logger.info(
                f"Database elements creation completed: {total_success} successes, "
                f"{total_failed} failures out of {total_databases} databases"
            )

            return {
                "status": "success",
                "processed": total_success,
                "failed": total_failed,
                "total": total_databases,
                "failed_databases": failed_databases,
            }
            
        except Exception as e:
            logger.error(f"Critical error in async database elements creation: {str(e)}")
            return {
                "status": "error", 
                "error": str(e), 
                "processed": 0, 
                "failed": len(sqldb_ids) if sqldb_ids else 0
            }


def start_async_db_elements_creation(
    workspace_id: int, sqldb_ids: List[int], user_id: int = None
) -> str:
    """
    Start async database elements creation in a separate thread.

    Args:
        workspace_id: ID of the workspace
        sqldb_ids: List of SqlDb IDs to process
        user_id: ID of the user who initiated the task

    Returns:
        Task ID for tracking
    """

    def run_task():
        AsyncDbElementsTask.process_db_elements(workspace_id, sqldb_ids, user_id)

    thread = threading.Thread(target=run_task)
    thread.daemon = True
    thread.start()

    return f"db_elements_{workspace_id}_{timezone.now().timestamp()}"