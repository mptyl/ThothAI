# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Async wrapper for database ERD generation.
Runs generate_erd_for_db logic in a daemon thread with status tracking on SqlDb.
"""

import logging
import threading
from typing import List
from django.utils import timezone

from thoth_core.models import SqlDb

logger = logging.getLogger(__name__)


def start_async_erd_generation(sqldb_ids: List[int], user_id: int = None) -> str:
    """Start async ERD generation in a separate thread."""
    task_id = f"erd_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

    def run_task():
        _process_erd_generation(sqldb_ids, task_id, user_id)

    thread = threading.Thread(target=run_task, daemon=True)
    thread.start()
    return task_id


def _process_erd_generation(sqldb_ids: List[int], task_id: str, user_id: int = None):
    """Process ERD generation for given databases."""
    from thoth_core.thoth_ai.thoth_workflow.generate_db_erd import generate_erd_for_db

    for sqldb_id in sqldb_ids:
        sql_db = None
        try:
            sql_db = SqlDb.objects.get(id=sqldb_id)
            sql_db.erd_status = "RUNNING"
            sql_db.erd_task_id = task_id
            sql_db.erd_start_time = timezone.now()
            sql_db.erd_end_time = None
            sql_db.save(update_fields=[
                "erd_status", "erd_task_id", "erd_start_time", "erd_end_time"
            ])

            generate_erd_for_db(sql_db)

            sql_db.erd_status = "COMPLETED"
            sql_db.erd_end_time = timezone.now()
            sql_db.save(update_fields=["erd_status", "erd_end_time"])
            logger.info(f"ERD generation completed for '{sql_db.name}'")

        except Exception as e:
            logger.error(f"ERD generation failed for DB id={sqldb_id}: {e}")
            try:
                if sql_db:
                    sql_db.erd_status = "FAILED"
                    sql_db.erd_end_time = timezone.now()
                    sql_db.save(update_fields=["erd_status", "erd_end_time"])
                else:
                    SqlDb.objects.filter(id=sqldb_id).update(
                        erd_status="FAILED", erd_end_time=timezone.now()
                    )
            except Exception:
                logger.error(f"Failed to reset erd_status for DB id={sqldb_id}")
