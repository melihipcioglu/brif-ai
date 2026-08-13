from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from brif_ai.llm.contracts import (
    PLAN_CHANGE_ACTIONS,
    ArchitecturalIntentResult,
    ConversationRequest,
    LocalModelInfo,
    ProviderHealth,
)
from brif_ai.llm.provider import ProviderUnavailableError
from brif_ai.llm.service import (
    LLM_DISABLED_MESSAGE,
    LocalLLMConversationService,
    StaleContextError,
)
from brif_ai.llm.settings import LocalLLMSettings

from .test_contracts import valid_result_data
from .test_policy_validator import assert_no_internal_ids, conversation_request


class MockProvider:
    def __init__(self, result: ArchitecturalIntentResult) -> None:
        self.result = result
        self.interpret_calls = 0
        self.schema: dict[str, object] | None = None

    async def health(self) -> ProviderHealth:
        return ProviderHealth(provider="mock", reachable=True)

    async def list_models(self) -> list[LocalModelInfo]:
        return [LocalModelInfo(name="local-model:latest")]

    async def interpret(
        self, request: ConversationRequest, output_schema: dict[str, object]
    ) -> ArchitecturalIntentResult:
        self.interpret_calls += 1
        self.schema = output_schema
        return self.result


def service(enabled: bool = True) -> tuple[LocalLLMConversationService, MockProvider]:
    provider = MockProvider(ArchitecturalIntentResult.model_validate(valid_result_data()))
    settings = LocalLLMSettings(enabled=enabled, model="local-model:latest")
    return LocalLLMConversationService(settings, provider), provider


def test_valid_structured_result_passes_policy() -> None:
    llm_service, provider = service()
    response = asyncio.run(llm_service.interpret(conversation_request()))

    assert response.success is True
    assert response.result is not None
    assert response.context_fingerprint == "house|main|ground|living|study"
    assert provider.schema == ArchitecturalIntentResult.model_json_schema()


def test_neutral_start_constrains_provider_schema() -> None:
    data = valid_result_data()
    data.update(
        {
            "assistant_message": "?nce hane yap?s?n? netle?tirelim.",
            "intent": "gather_requirement",
            "target": {
                "project_id": None,
                "building_id": None,
                "level_id": None,
                "zone_id": None,
                "entity_id": None,
            },
            "user_requirements": [],
            "interpreted_priorities": [],
            "constraints_to_check": [],
            "missing_information": ["Hane yap?s? hen?z netle?medi."],
            "proposed_actions": [],
            "proposed_brief_mutations": [],
            "answers_current_open_question": False,
            "needs_follow_up": True,
            "follow_up_question": "Evde ka? ki?i ya?ayacak?",
            "follow_up_topic": "household",
            "needs_user_confirmation": False,
            "warnings": [],
            "confidence": 0.95,
        }
    )

    provider = MockProvider(ArchitecturalIntentResult.model_validate(data))
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"),
        provider,
    )

    from brif_ai.conversation.elicitation.planner import ElicitationPlanner
    from brif_ai.llm.service import _build_provider_output_schema

    request = conversation_request(entity_id=None).model_copy(
        update={
            "message": "Başlayalım.",
            "elicitation_context": ElicitationPlanner().plan_context(
                conversation_request().brief_snapshot
            ),
        }
    )

    schema = _build_provider_output_schema(request)
    properties = schema["properties"]
    assert properties["intent"]["enum"] == ["gather_requirement"]
    assert properties["needs_follow_up"]["enum"] == [True]
    assert properties["follow_up_topic"]["enum"] == ["household"]
    assert properties["needs_user_confirmation"]["enum"] == [False]
    assert properties["answers_current_open_question"]["enum"] == [False]
    assert properties["proposed_actions"]["maxItems"] == 0
    assert properties["proposed_brief_mutations"]["maxItems"] == 0
    assert properties["user_requirements"]["maxItems"] == 0
    assert properties["warnings"]["maxItems"] == 0

    response = asyncio.run(llm_service.interpret(request))
    assert response.success is True
    assert response.result is not None
    assert response.result.assistant_message == "Evde kaç kişi yaşayacak?"


def test_follow_up_wording_is_server_authoritative() -> None:
    data = valid_result_data()
    data.update(
        {
            "assistant_message": "Salon ve mutfak ili\u015fkisini konu\u015fal\u0131m.",
            "intent": "gather_requirement",
            "target": {
                "project_id": None,
                "building_id": None,
                "level_id": None,
                "zone_id": None,
                "entity_id": None,
            },
            "user_requirements": [],
            "interpreted_priorities": [],
            "constraints_to_check": [],
            "missing_information": [],
            "proposed_actions": [],
            "proposed_brief_mutations": [],
            "answers_current_open_question": False,
            "needs_follow_up": True,
            "follow_up_question": "Salon ve mutfak nas\u0131l ili\u015fkili olsun?",
            "follow_up_topic": "household",
            "needs_user_confirmation": False,
            "warnings": [],
            "confidence": 0.9,
        }
    )

    provider = MockProvider(ArchitecturalIntentResult.model_validate(data))
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"),
        provider,
    )
    request = conversation_request(entity_id=None).model_copy(
        update={"message": "Ba\u015flayal\u0131m."}
    )

    response = asyncio.run(llm_service.interpret(request))

    assert response.result is not None
    assert response.result.follow_up_topic.value == "household"
    assert response.result.follow_up_question == "Evde ka\u00e7 ki\u015fi ya\u015fayacak?"
    assert response.result.assistant_message == "Evde ka\u00e7 ki\u015fi ya\u015fayacak?"


def test_llm_disabled_does_not_call_provider() -> None:
    llm_service, provider = service(enabled=False)
    response = asyncio.run(llm_service.interpret(conversation_request()))

    assert response.success is False
    assert response.error == LLM_DISABLED_MESSAGE
    assert provider.interpret_calls == 0


def test_stale_fingerprint_is_rejected() -> None:
    with pytest.raises(StaleContextError, match="Eski bağlama"):
        LocalLLMConversationService.ensure_current_context("old", "current")


def test_user_approval_only_creates_proposal_record() -> None:
    llm_service, _provider = service()
    action = ArchitecturalIntentResult.model_validate(valid_result_data()).proposed_actions[0]
    approved_at = datetime(2026, 8, 1, tzinfo=timezone.utc)  # noqa: UP017

    record = llm_service.record_user_approval(
        action,
        "same-fingerprint",
        "same-fingerprint",
        approved_at=approved_at,
    )

    assert record.model_dump(mode="json") == {
        "proposal_status": "user_approved",
        "approved_at": "2026-08-01T00:00:00Z",
        "context_fingerprint": "same-fingerprint",
        "proposed_action": action.model_dump(mode="json"),
    }


@pytest.mark.parametrize(
    ("message", "intent"),
    [
        (
            "Ebeveyn banyosu yataktan görünmesin ve kuzey tarafında olsun.",
            "modify_relationship",
        ),
        ("Bu iki plan üst üste gelince ne olduğunu anlamadım.", "explain_plan"),
        ("Çalışma odası sessiz olsun ama tamamen kopuk olmasın.", "modify_relationship"),
    ],
)
def test_scenarios_a_b_and_e(message: str, intent: str) -> None:
    data = valid_result_data()
    data["intent"] = intent
    if intent == "explain_plan":
        data["proposed_actions"] = [
            {
                "action_type": "explain_plan",
                "target_entity_id": "space_study",
                "description": "Plan çakışmasını açıkla.",
                "requires_user_confirmation": False,
            }
        ]
    request = conversation_request().model_copy(update={"message": message})
    provider = MockProvider(ArchitecturalIntentResult.model_validate(data))
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"), provider
    )

    response = asyncio.run(llm_service.interpret(request))

    assert response.result is not None
    assert response.result.intent.value == intent


def test_scenario_c_without_active_entity_requires_follow_up() -> None:
    data = valid_result_data()
    data["target"] = {
        "project_id": "proj_house_2story",
        "building_id": "bldg_main",
        "level_id": "lvl_ground",
        "zone_id": "zone_living",
        "entity_id": None,
    }
    data["proposed_actions"] = []
    data["needs_user_confirmation"] = False
    data["needs_follow_up"] = True
    data["follow_up_question"] = "Hangi mekânı düzenlemek istersiniz?"
    data["follow_up_topic"] = "household"
    provider = MockProvider(ArchitecturalIntentResult.model_validate(data))
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"), provider
    )

    response = asyncio.run(llm_service.interpret(conversation_request(entity_id=None)))

    assert response.result is not None
    assert response.result.needs_follow_up is True


def test_out_of_scope_room_request_becomes_safe_follow_up() -> None:
    data = valid_result_data()
    data["intent"] = "request_visual_preference"
    target = data["target"]
    assert isinstance(target, dict)
    target["entity_id"] = "space_master_bathroom"
    actions = data["proposed_actions"]
    assert isinstance(actions, list)
    actions[0]["target_entity_id"] = "space_master_bathroom"
    actions[0]["description"] = "space_master_bathroom kuzey yönüne alınsın."
    request = conversation_request().model_copy(
        update={"message": "Ebeveyn banyosu yataktan görünmesin ve kuzey tarafında olsun."}
    )
    original_request = request.model_dump()
    provider = MockProvider(ArchitecturalIntentResult.model_validate(data))
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"), provider
    )

    response = asyncio.run(llm_service.interpret(request))

    assert response.success is True
    assert response.error is None
    assert response.result is not None
    assert response.result.intent.value == "modify_relationship"
    assert response.result.target.entity_id is None
    assert response.result.needs_follow_up is False
    assert response.result.needs_user_confirmation is False
    assert not any(
        action.action_type in PLAN_CHANGE_ACTIONS for action in response.result.proposed_actions
    )
    assert "güvenlik kurallarını geçemedi" not in response.result.assistant_message
    assert_no_internal_ids(response.result)
    assert request.model_dump() == original_request


def test_active_relationship_request_stays_a_confirmation_only_suggestion() -> None:
    data = valid_result_data()
    data["intent"] = "modify_space"
    actions = data["proposed_actions"]
    assert isinstance(actions, list)
    actions[0].update(
        {
            "action_type": "suggest_relationship_change",
            "description": "Akustik bağlantıyı koruyacak bir tampon öner.",
        }
    )
    request = conversation_request().model_copy(
        update={"message": "Çalışma odası sessiz olsun ama tamamen kopuk olmasın."}
    )
    original_request = request.model_dump()
    provider = MockProvider(ArchitecturalIntentResult.model_validate(data))
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"), provider
    )

    response = asyncio.run(llm_service.interpret(request))

    assert response.result is not None
    assert response.result.intent.value == "modify_relationship"
    assert response.result.needs_user_confirmation is True
    assert response.result.proposed_actions[0].requires_user_confirmation is True
    assert request.model_dump() == original_request


def test_scenario_f_provider_failure_preserves_request_state() -> None:
    class OfflineProvider(MockProvider):
        async def interpret(
            self, request: ConversationRequest, output_schema: dict[str, object]
        ) -> ArchitecturalIntentResult:
            raise ProviderUnavailableError("offline")

    request = conversation_request()
    original = request.model_dump()
    provider = OfflineProvider(ArchitecturalIntentResult.model_validate(valid_result_data()))
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"), provider
    )

    with pytest.raises(ProviderUnavailableError):
        asyncio.run(llm_service.interpret(request))

    assert request.model_dump() == original


def test_successful_record_brief_mutation_approval() -> None:
    from brif_ai.brief.models.common import BriefItemKind, Priority
    from brif_ai.brief.models.snapshot import BriefSnapshot, Stakeholder
    from brif_ai.brief.mutation import (
        BriefItemProposalPayload,
        BriefMutationType,
        ProposedBriefMutation,
    )

    snapshot = BriefSnapshot(
        project_id="proj_01",
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime.now(timezone.utc),  # noqa: UP017
        stakeholders=[
            Stakeholder(
                id="stk_client_owner",
                display_name="Melih İpçioğlu",
                role="CLIENT_OWNER",
                active=True,
            )
        ],
        evidence=[],
        brief_items=[],
        space_requests=[],
        usage_scenarios=[],
        contradictions=[],
        open_questions=[],
    )
    llm_service, _provider = service()
    orig_snapshot_dump = snapshot.model_dump(mode="python")

    mutation = ProposedBriefMutation(
        mutation_id="mut_rec_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Mutfak ile teras doğrudan bağlantılı olsun.",
            priority=Priority.MUST,
        ),
    )

    fp = "house|main|ground|living|kitchen"
    gen_id = 7
    approved_at = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)  # noqa: UP017

    new_snapshot, record = llm_service.record_brief_mutation_approval(
        proposal_fingerprint=fp,
        current_fingerprint=fp,
        proposal_generation_id=gen_id,
        current_generation_id=gen_id,
        proposed_mutation=mutation,
        user_message="Mutfak ile teras doğrudan bağlantılı olsun.",
        snapshot=snapshot,
        approved_at=approved_at,
    )

    assert new_snapshot is not None
    assert record is not None
    assert len(new_snapshot.brief_items) == len(snapshot.brief_items) + 1
    assert (
        new_snapshot.brief_items[-1].normalized_statement
        == "Mutfak ile teras doğrudan bağlantılı olsun."
    )

    assert record.proposal_status == "user_approved"
    assert record.approved_at == approved_at
    assert record.context_fingerprint == fp
    assert record.generation_id == gen_id
    assert record.mutation_id == "mut_rec_01"
    assert record.proposed_brief_mutation == mutation
    assert record.resulting_brief_version == new_snapshot.brief_version

    assert new_snapshot.brief_version == snapshot.brief_version + 1
    assert snapshot.model_dump(mode="python") == orig_snapshot_dump


def test_active_open_question_schema_forbids_new_follow_up() -> None:
    from brif_ai.conversation.elicitation.models import (
        ElicitationContext,
        ElicitationTopic,
    )
    from brif_ai.llm.service import _build_provider_output_schema

    request = conversation_request().model_copy(
        update={
            "message": "Ben, e?im ve iki ?ocu?um.",
            "elicitation_context": ElicitationContext(
                allowed_follow_up_topic=None,
                reason="An existing household question is OPEN.",
                pending_proposals_exist=False,
                open_question_topics=[ElicitationTopic.HOUSEHOLD],
                answered_question_topics=[],
            ),
        }
    )

    schema = _build_provider_output_schema(request)
    properties = schema.get("properties")

    assert isinstance(properties, dict)
    assert properties["needs_follow_up"]["enum"] == [False]
    assert properties["follow_up_question"] == {"type": "null"}
    assert properties["follow_up_topic"] == {"type": "null"}
    assert properties["needs_user_confirmation"]["enum"] == [True]
    assert properties["intent"]["enum"] == ["gather_requirement"]
    assert properties["proposed_actions"]["maxItems"] == 0
    assert properties["proposed_brief_mutations"]["maxItems"] == 1
    assert "household_composition" in schema["required"]
    assert properties["household_composition"] == {"$ref": "#/$defs/HouseholdComposition"}
    household_def = schema["$defs"]["HouseholdComposition"]
    assert set(household_def["required"]) == {
        "total_count",
        "adult_count",
        "child_count",
        "child_ages",
        "notes",
    }


def _active_household_request(message: str) -> ConversationRequest:
    from brif_ai.brief.models.common import OpenQuestionStatus
    from brif_ai.brief.models.snapshot import BriefSnapshot, OpenQuestion, Stakeholder

    snapshot = BriefSnapshot(
        project_id="proj_house_2story",
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime(2026, 8, 13, tzinfo=timezone.utc),  # noqa: UP017
        stakeholders=[
            Stakeholder(
                id="stk_owner",
                display_name="Ev Sahibi",
                role="CLIENT_OWNER",
                active=True,
            )
        ],
        evidence=[],
        brief_items=[],
        space_requests=[],
        usage_scenarios=[],
        contradictions=[],
        open_questions=[
            OpenQuestion(
                id="oq_household",
                question="Evde kaç kişi yaşayacak?",
                reason="Hane yapısı henüz bilinmiyor.",
                related_brief_item_ids=[],
                status=OpenQuestionStatus.OPEN,
                topic_key="household",
            )
        ],
    )
    return conversation_request(entity_id=None).model_copy(
        update={
            "message": message,
            "visible_entities": [],
            "brief_snapshot": snapshot,
        }
    )


def _stale_household_result(
    *,
    total_count: int | None,
    adult_count: int | None,
    child_count: int | None,
    child_ages: list[int] | None = None,
) -> ArchitecturalIntentResult:
    data = valid_result_data()
    data.update(
        {
            "assistant_message": "Salon yerleşimini değerlendirebiliriz.",
            "intent": "gather_requirement",
            "target": {
                "project_id": "proj_house_2story",
                "building_id": None,
                "level_id": None,
                "zone_id": None,
                "entity_id": None,
            },
            "user_requirements": ["Salon geniş olsun."],
            "interpreted_priorities": [],
            "constraints_to_check": [],
            "missing_information": [],
            "proposed_actions": [],
            "proposed_brief_mutations": [],
            "household_composition": {
                "total_count": total_count,
                "adult_count": adult_count,
                "child_count": child_count,
                "child_ages": child_ages or [],
                "notes": None,
            },
            "answers_current_open_question": False,
            "needs_follow_up": False,
            "follow_up_question": None,
            "follow_up_topic": None,
            "needs_user_confirmation": False,
            "confidence": 0.8,
            "warnings": [],
        }
    )
    return ArchitecturalIntentResult.model_validate(data)


def test_active_household_reconciles_real_false_negative_and_builds_canonical_proposal() -> None:
    from brif_ai.brief.models.common import BriefItemKind, OpenQuestionStatus, Priority
    from brif_ai.brief.mutation import BriefMutationType
    from brif_ai.llm.contracts import IntentType

    request = _active_household_request("Ben, eşim ve iki çocuğum.")
    assert request.brief_snapshot is not None
    original_snapshot = request.brief_snapshot.model_dump(mode="python")
    provider = MockProvider(
        _stale_household_result(total_count=3, adult_count=1, child_count=2)
    )
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"),
        provider,
    )

    response = asyncio.run(llm_service.interpret(request))

    assert response.success is True
    result = response.result
    assert result is not None
    assert result.intent is IntentType.GATHER_REQUIREMENT
    assert result.household_composition is not None
    assert result.household_composition.total_count == 4
    assert result.household_composition.adult_count == 2
    assert result.household_composition.child_count == 2
    assert result.answers_current_open_question is True
    assert result.proposed_actions == []
    assert result.needs_follow_up is False
    assert result.follow_up_question is None
    assert result.follow_up_topic is None
    assert result.needs_user_confirmation is True
    assert len(result.proposed_brief_mutations) == 1

    mutation = result.proposed_brief_mutations[0]
    assert mutation.mutation_type is BriefMutationType.ADD_BRIEF_ITEM
    assert mutation.brief_item is not None
    assert mutation.brief_item.kind is BriefItemKind.CONTEXT
    assert mutation.brief_item.priority is Priority.MUST
    assert (
        mutation.brief_item.normalized_statement
        == "Evde 4 kişi yaşayacak (2 yetişkin, 2 çocuk)."
    )

    assert request.brief_snapshot.model_dump(mode="python") == original_snapshot
    assert request.brief_snapshot.brief_version == 1
    assert request.brief_snapshot.open_questions[0].status is OpenQuestionStatus.OPEN


def test_active_household_drops_child_ages_not_grounded_in_current_message() -> None:
    request = _active_household_request("Ben, eşim ve iki çocuğum.")
    provider = MockProvider(
        _stale_household_result(
            total_count=3,
            adult_count=1,
            child_count=2,
            child_ages=[2, 5],
        )
    )
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"),
        provider,
    )

    response = asyncio.run(llm_service.interpret(request))

    assert response.result is not None
    composition = response.result.household_composition
    assert composition is not None
    assert composition.total_count == 4
    assert composition.adult_count == 2
    assert composition.child_count == 2
    assert composition.child_ages == []
    mutation = response.result.proposed_brief_mutations[0]
    assert mutation.brief_item is not None
    assert (
        mutation.brief_item.normalized_statement
        == "Evde 4 kişi yaşayacak (2 yetişkin, 2 çocuk)."
    )


def test_active_household_keeps_child_ages_grounded_in_current_message() -> None:
    request = _active_household_request(
        "Ben, eşim ve 4 ve 8 yaşlarında iki çocuğum."
    )
    provider = MockProvider(
        _stale_household_result(
            total_count=4,
            adult_count=2,
            child_count=2,
            child_ages=[4, 8],
        )
    )
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"),
        provider,
    )

    response = asyncio.run(llm_service.interpret(request))

    assert response.result is not None
    composition = response.result.household_composition
    assert composition is not None
    assert composition.child_ages == [4, 8]
    mutation = response.result.proposed_brief_mutations[0]
    assert mutation.brief_item is not None
    assert (
        mutation.brief_item.normalized_statement
        == "Evde 4 kişi yaşayacak (2 yetişkin, 2 çocuk: 4, 8 yaşlarında)."
    )


def test_unrelated_message_rejects_stale_household_extraction() -> None:
    request = _active_household_request("Bu arada mutfak kapalı olsun.")
    assert request.brief_snapshot is not None
    original_snapshot = request.brief_snapshot.model_dump(mode="python")
    provider = MockProvider(
        _stale_household_result(total_count=3, adult_count=1, child_count=2)
    )
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"),
        provider,
    )

    response = asyncio.run(llm_service.interpret(request))

    assert response.result is not None
    assert response.result.answers_current_open_question is False
    assert response.result.household_composition is None
    assert response.result.proposed_actions == []
    assert response.result.proposed_brief_mutations == []
    assert response.result.needs_user_confirmation is False
    assert request.brief_snapshot.model_dump(mode="python") == original_snapshot


def test_household_service_does_not_use_text_fallback_as_primary_extraction() -> None:
    request = _active_household_request("Ben, eşim ve iki çocuğum.")
    provider = MockProvider(
        _stale_household_result(
            total_count=None,
            adult_count=None,
            child_count=None,
        )
    )
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"),
        provider,
    )

    response = asyncio.run(llm_service.interpret(request))

    assert response.result is not None
    assert response.result.answers_current_open_question is False
    assert response.result.household_composition is None
    assert response.result.proposed_brief_mutations == []
    assert response.result.needs_user_confirmation is False


def test_household_total_only_does_not_invent_subgroups() -> None:
    request = _active_household_request("Biz dört kişilik bir aileyiz.")
    provider = MockProvider(
        _stale_household_result(total_count=4, adult_count=2, child_count=2)
    )
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"),
        provider,
    )

    response = asyncio.run(llm_service.interpret(request))

    assert response.result is not None
    composition = response.result.household_composition
    assert composition is not None
    assert composition.total_count == 4
    assert composition.adult_count is None
    assert composition.child_count is None
    assert response.result.answers_current_open_question is True
    assert len(response.result.proposed_brief_mutations) == 1
    mutation = response.result.proposed_brief_mutations[0]
    assert mutation.brief_item is not None
    assert mutation.brief_item.normalized_statement == "Evde 4 kişi yaşayacak."


def test_greeting_does_not_invent_household_mutation() -> None:
    request = _active_household_request("Merhaba")
    provider = MockProvider(
        _stale_household_result(total_count=3, adult_count=1, child_count=2)
    )
    llm_service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"),
        provider,
    )

    response = asyncio.run(llm_service.interpret(request))

    assert response.result is not None
    assert response.result.answers_current_open_question is False
    assert response.result.proposed_brief_mutations == []
    assert response.result.household_composition is None
