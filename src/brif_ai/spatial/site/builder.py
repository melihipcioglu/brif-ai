"""Deterministic builder for SiteBuildableEnvelope V0 from SpatialProgram."""

from __future__ import annotations

from datetime import datetime

from brif_ai.spatial.models import RelationshipProvenance
from brif_ai.spatial.program.models import SpatialProgram
from brif_ai.spatial.site.errors import (
    SiteEnvelopeWithoutParcelError,
    SiteMissingInputError,
    SiteSchemaVersionMismatchError,
)
from brif_ai.spatial.site.geometry import validate_envelope_inside_parcel
from brif_ai.spatial.site.models import (
    SiteBuildableEnvelope,
    SiteGeometryRole,
    SitePolygon,
    SitePolygonInput,
    generate_site_geometry_id,
)


class SiteBuildableEnvelopeBuilder:
    """Deterministic builder constructing SiteBuildableEnvelope bound to a SpatialProgram.

    ARCHITECTURAL INVARIANTS:
    1. Single authoritative project context: Bound directly to SpatialProgram V0.
    2. Explicit absence: Absence of parcel boundary or buildable envelope means UNKNOWN.
       Zero inferred envelopes or default setback geometry.
    3. Buildable envelope containment: An envelope without a parcel is rejected.
       When both exist, the envelope must lie entirely inside or on the parcel boundary.
    4. Deterministic identity: Geometry IDs are generated deterministically based on
       project_id + role (independent of coordinates).
    5. Authority boundary: Only USER_CONFIRMED geometries enter authoritative_geometry_ids.
       Provenance is required explicitly on all inputs (no default).
    6. Timestamp determinism: Reuses program.created_at by default with strict UTC validation.
    7. Raw coordinates: Coordinates are preserved exactly as supplied (never mutated or rounded).
    8. Traceability boundary: Presence of evidence_ids is enforced for USER_CONFIRMED geometry
       and preserved deterministically; cross-domain existence validation against BriefSnapshot
       catalog is deferred to a future integration boundary.
    """

    def build(
        self,
        program: SpatialProgram,
        parcel_boundary: SitePolygonInput | None = None,
        buildable_envelope: SitePolygonInput | None = None,
        *,
        created_at: datetime | None = None,
    ) -> SiteBuildableEnvelope:
        """Build SiteBuildableEnvelope deterministically for a valid SpatialProgram."""
        if program is None:
            raise SiteMissingInputError("SpatialProgram is required.")

        # 1. Strict schema version validation
        if program.schema_version != "spatial_program.v0":
            raise SiteSchemaVersionMismatchError(
                expected_schema="spatial_program.v0",
                actual_schema=str(program.schema_version),
            )

        # 2. Absence and containment prerequisite check
        if parcel_boundary is None and buildable_envelope is not None:
            raise SiteEnvelopeWithoutParcelError(
                "Buildable envelope cannot be defined without an enclosing parcel boundary."
            )

        # 3. Materialize parcel boundary if supplied
        materialized_parcel: SitePolygon | None = None
        confirmed_ids: list[str] = []

        if parcel_boundary is not None:
            p_id = generate_site_geometry_id(
                project_id=program.project_id,
                role=SiteGeometryRole.PARCEL_BOUNDARY,
            )
            materialized_parcel = SitePolygon(
                id=p_id,
                role=SiteGeometryRole.PARCEL_BOUNDARY,
                vertices=parcel_boundary.vertices,
                provenance=parcel_boundary.provenance,
                evidence_ids=sorted(parcel_boundary.evidence_ids),
                rationale=parcel_boundary.rationale,
            )
            if materialized_parcel.provenance == RelationshipProvenance.USER_CONFIRMED:
                confirmed_ids.append(materialized_parcel.id)

        # 4. Materialize buildable envelope if supplied
        materialized_envelope: SitePolygon | None = None
        if buildable_envelope is not None:
            e_id = generate_site_geometry_id(
                project_id=program.project_id,
                role=SiteGeometryRole.BUILDABLE_ENVELOPE,
            )
            materialized_envelope = SitePolygon(
                id=e_id,
                role=SiteGeometryRole.BUILDABLE_ENVELOPE,
                vertices=buildable_envelope.vertices,
                provenance=buildable_envelope.provenance,
                evidence_ids=sorted(buildable_envelope.evidence_ids),
                rationale=buildable_envelope.rationale,
            )
            if materialized_envelope.provenance == RelationshipProvenance.USER_CONFIRMED:
                confirmed_ids.append(materialized_envelope.id)

        # 5. Validate containment when both exist
        if materialized_parcel is not None and materialized_envelope is not None:
            validate_envelope_inside_parcel(
                envelope_vertices=materialized_envelope.vertices,
                parcel_vertices=materialized_parcel.vertices,
            )

        # 6. Timestamp determinism
        ts = created_at if created_at is not None else program.created_at

        return SiteBuildableEnvelope(
            schema_version="site_buildable_envelope.v0",
            project_id=program.project_id,
            source_brief_version=program.source_brief_version,
            source_program_schema_version="spatial_program.v0",
            created_at=ts,
            coordinate_system="LOCAL_CARTESIAN_METRES",
            parcel_boundary=materialized_parcel,
            buildable_envelope=materialized_envelope,
            authoritative_geometry_ids=sorted(confirmed_ids),
        )
