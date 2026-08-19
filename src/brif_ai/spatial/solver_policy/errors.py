"""Domain exceptions for BRIF.AI Layout Solver Policy V0."""

from __future__ import annotations

from brif_ai.spatial.errors import SpatialGraphError


class SolverPolicyError(SpatialGraphError):
    """Base exception for all layout solver policy compilation errors."""


class SolverPolicyMissingInputError(SolverPolicyError):
    """Raised when required SchematicLayoutProblem input is missing."""


class SolverPolicySchemaVersionMismatchError(SolverPolicyError):
    """Raised when SchematicLayoutProblem schema_version is incompatible with compiler."""

    def __init__(self, expected_schema: str, actual_schema: str) -> None:
        super().__init__(
            f"Incompatible layout problem schema version: expected {expected_schema!r}, "
            f"got {actual_schema!r}."
        )
        self.expected_schema = expected_schema
        self.actual_schema = actual_schema


class SolverPolicyEndpointError(SolverPolicyError):
    """Raised when a directive or relationship references an unknown space ID."""
