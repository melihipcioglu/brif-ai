"""Domain exceptions for BRIF.AI Metric Spatial Requirements V0."""

from __future__ import annotations

from brif_ai.spatial.errors import SpatialGraphError


class MetricSpatialError(SpatialGraphError):
    """Base exception for all metric spatial requirement domain errors."""


class MetricMissingInputError(MetricSpatialError):
    """Raised when required SpatialProgram or input collection is missing."""


class MetricSchemaVersionMismatchError(MetricSpatialError):
    """Raised when SpatialProgram schema_version is incompatible with metric builder."""

    def __init__(self, expected_schema: str, actual_schema: str) -> None:
        super().__init__(
            f"Incompatible program schema version: expected {expected_schema!r}, "
            f"got {actual_schema!r}."
        )
        self.expected_schema = expected_schema
        self.actual_schema = actual_schema


class MetricNonexistentSpaceError(MetricSpatialError):
    """Raised when a metric requirement references a space_id not in SpatialProgram."""


class MetricRangeConflictError(MetricSpatialError):
    """Raised when metric requirements for a space violate range invariants (e.g. min > max)."""


class DuplicateMetricRequirementError(MetricSpatialError):
    """Raised when multiple requirements of the same type are specified for the same space."""


class MetricUnitMismatchError(MetricSpatialError):
    """Raised when a metric requirement uses an incompatible unit (e.g. METRE for area)."""


class MetricInvalidValueError(MetricSpatialError):
    """Raised when a metric requirement value is non-positive or non-finite."""


class MetricInvalidEvidenceError(MetricSpatialError):
    """Raised when a USER_CONFIRMED metric requirement lacks traceable evidence IDs."""
