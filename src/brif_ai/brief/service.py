"""BRIF.AI — Persistent Brief Application Service."""

from __future__ import annotations

from datetime import datetime

from brif_ai.brief.models.common import OpenQuestionStatus
from brif_ai.brief.models.snapshot import BriefSnapshot, Evidence
from brif_ai.brief.mutation import (
    ProposedBriefMutation,
    add_open_question_to_snapshot,
    append_chat_evidence_and_resolve_spatial_question,
    apply_approved_brief_mutation,
    atomic_apply_mutation_and_resolve_question,
    update_open_question_status_for_topic,
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

    def add_open_question(
        self,
        *,
        project_id: str,
        expected_brief_version: int,
        question_text: str,
        reason: str,
        topic_key: str,
    ) -> BriefSnapshot:
        """Add an OPEN question with concurrency check.

        Re-loads persisted snapshot and verifies version matches expected.
        If concurrent mutation happened, raises BriefVersionConflictError (HTTP 409).
        """
        persisted = self.repository.get_latest(project_id)
        if persisted is None:
            raise BriefNotFoundError(
                f"Cannot add open question: Project '{project_id}' brief is not initialized."
            )

        if persisted.brief_version != expected_brief_version:
            raise BriefVersionConflictError(
                f"Race condition during open question persistence: "
                f"expected version {expected_brief_version}, "
                f"but current version is {persisted.brief_version}."
            )

        new_snapshot = add_open_question_to_snapshot(
            persisted,
            question=question_text,
            reason=reason,
            topic_key=topic_key,
        )

        # If add_open_question_to_snapshot returned the same snapshot (duplicate),
        # no persistence needed
        if new_snapshot.brief_version == persisted.brief_version:
            return persisted

        return self.repository.save(new_snapshot)

    def dismiss_active_open_question(
        self,
        *,
        project_id: str,
        expected_brief_version: int,
    ) -> BriefSnapshot:
        """Dismiss the active OPEN elicitation question with concurrency check.

        Finds the single active OPEN question with a valid topic_key,
        transitions it to DISMISSED, and persists N+1.
        """
        persisted = self.repository.get_latest(project_id)
        if persisted is None:
            raise BriefNotFoundError(
                f"Cannot dismiss question: Project '{project_id}' brief is not initialized."
            )

        if persisted.brief_version != expected_brief_version:
            raise BriefVersionConflictError(
                f"Stale context for dismiss: expected version {expected_brief_version}, "
                f"but current version is {persisted.brief_version}."
            )

        # Find the active OPEN question with a topic_key
        active_topic_key: str | None = None
        for oq in persisted.open_questions:
            if oq.status == OpenQuestionStatus.OPEN and oq.topic_key:
                active_topic_key = oq.topic_key
                break

        if active_topic_key is None:
            return persisted

        new_snapshot = update_open_question_status_for_topic(
            persisted,
            active_topic_key,
            OpenQuestionStatus.DISMISSED,
            "Kullanıcı tarafından geçildi.",
        )

        if new_snapshot.brief_version == persisted.brief_version:
            return persisted

        return self.repository.save(new_snapshot)

    def record_brief_mutation_approval(
        self,
        *,
        current_project_id: str,
        expected_brief_version: int,
        proposed_mutation: ProposedBriefMutation,
        user_message: str,
        source_reference: str = "conversation_msg",
        approved_at: datetime | None = None,
        answers_current_open_question: bool = False,
    ) -> BriefSnapshot:
        """Server-authoritative brief mutation approval.

        Loads current persisted BriefSnapshot, enforces optimistic concurrency check,
        applies deterministic domain mutation, persists resulting N+1, and returns updated snapshot.

        If answers_current_open_question is True, atomically applies both the mutation
        and the OPEN->ANSWERED transition in a single N+1 step.
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

        if answers_current_open_question:
            new_snapshot = atomic_apply_mutation_and_resolve_question(
                snapshot=persisted,
                mutation=proposed_mutation,
                user_message=user_message,
                source_reference=source_reference,
                resolution_note=f"Kullanıcı yanıtı ile çözüldü: {user_message[:200]}",
                approved_at=approved_at,
            )
        else:
            new_snapshot = apply_approved_brief_mutation(
                snapshot=persisted,
                mutation=proposed_mutation,
                user_message=user_message,
                source_reference=source_reference,
                approved_at=approved_at,
            )

        return self.repository.save(new_snapshot)

    def record_chat_evidence_and_resolve_question(
        self,
        *,
        current_project_id: str,
        expected_brief_version: int,
        user_message: str,
        source_reference: str = "conversation_msg",
        resolve_topic: str | None = "spatial_relationships",
        resolution_note: str | None = None,
        approved_at: datetime | None = None,
    ) -> tuple[BriefSnapshot, Evidence]:
        """Server-authoritative evidence append and question resolution.

        Loads current persisted BriefSnapshot, enforces optimistic concurrency check,
        calls append_chat_evidence_and_resolve_spatial_question, persists if changed,
        and returns resulting (BriefSnapshot, Evidence).
        """
        persisted = self.repository.get_latest(current_project_id)
        if persisted is None:
            raise BriefNotFoundError(
                f"Cannot append evidence: Project '{current_project_id}' brief is not initialized."
            )

        if persisted.brief_version != expected_brief_version:
            raise BriefVersionConflictError(
                f"Stale brief version: Current persisted brief version for "
                f"'{current_project_id}' is {persisted.brief_version}, "
                f"but client expected version {expected_brief_version}."
            )

        new_snapshot, evidence = append_chat_evidence_and_resolve_spatial_question(
            snapshot=persisted,
            user_message=user_message,
            source_reference=source_reference,
            resolve_topic=resolve_topic,
            resolution_note=resolution_note,
            approved_at=approved_at,
        )

        if new_snapshot.brief_version == persisted.brief_version:
            return persisted, evidence

        saved_snapshot = self.repository.save(new_snapshot)
        return saved_snapshot, evidence
