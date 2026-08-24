"""Authoritative FloorPlate V0 package for BRIF.AI."""

from __future__ import annotations

from brif_ai.spatial.floor_plate.builder import FloorPlateBuilder
from brif_ai.spatial.floor_plate.errors import (
    FloorPlateError,
    FloorPlateMissingInputError,
    FloorPlateNonAuthoritativeError,
    FloorPlateOutsideBuildableEnvelopeError,
    FloorPlateSchemaVersionMismatchError,
)
from brif_ai.spatial.floor_plate.geometry import (
    validate_floor_plate_inside_buildable_envelope,
)
from brif_ai.spatial.floor_plate.models import (
    FloorPlate,
    FloorPlateInput,
    generate_floor_plate_id,
)
from brif_ai.spatial.floor_plate.source_binding import (
    FloorPlateSourceBindingError,
    validate_floor_plate_source_binding,
)

__all__ = [
    "FloorPlate",
    "FloorPlateBuilder",
    "FloorPlateError",
    "FloorPlateInput",
    "FloorPlateMissingInputError",
    "FloorPlateNonAuthoritativeError",
    "FloorPlateOutsideBuildableEnvelopeError",
    "FloorPlateSchemaVersionMismatchError",
    "FloorPlateSourceBindingError",
    "generate_floor_plate_id",
    "validate_floor_plate_inside_buildable_envelope",
    "validate_floor_plate_source_binding",
]
