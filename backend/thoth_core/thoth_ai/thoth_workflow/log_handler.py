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
Custom log handler for capturing async task logs and storing them in database fields.
This module provides a memory-based log handler that accumulates log messages
and can write them to database fields like table_comment_log.
"""

import logging
from typing import List
from django.utils import timezone


class MemoryLogHandler(logging.Handler):
    """
    Custom logging handler that stores log messages in memory
    and can write them to a database field.
    """

    def __init__(self, level=logging.INFO):
        super().__init__(level)
        self.log_messages: List[str] = []
        self.start_time = timezone.now()

        # Set a formatter for consistent log formatting
        formatter = logging.Formatter(
            "[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.setFormatter(formatter)

    def emit(self, record):
        """
        Emit a log record by storing it in memory.
        """
        try:
            msg = self.format(record)
            self.log_messages.append(msg)
        except Exception:
            self.handleError(record)

    def get_logs(self) -> str:
        """
        Get all accumulated log messages as a single string.

        Returns:
            str: All log messages joined with newlines
        """
        return "\n".join(self.log_messages)

    def clear_logs(self):
        """
        Clear all accumulated log messages.
        """
        self.log_messages.clear()

    def add_summary(self, processed: int, failed: int, total: int):
        """
        Add a summary message to the logs.

        Args:
            processed: Number of successfully processed items
            failed: Number of failed items
            total: Total number of items
        """
        end_time = timezone.now()
        duration = end_time - self.start_time

        # Format duration nicely
        total_seconds = int(duration.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60

        if minutes > 0:
            duration_str = f"{minutes}m {seconds}s"
        else:
            duration_str = f"{seconds}s"

        summary = f"Completed: {processed} successful, {failed} failed, Total time: {duration_str}"

        # Use the logger to format the message consistently
        record = logging.LogRecord(
            name=self.name or "async_task",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=summary,
            args=(),
            exc_info=None,
        )
        self.emit(record)


def create_table_comment_logger(
    workspace, base_logger_name: str = "async_table_comments"
) -> tuple[logging.Logger, MemoryLogHandler]:
    """
    Create a logger with a memory handler for table comment generation.

    Args:
        workspace: The workspace object to update with logs
        base_logger_name: Base name for the logger

    Returns:
        tuple: (logger, memory_handler) - The configured logger and its memory handler
    """
    # Create a unique logger name to avoid conflicts
    logger_name = f"{base_logger_name}_{workspace.id}_{timezone.now().timestamp()}"
    logger = logging.getLogger(logger_name)

    # Clear any existing handlers
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    # Create and add the memory handler
    memory_handler = MemoryLogHandler(logging.INFO)
    logger.addHandler(memory_handler)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    return logger, memory_handler


def create_column_comment_logger(
    workspace, base_logger_name: str = "async_column_comments"
) -> tuple[logging.Logger, MemoryLogHandler]:
    """
    Create a logger with a memory handler for column comment generation.

    Args:
        workspace: The workspace object to update with logs
        base_logger_name: Base name for the logger

    Returns:
        tuple: (logger, memory_handler) - The configured logger and its memory handler
    """
    # Create a unique logger name to avoid conflicts
    logger_name = f"{base_logger_name}_{workspace.id}_{timezone.now().timestamp()}"
    logger = logging.getLogger(logger_name)

    # Clear any existing handlers
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    # Create and add the memory handler
    memory_handler = MemoryLogHandler(logging.INFO)
    logger.addHandler(memory_handler)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    return logger, memory_handler


def update_workspace_log(
    workspace, memory_handler: MemoryLogHandler, field_name: str = "table_comment_log"
):
    """
    Update the workspace log field with accumulated log messages.

    Args:
        workspace: The workspace object to update
        memory_handler: The memory handler containing the logs
        field_name: Name of the field to update (default: 'table_comment_log')
    """
    try:
        logs = memory_handler.get_logs()
        setattr(workspace, field_name, logs)
        workspace.save(update_fields=[field_name])
    except Exception as e:
        # Fallback logging in case of database issues
        import logging

        fallback_logger = logging.getLogger("thoth_core.async_tasks")
        fallback_logger.error(f"Failed to update workspace log: {str(e)}")


# --- SqlDb-scoped logging helpers ---
def create_db_comment_logger(sql_db, base_logger_name: str = "async_table_comments") -> tuple[logging.Logger, MemoryLogHandler]:
    """
    Create a logger with a memory handler for tasks scoped to a SqlDb.

    Args:
        sql_db: The SqlDb object to associate with logs
        base_logger_name: Base name for the logger

    Returns:
        tuple: (logger, memory_handler)
    """
    # Create a unique logger name to avoid conflicts
    logger_name = f"{base_logger_name}_db_{sql_db.id}_{timezone.now().timestamp()}"
    logger = logging.getLogger(logger_name)

    # Clear any existing handlers
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    # Create and add the memory handler
    memory_handler = MemoryLogHandler(logging.INFO)
    logger.addHandler(memory_handler)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    return logger, memory_handler


def update_sqldb_log(sql_db, memory_handler: MemoryLogHandler, field_name: str = "table_comment_log"):
    """
    Update the SqlDb log field with accumulated log messages.

    Args:
        sql_db: The SqlDb object to update
        memory_handler: The memory handler containing the logs
        field_name: Name of the field to update (default: 'table_comment_log')
    """
    try:
        logs = memory_handler.get_logs()
        setattr(sql_db, field_name, logs)
        sql_db.save(update_fields=[field_name])
    except Exception as e:
        # Fallback logging in case of database issues
        import logging

        fallback_logger = logging.getLogger("thoth_core.async_tasks")
        fallback_logger.error(f"Failed to update SqlDb log: {str(e)}")
