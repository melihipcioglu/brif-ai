"""Domain exceptions for BRIF.AI Spatial Program V0."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brif_ai.spatial.errors import SpatialGraphError

if TYPE_CHECKING:
    from brif_ai.brief.readiness import BriefReadinessResult
    from brif_ai.spatial.models import SpatialConflict


class SpatialProgramError(SpatialGraphError):
    """Base exception for all spatial program domain errors."""


class SpatialProgramMissingInputError(SpatialProgramError):
    """Raised when required BriefSnapshot or SpatialRelationshipGraph is missing."""


class BriefNotReadyError(SpatialProgramError):
    """Raised when brief readiness evaluation fails with blocking conditions."""

    def __init__(self, readiness_result: BriefReadinessResult) -> None:
        blocker_summary = ", ".join(b.code.value for b in readiness_result.blockers)
        super().__init__(
            f"Brief snapshot is not ready for spatial program generation. "
            f"Blockers: [{blocker_summary}]"
        )
        self.readiness_result = readiness_result


class SpatialProgramProjectMismatchError(SpatialProgramError):
    """Raised when graph project_id does not match snapshot project_id."""

    def __init__(self, snapshot_project_id: str, graph_project_id: str) -> None:
        super().__init__(
            f"Project ID mismatch: snapshot has {snapshot_project_id!r}, "
            f"but graph has {graph_project_id!r}."
        )
        self.snapshot_project_id = snapshot_project_id
        self.graph_project_id = graph_project_id


class SpatialProgramVersionMismatchError(SpatialProgramError):
    """Raised when graph source_brief_version does not match snapshot brief_version."""

    def __init__(self, snapshot_version: int, graph_source_version: int) -> None:
        super().__init__(
            f"Version mismatch: snapshot is brief v{snapshot_version}, "
            f"but graph source_brief_version is v{graph_source_version}."
        )
        self.snapshot_version = snapshot_version
        self.graph_source_version = graph_source_version


class SpatialProgramConflictBlockerError(SpatialProgramError):
    """Raised when the spatial relationship graph contains unresolved spatial conflicts."""

    def __init__(self, conflicts: list[SpatialConflict]) -> None:
        conflict_ids = ", ".join(c.conflict_id for c in conflicts)
        super().__init__(
            f"Cannot build spatial program: graph contains {len(conflicts)} unresolved "
            f"spatial conflict(s): [{conflict_ids}]."
        )
        self.conflicts = conflicts


class SpatialProgramNodeMismatchError(SpatialProgramError):
    """Raised when graph nodes do not match confirmed SpaceRequests in the brief snapshot."""
