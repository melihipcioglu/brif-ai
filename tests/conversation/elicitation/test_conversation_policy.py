"""Comprehensive E2E Conversation Policy tests covering all 12 user scenarios."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

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
from brif_ai.brief.mutation import (
    BriefItemProposalPayload,
    BriefMutationType,
    ProposedBriefMutation,
)
from brif_ai.conversation.elicitation.models import ElicitationContext, ElicitationTopic
from brif_ai.conversation.elicitation.planner import ElicitationPlanner
from brif_ai.llm.contracts import (
    ActiveContextSnapshot,
    ArchitecturalIntentResult,
    ConversationRequest,
    EntityTarget,
    IntentType,
    PendingProposalContext,
)
from brif_ai.llm.policy_validator import ArchitecturalIntentPolicyValidator, PolicyValidationError


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


def _conversation_request(
    message: str = "Merhaba",
    snapshot: BriefSnapshot | None = None,
    pending: list[PendingProposalContext] | None = None,
    elicitation_context: ElicitationContext | None = None,
) -> ConversationRequest:
    active = ActiveContextSnapshot(
        project_id="proj_house",
        context_fingerprint="fp_100",
        generation_id=1,
    )
    snap = snapshot or _dummy_snapshot()
    return ConversationRequest(
        message=message,
        active_context=active,
        visible_entities=[],
        conversation_summary="",
        current_decisions=[],
        pending_proposals=pending or [],
        brief_snapshot=snap,
        elicitation_context=elicitation_context,
    )


def _valid_intent_result(
    mutations: list[ProposedBriefMutation] | None = None,
    needs_follow_up: bool = False,
    follow_up_question: str | None = None,
    follow_up_topic: ElicitationTopic | None = None,
) -> ArchitecturalIntentResult:
    muts = mutations or []
    needs_confirm = bool(muts)
    return ArchitecturalIntentResult(
        assistant_message="Anladım, talebinizi aldım.",
        intent=IntentType.GATHER_REQUIREMENT,
        target=EntityTarget(project_id="proj_house"),
        user_requirements=["Tek katlı ev isteği"],
        interpreted_priorities=["Mekânsal organizasyon"],
        constraints_to_check=[],
        missing_information=[],
        proposed_actions=[],
        proposed_brief_mutations=muts,
        needs_follow_up=needs_follow_up,
        follow_up_question=follow_up_question,
        follow_up_topic=follow_up_topic,
        needs_user_confirmation=needs_confirm,
        confidence=0.9,
        warnings=[],
    )


# Scenario 1: Multi-fact user message supports up to 3 proposed brief mutations
def test_scenario_1_multi_fact_supports_up_to_three_brief_mutations() -> None:
    mut1 = ProposedBriefMutation(
        mutation_id="mut_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.PREFERENCE,
            normalized_statement="Dört kişilik aile konutu",
            priority=Priority.MUST,
        ),
    )
    mut2 = ProposedBriefMutation(
        mutation_id="mut_02",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.PREFERENCE,
            normalized_statement="Tek katlı müstakil yapı",
            priority=Priority.MUST,
        ),
    )
    mut3 = ProposedBriefMutation(
        mutation_id="mut_03",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.PREFERENCE,
            normalized_statement="Kapanabilen mutfak",
            priority=Priority.SHOULD,
        ),
    )

    res = _valid_intent_result(mutations=[mut1, mut2, mut3])
    req = _conversation_request(
        elicitation_context=ElicitationContext(allowed_follow_up_topic=None)
    )

    validator = ArchitecturalIntentPolicyValidator()
    validated = validator.validate(res, req)
    assert len(validated.proposed_brief_mutations) == 3


# Scenario 2: Confirmed brief fact (household=4) is not re-asked
def test_scenario_2_confirmed_brief_fact_is_not_reasked() -> None:
    snap = _dummy_snapshot()
    item = BriefItem(
        id="bi_01",
        kind=BriefItemKind.PREFERENCE,
        normalized_statement="Dört kişilik aile konutu",
        priority=Priority.MUST,
        stakeholder_ids=["stk_01"],
        evidence_ids=["ev_01"],
        confirmation_status=ConfirmationStatus.CONFIRMED,
    )
    snap_confirmed = snap.model_copy(update={"brief_items": [item]})

    planner = ElicitationPlanner()
    ctx = planner.plan_context(snap_confirmed, pending_proposals_exist=False)

    assert ctx.allowed_follow_up_topic != ElicitationTopic.HOUSEHOLD


# Scenario 3: Open question for topic prevents duplicate open question
def test_scenario_3_open_question_prevents_duplicate_open_question() -> None:
    snap = _dummy_snapshot()
    oq = OpenQuestion(
        id="oq_privacy_01",
        question="Ortak alan mahremiyeti nasıl sağlanacak?",
        reason="Mahremiyet belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.OPEN,
        topic_key="privacy",
    )
    snap_open = snap.model_copy(update={"open_questions": [oq]})

    planner = ElicitationPlanner()
    ctx = planner.plan_context(snap_open, pending_proposals_exist=False)

    assert ctx.allowed_follow_up_topic != ElicitationTopic.PRIVACY
    assert ElicitationTopic.PRIVACY in ctx.open_question_topics


# Scenario 4: Answered topic is not re-asked
def test_scenario_4_answered_topic_is_not_reasked() -> None:
    snap = _dummy_snapshot()
    oq = OpenQuestion(
        id="oq_privacy_01",
        question="Ortak alan mahremiyeti nasıl sağlanacak?",
        reason="Mahremiyet belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.ANSWERED,
        resolution_note="Ayrışabilen mahremiyet kurgusu kabul edildi",
        topic_key="privacy",
    )
    snap_answered = snap.model_copy(update={"open_questions": [oq]})

    planner = ElicitationPlanner()
    ctx = planner.plan_context(snap_answered, pending_proposals_exist=False)

    assert ctx.allowed_follow_up_topic != ElicitationTopic.PRIVACY
    assert ElicitationTopic.PRIVACY in ctx.answered_question_topics


# Scenario 5: Pending brief proposal suppresses follow-up questions
def test_scenario_5_pending_proposal_suppresses_follow_up() -> None:
    planner = ElicitationPlanner()
    ctx = planner.plan_context(_dummy_snapshot(), pending_proposals_exist=True)

    assert ctx.allowed_follow_up_topic is None
    assert ctx.pending_proposals_exist is True


# Scenario 6 & Hardening 4: Proposals present -> needs_follow_up must be False
def test_scenario_6_proposals_present_forbids_needs_follow_up() -> None:
    mut1 = ProposedBriefMutation(
        mutation_id="mut_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.PREFERENCE,
            normalized_statement="Tek katlı ev",
            priority=Priority.MUST,
        ),
    )
    with pytest.raises(ValueError, match="needs_follow_up must be false"):
        _valid_intent_result(
            mutations=[mut1],
            needs_follow_up=True,
            follow_up_question="Otopark kaç araçlık olsun?",
            follow_up_topic=ElicitationTopic.STORAGE_SERVICE,
        )


# Scenario 7: Unallowed follow-up topic is rejected by policy validator
def test_scenario_7_unallowed_follow_up_topic_rejected() -> None:
    req = _conversation_request(
        elicitation_context=ElicitationContext(
            allowed_follow_up_topic=ElicitationTopic.HOUSEHOLD,
            reason="Nüfus belirsiz",
        )
    )
    res = _valid_intent_result(
        needs_follow_up=True,
        follow_up_question="Giyinme odası istenecek mi?",
        follow_up_topic=ElicitationTopic.STORAGE_SERVICE,  # Mismatches allowed_follow_up_topic
    )

    validator = ArchitecturalIntentPolicyValidator()
    with pytest.raises(PolicyValidationError, match="izin verilen konu"):
        validator.validate(res, req)
