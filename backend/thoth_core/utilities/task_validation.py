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

import threading
import logging
from django.utils import timezone
from datetime import timedelta
from thoth_core.models import Workspace

logger = logging.getLogger(__name__)


def validate_and_cleanup_running_task(workspace, task_type="table_comment"):
    """
    Validates if a task marked as RUNNING is actually still running.
    If not, resets the status to IDLE.

    Args:
        workspace: Workspace instance to check
        task_type: Type of task to validate ('table_comment', 'column_comment', 'preprocessing')

    Returns:
        bool: True if task is actually running, False if it was cleaned up
    """

    # Determine which fields to check based on task type
    if task_type == "table_comment":
        status_field = "table_comment_status"
        task_id_field = "table_comment_task_id"
        log_field = "table_comment_log"
        start_time_field = "table_comment_start_time"
        end_time_field = "table_comment_end_time"
    elif task_type == "column_comment":
        status_field = "column_comment_status"
        task_id_field = "column_comment_task_id"
        log_field = "column_comment_log"
        start_time_field = "column_comment_start_time"
        end_time_field = "column_comment_end_time"
    elif task_type == "preprocessing":
        status_field = "preprocessing_status"
        task_id_field = "task_id"
        log_field = "last_preprocess_log"
        start_time_field = "preprocessing_start_time"
        end_time_field = "preprocessing_end_time"
    else:
        raise ValueError(f"Unknown task type: {task_type}")

    current_status = getattr(workspace, status_field)

    # If not running, nothing to validate
    if current_status != Workspace.PreprocessingStatus.RUNNING:
        return False

    task_id = getattr(workspace, task_id_field)
    start_time = getattr(workspace, start_time_field)

    should_reset = False
    reset_reason = ""

    # Check 1: If no task_id, definitely not running
    if not task_id:
        should_reset = True
        reset_reason = "No task ID found for RUNNING status"

    # Check 2: Validate if thread is still active
    elif task_id:
        try:
            # Get all active thread identifiers
            active_thread_ids = [str(t.ident) for t in threading.enumerate() if t.ident]

            if task_id not in active_thread_ids:
                should_reset = True
                reset_reason = f"Task ID {task_id} not found in active threads"
        except Exception as e:
            logger.warning(f"Could not validate thread status for task {task_id}: {e}")
            # Don't reset based on thread validation error alone

    # Check 3: Timeout check (if task has been running too long)
    if start_time and not should_reset:
        # Consider a task stale if it's been running for more than 2 hours
        timeout_hours = 2
        cutoff_time = timezone.now() - timedelta(hours=timeout_hours)

        if start_time < cutoff_time:
            should_reset = True
            reset_reason = f"Task has been running for more than {timeout_hours} hours (started: {start_time})"

    # Perform reset if needed
    if should_reset:
        logger.warning(
            f"Resetting {task_type} status for workspace {workspace.id}: {reset_reason}"
        )

        setattr(workspace, status_field, Workspace.PreprocessingStatus.FAILED)
        setattr(workspace, task_id_field, None)
        setattr(workspace, log_field, f"Task reset automatically: {reset_reason}")
        setattr(workspace, end_time_field, timezone.now())

        try:
            workspace.save()
            logger.info(
                f"Successfully reset {task_type} status for workspace {workspace.id}"
            )
            return False  # Task was not actually running
        except Exception as e:
            logger.error(
                f"Failed to reset {task_type} status for workspace {workspace.id}: {e}"
            )
            return True  # Assume it's still running if we can't reset

    return True  # Task appears to be legitimately running


def check_task_can_start(workspace, task_type="table_comment"):
    """
    Checks if a new task can be started for the given workspace.
    Performs validation and cleanup if necessary.

    Args:
        workspace: Workspace instance to check
        task_type: Type of task to check ('table_comment', 'column_comment', 'preprocessing')

    Returns:
        tuple: (can_start: bool, message: str)
    """

    # Refresh workspace from database to get latest status
    workspace.refresh_from_db()

    # Determine status field based on task type
    if task_type == "table_comment":
        status_field = "table_comment_status"
    elif task_type == "column_comment":
        status_field = "column_comment_status"
    elif task_type == "preprocessing":
        status_field = "preprocessing_status"
    else:
        return False, f"Unknown task type: {task_type}"

    current_status = getattr(workspace, status_field)

    # If status is IDLE, can start immediately
    if current_status == Workspace.PreprocessingStatus.IDLE:
        return True, "Ready to start"

    # If status is COMPLETED or FAILED, can start
    if current_status in [
        Workspace.PreprocessingStatus.COMPLETED,
        Workspace.PreprocessingStatus.FAILED,
    ]:
        return True, "Previous task completed, ready to start new one"

    # If status is RUNNING, validate if it's actually running
    if current_status == Workspace.PreprocessingStatus.RUNNING:
        is_actually_running = validate_and_cleanup_running_task(workspace, task_type)

        if not is_actually_running:
            # Task was cleaned up, refresh and check again
            workspace.refresh_from_db()
            return (
                True,
                "Previous task was stale and has been cleaned up, ready to start",
            )
        else:
            return False, f"A {task_type.replace('_', ' ')} task is currently running"

    return False, f"Unknown status: {current_status}"


def force_reset_task_status(
    workspace, task_type="table_comment", reason="Manual reset"
):
    """
    Forcefully resets a task status regardless of current state.
    Use with caution - this should only be used when you're certain the task is not running.

    Args:
        workspace: Workspace instance to reset
        task_type: Type of task to reset ('table_comment', 'column_comment', 'preprocessing')
        reason: Reason for the reset (for logging)

    Returns:
        bool: True if reset was successful, False otherwise
    """

    # Determine which fields to reset based on task type
    if task_type == "table_comment":
        status_field = "table_comment_status"
        task_id_field = "table_comment_task_id"
        log_field = "table_comment_log"
        end_time_field = "table_comment_end_time"
    elif task_type == "column_comment":
        status_field = "column_comment_status"
        task_id_field = "column_comment_task_id"
        log_field = "column_comment_log"
        end_time_field = "column_comment_end_time"
    elif task_type == "preprocessing":
        status_field = "preprocessing_status"
        task_id_field = "task_id"
        log_field = "last_preprocess_log"
        end_time_field = "preprocessing_end_time"
    else:
        logger.error(f"Unknown task type for force reset: {task_type}")
        return False

    try:
        old_status = getattr(workspace, status_field)
        old_task_id = getattr(workspace, task_id_field)

        setattr(workspace, status_field, Workspace.PreprocessingStatus.IDLE)
        setattr(workspace, task_id_field, None)
        setattr(workspace, log_field, f"Force reset: {reason} (was: {old_status})")
        setattr(workspace, end_time_field, timezone.now())

        workspace.save()

        logger.warning(
            f"Force reset {task_type} for workspace {workspace.id}: {reason} "
            f"(was: {old_status}, task_id: {old_task_id})"
        )

        return True

    except Exception as e:
        logger.error(
            f"Failed to force reset {task_type} for workspace {workspace.id}: {e}"
        )
        return False
