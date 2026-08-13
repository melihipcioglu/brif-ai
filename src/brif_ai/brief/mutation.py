"""Structured brief mutation models and deterministic application logic."""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from enum import Enum

from pydantic import Field, model_validator

if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:  # pragma: no cover

    class StrEnum(str, Enum):  # noqa: UP042
        pass


from brif_ai.brief.models.common import (
    BriefItemKind,
    ConfirmationStatus,
    EvidenceSource,
    OpenQuestionStatus,
    Priority,
)
from brif_ai.brief.models.snapshot import (
    BriefItem,
    BriefSnapshot,
    DisplayName,
    Evidence,
    NormalizedStatement,
    SpaceRequest,
    UsageScenario,
)
from brif_ai.core.models.common import ContractModel, NonEmptyString, ObjectId, SpaceFunction


class BriefMutationType(StrEnum):
    ADD_BRIEF_ITEM = "ADD_BRIEF_ITEM"
    ADD_SPACE_REQUEST = "ADD_SPACE_REQUEST"
    ADD_USAGE_SCENARIO = "ADD_USAGE_SCENARIO"


class BriefItemProposalPayload(ContractModel):
    kind: BriefItemKind
    normalized_statement: NormalizedStatement
    priority: Priority


class SpaceRequestProposalPayload(ContractModel):
    display_name: DisplayName
    space_function: SpaceFunction
    minimum_quantity: int = Field(default=1, ge=1)
    maximum_quantity: int | None = Field(default=None, ge=1)
    mandatory: bool = True

    @model_validator(mode="after")
    def validate_quantity_range(self) -> SpaceRequestProposalPayload:
        if self.maximum_quantity is not None and self.maximum_quantity < self.minimum_quantity:
            raise ValueError("maximum_quantity cannot be less than minimum_quantity")
        return self


class UsageScenarioProposalPayload(ContractModel):
    title: NonEmptyString
    description: NonEmptyString


class ProposedBriefMutation(ContractModel):
    mutation_id: NonEmptyString
    mutation_type: BriefMutationType
    brief_item: BriefItemProposalPayload | None = None
    space_request: SpaceRequestProposalPayload | None = None
    usage_scenario: UsageScenarioProposalPayload | None = None
    target_stakeholder_id: ObjectId | None = None

    @model_validator(mode="after")
    def validate_mutation_payload_xor(self) -> ProposedBriefMutation:
        payloads = [
            ("ADD_BRIEF_ITEM", self.brief_item),
            ("ADD_SPACE_REQUEST", self.space_request),
            ("ADD_USAGE_SCENARIO", self.usage_scenario),
        ]
        active_payloads = [p_type for p_type, payload in payloads if payload is not None]
        expected_type = (
            self.mutation_type.value
            if hasattr(self.mutation_type, "value")
            else str(self.mutation_type)
        )

        if len(active_payloads) != 1:
            raise ValueError("Exactly one mutation payload must be provided")

        if active_payloads[0] != expected_type:
            raise ValueError(
                f"Payload for {active_payloads[0]} does not match mutation_type {expected_type}"
            )

        return self


def _generate_object_id(prefix: str, *components: str) -> str:
    content = "|".join(components).encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()[:16]
    return f"{prefix}{digest}"


def apply_approved_brief_mutation(
    snapshot: BriefSnapshot,
    mutation: ProposedBriefMutation,
    user_message: str,
    source_reference: str,
    *,
    approved_at: datetime | None = None,
) -> BriefSnapshot:
    """Deterministically apply an approved structured brief mutation to a BriefSnapshot.

    Guarantees:
    - Zero free-text parsing.
    - Deterministic ID and evidence creation/reuse.
    - Idempotent application (no duplicates on replay).
    - Immutable snapshot update (returns a new valid BriefSnapshot instance).
    - Increments brief_version exactly once if changed.
    """
    # 1. Resolve active stakeholder
    if mutation.target_stakeholder_id is not None:
        stakeholder = next(
            (s for s in snapshot.stakeholders if s.id == mutation.target_stakeholder_id),
            None,
        )
        if stakeholder is None:
            raise ValueError(
                f"Referenced stakeholder_id {mutation.target_stakeholder_id!r} "
                "not found in snapshot"
            )
        if not stakeholder.active:
            raise ValueError(
                f"Referenced stakeholder_id {mutation.target_stakeholder_id!r} is inactive"
            )
    else:
        active_stakeholders = [s for s in snapshot.stakeholders if s.active]
        if len(active_stakeholders) == 0:
            raise ValueError("No active stakeholder found in BriefSnapshot")
        if len(active_stakeholders) > 1:
            raise ValueError(
                "Multiple active stakeholders exist; target_stakeholder_id must be specified"
            )
        stakeholder = active_stakeholders[0]

    # 2. Create or reuse chat Evidence
    clean_msg = user_message.strip()
    excerpt = clean_msg[:500] if len(clean_msg) > 500 else clean_msg
    src_ref = (
        source_reference.strip()[:250]
        if len(source_reference.strip()) > 250
        else source_reference.strip()
    )
    if not src_ref:
        src_ref = "conversation_msg"

    ev_id = _generate_object_id("ev_", snapshot.project_id, src_ref, excerpt)
    existing_ev = next(
        (
            ev
            for ev in snapshot.evidence
            if ev.id == ev_id
            or (
                ev.source_type == EvidenceSource.CHAT
                and ev.source_reference == src_ref
                and ev.excerpt == excerpt
            )
        ),
        None,
    )

    if existing_ev is not None:
        target_ev = existing_ev
        new_evidence_list = list(snapshot.evidence)
        evidence_added = False
    else:
        target_ev = Evidence(
            id=ev_id,
            source_type=EvidenceSource.CHAT,
            source_reference=src_ref,
            excerpt=excerpt,
        )
        new_evidence_list = list(snapshot.evidence) + [target_ev]
        evidence_added = True

    # 3. Apply specific mutation payload
    items_changed = False
    new_brief_items = list(snapshot.brief_items)
    new_space_requests = list(snapshot.space_requests)
    new_usage_scenarios = list(snapshot.usage_scenarios)

    if mutation.mutation_type == BriefMutationType.ADD_BRIEF_ITEM:
        payload = mutation.brief_item
        assert payload is not None
        bi_id = _generate_object_id(
            "bi_",
            snapshot.project_id,
            payload.kind.value,
            payload.normalized_statement.casefold(),
            stakeholder.id,
        )

        existing_bi_index = next(
            (
                idx
                for idx, bi in enumerate(new_brief_items)
                if bi.id == bi_id
                or (
                    bi.kind == payload.kind
                    and bi.normalized_statement.casefold()
                    == payload.normalized_statement.casefold()
                    and stakeholder.id in bi.stakeholder_ids
                )
            ),
            None,
        )

        if existing_bi_index is not None:
            existing_bi = new_brief_items[existing_bi_index]
            if target_ev.id not in existing_bi.evidence_ids:
                updated_bi = existing_bi.model_copy(
                    update={"evidence_ids": list(existing_bi.evidence_ids) + [target_ev.id]}
                )
                new_brief_items[existing_bi_index] = updated_bi
                items_changed = True
        else:
            new_bi = BriefItem(
                id=bi_id,
                kind=payload.kind,
                normalized_statement=payload.normalized_statement,
                priority=payload.priority,
                stakeholder_ids=[stakeholder.id],
                evidence_ids=[target_ev.id],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            )
            new_brief_items.append(new_bi)
            items_changed = True

    elif mutation.mutation_type == BriefMutationType.ADD_SPACE_REQUEST:
        sr_payload = mutation.space_request
        assert sr_payload is not None
        sr_id = _generate_object_id(
            "sr_",
            snapshot.project_id,
            sr_payload.space_function.value,
            sr_payload.display_name.casefold(),
            stakeholder.id,
        )

        existing_sr_index = next(
            (
                idx
                for idx, sr in enumerate(new_space_requests)
                if sr.id == sr_id
                or (
                    sr.space_function == sr_payload.space_function
                    and sr.display_name.casefold() == sr_payload.display_name.casefold()
                    and stakeholder.id in sr.stakeholder_ids
                )
            ),
            None,
        )

        if existing_sr_index is not None:
            existing_sr = new_space_requests[existing_sr_index]
            if target_ev.id not in existing_sr.evidence_ids:
                updated_sr = existing_sr.model_copy(
                    update={"evidence_ids": list(existing_sr.evidence_ids) + [target_ev.id]}
                )
                new_space_requests[existing_sr_index] = updated_sr
                items_changed = True
        else:
            new_sr = SpaceRequest(
                id=sr_id,
                display_name=sr_payload.display_name,
                space_function=sr_payload.space_function,
                minimum_quantity=sr_payload.minimum_quantity,
                maximum_quantity=sr_payload.maximum_quantity,
                mandatory=sr_payload.mandatory,
                stakeholder_ids=[stakeholder.id],
                evidence_ids=[target_ev.id],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            )
            new_space_requests.append(new_sr)
            items_changed = True

    elif mutation.mutation_type == BriefMutationType.ADD_USAGE_SCENARIO:
        us_payload = mutation.usage_scenario
        assert us_payload is not None
        us_id = _generate_object_id(
            "us_",
            snapshot.project_id,
            us_payload.title.casefold(),
            stakeholder.id,
        )

        existing_us_index = next(
            (
                idx
                for idx, us in enumerate(new_usage_scenarios)
                if us.id == us_id
                or (
                    us.title.casefold() == us_payload.title.casefold()
                    and stakeholder.id in us.stakeholder_ids
                )
            ),
            None,
        )

        if existing_us_index is not None:
            existing_us = new_usage_scenarios[existing_us_index]
            if target_ev.id not in existing_us.evidence_ids:
                updated_us = existing_us.model_copy(
                    update={"evidence_ids": list(existing_us.evidence_ids) + [target_ev.id]}
                )
                new_usage_scenarios[existing_us_index] = updated_us
                items_changed = True
        else:
            new_us = UsageScenario(
                id=us_id,
                title=us_payload.title,
                description=us_payload.description,
                stakeholder_ids=[stakeholder.id],
                evidence_ids=[target_ev.id],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            )
            new_usage_scenarios.append(new_us)
            items_changed = True

    # 4. Check if true no-op
    if not items_changed and not evidence_added:
        return snapshot

    # 5. Construct new BriefSnapshot and validate
    ts = approved_at or datetime.now(timezone.utc)  # noqa: UP017
    if ts.tzinfo is None or ts.utcoffset() != timezone.utc:  # noqa: UP017
        ts = ts.replace(tzinfo=timezone.utc)  # noqa: UP017

    candidate_data = {
        "project_id": snapshot.project_id,
        "schema_version": snapshot.schema_version,
        "brief_version": snapshot.brief_version + 1,
        "created_at": ts,
        "stakeholders": [s.model_dump(mode="python") for s in snapshot.stakeholders],
        "evidence": [ev.model_dump(mode="python") for ev in new_evidence_list],
        "brief_items": [bi.model_dump(mode="python") for bi in new_brief_items],
        "space_requests": [sr.model_dump(mode="python") for sr in new_space_requests],
        "usage_scenarios": [us.model_dump(mode="python") for us in new_usage_scenarios],
        "contradictions": [c.model_dump(mode="python") for c in snapshot.contradictions],
        "open_questions": [oq.model_dump(mode="python") for oq in snapshot.open_questions],
    }

    return BriefSnapshot.model_validate(candidate_data)


def add_open_question_to_snapshot(
    snapshot: BriefSnapshot,
    question: str,
    reason: str,
    topic_key: str,
    *,
    related_brief_item_ids: list[str] | None = None,
    created_at: datetime | None = None,
) -> BriefSnapshot:
    """Add a new OPEN question with topic_key to BriefSnapshot, returning version N+1."""
    from brif_ai.brief.models.common import OpenQuestionStatus
    from brif_ai.brief.models.snapshot import OpenQuestion

    # Hard invariant: at most one active elicitation OPEN question.
    # Any existing OPEN question with a topic_key blocks creation of another.
    for oq in snapshot.open_questions:
        if oq.status == OpenQuestionStatus.OPEN and oq.topic_key:
            return snapshot

    ts = created_at or datetime.now(timezone.utc)  # noqa: UP017
    if ts.tzinfo is None or ts.utcoffset() != timezone.utc:  # noqa: UP017
        ts = ts.replace(tzinfo=timezone.utc)  # noqa: UP017

    qid = f"oq_{topic_key}_{snapshot.brief_version + 1}"
    new_oq = OpenQuestion(
        id=qid,
        question=question,
        reason=reason,
        related_brief_item_ids=related_brief_item_ids or [],
        status=OpenQuestionStatus.OPEN,
        resolution_note=None,
        topic_key=topic_key,
    )

    new_oqs = [oq.model_copy() for oq in snapshot.open_questions]
    new_oqs.append(new_oq)

    candidate_data = {
        "project_id": snapshot.project_id,
        "schema_version": snapshot.schema_version,
        "brief_version": snapshot.brief_version + 1,
        "created_at": ts,
        "stakeholders": [s.model_dump(mode="python") for s in snapshot.stakeholders],
        "evidence": [ev.model_dump(mode="python") for ev in snapshot.evidence],
        "brief_items": [bi.model_dump(mode="python") for bi in snapshot.brief_items],
        "space_requests": [sr.model_dump(mode="python") for sr in snapshot.space_requests],
        "usage_scenarios": [us.model_dump(mode="python") for us in snapshot.usage_scenarios],
        "contradictions": [c.model_dump(mode="python") for c in snapshot.contradictions],
        "open_questions": [oq.model_dump(mode="python") for oq in new_oqs],
    }

    return BriefSnapshot.model_validate(candidate_data)


def update_open_question_status_for_topic(
    snapshot: BriefSnapshot,
    topic_key: str,
    new_status: OpenQuestionStatus,
    resolution_note: str,
    *,
    updated_at: datetime | None = None,
) -> BriefSnapshot:
    """Transition matching OPEN question for topic_key, returning N+1 snapshot."""
    from brif_ai.brief.models.common import OpenQuestionStatus

    matching_index = next(
        (
            i
            for i, oq in enumerate(snapshot.open_questions)
            if oq.topic_key == topic_key and oq.status == OpenQuestionStatus.OPEN
        ),
        None,
    )
    if matching_index is None:
        return snapshot

    ts = updated_at or datetime.now(timezone.utc)  # noqa: UP017
    if ts.tzinfo is None or ts.utcoffset() != timezone.utc:  # noqa: UP017
        ts = ts.replace(tzinfo=timezone.utc)  # noqa: UP017

    new_oqs = [oq.model_copy() for oq in snapshot.open_questions]
    target = new_oqs[matching_index]
    new_oqs[matching_index] = target.model_copy(
        update={"status": new_status, "resolution_note": resolution_note}
    )

    candidate_data = {
        "project_id": snapshot.project_id,
        "schema_version": snapshot.schema_version,
        "brief_version": snapshot.brief_version + 1,
        "created_at": ts,
        "stakeholders": [s.model_dump(mode="python") for s in snapshot.stakeholders],
        "evidence": [ev.model_dump(mode="python") for ev in snapshot.evidence],
        "brief_items": [bi.model_dump(mode="python") for bi in snapshot.brief_items],
        "space_requests": [sr.model_dump(mode="python") for sr in snapshot.space_requests],
        "usage_scenarios": [us.model_dump(mode="python") for us in snapshot.usage_scenarios],
        "contradictions": [c.model_dump(mode="python") for c in snapshot.contradictions],
        "open_questions": [oq.model_dump(mode="python") for oq in new_oqs],
    }

    return BriefSnapshot.model_validate(candidate_data)


class NoActiveElicitationQuestionError(ValueError):
    """Raised when answers_current_open_question=True but no active OPEN question exists."""


def atomic_apply_mutation_and_resolve_question(
    snapshot: BriefSnapshot,
    mutation: ProposedBriefMutation,
    user_message: str,
    source_reference: str,
    resolution_note: str,
    *,
    approved_at: datetime | None = None,
) -> BriefSnapshot:
    """Apply a brief mutation AND resolve the active OPEN question atomically.

    Produces exactly ONE N+1 snapshot containing both:
    1. The applied brief mutation (items/spaces/scenarios)
    2. The active OPEN question transitioned to ANSWERED

    Raises NoActiveElicitationQuestionError if no active OPEN question exists.
    """
    # First find the active OPEN question with a valid topic_key
    active_oq_index = None
    for i, oq in enumerate(snapshot.open_questions):
        if oq.status == OpenQuestionStatus.OPEN and oq.topic_key:
            active_oq_index = i
            break

    if active_oq_index is None:
        raise NoActiveElicitationQuestionError(
            "answers_current_open_question=True but no active OPEN question with topic_key exists"
        )

    # Apply the brief mutation first (this produces version N+1)
    mutated = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message=user_message,
        source_reference=source_reference,
        approved_at=approved_at,
    )

    # Now apply the question resolution ON the mutated snapshot
    # but WITHOUT incrementing version again — we merge both into the same N+1
    ts = approved_at or datetime.now(timezone.utc)  # noqa: UP017
    if ts.tzinfo is None or ts.utcoffset() != timezone.utc:  # noqa: UP017
        ts = ts.replace(tzinfo=timezone.utc)  # noqa: UP017

    new_oqs = [oq.model_copy() for oq in mutated.open_questions]
    # Find the same question in the mutated snapshot (index should be same)
    target_oq = new_oqs[active_oq_index]
    new_oqs[active_oq_index] = target_oq.model_copy(
        update={
            "status": OpenQuestionStatus.ANSWERED,
            "resolution_note": resolution_note,
        }
    )

    candidate_data = {
        "project_id": mutated.project_id,
        "schema_version": mutated.schema_version,
        "brief_version": mutated.brief_version,  # Same version as mutation result (N+1)
        "created_at": ts,
        "stakeholders": [s.model_dump(mode="python") for s in mutated.stakeholders],
        "evidence": [ev.model_dump(mode="python") for ev in mutated.evidence],
        "brief_items": [bi.model_dump(mode="python") for bi in mutated.brief_items],
        "space_requests": [sr.model_dump(mode="python") for sr in mutated.space_requests],
        "usage_scenarios": [us.model_dump(mode="python") for us in mutated.usage_scenarios],
        "contradictions": [c.model_dump(mode="python") for c in mutated.contradictions],
        "open_questions": [oq.model_dump(mode="python") for oq in new_oqs],
    }

    return BriefSnapshot.model_validate(candidate_data)
