"""BRIF.AI Metric Spatial Requirements V0 Package."""

from __future__ import annotations

from brif_ai.spatial.metrics.builder import MetricSpatialRequirementsBuilder
from brif_ai.spatial.metrics.errors import (
    DuplicateMetricRequirementError,
    MetricInvalidEvidenceError,
    MetricInvalidValueError,
    MetricMissingInputError,
    MetricNonexistentSpaceError,
    MetricRangeConflictError,
    MetricSchemaVersionMismatchError,
    MetricSpatialError,
    MetricUnitMismatchError,
)
from brif_ai.spatial.metrics.models import (
    MetricRequirement,
    MetricRequirementInput,
    MetricRequirementType,
    MetricSpatialRequirements,
    MetricUnit,
    SpaceMetricRequirements,
    generate_metric_requirement_id,
)

__all__ = [
    "DuplicateMetricRequirementError",
    "MetricInvalidEvidenceError",
    "MetricInvalidValueError",
    "MetricMissingInputError",
    "MetricNonexistentSpaceError",
    "MetricRangeConflictError",
    "MetricRequirement",
    "MetricRequirementInput",
    "MetricRequirementType",
    "MetricSchemaVersionMismatchError",
    "MetricSpatialError",
    "MetricSpatialRequirements",
    "MetricSpatialRequirementsBuilder",
    "MetricUnit",
    "MetricUnitMismatchError",
    "SpaceMetricRequirements",
    "generate_metric_requirement_id",
]
