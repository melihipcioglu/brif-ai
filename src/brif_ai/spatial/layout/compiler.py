"""Deterministic compiler converting SpatialProgram into SchematicLayoutProblem V0."""

from __future__ import annotations

from datetime import UTC, datetime

from brif_ai.spatial.layout.errors import (
    LayoutProblemAuthoritativeMismatchError,
    LayoutProblemEndpointError,
    LayoutProblemMissingInputError,
    LayoutProblemSchemaVersionMismatchError,
)
from brif_ai.spatial.layout.models import (
    LayoutConstraint,
    LayoutSpace,
    SchematicLayoutProblem,
)
from brif_ai.spatial.models import RelationshipProvenance
from brif_ai.spatial.program.models import SpatialProgram


class LayoutProblemCompiler:
    """Deterministic compiler creating SchematicLayoutProblem from SpatialProgram.

    ARCHITECTURAL INVARIANTS:
    1. Deterministic compilation: Given identical SpatialProgram input, produces reproducible,
       byte-for-byte equivalent serialized output.
       By default, created_at reuses program.created_at (zero datetime.now() nondeterminism).
    2. Authority segregation: Only relationships in program.authoritative_relationship_ids
       (which MUST be USER_CONFIRMED) become authoritative_constraints.
    3. Epistemic preservation: USER_STATED and AI_INFERRED relationships remain strictly
       informational without silent authority promotion.
    4. Exact priority preservation: Preserves relationship Priority (MUST/SHOULD/COULD)
       without prematurely converting priority into solver hard vs. soft mechanics.
    5. Traceability & endpoint integrity: Preserves source program space and relationship IDs
       while validating that all constraints connect valid spaces.
    6. Zero geometry: Introduces zero coordinates, dimensions, bounding boxes, or floor positions.
    """

    def compile(
        self,
        program: SpatialProgram,
        *,
        created_at: datetime | None = None,
    ) -> SchematicLayoutProblem:
        """Compile a validated SpatialProgram into a SchematicLayoutProblem deterministically."""
        if program is None:
            raise LayoutProblemMissingInputError("SpatialProgram is required.")

        # 1. Strict schema version validation
        if program.schema_version != "spatial_program.v0":
            raise LayoutProblemSchemaVersionMismatchError(
                expected_schema="spatial_program.v0",
                actual_schema=str(program.schema_version),
            )

        # 2. Validate authoritative_relationship_ids consistency
        rel_by_id = {r.id: r for r in program.relationships}
        for auth_id in program.authoritative_relationship_ids:
            if auth_id not in rel_by_id:
                raise LayoutProblemAuthoritativeMismatchError(
                    f"Authoritative relationship ID {auth_id!r} not found in program relationships."
                )
            if rel_by_id[auth_id].provenance is not RelationshipProvenance.USER_CONFIRMED:
                raise LayoutProblemAuthoritativeMismatchError(
                    f"Relationship {auth_id!r} in authoritative_relationship_ids has non-confirmed "
                    f"provenance {rel_by_id[auth_id].provenance.value!r}."
                )

        # 3. Materialize LayoutSpaces with full traceability
        spaces = [
            LayoutSpace(
                id=s.id,
                source_program_space_id=s.id,
                display_name=s.display_name,
                function=s.function,
                instance_index=s.instance_index,
                mandatory=s.mandatory,
                stakeholder_ids=sorted(s.stakeholder_ids),
                evidence_ids=sorted(s.evidence_ids),
            )
            for s in sorted(program.spaces, key=lambda s: s.id)
        ]
        space_id_set = {s.id for s in spaces}

        # 4. Partition relationships into authoritative constraints and informational
        auth_id_set = set(program.authoritative_relationship_ids)
        authoritative_constraints: list[LayoutConstraint] = []
        informational_relationships = []

        for rel in sorted(program.relationships, key=lambda r: r.id):
            if rel.source_space_id not in space_id_set or rel.target_space_id not in space_id_set:
                raise LayoutProblemEndpointError(
                    f"Relationship {rel.id!r} references unknown space endpoint "
                    f"(source={rel.source_space_id!r}, target={rel.target_space_id!r})."
                )

            if rel.id in auth_id_set:
                authoritative_constraints.append(
                    LayoutConstraint(
                        id=rel.id,
                        source_relationship_id=rel.id,
                        source_space_id=rel.source_space_id,
                        target_space_id=rel.target_space_id,
                        relation_type=rel.relation_type,
                        provenance=RelationshipProvenance.USER_CONFIRMED,
                        priority=rel.priority,
                        evidence_ids=sorted(rel.evidence_ids),
                        rationale=rel.rationale,
                        bidirectional=rel.bidirectional,
                    )
                )
            else:
                informational_relationships.append(rel)

        # 5. Sort unconstrained pairs
        unconstrained_pairs = sorted(
            program.unconstrained_pairs,
            key=lambda p: (p.space_a_id, p.space_b_id),
        )
        for pair in unconstrained_pairs:
            if pair.space_a_id not in space_id_set or pair.space_b_id not in space_id_set:
                raise LayoutProblemEndpointError(
                    f"Unconstrained pair references unknown space endpoint "
                    f"(space_a={pair.space_a_id!r}, space_b={pair.space_b_id!r})."
                )

        # 6. Timestamp determinism: reuse program.created_at by default
        ts = created_at or program.created_at
        if ts.tzinfo is None or ts.utcoffset() != UTC.utcoffset(None):
            ts = ts.replace(tzinfo=UTC)

        return SchematicLayoutProblem(
            schema_version="schematic_layout_problem.v0",
            project_id=program.project_id,
            source_brief_version=program.source_brief_version,
            source_program_schema_version="spatial_program.v0",
            created_at=ts,
            spaces=spaces,
            authoritative_constraints=authoritative_constraints,
            informational_relationships=informational_relationships,
            unconstrained_pairs=unconstrained_pairs,
        )
