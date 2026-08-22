"""LEVEL 3 — Live Ollama E2E Integration Suite for BRIF.AI Elicitation V1."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from brif_ai.brief.models.common import ConfirmationStatus, EvidenceSource, OpenQuestionStatus
from brif_ai.brief.models.snapshot import (
    BriefSnapshot,
    Evidence,
    OpenQuestion,
    SpaceRequest,
    Stakeholder,
)
from brif_ai.conversation.elicitation.models import ElicitationTopic
from brif_ai.core.models.common import SpaceFunction
from brif_ai.llm.contracts import (
    ActiveContextSnapshot,
    ConversationRequest,
    IntentType,
)
from brif_ai.llm.ollama_provider import OllamaProvider
from brif_ai.llm.service import LocalLLMConversationService
from brif_ai.llm.settings import LocalLLMSettings


def is_ollama_live() -> bool:
    try:
        res = httpx.get("http://127.0.0.1:11434/api/tags", timeout=2.0)
        return res.status_code == 200 and len(res.json().get("models", [])) > 0
    except Exception:
        return False


def get_live_model_name() -> str:
    try:
        res = httpx.get("http://127.0.0.1:11434/api/tags", timeout=2.0)
        payload: object = res.json()
        if isinstance(payload, dict):
            models = payload.get("models")
            if isinstance(models, list) and models:
                first_model = models[0]
                if isinstance(first_model, dict) and "name" in first_model:
                    return str(first_model["name"])
    except Exception:
        pass
    return "qwen3:4b-instruct"


pytestmark = pytest.mark.skipif(
    not is_ollama_live(),
    reason="Local Ollama server is not reachable on 127.0.0.1:11434",
)


def sample_snapshot(project_id: str = "proj_live_test", version: int = 1) -> BriefSnapshot:
    return BriefSnapshot(
        project_id=project_id,
        schema_version="brief.v0",
        brief_version=version,
        created_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(
                id="stk_owner",
                display_name="Ev Sahibi",
                role="CLIENT_OWNER",
                active=True,
            )
        ],
        evidence=[
            Evidence(
                id="ev_live_1",
                source_type=EvidenceSource.CHAT,
                source_reference="chat_live",
                excerpt="Live test conversation",
            )
        ],
        brief_items=[],
        space_requests=[],
        usage_scenarios=[],
        contradictions=[],
        open_questions=[],
    )


def live_service() -> LocalLLMConversationService:
    model_name = get_live_model_name()
    settings = LocalLLMSettings(
        enabled=True,
        provider="ollama",
        base_url="http://127.0.0.1:11434",
        model=model_name,
    )
    provider = OllamaProvider(settings)
    return LocalLLMConversationService(settings, provider)


def build_request(message: str, snapshot: BriefSnapshot) -> ConversationRequest:
    return ConversationRequest(
        message=message,
        active_context=ActiveContextSnapshot(
            project_id=snapshot.project_id,
            context_fingerprint="fp_live_01",
            generation_id=1,
        ),
        visible_entities=[],
        conversation_summary="",
        current_decisions=[],
        pending_proposals=[],
        brief_snapshot=snapshot,
    )


# ============================================================================
# SCENARIO A: Fresh Elicitation Starter ("Başlayalım.")
# ============================================================================


def test_live_scenario_a_neutral_starter() -> None:
    service = live_service()
    snap = sample_snapshot()
    req = build_request("Başlayalım.", snap)

    response = asyncio.run(service.interpret(req))

    assert response.success is True
    assert response.result is not None
    assert response.result.intent == IntentType.GATHER_REQUIREMENT
    assert response.result.needs_follow_up is True
    assert response.result.follow_up_topic == ElicitationTopic.HOUSEHOLD
    assert response.result.follow_up_question == "Evde kaç kişi yaşayacak?"
    assert response.result.proposed_actions == []
    assert response.result.proposed_brief_mutations == []


# ============================================================================
# SCENARIO B: Active Household Question Answered Strict ("Ben, eşim ve iki çocuğum.")
# ============================================================================


def test_live_scenario_b_household_answer() -> None:
    service = live_service()
    snap = sample_snapshot()
    oq_household = OpenQuestion(
        id="oq_household_1",
        question="Evde kaç kişi yaşayacak?",
        reason="Nüfus belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.OPEN,
        topic_key="household",
    )
    snap = snap.model_copy(update={"open_questions": [oq_household]})
    req = build_request("Ben, eşim ve iki çocuğum.", snap)

    response = asyncio.run(service.interpret(req))

    assert response.success is True
    res = response.result
    assert res is not None
    assert res.answers_current_open_question is True
    assert res.needs_follow_up is False
    assert res.needs_user_confirmation is True
    assert res.proposed_actions == []  # NO plan actions!
    assert len(res.proposed_brief_mutations) == 1

    mutation = res.proposed_brief_mutations[0]
    assert mutation.mutation_type.value == "ADD_BRIEF_ITEM"
    assert mutation.brief_item is not None
    statement = mutation.brief_item.normalized_statement.casefold()
    # STRICT ASSERTIONS:
    assert "3 kişi" not in statement
    assert "4 kişi" in statement or "4" in statement
    assert res.household_composition is not None
    assert res.household_composition.total_count == 4
    assert res.household_composition.adult_count == 2
    assert res.household_composition.child_count == 2
    assert res.household_composition.child_ages == []


def test_live_scenario_b_household_3_trials() -> None:
    """Run 3 repeated real Ollama trials for 'Ben, eşim ve iki çocuğum.'"""
    service = live_service()
    snap = sample_snapshot()
    oq_household = OpenQuestion(
        id="oq_household_1",
        question="Evde kaç kişi yaşayacak?",
        reason="Nüfus belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.OPEN,
        topic_key="household",
    )
    snap = snap.model_copy(update={"open_questions": [oq_household]})
    req = build_request("Ben, eşim ve iki çocuğum.", snap)

    for trial in range(1, 4):
        response = asyncio.run(service.interpret(req))
        assert response.success is True, f"Trial {trial} failed"
        res = response.result
        assert res is not None, f"Trial {trial} result is None"
        assert res.answers_current_open_question is True, (
            f"Trial {trial} answers_current_open_question is False"
        )
        assert res.needs_follow_up is False, f"Trial {trial} needs_follow_up is True"
        assert res.needs_user_confirmation is True, (
            f"Trial {trial} needs_user_confirmation is False"
        )
        assert res.proposed_actions == [], f"Trial {trial} proposed actions non-empty"
        assert len(res.proposed_brief_mutations) == 1, f"Trial {trial} mutations len != 1"

        mutation = res.proposed_brief_mutations[0]
        assert mutation.mutation_type.value == "ADD_BRIEF_ITEM"
        assert mutation.brief_item is not None
        statement = mutation.brief_item.normalized_statement.casefold()
        assert "3 kişi" not in statement, f"Trial {trial} falsely claimed 3 kişi: {statement!r}"
        assert "4" in statement or "4 kişi" in statement, f"Trial {trial} missing 4: {statement!r}"

        # Structured LLM Household Composition Assertions:
        assert res.household_composition is not None, f"Trial {trial} missing household_composition"
        assert res.household_composition.total_count == 4, f"Trial {trial} total_count != 4"
        assert res.household_composition.adult_count == 2, f"Trial {trial} adult_count != 2"
        assert res.household_composition.child_count == 2, f"Trial {trial} child_count != 2"


# ============================================================================
# SCENARIO C: Unrelated Message While Question OPEN ("Bu arada mutfak kapalı olsun.")
# ============================================================================


def test_live_scenario_c_unrelated_requirement_keeps_household_open() -> None:
    service = live_service()
    snap = sample_snapshot()
    oq_household = OpenQuestion(
        id="oq_household_1",
        question="Evde kaç kişi yaşayacak?",
        reason="Nüfus belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.OPEN,
        topic_key="household",
    )
    snap = snap.model_copy(update={"open_questions": [oq_household]})
    req = build_request("Bu arada mutfak kapalı olsun.", snap)

    response = asyncio.run(service.interpret(req))

    assert response.success is True
    res = response.result
    assert res is not None
    # Must NOT claim to answer household question!
    assert res.answers_current_open_question is False
    assert res.needs_follow_up is False
    assert res.proposed_actions == []


# ============================================================================
# SCENARIO D: 5 Natural Paraphrases of Household Answers
# ============================================================================


@pytest.mark.parametrize(
    "user_msg",
    [
        "Dört kişiyiz, iki çocuğumuz var.",
        "Evde eşimle ben ve iki oğlum yaşayacağız.",
        "2 yetişkin 2 çocuk.",
        "Biz dört kişilik bir aileyiz.",
        "Ben, eşim, 4 ve 8 yaşlarında iki çocuğum.",
    ],
)
def test_live_scenario_d_household_paraphrases(user_msg: str) -> None:
    service = live_service()
    snap = sample_snapshot()
    oq_household = OpenQuestion(
        id="oq_household_1",
        question="Evde kaç kişi yaşayacak?",
        reason="Nüfus belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.OPEN,
        topic_key="household",
    )
    snap = snap.model_copy(update={"open_questions": [oq_household]})
    req = build_request(user_msg, snap)

    response = asyncio.run(service.interpret(req))

    assert response.success is True
    res = response.result
    assert res is not None
    assert res.answers_current_open_question is True
    assert res.needs_follow_up is False
    assert res.proposed_actions == []
    assert len(res.proposed_brief_mutations) == 1
    mutation = res.proposed_brief_mutations[0]
    assert mutation.mutation_type.value == "ADD_BRIEF_ITEM"
    assert mutation.brief_item is not None
    statement = mutation.brief_item.normalized_statement.casefold()
    assert "3 kişi" not in statement
    assert "4" in statement or "4 kişi" in statement
    comp = res.household_composition
    assert comp is not None
    assert comp.total_count == 4
    if user_msg == "Biz dört kişilik bir aileyiz.":
        assert comp.adult_count is None
        assert comp.child_count is None
    else:
        assert comp.adult_count == 2
        assert comp.child_count == 2
    if "4 ve 8 yaşlarında" in user_msg:
        assert comp.child_ages == [4, 8]


# ============================================================================
# SCENARIO E: Adversarial Greeting ("Merhaba") While Question OPEN
# ============================================================================


def test_live_scenario_e_adversarial_greeting_keeps_household_open() -> None:
    service = live_service()
    snap = sample_snapshot()
    oq_household = OpenQuestion(
        id="oq_household_1",
        question="Evde kaç kişi yaşayacak?",
        reason="Nüfus belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.OPEN,
        topic_key="household",
    )
    snap = snap.model_copy(update={"open_questions": [oq_household]})
    req = build_request("Merhaba", snap)

    response = asyncio.run(service.interpret(req))

    assert response.success is True
    res = response.result
    assert res is not None
    assert res.answers_current_open_question is False
    assert res.needs_follow_up is False
    assert res.proposed_actions == []
    assert res.proposed_brief_mutations == []


# ============================================================================
# SCENARIO F: Natural Spatial Preference ("Yatak odaları birbirine yakın olsun.")
# ============================================================================


def test_live_scenario_f_spatial_relationship_bedroom_near() -> None:
    service = live_service()
    snap = sample_snapshot()
    snap = snap.model_copy(
        update={
            "space_requests": [
                SpaceRequest(
                    id="sr_bed",
                    display_name="Yatak Odası",
                    space_function=SpaceFunction.SLEEPING,
                    minimum_quantity=2,
                    mandatory=True,
                    confirmation_status=ConfirmationStatus.CONFIRMED,
                    stakeholder_ids=["stk_owner"],
                    evidence_ids=["ev_live_1"],
                ),
                SpaceRequest(
                    id="sr_living",
                    display_name="Salon",
                    space_function=SpaceFunction.LIVING,
                    minimum_quantity=1,
                    mandatory=True,
                    confirmation_status=ConfirmationStatus.CONFIRMED,
                    stakeholder_ids=["stk_owner"],
                    evidence_ids=["ev_live_1"],
                ),
            ]
        }
    )
    req = build_request("Yatak odaları birbirine yakın olsun.", snap)

    response = asyncio.run(service.interpret(req))

    assert response.success is True
    res = response.result
    assert res is not None
    assert res.intent == IntentType.MODIFY_RELATIONSHIP
    assert len(res.proposed_spatial_relationships) == 1
    assert res.proposed_actions == []
    assert res.proposed_brief_mutations == []
    assert res.needs_user_confirmation is True
    assert res.needs_follow_up is False

    rel = res.proposed_spatial_relationships[0]
    assert rel.source_space_id == "sn_bed_01"
    assert rel.target_space_id == "sn_bed_02"
    assert rel.relation_type.value == "NEAR"


# ============================================================================
# SCENARIO G: Natural Spatial Preference ("Mutfak salona yakın olsun.")
# ============================================================================


def test_live_scenario_g_spatial_relationship_kitchen_living_near() -> None:
    service = live_service()
    snap = sample_snapshot()
    snap = snap.model_copy(
        update={
            "space_requests": [
                SpaceRequest(
                    id="sr_kitchen",
                    display_name="Mutfak",
                    space_function=SpaceFunction.COOKING,
                    minimum_quantity=1,
                    mandatory=True,
                    confirmation_status=ConfirmationStatus.CONFIRMED,
                    stakeholder_ids=["stk_owner"],
                    evidence_ids=["ev_live_1"],
                ),
                SpaceRequest(
                    id="sr_living",
                    display_name="Salon",
                    space_function=SpaceFunction.LIVING,
                    minimum_quantity=1,
                    mandatory=True,
                    confirmation_status=ConfirmationStatus.CONFIRMED,
                    stakeholder_ids=["stk_owner"],
                    evidence_ids=["ev_live_1"],
                ),
            ]
        }
    )
    req = build_request("Mutfak salona yakın olsun.", snap)

    response = asyncio.run(service.interpret(req))

    assert response.success is True
    res = response.result
    assert res is not None
    assert len(res.proposed_spatial_relationships) == 1
    rel = res.proposed_spatial_relationships[0]
    assert rel.source_space_id == "sn_kitchen_01"
    assert rel.target_space_id == "sn_living_01"
    assert rel.relation_type.value == "NEAR"


# ============================================================================
# SCENARIO H: Negative Spatial Preference ("Misafir bölümü çocuk odalarından uzak olsun.")
# ============================================================================


def test_live_scenario_h_spatial_relationship_guest_child_separated() -> None:
    service = live_service()
    snap = sample_snapshot()
    snap = snap.model_copy(
        update={
            "space_requests": [
                SpaceRequest(
                    id="sr_guest",
                    display_name="Misafir Odası",
                    space_function=SpaceFunction.SLEEPING,
                    minimum_quantity=1,
                    mandatory=True,
                    confirmation_status=ConfirmationStatus.CONFIRMED,
                    stakeholder_ids=["stk_owner"],
                    evidence_ids=["ev_live_1"],
                ),
                SpaceRequest(
                    id="sr_child",
                    display_name="Çocuk Odası",
                    space_function=SpaceFunction.SLEEPING,
                    minimum_quantity=1,
                    mandatory=True,
                    confirmation_status=ConfirmationStatus.CONFIRMED,
                    stakeholder_ids=["stk_owner"],
                    evidence_ids=["ev_live_1"],
                ),
            ]
        }
    )
    req = build_request("Misafir bölümü çocuk odalarından uzak olsun.", snap)

    response = asyncio.run(service.interpret(req))

    assert response.success is True
    res = response.result
    assert res is not None
    assert len(res.proposed_spatial_relationships) == 1
    rel = res.proposed_spatial_relationships[0]
    assert rel.source_space_id == "sn_guest_01"
    assert rel.target_space_id == "sn_child_01"
    assert rel.relation_type.value == "SEPARATED_FROM"
