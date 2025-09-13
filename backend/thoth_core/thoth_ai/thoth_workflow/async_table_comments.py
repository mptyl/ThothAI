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
Async task functions for generating AI comments for tables.
This module provides background processing capabilities to prevent timeouts
when generating comments for large datasets.
"""

import logging
import threading
from typing import List, Dict, Any
from django.utils import timezone

from thoth_core.models import SqlTable, SqlDb
from thoth_core.thoth_ai.thoth_workflow.create_table_comments import (
    create_table_comments_async,
)
from thoth_core.thoth_ai.thoth_workflow.create_column_comments import (
    create_selected_column_comments_async,
)
from thoth_core.thoth_ai.thoth_workflow.log_handler import (
    create_db_comment_logger,
    update_sqldb_log,
)

logger = logging.getLogger(__name__)


class AsyncTableCommentTask:
    """Handles async processing of table comments generation."""

    @staticmethod
    def process_table_comments(
        workspace_id: int, table_ids: List[int], user_id: int = None
    ) -> Dict[str, Any]:
        """
        Async task to generate comments for specified tables.

        Args:
            workspace_id: ID of the workspace
            table_ids: List of table IDs to process
            user_id: ID of the user who initiated the task

        Returns:
            Dict with task results and status
        """
        # Group incoming table IDs by SqlDb
        try:
            tables = SqlTable.objects.filter(id__in=table_ids).select_related("sql_db")
            by_db: Dict[int, Dict[str, Any]] = {}
            for t in tables:
                if not t.sql_db:
                    continue
                by_db.setdefault(t.sql_db.id, {"db": t.sql_db, "table_ids": []})
                by_db[t.sql_db.id]["table_ids"].append(t.id)

            total_processed = 0
            total_failed = 0

            for db_id, payload in by_db.items():
                sql_db: SqlDb = payload["db"]
                db_table_ids: List[int] = payload["table_ids"]

                # Initialize DB-scoped status and log
                sql_db.table_comment_status = "RUNNING"
                sql_db.table_comment_task_id = f"table_comments_db_{sql_db.id}_{timezone.now().timestamp()}"
                sql_db.table_comment_start_time = timezone.now()
                sql_db.table_comment_log = ""
                sql_db.save(update_fields=[
                    "table_comment_status",
                    "table_comment_task_id",
                    "table_comment_start_time",
                    "table_comment_log",
                ])

                # Logger for this DB
                custom_logger, memory_handler = create_db_comment_logger(sql_db)
                custom_logger.info(
                    f"Starting async table comment generation for DB '{sql_db.name}' with {len(db_table_ids)} table(s)"
                )

                # Process tables in chunks
                chunk_size = 10
                processed_count = 0
                failed_count = 0
                for i in range(0, len(db_table_ids), chunk_size):
                    chunk = db_table_ids[i : i + chunk_size]
                    chunk_start = i + 1
                    chunk_end = min(i + chunk_size, len(db_table_ids))

                    custom_logger.info(
                        f"Processing chunk {chunk_start}-{chunk_end} of {len(db_table_ids)} tables"
                    )

                    try:
                        # Use env-based async function; ignore workspace_id
                        results = create_table_comments_async(chunk, None, custom_logger)
                        processed_count += results.get("processed", 0)
                        failed_count += results.get("failed", 0)

                        for error in results.get("errors", []):
                            custom_logger.error(f"Error in chunk {chunk_start}-{chunk_end}: {error}")

                        update_sqldb_log(sql_db, memory_handler, "table_comment_log")

                        custom_logger.info(
                            f"Chunk {chunk_start}-{chunk_end} completed: {results.get('processed',0)} processed, {results.get('failed',0)} failed"
                        )
                    except Exception as e:
                        custom_logger.error(
                            f"Error processing table chunk {chunk_start}-{chunk_end}: {str(e)}"
                        )
                        failed_count += len(chunk)
                        update_sqldb_log(sql_db, memory_handler, "table_comment_log")

                # Add summary and finalize per-DB
                memory_handler.add_summary(processed_count, failed_count, len(db_table_ids))
                sql_db.table_comment_end_time = timezone.now()
                sql_db.table_comment_status = "COMPLETED" if failed_count == 0 else "FAILED"
                update_sqldb_log(sql_db, memory_handler, "table_comment_log")
                sql_db.save(update_fields=[
                    "table_comment_status",
                    "table_comment_end_time",
                    "table_comment_log",
                ])

                total_processed += processed_count
                total_failed += failed_count

            logger.info(
                f"Table comments generation completed across DBs: {total_processed} processed, {total_failed} failed"
            )

            return {
                "status": "success",
                "processed": total_processed,
                "failed": total_failed,
                "total": len(table_ids),
            }
        except Exception as e:
            logger.error(f"Critical error in async table comments: {str(e)}")
            return {"status": "error", "error": str(e), "processed": 0, "failed": len(table_ids) if table_ids else 0}


class AsyncColumnCommentTask:
    """Handles async processing of column comments generation."""

    @staticmethod
    def process_column_comments(
        workspace_id: int, column_ids: List[int], user_id: int = None
    ) -> Dict[str, Any]:
        """
        Async task to generate comments for specified columns.

        Args:
            workspace_id: ID of the workspace
            column_ids: List of column IDs to process
            user_id: ID of the user who initiated the task

        Returns:
            Dict with task results and status
        """
        # Group incoming column IDs by SqlDb (via their tables)
        try:
            columns = (
                SqlTable.objects.none()  # placeholder to keep type hints happy
            )
            # Fetch columns with their tables and dbs
            from thoth_core.models import SqlColumn as _SqlColumn

            col_qs = _SqlColumn.objects.filter(id__in=column_ids).select_related(
                "sql_table", "sql_table__sql_db"
            )
            by_db: Dict[int, Dict[str, Any]] = {}
            for c in col_qs:
                table = c.sql_table
                if not table or not table.sql_db:
                    continue
                db_id = table.sql_db.id
                if db_id not in by_db:
                    by_db[db_id] = {"db": table.sql_db, "column_ids": []}
                by_db[db_id]["column_ids"].append(c.id)

            total_processed = 0
            total_failed = 0

            for db_id, payload in by_db.items():
                sql_db: SqlDb = payload["db"]
                db_column_ids: List[int] = payload["column_ids"]

                # Initialize DB-scoped status and log
                sql_db.column_comment_status = "RUNNING"
                sql_db.column_comment_task_id = f"column_comments_db_{sql_db.id}_{timezone.now().timestamp()}"
                sql_db.column_comment_start_time = timezone.now()
                sql_db.column_comment_log = ""
                sql_db.save(update_fields=[
                    "column_comment_status",
                    "column_comment_task_id",
                    "column_comment_start_time",
                    "column_comment_log",
                ])

                # Logger for this DB
                custom_logger, memory_handler = create_db_comment_logger(
                    sql_db, base_logger_name="async_column_comments"
                )
                custom_logger.info(
                    f"Starting async column comment generation for DB '{sql_db.name}' with {len(db_column_ids)} column(s)"
                )

                try:
                    results = create_selected_column_comments_async(
                        db_column_ids, None, custom_logger
                    )
                    processed_count = results.get("processed", 0)
                    failed_count = results.get("failed", 0)

                    for detail in results.get("details", []):
                        if detail.get("status") == "success":
                            custom_logger.info(
                                f"✓ Successfully processed column: {detail.get('column')}"
                            )
                        else:
                            custom_logger.error(
                                f"✗ Failed to process column: {detail.get('column')} - {detail.get('message')}"
                            )

                    for error in results.get("errors", []):
                        custom_logger.error(f"Error during processing: {error}")

                    update_sqldb_log(sql_db, memory_handler, "column_comment_log")

                except Exception as e:
                    custom_logger.error(
                        f"Error during column comment generation: {str(e)}"
                    )
                    processed_count = 0
                    failed_count = len(db_column_ids)
                    update_sqldb_log(sql_db, memory_handler, "column_comment_log")

                # Add summary and finalize per-DB
                memory_handler.add_summary(processed_count, failed_count, len(db_column_ids))
                sql_db.column_comment_end_time = timezone.now()
                sql_db.column_comment_status = "COMPLETED" if failed_count == 0 else "FAILED"
                update_sqldb_log(sql_db, memory_handler, "column_comment_log")
                sql_db.save(update_fields=[
                    "column_comment_status",
                    "column_comment_end_time",
                    "column_comment_log",
                ])

                total_processed += processed_count
                total_failed += failed_count

            logger.info(
                f"Column comments generation completed across DBs: {total_processed} processed, {total_failed} failed"
            )

            return {
                "status": "success",
                "processed": total_processed,
                "failed": total_failed,
                "total": len(column_ids),
            }
        except Exception as e:
            logger.error(f"Critical error in async column comments: {str(e)}")
            return {"status": "error", "error": str(e), "processed": 0, "failed": len(column_ids) if column_ids else 0}


def start_async_table_comments(
    workspace_id: int, table_ids: List[int], user_id: int = None
) -> str:
    """
    Start async table comments generation in a separate thread.

    Args:
        workspace_id: ID of the workspace
        table_ids: List of table IDs to process
        user_id: ID of the user who initiated the task

    Returns:
        Task ID for tracking
    """

    def run_task():
        AsyncTableCommentTask.process_table_comments(workspace_id, table_ids, user_id)

    thread = threading.Thread(target=run_task)
    thread.daemon = True
    thread.start()

    return f"table_comments_{workspace_id}_{timezone.now().timestamp()}"


def start_async_column_comments(
    workspace_id: int, column_ids: List[int], user_id: int = None
) -> str:
    """
    Start async column comments generation in a separate thread.

    Args:
        workspace_id: ID of the workspace
        column_ids: List of column IDs to process
        user_id: ID of the user who initiated the task

    Returns:
        Task ID for tracking
    """

    def run_task():
        AsyncColumnCommentTask.process_column_comments(
            workspace_id, column_ids, user_id
        )

    thread = threading.Thread(target=run_task)
    thread.daemon = True
    thread.start()

    return f"column_comments_{workspace_id}_{timezone.now().timestamp()}"
