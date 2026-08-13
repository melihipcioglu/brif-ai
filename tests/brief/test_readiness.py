"""Tests for deterministic Brief Readiness Gate V0 evaluation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from brif_ai.brief.models.common import (
    BriefItemKind,
    ConfirmationStatus,
    ContradictionStatus,
    EvidenceSource,
    OpenQuestionStatus,
    Priority,
)
from brif_ai.brief.models.snapshot import (
    BriefItem,
    BriefSnapshot,
    Contradiction,
    Evidence,
    OpenQuestion,
    SpaceRequest,
    Stakeholder,
    UsageScenario,
)
from brif_ai.brief.readiness import (
    BriefReadinessEvaluator,
    ReadinessBlocker,
    ReadinessBlockerCode,
)
from brif_ai.conversation.elicitation.models import ElicitationTopic
from brif_ai.conversation.elicitation.planner import elicitation_topic_priority_order
from brif_ai.core.models.common import SpaceFunction

CANONICAL_TOPICS = [
    ElicitationTopic.HOUSEHOLD,
    ElicitationTopic.SPACE_PROGRAM,
    ElicitationTopic.ACCESSIBILITY,
    ElicitationTopic.SPATIAL_RELATIONSHIPS,
    ElicitationTopic.KITCHEN_SERVICE,
    ElicitationTopic.PRIVACY,
    ElicitationTopic.WORK_STUDY,
    ElicitationTopic.STORAGE_SERVICE,
    ElicitationTopic.OUTDOOR_USE,
    ElicitationTopic.DAILY_ROUTINES,
    ElicitationTopic.BUDGET_PRIORITY,
]


def _evidence() -> Evidence:
    return Evidence(
        id="evidence_1",
        source_type=EvidenceSource.CHAT,
        source_reference="chat:turn-1",
        excerpt="Readiness test evidence.",
    )


def _closed_topic_questions(
    *,
    excluded_topics: set[ElicitationTopic] | None = None,
    status: OpenQuestionStatus = OpenQuestionStatus.ANSWERED,
) -> list[OpenQuestion]:
    excluded = excluded_topics or set()
    return [
        OpenQuestion(
            id=f"oq_{topic.value}",
            question=f"{topic.value} konusu tamamlandı mı?",
            reason="Readiness coverage fixture.",
            related_brief_item_ids=[],
            status=status,
            resolution_note="Konu kullanıcı tarafından kapatıldı.",
            topic_key=topic.value,
        )
        for topic in reversed(CANONICAL_TOPICS)
        if topic not in excluded
    ]


def _snapshot(
    *,
    brief_items: list[BriefItem] | None = None,
    space_requests: list[SpaceRequest] | None = None,
    usage_scenarios: list[UsageScenario] | None = None,
    contradictions: list[Contradiction] | None = None,
    open_questions: list[OpenQuestion] | None = None,
) -> BriefSnapshot:
    return BriefSnapshot(
        project_id="project_1",
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime(2026, 8, 14, tzinfo=UTC),
        stakeholders=[
            Stakeholder(
                id="stakeholder_1",
                display_name="Ev Sahibi",
                role="CLIENT_OWNER",
                active=True,
            )
        ],
        evidence=[_evidence()],
        brief_items=brief_items or [],
        space_requests=space_requests or [],
        usage_scenarios=usage_scenarios or [],
        contradictions=contradictions or [],
        open_questions=open_questions or [],
    )


def _covered_snapshot(
    *,
    excluded_topics: set[ElicitationTopic] | None = None,
    status: OpenQuestionStatus = OpenQuestionStatus.ANSWERED,
    **updates: object,
) -> BriefSnapshot:
    snapshot = _snapshot(
        open_questions=_closed_topic_questions(
            excluded_topics=excluded_topics,
            status=status,
        )
    )
    return snapshot.model_copy(update=updates)


def _brief_item(
    item_id: str,
    confirmation_status: ConfirmationStatus,
    *,
    statement: str = "Teknik brief kaydı.",
) -> BriefItem:
    return BriefItem(
        id=item_id,
        kind=BriefItemKind.NEED,
        normalized_statement=statement,
        priority=Priority.MUST,
        stakeholder_ids=["stakeholder_1"],
        evidence_ids=["evidence_1"],
        confirmation_status=confirmation_status,
    )


def _space_request(
    request_id: str,
    confirmation_status: ConfirmationStatus,
) -> SpaceRequest:
    return SpaceRequest(
        id=request_id,
        display_name="Teknik servis alanı",
        space_function=SpaceFunction.STORAGE,
        minimum_quantity=1,
        maximum_quantity=1,
        mandatory=True,
        stakeholder_ids=["stakeholder_1"],
        evidence_ids=["evidence_1"],
        confirmation_status=confirmation_status,
    )


def _usage_scenario(
    scenario_id: str,
    confirmation_status: ConfirmationStatus,
) -> UsageScenario:
    return UsageScenario(
        id=scenario_id,
        title="Teknik kullanım",
        description="Tanımlı bir kullanım senaryosu.",
        stakeholder_ids=["stakeholder_1"],
        evidence_ids=["evidence_1"],
        confirmation_status=confirmation_status,
    )


def _contradiction(
    contradiction_id: str,
    status: ContradictionStatus,
) -> Contradiction:
    return Contradiction(
        id=contradiction_id,
        brief_item_ids=["brief_a", "brief_b"],
        description="İki brief kaydı birbiriyle çelişiyor.",
        status=status,
        resolution_note="Çelişki çözüldü." if status is ContradictionStatus.RESOLVED else None,
    )


def _supporting_brief_items() -> list[BriefItem]:
    return [
        _brief_item("brief_a", ConfirmationStatus.CONFIRMED),
        _brief_item("brief_b", ConfirmationStatus.CONFIRMED),
    ]


def _blocker_codes(result: object) -> list[ReadinessBlockerCode]:
    assert hasattr(result, "blockers")
    return [blocker.code for blocker in result.blockers]


def test_none_snapshot_is_not_ready_and_reports_all_topics() -> None:
    result = BriefReadinessEvaluator().evaluate(None)

    assert result.ready_for_next_stage is False
    assert result.covered_topics == []
    assert result.uncovered_topics == CANONICAL_TOPICS
    assert _blocker_codes(result) == [
        ReadinessBlockerCode.SNAPSHOT_MISSING,
        ReadinessBlockerCode.UNCOVERED_REQUIRED_TOPICS,
    ]


def test_empty_snapshot_is_blocked_by_uncovered_required_topics() -> None:
    result = BriefReadinessEvaluator().evaluate(_snapshot())

    assert result.ready_for_next_stage is False
    assert result.covered_topics == []
    assert result.uncovered_topics == CANONICAL_TOPICS
    assert _blocker_codes(result) == [ReadinessBlockerCode.UNCOVERED_REQUIRED_TOPICS]


def test_all_topics_covered_without_other_blockers_is_ready() -> None:
    result = BriefReadinessEvaluator().evaluate(_covered_snapshot())

    assert result.ready_for_next_stage is True
    assert result.covered_topics == CANONICAL_TOPICS
    assert result.uncovered_topics == []
    assert result.blockers == []


def test_one_required_topic_missing_is_not_ready() -> None:
    result = BriefReadinessEvaluator().evaluate(
        _covered_snapshot(excluded_topics={ElicitationTopic.BUDGET_PRIORITY})
    )

    assert result.ready_for_next_stage is False
    assert result.uncovered_topics == [ElicitationTopic.BUDGET_PRIORITY]
    assert _blocker_codes(result) == [ReadinessBlockerCode.UNCOVERED_REQUIRED_TOPICS]


def test_proposed_brief_item_blocks_even_when_it_provides_topic_coverage() -> None:
    snapshot = _covered_snapshot(
        excluded_topics={ElicitationTopic.BUDGET_PRIORITY},
        brief_items=[
            _brief_item(
                "pending_brief",
                ConfirmationStatus.PROPOSED,
                statement="Bütçe önceliği kalite olacak.",
            )
        ],
    )

    result = BriefReadinessEvaluator().evaluate(snapshot)

    assert result.uncovered_topics == []
    assert result.ready_for_next_stage is False
    assert _blocker_codes(result) == [ReadinessBlockerCode.PENDING_CONFIRMATIONS]
    assert result.blockers[0].related_ids == ["pending_brief"]


def test_proposed_space_request_blocks_readiness() -> None:
    result = BriefReadinessEvaluator().evaluate(
        _covered_snapshot(
            space_requests=[_space_request("pending_space", ConfirmationStatus.PROPOSED)]
        )
    )

    assert result.ready_for_next_stage is False
    assert _blocker_codes(result) == [ReadinessBlockerCode.PENDING_CONFIRMATIONS]
    assert result.blockers[0].related_ids == ["pending_space"]


def test_proposed_usage_scenario_blocks_readiness() -> None:
    result = BriefReadinessEvaluator().evaluate(
        _covered_snapshot(
            usage_scenarios=[_usage_scenario("pending_scenario", ConfirmationStatus.PROPOSED)]
        )
    )

    assert result.ready_for_next_stage is False
    assert _blocker_codes(result) == [ReadinessBlockerCode.PENDING_CONFIRMATIONS]
    assert result.blockers[0].related_ids == ["pending_scenario"]


def test_rejected_item_is_not_a_blocker() -> None:
    result = BriefReadinessEvaluator().evaluate(
        _covered_snapshot(brief_items=[_brief_item("rejected_brief", ConfirmationStatus.REJECTED)])
    )

    assert result.ready_for_next_stage is True
    assert result.blockers == []


def test_open_contradiction_blocks_readiness() -> None:
    result = BriefReadinessEvaluator().evaluate(
        _covered_snapshot(
            brief_items=_supporting_brief_items(),
            contradictions=[_contradiction("contradiction_open", ContradictionStatus.OPEN)],
        )
    )

    assert result.ready_for_next_stage is False
    assert _blocker_codes(result) == [ReadinessBlockerCode.OPEN_CONTRADICTIONS]
    assert result.blockers[0].related_ids == ["contradiction_open"]


def test_resolved_contradiction_is_not_a_blocker() -> None:
    result = BriefReadinessEvaluator().evaluate(
        _covered_snapshot(
            brief_items=_supporting_brief_items(),
            contradictions=[_contradiction("contradiction_resolved", ContradictionStatus.RESOLVED)],
        )
    )

    assert result.ready_for_next_stage is True
    assert result.blockers == []


def test_open_elicitation_question_blocks_readiness() -> None:
    questions = [
        *_closed_topic_questions(),
        OpenQuestion(
            id="open_household",
            question="Evde kaç kişi yaşayacak?",
            reason="Hane bilgisi açık.",
            related_brief_item_ids=[],
            status=OpenQuestionStatus.OPEN,
            topic_key=ElicitationTopic.HOUSEHOLD.value,
        ),
    ]
    result = BriefReadinessEvaluator().evaluate(_snapshot(open_questions=questions))

    assert result.ready_for_next_stage is False
    assert _blocker_codes(result) == [ReadinessBlockerCode.OPEN_QUESTIONS]
    assert result.blockers[0].related_ids == ["open_household"]


def test_open_non_elicitation_question_blocks_readiness() -> None:
    questions = [
        *_closed_topic_questions(),
        OpenQuestion(
            id="open_general",
            question="Genel karar teyit edilecek mi?",
            reason="Genel brief kararı açık.",
            related_brief_item_ids=[],
            status=OpenQuestionStatus.OPEN,
            topic_key="general",
        ),
    ]
    result = BriefReadinessEvaluator().evaluate(_snapshot(open_questions=questions))

    assert result.ready_for_next_stage is False
    assert _blocker_codes(result) == [ReadinessBlockerCode.OPEN_QUESTIONS]
    assert result.blockers[0].related_ids == ["open_general"]


@pytest.mark.parametrize(
    "status",
    [OpenQuestionStatus.ANSWERED, OpenQuestionStatus.DISMISSED],
)
def test_answered_and_dismissed_questions_are_not_blockers(
    status: OpenQuestionStatus,
) -> None:
    result = BriefReadinessEvaluator().evaluate(_covered_snapshot(status=status))

    assert result.ready_for_next_stage is True
    assert result.covered_topics == CANONICAL_TOPICS
    assert result.blockers == []


def test_multiple_blockers_and_related_ids_are_deterministic() -> None:
    questions = [
        *_closed_topic_questions(excluded_topics={ElicitationTopic.BUDGET_PRIORITY}),
        OpenQuestion(
            id="open_general",
            question="Genel karar açık mı?",
            reason="Genel karar bekleniyor.",
            related_brief_item_ids=[],
            status=OpenQuestionStatus.OPEN,
        ),
    ]
    result = BriefReadinessEvaluator().evaluate(
        _snapshot(
            brief_items=[
                *_supporting_brief_items(),
                _brief_item("pending_z", ConfirmationStatus.PROPOSED),
            ],
            space_requests=[_space_request("pending_a", ConfirmationStatus.PROPOSED)],
            usage_scenarios=[_usage_scenario("pending_m", ConfirmationStatus.PROPOSED)],
            contradictions=[
                _contradiction("contradiction_z", ContradictionStatus.OPEN),
                _contradiction("contradiction_a", ContradictionStatus.OPEN),
            ],
            open_questions=questions,
        )
    )

    assert result.ready_for_next_stage is False
    assert _blocker_codes(result) == [
        ReadinessBlockerCode.PENDING_CONFIRMATIONS,
        ReadinessBlockerCode.OPEN_CONTRADICTIONS,
        ReadinessBlockerCode.OPEN_QUESTIONS,
        ReadinessBlockerCode.UNCOVERED_REQUIRED_TOPICS,
    ]
    assert result.blockers[0].related_ids == ["pending_a", "pending_m", "pending_z"]
    assert result.blockers[1].related_ids == ["contradiction_a", "contradiction_z"]
    assert result.blockers[2].related_ids == ["open_general"]
    assert result.blockers[3].related_ids == []


def test_covered_and_uncovered_topic_order_is_canonical() -> None:
    selected_topics = {
        ElicitationTopic.DAILY_ROUTINES,
        ElicitationTopic.STORAGE_SERVICE,
        ElicitationTopic.HOUSEHOLD,
    }
    snapshot = _snapshot(
        open_questions=[
            question
            for question in _closed_topic_questions()
            if question.topic_key in {topic.value for topic in selected_topics}
        ]
    )

    result = BriefReadinessEvaluator().evaluate(snapshot)

    assert list(elicitation_topic_priority_order()) == CANONICAL_TOPICS
    assert set(CANONICAL_TOPICS) == set(ElicitationTopic)
    assert result.covered_topics == [
        ElicitationTopic.HOUSEHOLD,
        ElicitationTopic.STORAGE_SERVICE,
        ElicitationTopic.DAILY_ROUTINES,
    ]
    assert result.uncovered_topics == [
        topic for topic in CANONICAL_TOPICS if topic not in selected_topics
    ]


def test_evaluator_does_not_mutate_snapshot() -> None:
    snapshot = _covered_snapshot(
        space_requests=[_space_request("pending_space", ConfirmationStatus.PROPOSED)]
    )
    original = snapshot.model_dump(mode="python")

    BriefReadinessEvaluator().evaluate(snapshot)

    assert snapshot.model_dump(mode="python") == original


def test_readiness_contracts_are_frozen_and_forbid_extra_fields() -> None:
    blocker = ReadinessBlocker(
        code=ReadinessBlockerCode.OPEN_QUESTIONS,
        message="Açık soru var.",
    )

    with pytest.raises(ValidationError, match="frozen_instance"):
        blocker.message = "Değiştirilemez."

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ReadinessBlocker.model_validate(
            {
                "code": ReadinessBlockerCode.OPEN_QUESTIONS,
                "message": "Açık soru var.",
                "unexpected": True,
            }
        )
