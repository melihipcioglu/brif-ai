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
    assert response.result.needs_follow_up is True
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
