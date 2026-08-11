"""BRIF.AI — Persistent Brief Application Service."""

from __future__ import annotations

from datetime import datetime

from brif_ai.brief.models.snapshot import BriefSnapshot
from brif_ai.brief.mutation import (
    ProposedBriefMutation,
    apply_approved_brief_mutation,
)
from brif_ai.brief.persistence.errors import (
    BriefNotFoundError,
    BriefVersionConflictError,
)
from brif_ai.brief.persistence.repository import BriefRepository


class PersistentBriefService:
    """Application service coordinating persistent brief state operations.

    Separates storage repository responsibilities from conversation interpretation services.
    Contains zero imports from the LLM package layer.
    """

    def __init__(self, repository: BriefRepository) -> None:
        self.repository = repository

    def get_latest_brief(self, project_id: str) -> BriefSnapshot | None:
        """Retrieve latest BriefSnapshot for project_id or None if not found."""
        return self.repository.get_latest(project_id)

    def get_brief_version(self, project_id: str, version: int) -> BriefSnapshot | None:
        """Retrieve specific BriefSnapshot version for project_id or None if not found."""
        return self.repository.get_version(project_id, version)

    def list_brief_versions(self, project_id: str) -> list[int]:
        """List all available brief version numbers for project_id in ascending order."""
        return self.repository.list_versions(project_id)

    def initialize_brief(self, project_id: str, snapshot: BriefSnapshot) -> BriefSnapshot:
        """Initialize project brief storage with initial snapshot.

        Enforces project_id consistency and version 1 requirement.
        """
        if snapshot.project_id != project_id:
            raise ValueError(
                f"snapshot project_id '{snapshot.project_id}' does not match "
                f"target project_id '{project_id}'"
            )

        existing = self.repository.get_latest(project_id)
        if existing is not None:
            # Check idempotency
            if (
                existing.project_id == snapshot.project_id
                and existing.brief_version == snapshot.brief_version
                and existing.model_dump(mode="json") == snapshot.model_dump(mode="json")
            ):
                return existing
            raise BriefVersionConflictError(
                f"Project '{project_id}' brief is already initialized with different content."
            )

        return self.repository.save(snapshot)

    def record_brief_mutation_approval(
        self,
        *,
        current_project_id: str,
        expected_brief_version: int,
        proposed_mutation: ProposedBriefMutation,
        user_message: str,
        source_reference: str = "conversation_msg",
        approved_at: datetime | None = None,
    ) -> BriefSnapshot:
        """Server-authoritative brief mutation approval.

        Loads current persisted BriefSnapshot, enforces optimistic concurrency check,
        applies deterministic domain mutation, persists resulting N+1, and returns updated snapshot.

        Enforces explicit initialization boundary: if project brief is uninitialized in repository,
        raises BriefNotFoundError (HTTP 404).
        """
        persisted = self.repository.get_latest(current_project_id)
        if persisted is None:
            raise BriefNotFoundError(
                f"Cannot approve mutation: Project '{current_project_id}' brief is not initialized."
            )

        if persisted.brief_version != expected_brief_version:
            raise BriefVersionConflictError(
                f"Stale brief approval: Current persisted brief version for "
                f"'{current_project_id}' is {persisted.brief_version}, "
                f"but client expected version {expected_brief_version}."
            )

        new_snapshot = apply_approved_brief_mutation(
            snapshot=persisted,
            mutation=proposed_mutation,
            user_message=user_message,
            source_reference=source_reference,
            approved_at=approved_at,
        )

        return self.repository.save(new_snapshot)
