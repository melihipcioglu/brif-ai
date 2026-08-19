"""Deterministic builder for BRIF.AI Spatial Program V0."""

from __future__ import annotations

from datetime import UTC, datetime

from brif_ai.brief.models.common import ConfirmationStatus
from brif_ai.brief.models.snapshot import BriefSnapshot
from brif_ai.brief.readiness import BriefReadinessEvaluator
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationshipGraph,
    project_space_requests_to_spatial_nodes,
)
from brif_ai.spatial.program.errors import (
    BriefNotReadyError,
    SpatialProgramConflictBlockerError,
    SpatialProgramMissingInputError,
    SpatialProgramNodeMismatchError,
    SpatialProgramProjectMismatchError,
    SpatialProgramVersionMismatchError,
)
from brif_ai.spatial.program.models import ProgramSpace, SpatialProgram


class SpatialProgramBuilder:
    """Deterministic builder for SpatialProgram from BriefSnapshot and SpatialRelationshipGraph.

    ARCHITECTURAL INVARIANTS:
    1. Deterministic construction: Given identical inputs, produces reproducible output.
       By default, created_at reuses graph.created_at (zero non-deterministic datetime.now()).
    2. Brief readiness gate: BriefReadinessEvaluator must evaluate ready_for_next_stage=True.
       Unready briefs (open questions, contradictions, pending confirmations, uncovered topics)
       are deterministically blocked via BriefNotReadyError.
    3. Conflict gate: Any unresolved item in graph.conflicts blocks program generation via
       SpatialProgramConflictBlockerError.
    4. Referential & version integrity: Project IDs and brief versions must match exactly.
    5. Node traceability: Every ProgramSpace retains exact traceability to its source SpaceRequest,
       stakeholder IDs, and evidence IDs.
    6. Authority boundary: Only USER_CONFIRMED relationships are marked as
       authoritative_relationship_ids. USER_STATED and AI_INFERRED relationships are preserved
       for traceability without silent promotion.
    7. Unconstrained pairs preservation: Unconstrained pairs are preserved without hallucinating
       default relations.
    """

    def __init__(self, readiness_evaluator: BriefReadinessEvaluator | None = None) -> None:
        self.readiness_evaluator = readiness_evaluator or BriefReadinessEvaluator()

    def build(
        self,
        snapshot: BriefSnapshot,
        graph: SpatialRelationshipGraph,
        *,
        created_at: datetime | None = None,
    ) -> SpatialProgram:
        """Construct a validated SpatialProgram deterministically."""
        if snapshot is None or graph is None:
            raise SpatialProgramMissingInputError("Both snapshot and graph are required.")

        # 1. Brief readiness validation
        readiness_result = self.readiness_evaluator.evaluate(snapshot)
        if not readiness_result.ready_for_next_stage:
            raise BriefNotReadyError(readiness_result)

        # 2. Project ID consistency
        if graph.project_id != snapshot.project_id:
            raise SpatialProgramProjectMismatchError(
                snapshot_project_id=snapshot.project_id,
                graph_project_id=graph.project_id,
            )

        # 3. Version consistency
        if graph.source_brief_version != snapshot.brief_version:
            raise SpatialProgramVersionMismatchError(
                snapshot_version=snapshot.brief_version,
                graph_source_version=graph.source_brief_version,
            )

        # 4. Strict conflict gating
        if graph.conflicts:
            raise SpatialProgramConflictBlockerError(graph.conflicts)

        # 5. Node correspondence validation against confirmed space requests
        confirmed_requests = [
            req
            for req in snapshot.space_requests
            if req.confirmation_status is ConfirmationStatus.CONFIRMED
        ]
        projected_nodes = project_space_requests_to_spatial_nodes(confirmed_requests)
        projected_node_ids = {node.id for node in projected_nodes}
        graph_node_ids = {node.id for node in graph.nodes}

        if projected_node_ids != graph_node_ids:
            raise SpatialProgramNodeMismatchError(
                f"Graph nodes do not match confirmed space requests in snapshot. "
                f"Projected node IDs: {sorted(projected_node_ids)}, "
                f"Graph node IDs: {sorted(graph_node_ids)}."
            )

        # 6. Materialize ProgramSpace instances with full traceability
        space_request_by_id = {req.id: req for req in confirmed_requests}
        spaces: list[ProgramSpace] = []
        for node in projected_nodes:
            sr = space_request_by_id[node.source_space_request_id]
            spaces.append(
                ProgramSpace(
                    id=node.id,
                    source_space_request_id=sr.id,
                    display_name=node.display_name,
                    function=node.function,
                    instance_index=node.instance_index,
                    mandatory=node.mandatory,
                    stakeholder_ids=sorted(sr.stakeholder_ids),
                    evidence_ids=sorted(sr.evidence_ids),
                )
            )
        spaces.sort(key=lambda s: s.id)

        # 7. Materialize and sort relationships
        relationships = sorted(graph.relationships, key=lambda r: r.id)

        # 8. Compute authoritative relationship IDs (USER_CONFIRMED only)
        authoritative_relationship_ids = sorted(
            r.id for r in relationships if r.provenance is RelationshipProvenance.USER_CONFIRMED
        )

        # 9. Sort unconstrained pairs
        unconstrained_pairs = sorted(
            graph.unconstrained_pairs,
            key=lambda p: (p.space_a_id, p.space_b_id),
        )

        # 10. Timestamp determinism: reuse graph.created_at by default
        ts = created_at or graph.created_at
        if ts.tzinfo is None or ts.utcoffset() != UTC.utcoffset(None):
            ts = ts.replace(tzinfo=UTC)

        return SpatialProgram(
            schema_version="spatial_program.v0",
            project_id=snapshot.project_id,
            source_brief_version=snapshot.brief_version,
            created_at=ts,
            spaces=spaces,
            relationships=relationships,
            unconstrained_pairs=unconstrained_pairs,
            authoritative_relationship_ids=authoritative_relationship_ids,
        )
