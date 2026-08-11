"""BRIF.AI — Brief Persistence Exceptions."""

from __future__ import annotations


class BriefPersistenceError(Exception):
    """Base exception for brief persistence failures."""


class BriefNotFoundError(BriefPersistenceError):
    """Raised when a brief snapshot or version is not found."""


class BriefVersionConflictError(BriefPersistenceError):
    """Raised when a version conflict or optimistic concurrency check fails."""


class InvalidProjectIdError(BriefPersistenceError):
    """Raised when a project identifier is malformed or attempts path traversal."""
