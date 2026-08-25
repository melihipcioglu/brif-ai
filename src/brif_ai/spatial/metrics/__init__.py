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
    ProposedMetricRequirement,
    SpaceMetricRequirements,
    generate_metric_requirement_id,
)
from brif_ai.spatial.metrics.source_binding import (
    MetricSourceBindingError,
    normalize_metric_source_text,
    split_metric_clauses,
    validate_metric_source_binding,
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
    "MetricSourceBindingError",
    "MetricUnit",
    "MetricUnitMismatchError",
    "ProposedMetricRequirement",
    "SpaceMetricRequirements",
    "generate_metric_requirement_id",
    "normalize_metric_source_text",
    "split_metric_clauses",
    "validate_metric_source_binding",
]
