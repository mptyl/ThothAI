# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Async wrapper for database scope generation.
Runs generate_scope logic in a daemon thread with status tracking on SqlDb.
"""

import logging
import threading
from typing import List
from django.utils import timezone

from thoth_core.models import SqlDb

logger = logging.getLogger(__name__)


def start_async_scope_generation(sqldb_ids: List[int], user_id: int = None) -> str:
    """Start async scope generation in a separate thread."""
    task_id = f"scope_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

    def run_task():
        _process_scope_generation(sqldb_ids, task_id, user_id)

    thread = threading.Thread(target=run_task, daemon=True)
    thread.start()
    return task_id


def _process_scope_generation(sqldb_ids: List[int], task_id: str, user_id: int = None):
    """Process scope generation for given databases."""
    from thoth_core.thoth_ai.thoth_workflow.create_db_scope import generate_scope_for_db

    for sqldb_id in sqldb_ids:
        sql_db = None
        try:
            sql_db = SqlDb.objects.get(id=sqldb_id)
            sql_db.scope_status = "RUNNING"
            sql_db.scope_task_id = task_id
            sql_db.scope_start_time = timezone.now()
            sql_db.scope_end_time = None
            sql_db.save(update_fields=[
                "scope_status", "scope_task_id", "scope_start_time", "scope_end_time"
            ])

            generate_scope_for_db(sql_db)

            sql_db.scope_status = "COMPLETED"
            sql_db.scope_end_time = timezone.now()
            sql_db.save(update_fields=["scope_status", "scope_end_time"])
            logger.info(f"Scope generation completed for '{sql_db.name}'")

        except Exception as e:
            logger.error(f"Scope generation failed for DB id={sqldb_id}: {e}")
            try:
                if sql_db:
                    sql_db.scope_status = "FAILED"
                    sql_db.scope_end_time = timezone.now()
                    sql_db.save(update_fields=["scope_status", "scope_end_time"])
                else:
                    SqlDb.objects.filter(id=sqldb_id).update(
                        scope_status="FAILED", scope_end_time=timezone.now()
                    )
            except Exception:
                logger.error(f"Failed to reset scope_status for DB id={sqldb_id}")
