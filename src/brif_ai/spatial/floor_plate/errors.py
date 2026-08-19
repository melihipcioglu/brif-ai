"""Typed domain exceptions for BRIF.AI Authoritative FloorPlate V0."""

from __future__ import annotations

from brif_ai.spatial.errors import SpatialGraphError


class FloorPlateError(SpatialGraphError):
    """Base class for all FloorPlate V0 domain errors."""


class FloorPlateMissingInputError(FloorPlateError):
    """Raised when required inputs to FloorPlateBuilder are missing or None."""


class FloorPlateSchemaVersionMismatchError(FloorPlateError):
    """Raised when LayoutSolverInputSet schema version is incompatible with FloorPlate V0."""


class FloorPlateNonAuthoritativeError(FloorPlateError):
    """Raised when FloorPlateInput does not have authoritative (USER_CONFIRMED) provenance."""


class FloorPlateOutsideBuildableEnvelopeError(FloorPlateError):
    """Raised when the floor plate polygon passes or lies outside the site buildable envelope."""
