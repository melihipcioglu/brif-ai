from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from brif_ai.brief.models.common import BriefItemKind, Priority
from brif_ai.brief.models.snapshot import BriefSnapshot, Stakeholder
from brif_ai.brief.mutation import (
    BriefItemProposalPayload,
    BriefMutationType,
    ProposedBriefMutation,
    SpaceRequestProposalPayload,
    UsageScenarioProposalPayload,
)
from brif_ai.core.models.common import SpaceFunction
from brif_ai.llm.contracts import (
    ActiveContextSnapshot,
    ArchitecturalIntentResult,
    ConversationRequest,
    LocalModelInfo,
    ProviderHealth,
)
from brif_ai.llm.prompts import build_user_prompt
from brif_ai.llm.settings import LocalLLMSettings


class MockAPIProvider:
    async def health(self) -> ProviderHealth:
        return ProviderHealth(provider="ollama", reachable=True)

    async def list_models(self) -> list[LocalModelInfo]:
        return [LocalModelInfo(name="local-model:latest", size=42)]

    async def interpret(
        self, request: ConversationRequest, output_schema: dict[str, object]
    ) -> ArchitecturalIntentResult:
        raise NotImplementedError("Not used in approval endpoint tests")


def sample_snapshot(project_id: str = "proj_house_2story") -> BriefSnapshot:
    return BriefSnapshot(
        project_id=project_id,
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime.now(timezone.utc),  # noqa: UP017
        stakeholders=[
            Stakeholder(
                id="stk_house_owner",
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
        open_questions=[],
    )


def test_approval_endpoint_succeeds_add_brief_item() -> None:
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_item_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Salon doğrudan bahçeye açılsın.",
            priority=Priority.MUST,
        ),
    )
    req_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",
        "proposal_fingerprint": "house|main|ground|living|study",
        "current_fingerprint": "house|main|ground|living|study",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Salon doğrudan bahçeye açılsın istiyorum.",
        "source_reference": "chatmsg_10",
    }
    response = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["resulting_snapshot"]["brief_version"] == 2
    assert len(data["resulting_snapshot"]["brief_items"]) == 1
    assert (
        data["resulting_snapshot"]["brief_items"][0]["normalized_statement"]
        == "Salon doğrudan bahçeye açılsın."
    )
    assert data["approval_record"]["proposal_status"] == "user_approved"


def test_approval_endpoint_succeeds_add_space_request() -> None:
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_space_01",
        mutation_type=BriefMutationType.ADD_SPACE_REQUEST,
        space_request=SpaceRequestProposalPayload(
            display_name="Misafir Odası",
            space_function=SpaceFunction.SLEEPING,
            minimum_quantity=1,
            maximum_quantity=2,
            mandatory=True,
        ),
    )
    req_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",
        "proposal_fingerprint": "house|main|ground|living|study",
        "current_fingerprint": "house|main|ground|living|study",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Bir misafir odası mutlaka olsun.",
        "source_reference": "chatmsg_11",
    }
    response = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["resulting_snapshot"]["brief_version"] == 2
    assert len(data["resulting_snapshot"]["space_requests"]) == 1
    assert data["resulting_snapshot"]["space_requests"][0]["display_name"] == "Misafir Odası"


def test_approval_endpoint_succeeds_add_usage_scenario() -> None:
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_usage_01",
        mutation_type=BriefMutationType.ADD_USAGE_SCENARIO,
        usage_scenario=UsageScenarioProposalPayload(
            title="Hafta Sonu Kahvaltısı",
            description="Mutfak ve teras arasında akıcı servis imkânı.",
        ),
    )
    req_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",
        "proposal_fingerprint": "house|main|ground|living|study",
        "current_fingerprint": "house|main|ground|living|study",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Hafta sonu kahvaltısı için geniş teras bağlantısı istiyoruz.",
        "source_reference": "chatmsg_12",
    }
    response = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["resulting_snapshot"]["brief_version"] == 2
    assert len(data["resulting_snapshot"]["usage_scenarios"]) == 1
    assert data["resulting_snapshot"]["usage_scenarios"][0]["title"] == "Hafta Sonu Kahvaltısı"


def test_approval_endpoint_version_increments_exactly_once() -> None:
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot()
    assert snapshot.brief_version == 1

    mutation = ProposedBriefMutation(
        mutation_id="mut_ver_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Çalışma odasında sessizlik sağlansın.",
            priority=Priority.MUST,
        ),
    )
    req_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",
        "proposal_fingerprint": "fp1",
        "current_fingerprint": "fp1",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Sessiz alan gerekli.",
        "source_reference": "chatmsg_13",
    }
    response = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["resulting_snapshot"]["brief_version"] == 2


def test_approval_endpoint_returns_correct_record() -> None:
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_rec_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Depolama alanı eklensin.",
            priority=Priority.SHOULD,
        ),
    )
    req_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",
        "proposal_fingerprint": "fp1",
        "current_fingerprint": "fp1",
        "proposal_generation_id": 2,
        "current_generation_id": 2,
        "user_message": "Depolama alanı olsun.",
        "source_reference": "chatmsg_14",
    }
    response = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert response.status_code == 200
    record = response.json()["approval_record"]
    assert record["proposal_status"] == "user_approved"
    assert record["generation_id"] == 2
    assert record["mutation_id"] == "mut_rec_01"
    assert record["resulting_brief_version"] == 2


def test_stale_fingerprint_rejected() -> None:
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_stale_fp",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Test statement",
            priority=Priority.MUST,
        ),
    )
    req_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",
        "proposal_fingerprint": "old_fingerprint",
        "current_fingerprint": "new_fingerprint",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Test message",
        "source_reference": "chatmsg_15",
    }
    response = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert response.status_code == 409
    assert response.json()["success"] is False
    assert "uyumsuz" in response.json()["error"] or "eski" in response.json()["error"].lower()


def test_stale_generation_rejected() -> None:
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_stale_gen",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Test statement",
            priority=Priority.MUST,
        ),
    )
    req_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",
        "proposal_fingerprint": "fp1",
        "current_fingerprint": "fp1",
        "proposal_generation_id": 1,
        "current_generation_id": 2,
        "user_message": "Test message",
        "source_reference": "chatmsg_16",
    }
    response = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert response.status_code == 409
    assert response.json()["success"] is False
    assert "jenerasyon" in response.json()["error"].lower()


def test_wrong_project_snapshot_rejected() -> None:
    """Real wrong-project snapshot validation test:

    current_project_id = proj_house_2story
    brief_snapshot.project_id = proj_tower_50floor
    otherwise valid mutation and valid stakeholder inside tower snapshot
    Expected: HTTP 422, input snapshot unchanged, domain mutation not applied.
    """
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    tower_snapshot = BriefSnapshot(
        project_id="proj_tower_50floor",
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime.now(timezone.utc),  # noqa: UP017
        stakeholders=[
            Stakeholder(
                id="stk_tower_owner",
                display_name="Kule Yatırımcısı",
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
    tower_snapshot_copy = tower_snapshot.model_copy(deep=True)

    mutation = ProposedBriefMutation(
        mutation_id="mut_wrong_proj",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        target_stakeholder_id="stk_tower_owner",
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Toplantı salonu eklensin.",
            priority=Priority.MUST,
        ),
    )
    req_payload = {
        "brief_snapshot": tower_snapshot.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",  # Mismatched current_project_id!
        "proposal_fingerprint": "fp1",
        "current_fingerprint": "fp1",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Toplantı salonu ekleyin.",
        "source_reference": "chatmsg_17",
    }
    response = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert response.status_code == 422
    assert "project_id" in str(response.json()).lower()
    # Input snapshot remains unchanged
    assert tower_snapshot.brief_version == tower_snapshot_copy.brief_version
    assert len(tower_snapshot.brief_items) == 0


def test_invalid_stakeholder_rejected() -> None:
    """Separate test for invalid stakeholder ID inside same-project snapshot."""
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot("proj_house_2story")
    mutation = ProposedBriefMutation(
        mutation_id="mut_bad_stk",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        target_stakeholder_id="stk_non_existent",
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Test statement",
            priority=Priority.MUST,
        ),
    )
    req_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",
        "proposal_fingerprint": "fp1",
        "current_fingerprint": "fp1",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Test message",
        "source_reference": "chatmsg_17b",
    }
    response = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert response.status_code == 422
    assert response.json()["success"] is False
    assert "stakeholder" in response.json()["error"].lower()


def test_malformed_mutation_rejected() -> None:
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot()
    req_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_mutation": {
            "mutation_id": "bad_mut",
            "mutation_type": "ADD_BRIEF_ITEM",
            # missing brief_item payload
        },
        "current_project_id": "proj_house_2story",
        "proposal_fingerprint": "fp1",
        "current_fingerprint": "fp1",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Test message",
        "source_reference": "chatmsg_18",
    }
    response = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert response.status_code == 422


def test_failed_approval_leaves_input_snapshot_unchanged() -> None:
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot()
    snapshot_copy = snapshot.model_copy(deep=True)

    mutation = ProposedBriefMutation(
        mutation_id="mut_stale_gen",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Test statement",
            priority=Priority.MUST,
        ),
    )
    req_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",
        "proposal_fingerprint": "fp1",
        "current_fingerprint": "fp1",
        "proposal_generation_id": 1,
        "current_generation_id": 2,  # stale!
        "user_message": "Test message",
        "source_reference": "chatmsg_19",
    }
    response = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert response.status_code == 409
    assert snapshot.brief_version == snapshot_copy.brief_version
    assert snapshot.model_dump() == snapshot_copy.model_dump()


def test_source_reference_becomes_chat_evidence_source_reference() -> None:
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_ev_ref",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Ebeveyn banyosu eklensin.",
            priority=Priority.MUST,
        ),
    )
    req_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",
        "proposal_fingerprint": "fp1",
        "current_fingerprint": "fp1",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Ebeveyn banyosu olmalı.",
        "source_reference": "chatmsg_42",
    }
    response = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert response.status_code == 200
    res_snapshot = response.json()["resulting_snapshot"]
    assert len(res_snapshot["evidence"]) == 1
    assert res_snapshot["evidence"][0]["source_reference"] == "chatmsg_42"


def test_original_requirement_message_becomes_evidence_excerpt() -> None:
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot()
    original_msg = "Mutfak terasa doğrudan açılmalı, sabah güneşi alsın."
    mutation = ProposedBriefMutation(
        mutation_id="mut_ev_excerpt",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Mutfak-teras doğrudan bağlantısı.",
            priority=Priority.MUST,
        ),
    )
    req_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",
        "proposal_fingerprint": "fp1",
        "current_fingerprint": "fp1",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": original_msg,
        "source_reference": "chatmsg_43",
    }
    response = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert response.status_code == 200
    res_snapshot = response.json()["resulting_snapshot"]
    assert res_snapshot["evidence"][0]["excerpt"] == original_msg


def test_exact_replay_remains_idempotent() -> None:
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_idempotent",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Balkon genişletilsin.",
            priority=Priority.SHOULD,
        ),
    )
    req_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",
        "proposal_fingerprint": "fp1",
        "current_fingerprint": "fp1",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Balkon genişletilsin.",
        "source_reference": "chatmsg_44",
    }
    # First approval -> version becomes 2
    resp1 = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert resp1.status_code == 200
    snap1 = resp1.json()["resulting_snapshot"]
    assert snap1["brief_version"] == 2

    # Second approval with updated snapshot (exact replay of same mutation & source_reference)
    req_payload["brief_snapshot"] = snap1
    resp2 = client.post("/api/v1/brief/mutations/approve", json=req_payload)
    assert resp2.status_code == 200
    snap2 = resp2.json()["resulting_snapshot"]
    assert snap2["brief_version"] == 2  # Idempotent: version did not increment!
    assert len(snap2["brief_items"]) == 1


def test_conversation_request_rejects_brief_snapshot_from_different_project() -> None:
    wrong_snapshot = sample_snapshot("proj_tower_50floor")
    with pytest.raises(ValueError, match="project_id must match active context"):
        ConversationRequest(
            active_context=ActiveContextSnapshot(
                project_id="proj_house_2story",
                building_id="bldg_main",
                level_id="lvl_ground",
                zone_id="zone_living",
                entity_id="space_study",
                context_fingerprint="house|main|ground|living|study",
                generation_id=1,
            ),
            message="Test message",
            brief_snapshot=wrong_snapshot,
        )


def test_prompt_includes_confirmed_active_brief_content() -> None:
    client = TestClient(create_app(LocalLLMSettings(enabled=True), MockAPIProvider()))
    snapshot = sample_snapshot()
    # Approve space request first
    mutation = ProposedBriefMutation(
        mutation_id="mut_prompt_01",
        mutation_type=BriefMutationType.ADD_SPACE_REQUEST,
        space_request=SpaceRequestProposalPayload(
            display_name="Çalışma Odası",
            space_function=SpaceFunction.WORK,
            minimum_quantity=1,
            mandatory=True,
        ),
    )
    resp = client.post(
        "/api/v1/brief/mutations/approve",
        json={
            "brief_snapshot": snapshot.model_dump(mode="json"),
            "proposed_mutation": mutation.model_dump(mode="json"),
            "current_project_id": "proj_house_2story",
            "proposal_fingerprint": "fp1",
            "current_fingerprint": "fp1",
            "proposal_generation_id": 1,
            "current_generation_id": 1,
            "user_message": "Çalışma odası eklensin.",
            "source_reference": "chatmsg_45",
        },
    )
    approved_snapshot = BriefSnapshot.model_validate(resp.json()["resulting_snapshot"])

    request = ConversationRequest(
        active_context=ActiveContextSnapshot(
            project_id="proj_house_2story",
            building_id="bldg_main",
            level_id="lvl_ground",
            zone_id="zone_living",
            entity_id="space_study",
            context_fingerprint="house|main|ground|living|study",
            generation_id=1,
        ),
        message="Yeni istek...",
        brief_snapshot=approved_snapshot,
    )
    prompt = build_user_prompt(request)
    data = json.loads(prompt)
    assert "active_brief" in data
    assert data["active_brief"]["brief_version"] == 2
    assert data["active_brief"]["space_requests"][0]["display_name"] == "Çalışma Odası"


def test_prompt_does_not_expose_unnecessary_provenance_noise() -> None:
    snapshot = sample_snapshot()
    request = ConversationRequest(
        active_context=ActiveContextSnapshot(
            project_id="proj_house_2story",
            building_id="bldg_main",
            level_id="lvl_ground",
            zone_id="zone_living",
            entity_id="space_study",
            context_fingerprint="house|main|ground|living|study",
            generation_id=1,
        ),
        message="Yeni istek...",
        brief_snapshot=snapshot,
    )
    prompt = build_user_prompt(request)
    data = json.loads(prompt)
    active_brief = data["active_brief"]
    # Verify no raw internal provenance/evidence/stakeholder IDs leaked in prompt payload
    assert "evidence" not in active_brief
    assert "stakeholders" not in active_brief
    assert "schema_version" not in active_brief


def test_validate_demo_brief_snapshot_seeds() -> None:
    """Requirement 7: Deterministically validate brief_snapshots.demo.json

    seeds against the real BriefSnapshot model for proj_house_2story, proj_tower_50floor,
    and proj_campus_multiblock.
    """
    json_path = (
        Path(__file__).parents[2]
        / "prototypes"
        / "conversation_ui_v0"
        / "data"
        / "brief_snapshots.demo.json"
    )
    assert json_path.exists(), f"Demo seeds file missing at {json_path}"

    with json_path.open("r", encoding="utf-8") as f:
        demo_seeds = json.load(f)

    expected_project_ids = [
        "proj_house_2story",
        "proj_tower_50floor",
        "proj_campus_multiblock",
    ]

    for project_id in expected_project_ids:
        assert project_id in demo_seeds, f"Missing demo snapshot seed for '{project_id}'"
        snapshot_data = demo_seeds[project_id]
        validated = BriefSnapshot.model_validate(snapshot_data)
        assert validated.project_id == project_id
        assert validated.brief_version == 1
        assert len(validated.stakeholders) == 1
