"""Domain exceptions for BRIF.AI Schematic Layout Problem V0."""

from __future__ import annotations

from brif_ai.spatial.errors import SpatialGraphError


class LayoutProblemError(SpatialGraphError):
    """Base exception for all schematic layout problem compilation errors."""


class LayoutProblemMissingInputError(LayoutProblemError):
    """Raised when required SpatialProgram input is missing."""


class LayoutProblemSchemaVersionMismatchError(LayoutProblemError):
    """Raised when SpatialProgram schema_version is incompatible with layout problem compiler."""

    def __init__(self, expected_schema: str, actual_schema: str) -> None:
        super().__init__(
            f"Incompatible program schema version: expected {expected_schema!r}, "
            f"got {actual_schema!r}."
        )
        self.expected_schema = expected_schema
        self.actual_schema = actual_schema


class LayoutProblemAuthoritativeMismatchError(LayoutProblemError):
    """Raised when authoritative_relationship_ids contains invalid or unconfirmed relationships."""


class LayoutProblemEndpointError(LayoutProblemError):
    """Raised when a relationship or constraint references an unknown space ID."""
