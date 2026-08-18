"""Deterministic Spatial Relationship Graph Builder for approved briefs."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from itertools import combinations

from brif_ai.brief.models.snapshot import BriefSnapshot
from brif_ai.spatial.errors import SpatialGraphError
from brif_ai.spatial.models import (
    SpatialRelationshipGraph,
    SpatialRelationshipInput,
    UnconstrainedPair,
    project_space_requests_to_spatial_nodes,
)
from brif_ai.spatial.validator import (
    deduplicate_and_materialize_relationships,
    detect_spatial_conflicts,
    validate_evidence_references,
    validate_spatial_relationship_inputs,
)


class SpatialRelationshipGraphBuilder:
    """Deterministic builder for SpatialRelationshipGraph from approved brief and inputs.

    CRITICAL ARCHITECTURAL INVARIANTS:
    1. Zero free-text parsing: BriefItem.normalized_statement, Evidence.excerpt, and
       UsageScenario.description are never parsed for relationships.
    2. Discrete spatial node identity: SpaceRequest.minimum_quantity (guaranteed >= 1 by
       authoritative contract) expands deterministically into discrete SpatialNode instances
       via project_space_requests_to_spatial_nodes.
    3. Explicit relationship boundary: All relationships must enter through structured
       SpatialRelationshipInput items.
    4. Evidence referential integrity: Every referenced evidence_id must exist in the
       authoritative BriefSnapshot.evidence collection, and USER_CONFIRMED relationships
       must reference at least one evidence_id.
    5. Zero silent provenance promotion: USER_STATED, AI_INFERRED, and USER_CONFIRMED
       are preserved exactly as supplied.
    6. Derived unconstrained pairs: All space pairs lacking an explicit relationship are
       recorded as UnconstrainedPairs; no default relationships are guessed or hallucinated.
    7. Structured conflicts: Contradictory relationships on the same space pair are
       captured as SpatialConflict records in the graph rather than crashing construction.
    """

    def build(
        self,
        snapshot: BriefSnapshot,
        relationships: Sequence[SpatialRelationshipInput] | None = None,
        *,
        include_unconfirmed_spaces: bool = False,
        created_at: datetime | None = None,
    ) -> SpatialRelationshipGraph:
        """Build an authoritative SpatialRelationshipGraph deterministically."""
        # 1. Project SpaceRequests into discrete SpatialNodes using single authoritative helper
        nodes = project_space_requests_to_spatial_nodes(
            snapshot.space_requests,
            include_unconfirmed=include_unconfirmed_spaces,
        )

        if not nodes:
            raise SpatialGraphError(
                f"No suitable spaces found in project '{snapshot.project_id}' "
                f"brief v{snapshot.brief_version} to construct a spatial relationship graph."
            )

        node_ids = {node.id for node in nodes}
        input_relationships = list(relationships or [])

        # 2. Hard Structural Validation (raises on nonexistent spaces or self-relations)
        validate_spatial_relationship_inputs(input_relationships, node_ids)

        # 3. Evidence Referential Integrity Validation
        snapshot_evidence_ids = {ev.id for ev in snapshot.evidence}
        validate_evidence_references(input_relationships, snapshot_evidence_ids)

        # 4. Deduplicate and materialize relationships with stable IDs & exact provenance
        materialized_rels = deduplicate_and_materialize_relationships(
            snapshot.project_id,
            input_relationships,
        )

        # 5. Detect semantic contradictions and produce structured SpatialConflicts
        conflicts = detect_spatial_conflicts(materialized_rels)

        # 6. Derive unconstrained pairs (pairs with NO relationship assertions)
        related_pairs: set[tuple[str, str]] = set()
        for rel in materialized_rels:
            pk = tuple(sorted([rel.source_space_id, rel.target_space_id]))
            related_pairs.add(pk)  # type: ignore[arg-type]

        unconstrained_pairs: list[UnconstrainedPair] = []
        sorted_node_ids = sorted(node_ids)
        for space_a, space_b in combinations(sorted_node_ids, 2):
            if (space_a, space_b) not in related_pairs:
                unconstrained_pairs.append(
                    UnconstrainedPair(space_a_id=space_a, space_b_id=space_b)
                )

        unconstrained_pairs.sort(key=lambda p: (p.space_a_id, p.space_b_id))

        # 7. Assemble complete validated graph
        ts = created_at or datetime.now(UTC)
        if ts.tzinfo is None or ts.utcoffset() != UTC.utcoffset(None):
            ts = ts.replace(tzinfo=UTC)

        return SpatialRelationshipGraph(
            schema_version="spatial_graph.v0",
            project_id=snapshot.project_id,
            source_brief_version=snapshot.brief_version,
            created_at=ts,
            nodes=nodes,
            relationships=materialized_rels,
            unconstrained_pairs=unconstrained_pairs,
            conflicts=conflicts,
        )
