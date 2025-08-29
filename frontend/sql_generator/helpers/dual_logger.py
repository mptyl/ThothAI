# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Dual logging helper: logs a given string message to both the standard app logger
and Logfire at the corresponding level.

Functions provided (one per common level supported by both systems):
- log_debug
- log_info
- log_warning
- log_error
- log_critical
- log_exception

All functions accept a single string message.
"""

from __future__ import annotations

from typing import Callable

import logfire

from .logging_config import app_logger as logger


def _call_if_available(func: Callable[..., None] | None, message: str) -> None:
    if func is not None:
        func(message)  # type: ignore[misc]


def log_debug(message: str) -> None:
    """Log at DEBUG level to both logger and logfire."""
    logger.debug(message)
    _call_if_available(getattr(logfire, "debug", None), message)


def log_info(message: str) -> None:
    """Log at INFO level to both logger and logfire."""
    logger.info(message)
    _call_if_available(getattr(logfire, "info", None), message)


def log_warning(message: str) -> None:
    """Log at WARNING level to both logger and logfire."""
    logger.warning(message)
    _call_if_available(getattr(logfire, "warning", None), message)


def log_error(message: str) -> None:
    """Log at ERROR level to both logger and logfire."""
    logger.error(message)
    _call_if_available(getattr(logfire, "error", None), message)


def log_critical(message: str) -> None:
    """Log at CRITICAL level to both logger and logfire."""
    logger.critical(message)
    _call_if_available(getattr(logfire, "critical", None), message)


def log_exception(message: str) -> None:
    """Log an exception (with traceback) to both logger and logfire.

    Should be called within an exception handler context.
    """
    logger.exception(message)
    # Prefer logfire.exception if available; otherwise fall back to error
    lf_exc = getattr(logfire, "exception", None)
    if lf_exc is not None:
        lf_exc(message)
    else:
        _call_if_available(getattr(logfire, "error", None), message)


