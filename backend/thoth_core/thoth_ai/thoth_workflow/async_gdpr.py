# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Async wrapper for GDPR compliance scanning.
Runs scan_gdpr_for_db logic in a daemon thread with status tracking on SqlDb.
"""

import logging
import threading
from typing import List
from django.utils import timezone

from thoth_core.models import SqlDb

logger = logging.getLogger(__name__)


def start_async_gdpr_scan(sqldb_ids: List[int], user_id: int = None) -> str:
    """Start async GDPR scan in a separate thread."""
    task_id = f"gdpr_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

    def run_task():
        _process_gdpr_scan(sqldb_ids, task_id, user_id)

    thread = threading.Thread(target=run_task, daemon=True)
    thread.start()
    return task_id


def _process_gdpr_scan(sqldb_ids: List[int], task_id: str, user_id: int = None):
    """Process GDPR scan for given databases."""
    from thoth_core.thoth_ai.thoth_workflow.gdpr_scanner import scan_gdpr_for_db

    for sqldb_id in sqldb_ids:
        sql_db = None
        try:
            sql_db = SqlDb.objects.get(id=sqldb_id)
            sql_db.gdpr_status = "RUNNING"
            sql_db.gdpr_task_id = task_id
            sql_db.gdpr_start_time = timezone.now()
            sql_db.gdpr_end_time = None
            sql_db.save(update_fields=[
                "gdpr_status", "gdpr_task_id", "gdpr_start_time", "gdpr_end_time"
            ])

            scan_gdpr_for_db(sql_db)

            sql_db.gdpr_status = "COMPLETED"
            sql_db.gdpr_end_time = timezone.now()
            sql_db.save(update_fields=["gdpr_status", "gdpr_end_time"])
            logger.info(f"GDPR scan completed for '{sql_db.name}'")

        except Exception as e:
            logger.error(f"GDPR scan failed for DB id={sqldb_id}: {e}")
            try:
                if sql_db:
                    sql_db.gdpr_status = "FAILED"
                    sql_db.gdpr_end_time = timezone.now()
                    sql_db.save(update_fields=["gdpr_status", "gdpr_end_time"])
                else:
                    SqlDb.objects.filter(id=sqldb_id).update(
                        gdpr_status="FAILED", gdpr_end_time=timezone.now()
                    )
            except Exception:
                logger.error(f"Failed to reset gdpr_status for DB id={sqldb_id}")
