"""BRIF.AI — Persistent Spatial Graph Application Service."""

from __future__ import annotations

from datetime import datetime

from brif_ai.brief.models.snapshot import BriefSnapshot
from brif_ai.spatial.builder import SpatialRelationshipGraphBuilder
from brif_ai.spatial.models import (
    SpatialRelationshipGraph,
    SpatialRelationshipInput,
)
from brif_ai.spatial.persistence.repository import SpatialRelationshipRepository


class PersistentSpatialService:
    """Application service coordinating persistent spatial relationship graph operations.

    Maintains zero independent graph version counters: the authoritative BriefSnapshot.brief_version
    is always used as the version key.
    """

    def __init__(
        self,
        repository: SpatialRelationshipRepository,
        builder: SpatialRelationshipGraphBuilder | None = None,
    ) -> None:
        self.repository = repository
        self.builder = builder or SpatialRelationshipGraphBuilder()

    def get_latest_graph(self, project_id: str) -> SpatialRelationshipGraph | None:
        """Retrieve latest SpatialRelationshipGraph for project_id or None if not found."""
        return self.repository.get_latest(project_id)

    def get_graph_version(self, project_id: str, version: int) -> SpatialRelationshipGraph | None:
        """Retrieve specific source_brief_version graph for project_id or None."""
        return self.repository.get_version(project_id, version)

    def list_graph_versions(self, project_id: str) -> list[int]:
        """List all available graph version numbers in ascending order."""
        return self.repository.list_versions(project_id)

    def get_or_create_baseline_graph(self, snapshot: BriefSnapshot) -> SpatialRelationshipGraph:
        """Retrieve existing graph or build and persist baseline graph from snapshot."""
        existing = self.repository.get_latest(snapshot.project_id)
        if existing is not None and existing.source_brief_version == snapshot.brief_version:
            return existing

        # Extract previous relationships if existing graph exists
        previous_inputs: list[SpatialRelationshipInput] = []
        if existing is not None:
            previous_inputs = [
                SpatialRelationshipInput(
                    source_space_id=r.source_space_id,
                    target_space_id=r.target_space_id,
                    relation_type=r.relation_type,
                    provenance=r.provenance,
                    priority=r.priority,
                    evidence_ids=r.evidence_ids,
                    rationale=r.rationale,
                    bidirectional=r.bidirectional,
                )
                for r in existing.relationships
            ]

        graph = self.builder.build(snapshot, previous_inputs)
        return self.repository.save(graph)

    def build_updated_graph_in_memory(
        self,
        snapshot: BriefSnapshot,
        existing_graph: SpatialRelationshipGraph | None,
        new_relationship: SpatialRelationshipInput,
        *,
        created_at: datetime | None = None,
    ) -> SpatialRelationshipGraph:
        """Construct the resulting SpatialRelationshipGraph in memory without persisting.

        Collects existing structured relationships from existing_graph, appends the new input,
        and builds a complete deterministic graph against snapshot.
        """
        all_inputs: list[SpatialRelationshipInput] = []
        if existing_graph is not None:
            all_inputs.extend(
                SpatialRelationshipInput(
                    source_space_id=r.source_space_id,
                    target_space_id=r.target_space_id,
                    relation_type=r.relation_type,
                    provenance=r.provenance,
                    priority=r.priority,
                    evidence_ids=r.evidence_ids,
                    rationale=r.rationale,
                    bidirectional=r.bidirectional,
                )
                for r in existing_graph.relationships
            )

        all_inputs.append(new_relationship)
        ts = created_at
        if (
            ts is None
            and existing_graph is not None
            and existing_graph.source_brief_version == snapshot.brief_version
        ):
            ts = existing_graph.created_at
        return self.builder.build(snapshot, all_inputs, created_at=ts)

    def save_graph(self, graph: SpatialRelationshipGraph) -> SpatialRelationshipGraph:
        """Persist a SpatialRelationshipGraph."""
        return self.repository.save(graph)
