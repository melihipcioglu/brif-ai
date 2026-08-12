"""Tests for ElicitationPlanner."""

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
    Stakeholder,
)
from brif_ai.conversation.elicitation.models import ElicitationTopic
from brif_ai.conversation.elicitation.planner import ElicitationPlanner


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


def test_planner_selects_first_priority_topic_for_empty_snapshot() -> None:
    snap = _dummy_snapshot()
    planner = ElicitationPlanner()
    ctx = planner.plan_context(snap, pending_proposals_exist=False)

    assert ctx.allowed_follow_up_topic == ElicitationTopic.HOUSEHOLD
    assert ctx.pending_proposals_exist is False


def test_planner_suppresses_follow_up_when_pending_proposals_exist() -> None:
    snap = _dummy_snapshot()
    planner = ElicitationPlanner()
    ctx = planner.plan_context(snap, pending_proposals_exist=True)

    assert ctx.allowed_follow_up_topic is None
    assert ctx.pending_proposals_exist is True
    assert "Bekleyen öneriler" in ctx.reason


def test_planner_skips_covered_and_open_topics() -> None:
    snap = _dummy_snapshot()
    # HOUSEHOLD is covered by brief item
    item = BriefItem(
        id="bi_01",
        kind=BriefItemKind.PREFERENCE,
        normalized_statement="Dört kişilik aile",
        priority=Priority.MUST,
        stakeholder_ids=["stk_01"],
        evidence_ids=["ev_01"],
        confirmation_status=ConfirmationStatus.CONFIRMED,
    )
    # SPACE_PROGRAM has an OPEN question
    oq = OpenQuestion(
        id="oq_01",
        question="Kaç katlı ev istiyorsunuz?",
        reason="Kat sayısı belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.OPEN,
        topic_key="space_program",
    )
    snap_updated = snap.model_copy(update={"brief_items": [item], "open_questions": [oq]})

    planner = ElicitationPlanner()
    ctx = planner.plan_context(snap_updated, pending_proposals_exist=False)

    # Next priority after HOUSEHOLD and SPACE_PROGRAM is ACCESSIBILITY
    assert ctx.allowed_follow_up_topic == ElicitationTopic.ACCESSIBILITY
