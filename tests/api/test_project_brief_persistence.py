"""BRIF.AI — API Tests for Project Brief Persistence and Approval Boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from apps.api.main import create_app
from fastapi.testclient import TestClient

from brif_ai.brief.models.common import BriefItemKind, Priority
from brif_ai.brief.models.snapshot import BriefSnapshot, Stakeholder
from brif_ai.brief.mutation import (
    BriefItemProposalPayload,
    BriefMutationType,
    ProposedBriefMutation,
)
from brif_ai.brief.persistence.json_repository import JSONBriefRepository
from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    ConversationRequest,
    LocalModelInfo,
    ProviderHealth,
)
from brif_ai.llm.settings import LocalLLMSettings


class MockAPIProvider:
    async def health(self) -> ProviderHealth:
        return ProviderHealth(provider="ollama", reachable=True)

    async def list_models(self) -> list[LocalModelInfo]:
        return [LocalModelInfo(name="local-model:latest", size=42)]

    async def interpret(
        self, request: ConversationRequest, output_schema: dict[str, object]
    ) -> ArchitecturalIntentResult:
        raise NotImplementedError("Not used in persistence API tests")


def sample_snapshot(project_id: str = "proj_house_2story", version: int = 1) -> BriefSnapshot:
    return BriefSnapshot(
        project_id=project_id,
        schema_version="brief.v0",
        brief_version=version,
        created_at=datetime.now(timezone.utc),  # noqa: UP017
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
        open_questions=[],
    )


def test_get_uninitialized_project_brief_returns_404(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    client = TestClient(
        create_app(LocalLLMSettings(enabled=True), MockAPIProvider(), brief_repository=repo)
    )

    response = client.get("/api/v1/projects/proj_non_existent/brief")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_initialize_project_brief_endpoint(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    client = TestClient(
        create_app(LocalLLMSettings(enabled=True), MockAPIProvider(), brief_repository=repo)
    )
    snap = sample_snapshot("proj_house_2story", 1)

    # 1. Successful initialization -> HTTP 200
    res_init = client.post(
        "/api/v1/projects/proj_house_2story/brief/initialize",
        json=snap.model_dump(mode="json"),
    )
    assert res_init.status_code == 200
    assert res_init.json()["project_id"] == "proj_house_2story"
    assert res_init.json()["brief_version"] == 1

    # 2. Get latest -> HTTP 200
    res_get = client.get("/api/v1/projects/proj_house_2story/brief")
    assert res_get.status_code == 200
    assert res_get.json()["brief_version"] == 1

    # 3. List versions -> [1]
    res_ver = client.get("/api/v1/projects/proj_house_2story/brief/versions")
    assert res_ver.status_code == 200
    assert res_ver.json()["versions"] == [1]

    # 4. Get specific version -> HTTP 200
    res_v1 = client.get("/api/v1/projects/proj_house_2story/brief/versions/1")
    assert res_v1.status_code == 200
    assert res_v1.json()["brief_version"] == 1


def test_approve_mutation_server_authoritative_and_stale_409(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    client = TestClient(
        create_app(LocalLLMSettings(enabled=True), MockAPIProvider(), brief_repository=repo)
    )

    # Initialize brief
    snap = sample_snapshot("proj_house_2story", 1)
    client.post(
        "/api/v1/projects/proj_house_2story/brief/initialize",
        json=snap.model_dump(mode="json"),
    )

    mutation = ProposedBriefMutation(
        mutation_id="mut_api_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Mutfak genişletilsin.",
            priority=Priority.MUST,
        ),
    )

    # 1. Successful approval on server snapshot -> version 2
    app_payload = {
        "brief_snapshot": snap.model_dump(mode="json"),
        "proposed_mutation": mutation.model_dump(mode="json"),
        "current_project_id": "proj_house_2story",
        "expected_brief_version": 1,
        "proposal_fingerprint": "fp1",
        "current_fingerprint": "fp1",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Mutfak genişletilsin.",
        "source_reference": "chatmsg_01",
    }
    res_app = client.post("/api/v1/brief/mutations/approve", json=app_payload)
    assert res_app.status_code == 200
    assert res_app.json()["success"] is True
    assert res_app.json()["resulting_snapshot"]["brief_version"] == 2

    # 2. Stale approval attempt -> HTTP 409
    # (client still sends expected_brief_version=1 when server is at v2)
    res_stale = client.post("/api/v1/brief/mutations/approve", json=app_payload)
    assert res_stale.status_code == 409
    assert res_stale.json()["success"] is False
    assert "stale" in res_stale.json()["error"].lower()


def test_path_traversal_via_api_returns_422(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    client = TestClient(
        create_app(LocalLLMSettings(enabled=True), MockAPIProvider(), brief_repository=repo)
    )

    response = client.get("/api/v1/projects/..%2Ffoo/brief")
    assert response.status_code in {422, 404}
