"""Tests for ElicitationCoverageEngine."""

from __future__ import annotations

from datetime import UTC, datetime

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
    Evidence,
    OpenQuestion,
    SpaceRequest,
    Stakeholder,
)
from brif_ai.conversation.elicitation.coverage import ElicitationCoverageEngine
from brif_ai.conversation.elicitation.models import ElicitationTopic
from brif_ai.core.models.common import SpaceFunction


def _dummy_snapshot() -> BriefSnapshot:
    return BriefSnapshot(
        project_id="proj_house",
        schema_version="v0",
        brief_version=1,
        created_at=datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
        stakeholders=[Stakeholder(id="stk_01", display_name="Ali", role="Mimar", active=True)],
        evidence=[
            Evidence(
                id="ev_01",
                source_type=EvidenceSource.CHAT,
                source_reference="msg_1",
                excerpt="4 kişiyiz",
            )
        ],
        brief_items=[],
        space_requests=[],
        usage_scenarios=[],
        contradictions=[],
        open_questions=[],
    )


def test_coverage_detects_covered_topics_from_snapshot_objects() -> None:
    snap = _dummy_snapshot()

    # Add brief item about 4 family members -> HOUSEHOLD covered
    item = BriefItem(
        id="bi_01",
        kind=BriefItemKind.PREFERENCE,
        normalized_statement="Dört kişilik aile için ev tasarlanacak",
        priority=Priority.MUST,
        stakeholder_ids=["stk_01"],
        evidence_ids=["ev_01"],
        confirmation_status=ConfirmationStatus.CONFIRMED,
    )
    # Add room request for kitchen -> KITCHEN_SERVICE covered
    sr = SpaceRequest(
        id="sr_01",
        display_name="Kapanabilen mutfak",
        space_function=SpaceFunction.COOKING,
        minimum_quantity=1,
        maximum_quantity=1,
        mandatory=True,
        stakeholder_ids=["stk_01"],
        evidence_ids=["ev_01"],
        confirmation_status=ConfirmationStatus.CONFIRMED,
    )

    snap_covered = snap.model_copy(update={"brief_items": [item], "space_requests": [sr]})

    engine = ElicitationCoverageEngine()
    covered = engine.evaluate_covered_topics(snap_covered)

    assert ElicitationTopic.HOUSEHOLD in covered
    assert ElicitationTopic.KITCHEN_SERVICE in covered
    assert ElicitationTopic.BUDGET_PRIORITY not in covered


def test_confirmed_laundry_room_brief_item_covers_storage_service() -> None:
    snap = _dummy_snapshot()
    item = BriefItem(
        id="bi_laundry_room",
        kind=BriefItemKind.NEED,
        normalized_statement="Çamaşır odası isteniyor.",
        priority=Priority.MUST,
        stakeholder_ids=["stk_01"],
        evidence_ids=["ev_01"],
        confirmation_status=ConfirmationStatus.CONFIRMED,
    )
    snap_with_laundry_room = snap.model_copy(update={"brief_items": [item]})

    covered = ElicitationCoverageEngine().evaluate_covered_topics(snap_with_laundry_room)

    assert ElicitationTopic.STORAGE_SERVICE in covered


def test_coverage_detects_open_and_answered_question_topics() -> None:
    snap = _dummy_snapshot()
    oq_open = OpenQuestion(
        id="oq_01",
        question="Giyinme odası istenecek mi?",
        reason="Depolama alanı belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.OPEN,
        topic_key="storage_service",
    )
    oq_answered = OpenQuestion(
        id="oq_02",
        question="Kaç kişisiniz?",
        reason="Nüfus belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.ANSWERED,
        resolution_note="4 kişi olarak teyit edildi",
        topic_key="household",
    )
    snap_oqs = snap.model_copy(update={"open_questions": [oq_open, oq_answered]})

    engine = ElicitationCoverageEngine()

    open_topics = engine.get_open_question_topics(snap_oqs)
    answered_topics = engine.get_answered_question_topics(snap_oqs)
    covered = engine.evaluate_covered_topics(snap_oqs)

    assert open_topics == [ElicitationTopic.STORAGE_SERVICE]
    assert answered_topics == [ElicitationTopic.HOUSEHOLD]
    assert ElicitationTopic.HOUSEHOLD in covered
