# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Async wrapper for database documentation generation.
Runs generate_documentation_for_db logic in a daemon thread with status tracking on SqlDb.
"""

import logging
import threading
from typing import List
from django.utils import timezone

from thoth_core.models import SqlDb
from thoth_core.thoth_ai.thoth_workflow.log_handler import create_db_comment_logger, update_sqldb_log

logger = logging.getLogger(__name__)


def start_async_documentation_generation(sqldb_ids: List[int], user_id: int = None) -> str:
    """Start async documentation generation in a separate thread."""
    task_id = f"documentation_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

    def run_task():
        _process_documentation_generation(sqldb_ids, task_id, user_id)

    thread = threading.Thread(target=run_task, daemon=True)
    thread.start()
    return task_id


def _process_documentation_generation(sqldb_ids: List[int], task_id: str, user_id: int = None):
    """Process documentation generation for given databases."""
    from thoth_core.thoth_ai.thoth_workflow.generate_db_documentation import generate_documentation_for_db

    for sqldb_id in sqldb_ids:
        sql_db = None
        try:
            sql_db = SqlDb.objects.get(id=sqldb_id)

            custom_logger, memory_handler = create_db_comment_logger(sql_db, "async_documentation")
            custom_logger.info(f"Starting documentation generation for DB '{sql_db.name}'...")

            sql_db.documentation_status = "RUNNING"
            sql_db.documentation_task_id = task_id
            sql_db.documentation_start_time = timezone.now()
            sql_db.documentation_end_time = None
            sql_db.documentation_log = None
            sql_db.save(update_fields=[
                "documentation_status", "documentation_task_id", "documentation_start_time", "documentation_end_time", "documentation_log"
            ])

            update_sqldb_log(sql_db, memory_handler, "documentation_log")

            generate_documentation_for_db(sql_db)

            custom_logger.info(f"Documentation generation completed successfully for DB '{sql_db.name}'.")
            sql_db.documentation_status = "COMPLETED"
            sql_db.documentation_end_time = timezone.now()
            update_sqldb_log(sql_db, memory_handler, "documentation_log")
            sql_db.save(update_fields=["documentation_status", "documentation_end_time", "documentation_log"])

        except Exception as e:
            logger.error(f"Documentation generation failed for DB id={sqldb_id}: {e}")
            try:
                if sql_db:
                    if 'custom_logger' in dir():
                        custom_logger.error(f"Documentation generation failed: {e}")
                        update_sqldb_log(sql_db, memory_handler, "documentation_log")
                    sql_db.documentation_status = "FAILED"
                    sql_db.documentation_end_time = timezone.now()
                    sql_db.save(update_fields=["documentation_status", "documentation_end_time", "documentation_log"])
                else:
                    SqlDb.objects.filter(id=sqldb_id).update(
                        documentation_status="FAILED", documentation_end_time=timezone.now()
                    )
            except Exception:
                logger.error(f"Failed to reset documentation_status for DB id={sqldb_id}")
