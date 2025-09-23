"""Minimal fastuuid shim.

This module mirrors the tiny interface that litellm expects from the upstream
`fastuuid` package while delegating to Python's standard `uuid` library.
"""
from uuid import (
    NAMESPACE_DNS,
    NAMESPACE_OID,
    NAMESPACE_URL,
    NAMESPACE_X500,
    UUID,
    SafeUUID,
    UUID as UUIDType,
    getnode,
    uuid1,
    uuid3,
    uuid4,
    uuid5,
)

try:  # Python 3.11+
    from uuid import uuid7  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - older runtimes
    uuid7 = None  # type: ignore[assignment]

__all__ = [
    "UUID",
    "UUIDType",
    "SafeUUID",
    "NAMESPACE_DNS",
    "NAMESPACE_OID",
    "NAMESPACE_URL",
    "NAMESPACE_X500",
    "getnode",
    "uuid1",
    "uuid3",
    "uuid4",
    "uuid5",
    "uuid7",
]
