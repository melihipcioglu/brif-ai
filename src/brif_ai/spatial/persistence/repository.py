"""Abstract repository interface for SpatialRelationshipGraph persistence."""

from __future__ import annotations

from typing import Protocol

from brif_ai.spatial.models import SpatialRelationshipGraph


class SpatialRelationshipRepository(Protocol):
    """Storage repository interface for SpatialRelationshipGraph."""

    def get_latest(self, project_id: str) -> SpatialRelationshipGraph | None:
        """Retrieve the latest graph for project_id or None if not found."""
        ...

    def get_version(self, project_id: str, version: int) -> SpatialRelationshipGraph | None:
        """Retrieve a specific source_brief_version graph for project_id or None."""
        ...

    def list_versions(self, project_id: str) -> list[int]:
        """List all available source_brief_version numbers for project_id in ascending order."""
        ...

    def save(self, graph: SpatialRelationshipGraph) -> SpatialRelationshipGraph:
        """Persist a SpatialRelationshipGraph deterministically."""
        ...
