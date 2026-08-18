"""Errors for Spatial Relationship Graph persistence."""

from __future__ import annotations


class SpatialGraphPersistenceError(Exception):
    """Base error for spatial relationship graph persistence operations."""


class SpatialGraphNotFoundError(SpatialGraphPersistenceError):
    """Raised when a spatial relationship graph for a project is not found."""


class SpatialGraphVersionConflictError(SpatialGraphPersistenceError):
    """Raised when attempting to overwrite an immutable version file with different content."""
