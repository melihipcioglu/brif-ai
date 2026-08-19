"""Typed domain exceptions for BRIF.AI SVG Plan View V0."""

from __future__ import annotations

from brif_ai.spatial.errors import SpatialGraphError


class SvgPlanError(SpatialGraphError):
    """Base exception for all SVG Plan View V0 domain errors."""


class SvgPlanInputMismatchError(SvgPlanError):
    """Raised when cross-contract metadata (project_id, brief_version, etc.) mismatch."""


class SvgPlanUnknownSpaceError(SvgPlanError):
    """Raised when a room space_id cannot be found in solver_input spaces."""


class SvgPlanInvalidGeometryError(SvgPlanError):
    """Raised when room geometry violates spatial containment inside FloorPlate."""


class SvgPlanRenderError(SvgPlanError):
    """Raised when SVG assembly or XML validation fails."""
