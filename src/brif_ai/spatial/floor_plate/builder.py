"""Deterministic builder for Authoritative FloorPlate V0 bound to LayoutSolverInputSet."""

from __future__ import annotations

from datetime import datetime, timedelta

from brif_ai.spatial.floor_plate.errors import (
    FloorPlateMissingInputError,
    FloorPlateNonAuthoritativeError,
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
from brif_ai.spatial.models import RelationshipProvenance
from brif_ai.spatial.site.geometry import validate_polygon_geometry
from brif_ai.spatial.solver_input.models import LayoutSolverInputSet


class FloorPlateBuilder:
    """Deterministic builder constructing Authoritative FloorPlate V0 bound to LayoutSolverInputSet.

    ARCHITECTURAL INVARIANTS:
    1. Single authoritative solver input source: Bound strictly to LayoutSolverInputSet V0.
    2. Authority boundary: Only USER_CONFIRMED floor plate inputs are accepted.
       USER_STATED and AI_INFERRED inputs are rejected via FloorPlateNonAuthoritativeError.
    3. Buildable envelope containment: The floor plate must lie entirely inside or on
       solver_input.buildable_envelope (supporting convex and concave envelopes).
    4. Deterministic identity: Geometry ID is generated deterministically based on project_id.
    5. Timestamp determinism: Reuses solver_input.created_at by default with strict UTC validation.
    6. Raw coordinates: Coordinates and vertex sequence are preserved exactly as supplied.
    7. Zero geometry/solver execution: No room geometry, floor level hierarchies, or solver models.
    """

    def build(
        self,
        solver_input: LayoutSolverInputSet,
        floor_plate: FloorPlateInput,
        *,
        created_at: datetime | None = None,
    ) -> FloorPlate:
        """Build Authoritative FloorPlate deterministically for a valid LayoutSolverInputSet."""
        if solver_input is None:
            raise FloorPlateMissingInputError("solver_input must not be None.")
        if floor_plate is None:
            raise FloorPlateMissingInputError("floor_plate must not be None.")

        # 1. Strict schema version validation
        if solver_input.schema_version != "layout_solver_input_set.v0":
            raise FloorPlateSchemaVersionMismatchError(
                f"Unsupported solver_input schema_version: {solver_input.schema_version!r} "
                f"(expected 'layout_solver_input_set.v0')."
            )

        # 2. Authority enforcement
        if floor_plate.provenance != RelationshipProvenance.USER_CONFIRMED:
            raise FloorPlateNonAuthoritativeError(
                f"FloorPlateInput has non-authoritative provenance "
                f"{floor_plate.provenance.value!r}; only USER_CONFIRMED is permitted."
            )
        if not floor_plate.evidence_ids:
            raise FloorPlateNonAuthoritativeError(
                "USER_CONFIRMED floor plate requires at least one evidence ID."
            )

        # 3. Geometric simplicity & non-degeneracy validation
        validate_polygon_geometry(floor_plate.vertices)

        # 4. Containment within solver_input.buildable_envelope
        validate_floor_plate_inside_buildable_envelope(
            floor_plate_vertices=floor_plate.vertices,
            envelope_vertices=solver_input.buildable_envelope.vertices,
        )

        # 5. Deterministic ID generation
        fplate_id = generate_floor_plate_id(solver_input.project_id)

        # 6. Timestamp handling
        if created_at is not None:
            offset = created_at.utcoffset()
            if created_at.tzinfo is None or offset is None:
                raise ValueError("created_at must be timezone-aware")
            if offset != timedelta(0):
                raise ValueError("created_at must use UTC offset")
            ts = created_at
        else:
            ts = solver_input.created_at

        return FloorPlate(
            schema_version="floor_plate.v0",
            id=fplate_id,
            project_id=solver_input.project_id,
            source_brief_version=solver_input.source_brief_version,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            created_at=ts,
            coordinate_system=solver_input.coordinate_system,
            vertices=list(floor_plate.vertices),
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=list(floor_plate.evidence_ids),
            rationale=floor_plate.rationale,
        )
