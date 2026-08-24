"""API tests for Site Geometry Approval and Plan Input State integration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

import pytest
from apps.api.main import create_app
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from brif_ai.brief.models.common import (
    ConfirmationStatus,
    EvidenceSource,
    OpenQuestionStatus,
    Priority,
)
from brif_ai.brief.models.snapshot import (
    BriefSnapshot,
    Evidence,
    OpenQuestion,
    SpaceRequest,
    Stakeholder,
)
from brif_ai.brief.persistence import JSONBriefRepository
from brif_ai.conversation.elicitation.models import ElicitationTopic
from brif_ai.core.models.common import SpaceFunction
from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    ConversationRequest,
    LocalModelInfo,
    ProposedSiteGeometry,
    ProviderHealth,
    SiteGeometryApprovalRequest,
)
from brif_ai.llm.settings import LocalLLMSettings
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialNode,
    SpatialRelationship,
    SpatialRelationshipGraph,
    SpatialRelationType,
)
from brif_ai.spatial.persistence import JSONSpatialRelationshipRepository
from brif_ai.spatial.plan_input import (
    AuthoritativePlanInputState,
    JSONPlanInputStateRepository,
)
from brif_ai.spatial.site.approval_evidence import (
    SiteApprovalEvidenceRepository,
    SiteEvidencePersistenceError,
)
from brif_ai.spatial.site.models import SiteGeometryRole, SitePoint

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


class ApiTestEnv(TypedDict):
    client: TestClient
    brief_repo: JSONBriefRepository
    spatial_repo: JSONSpatialRelationshipRepository
    plan_input_repo: JSONPlanInputStateRepository
    site_evidence_repo: SiteApprovalEvidenceRepository


def _closed_topic_questions() -> list[OpenQuestion]:
    return [
        OpenQuestion(
            id=f"oq_{topic.value}",
            question=f"{topic.value} tamamlandı mı?",
            reason="Ready brief fixture.",
            related_brief_item_ids=[],
            status=OpenQuestionStatus.ANSWERED,
            resolution_note="Tamamlandı.",
            topic_key=topic.value,
        )
        for topic in CANONICAL_TOPICS
    ]


class MockProvider:
    async def health(self) -> ProviderHealth:
        return ProviderHealth(provider="ollama", reachable=True)

    async def list_models(self) -> list[LocalModelInfo]:
        return [
            LocalModelInfo(name="qwen2.5:7b-instruct-q4_K_M", size=4500000000, modified_at=None)
        ]

    async def interpret(
        self,
        request: ConversationRequest,
        output_schema: dict[str, object],
        *args: Any,
        **kwargs: Any,
    ) -> ArchitecturalIntentResult:
        raise AssertionError(
            "MockProvider.interpret should not be called in site approval API tests."
        )


def _seed_valid_brief_and_graph(
    brief_repo: JSONBriefRepository,
    spatial_repo: JSONSpatialRelationshipRepository,
    project_id: str = "proj_site_01",
    brief_version: int = 1,
) -> tuple[BriefSnapshot, SpatialRelationshipGraph]:
    ev1 = Evidence(
        id="ev_chat_01",
        source_type=EvidenceSource.CHAT,
        source_reference="msg_01",
        excerpt="Salon ve mutfak olsun.",
    )
    stk = Stakeholder(id="stk_1", display_name="Owner", role="CLIENT_OWNER", active=True)
    sr1 = SpaceRequest(
        id="sr_living_room",
        display_name="Salon",
        space_function=SpaceFunction.LIVING,
        minimum_quantity=1,
        maximum_quantity=1,
        mandatory=True,
        stakeholder_ids=["stk_1"],
        confirmation_status=ConfirmationStatus.CONFIRMED,
        evidence_ids=[ev1.id],
    )
    sr2 = SpaceRequest(
        id="sr_kitchen",
        display_name="Mutfak",
        space_function=SpaceFunction.COOKING,
        minimum_quantity=1,
        maximum_quantity=1,
        mandatory=True,
        stakeholder_ids=["stk_1"],
        confirmation_status=ConfirmationStatus.CONFIRMED,
        evidence_ids=[ev1.id],
    )
    brief = BriefSnapshot(
        project_id=project_id,
        schema_version="brief.v0",
        brief_version=brief_version,
        created_at=datetime.now(UTC),
        stakeholders=[stk],
        brief_items=[],
        space_requests=[sr1, sr2],
        usage_scenarios=[],
        evidence=[ev1],
        contradictions=[],
        open_questions=_closed_topic_questions(),
    )
    brief_repo.save(brief)

    node1 = SpatialNode(
        id="sn_living_room_01",
        display_name="Salon",
        function=SpaceFunction.LIVING,
        source_space_request_id=sr1.id,
        instance_index=1,
    )
    node2 = SpatialNode(
        id="sn_kitchen_01",
        display_name="Mutfak",
        function=SpaceFunction.COOKING,
        source_space_request_id=sr2.id,
        instance_index=1,
    )
    rel = SpatialRelationship(
        id="rel_01",
        source_space_id=node1.id,
        target_space_id=node2.id,
        relation_type=SpatialRelationType.ADJACENT_TO,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.MUST,
        evidence_ids=[ev1.id],
    )
    graph = SpatialRelationshipGraph(
        project_id=project_id,
        schema_version="spatial_graph.v0",
        source_brief_version=brief_version,
        created_at=datetime.now(UTC),
        nodes=[node1, node2],
        relationships=[rel],
    )
    spatial_repo.save(graph)
    return brief, graph


@pytest.fixture
def api_test_env(tmp_path: Path) -> ApiTestEnv:
    settings = LocalLLMSettings(
        enabled=True,
        model="qwen2.5:7b-instruct-q4_K_M",
    )
    provider = MockProvider()
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    site_evidence_repo = SiteApprovalEvidenceRepository(root_dir=tmp_path)

    app = create_app(
        settings=settings,
        provider=provider,
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
        site_evidence_repository=site_evidence_repo,
    )
    client = TestClient(app)
    return {
        "client": client,
        "brief_repo": brief_repo,
        "spatial_repo": spatial_repo,
        "plan_input_repo": plan_input_repo,
        "site_evidence_repo": site_evidence_repo,
    }


def test_approve_parcel_boundary_from_uninitialized_state(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    pid = "proj_site_01"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    user_msg = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"
    prop_geom = ProposedSiteGeometry(
        proposal_id="prop_parcel_01",
        role=SiteGeometryRole.PARCEL_BOUNDARY,
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=30.0),
            SitePoint(x_m=0.0, y_m=30.0),
        ],
        rationale="Parsel sınırı",
    )
    req = SiteGeometryApprovalRequest(
        proposed_geometry=prop_geom,
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message=user_msg,
        source_reference="msg_01",
    )

    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req.model_dump(mode="json"),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    resulting_state = AuthoritativePlanInputState.model_validate(data["resulting_plan_input_state"])
    assert resulting_state.state_version == 1
    assert resulting_state.site_envelope is not None
    assert resulting_state.site_envelope.parcel_boundary is not None
    assert len(resulting_state.site_envelope.parcel_boundary.vertices) == 4
    assert resulting_state.site_envelope.buildable_envelope is None
    assert (
        data["approval_record"]["geometry_id"] == resulting_state.site_envelope.parcel_boundary.id
    )
    assert data["approval_record"]["resulting_state_version"] == 1


def test_approve_parcel_idempotent_replay(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    pid = "proj_site_02"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    user_msg = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"
    prop_geom = ProposedSiteGeometry(
        proposal_id="prop_parcel_01",
        role=SiteGeometryRole.PARCEL_BOUNDARY,
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=30.0),
            SitePoint(x_m=0.0, y_m=30.0),
        ],
    )
    req1 = SiteGeometryApprovalRequest(
        proposed_geometry=prop_geom,
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message=user_msg,
        source_reference="msg_01",
    )
    resp1 = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req1.model_dump(mode="json"),
    )
    assert resp1.status_code == 200
    assert resp1.json()["resulting_plan_input_state"]["state_version"] == 1

    # Exact replay with expected_plan_input_state_version=1 or None
    req2 = req1.model_copy(update={"expected_plan_input_state_version": 1})
    resp2 = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req2.model_dump(mode="json"),
    )
    assert resp2.status_code == 200
    # State version remains unchanged at 1
    assert resp2.json()["resulting_plan_input_state"]["state_version"] == 1


def test_approve_buildable_envelope_inside_parcel(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    pid = "proj_site_03"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    # 1. Approve Parcel (0,0) to (20,30)
    parcel_msg = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"
    parcel_geom = ProposedSiteGeometry(
        proposal_id="prop_p1",
        role=SiteGeometryRole.PARCEL_BOUNDARY,
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=30.0),
            SitePoint(x_m=0.0, y_m=30.0),
        ],
    )
    req_parcel = SiteGeometryApprovalRequest(
        proposed_geometry=parcel_geom,
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message=parcel_msg,
        source_reference="msg_01",
    )
    resp1 = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req_parcel.model_dump(mode="json"),
    )
    assert resp1.status_code == 200
    assert resp1.json()["resulting_plan_input_state"]["state_version"] == 1

    # 2. Approve Envelope inside Parcel: (2,2) to (18,28)
    env_msg = "Yapılaşma zarfı: (2;2), (18;2), (18;28), (2;28)"
    env_geom = ProposedSiteGeometry(
        proposal_id="prop_e1",
        role=SiteGeometryRole.BUILDABLE_ENVELOPE,
        vertices=[
            SitePoint(x_m=2.0, y_m=2.0),
            SitePoint(x_m=18.0, y_m=2.0),
            SitePoint(x_m=18.0, y_m=28.0),
            SitePoint(x_m=2.0, y_m=28.0),
        ],
    )
    req_env = SiteGeometryApprovalRequest(
        proposed_geometry=env_geom,
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message=env_msg,
        source_reference="msg_02",
    )
    resp2 = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req_env.model_dump(mode="json"),
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["success"] is True
    resulting_state = AuthoritativePlanInputState.model_validate(
        data2["resulting_plan_input_state"]
    )
    assert resulting_state.state_version == 2
    assert resulting_state.site_envelope is not None
    site = resulting_state.site_envelope
    assert site.parcel_boundary is not None
    assert site.buildable_envelope is not None
    assert len(site.buildable_envelope.vertices) == 4
    assert len(site.authoritative_geometry_ids) == 2


def test_approve_buildable_envelope_without_parcel_fails(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    pid = "proj_site_04"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    env_msg = "Yapılaşma zarfı: (2;2), (18;2), (18;28), (2;28)"
    env_geom = ProposedSiteGeometry(
        proposal_id="prop_e1",
        role=SiteGeometryRole.BUILDABLE_ENVELOPE,
        vertices=[
            SitePoint(x_m=2.0, y_m=2.0),
            SitePoint(x_m=18.0, y_m=2.0),
            SitePoint(x_m=18.0, y_m=28.0),
            SitePoint(x_m=2.0, y_m=28.0),
        ],
    )
    req_env = SiteGeometryApprovalRequest(
        proposed_geometry=env_geom,
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message=env_msg,
        source_reference="msg_02",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req_env.model_dump(mode="json"),
    )
    assert resp.status_code == 422
    assert "parsel sınırı" in resp.json()["error"].lower()


def test_approve_envelope_outside_parcel_fails(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    pid = "proj_site_05"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    # 1. Parcel (0,0) to (20,30)
    parcel_msg = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"
    parcel_geom = ProposedSiteGeometry(
        proposal_id="prop_p1",
        role=SiteGeometryRole.PARCEL_BOUNDARY,
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=30.0),
            SitePoint(x_m=0.0, y_m=30.0),
        ],
    )
    req_parcel = SiteGeometryApprovalRequest(
        proposed_geometry=parcel_geom,
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message=parcel_msg,
        source_reference="msg_01",
    )
    client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req_parcel.model_dump(mode="json"),
    )

    # 2. Envelope extending outside parcel (x up to 25.0)
    env_msg = "Yapılaşma zarfı: (2;2), (25;2), (25;28), (2;28)"
    env_geom = ProposedSiteGeometry(
        proposal_id="prop_e1",
        role=SiteGeometryRole.BUILDABLE_ENVELOPE,
        vertices=[
            SitePoint(x_m=2.0, y_m=2.0),
            SitePoint(x_m=25.0, y_m=2.0),
            SitePoint(x_m=25.0, y_m=28.0),
            SitePoint(x_m=2.0, y_m=28.0),
        ],
    )
    req_env = SiteGeometryApprovalRequest(
        proposed_geometry=env_geom,
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message=env_msg,
        source_reference="msg_02",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req_env.model_dump(mode="json"),
    )
    assert resp.status_code == 422


def test_parcel_replacement_clears_existing_buildable_envelope(
    api_test_env: ApiTestEnv,
) -> None:
    client = api_test_env["client"]
    pid = "proj_site_06"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    # 1. Parcel 1
    req_p1 = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        source_reference="msg_01",
    )
    client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve", json=req_p1.model_dump(mode="json")
    )

    # 2. Envelope 1
    req_e1 = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="e1",
            role=SiteGeometryRole.BUILDABLE_ENVELOPE,
            vertices=[
                SitePoint(x_m=2.0, y_m=2.0),
                SitePoint(x_m=18.0, y_m=2.0),
                SitePoint(x_m=18.0, y_m=28.0),
                SitePoint(x_m=2.0, y_m=28.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Yapılaşma zarfı: (2;2), (18;2), (18;28), (2;28)",
        source_reference="msg_02",
    )
    resp_e1 = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve", json=req_e1.model_dump(mode="json")
    )
    assert resp_e1.json()["resulting_plan_input_state"]["state_version"] == 2
    assert (
        resp_e1.json()["resulting_plan_input_state"]["site_envelope"]["buildable_envelope"]
        is not None
    )

    # 3. Parcel 2 (Replacing parcel) -> Must clear buildable_envelope and advance state version to 3
    req_p2 = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p2",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=30.0, y_m=0.0),
                SitePoint(x_m=30.0, y_m=40.0),
                SitePoint(x_m=0.0, y_m=40.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=2,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (30;0), (30;40), (0;40)",
        source_reference="msg_03",
    )
    resp_p2 = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve", json=req_p2.model_dump(mode="json")
    )
    assert resp_p2.status_code == 200
    st3 = resp_p2.json()["resulting_plan_input_state"]
    assert st3["state_version"] == 3
    assert st3["site_envelope"]["buildable_envelope"] is None


def test_endpoint_revalidates_source_and_blocks_tampered_proposal(
    api_test_env: ApiTestEnv,
) -> None:
    client = api_test_env["client"]
    pid = "proj_site_07"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    # User message says (0;0), (20;0), (20;30), (0;30)
    user_msg = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"

    # Tampered proposal sends (0,0), (25,0), (25,30), (0,30)
    tampered_prop = ProposedSiteGeometry(
        proposal_id="prop_tampered",
        role=SiteGeometryRole.PARCEL_BOUNDARY,
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=25.0, y_m=0.0),
            SitePoint(x_m=25.0, y_m=30.0),
            SitePoint(x_m=0.0, y_m=30.0),
        ],
    )
    req = SiteGeometryApprovalRequest(
        proposed_geometry=tampered_prop,
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message=user_msg,
        source_reference="msg_01",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req.model_dump(mode="json"),
    )
    # Re-validation must reject
    assert resp.status_code == 422
    assert "Kaynak doğrulama hatası" in resp.json()["error"]


def test_project_id_route_mismatch_returns_422(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    pid = "proj_site_08"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    req = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id="other_project",  # Mismatch
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        source_reference="msg_01",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req.model_dump(mode="json"),
    )
    assert resp.status_code == 422


def test_missing_brief_returns_404(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    pid = "non_existent_project"

    req = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        source_reference="msg_01",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req.model_dump(mode="json"),
    )
    assert resp.status_code == 404


def test_stale_brief_version_returns_409(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    pid = "proj_site_09"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    req = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=99,  # Mismatch with version 1
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        source_reference="msg_01",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req.model_dump(mode="json"),
    )
    assert resp.status_code == 409


def test_stale_plan_input_state_version_conflict_returns_409(
    api_test_env: ApiTestEnv,
) -> None:
    client = api_test_env["client"]
    pid = "proj_site_10"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    # First approval -> version 1
    req1 = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        source_reference="msg_01",
    )
    resp1 = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve", json=req1.model_dump(mode="json")
    )
    assert resp1.status_code == 200

    # Second approval claiming expected_plan_input_state_version=None or 5 -> 409 conflict
    req_stale = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p2",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=30.0, y_m=0.0),
                SitePoint(x_m=30.0, y_m=40.0),
                SitePoint(x_m=0.0, y_m=40.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=5,  # Stale: actual is 1
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (30;0), (30;40), (0;40)",
        source_reference="msg_02",
    )
    resp_stale = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req_stale.model_dump(mode="json"),
    )
    assert resp_stale.status_code == 409


def test_stale_fingerprint_or_generation_returns_409(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    pid = "proj_site_11"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    req = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_old",
        current_fingerprint="fp_new",  # Mismatch
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        source_reference="msg_01",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req.model_dump(mode="json"),
    )
    assert resp.status_code == 409


def test_self_intersecting_polygon_returns_422(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    pid = "proj_site_12"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    # Self-intersecting polygon with positive area:
    # edge (20;10)-(20;40) intersects (30;30)-(10;30) at (20;30)
    msg = "Parsel sınırı: (0;0), (30;0), (30;30), (10;30), (10;10), (20;10), (20;40), (0;40)"
    req = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p_self_intersect",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=30.0, y_m=0.0),
                SitePoint(x_m=30.0, y_m=30.0),
                SitePoint(x_m=10.0, y_m=30.0),
                SitePoint(x_m=10.0, y_m=10.0),
                SitePoint(x_m=20.0, y_m=10.0),
                SitePoint(x_m=20.0, y_m=40.0),
                SitePoint(x_m=0.0, y_m=40.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message=msg,
        source_reference="msg_01",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req.model_dump(mode="json"),
    )
    assert resp.status_code == 422
    assert "intersect" in resp.json()["error"].lower() or "overlap" in resp.json()["error"].lower()


def test_persistent_evidence_stored_and_reloadable(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    pid = "proj_site_13"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    user_msg = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"
    req = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message=user_msg,
        source_reference="msg_01",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req.model_dump(mode="json"),
    )
    assert resp.status_code == 200
    evidence_repo = api_test_env["site_evidence_repo"]
    records = evidence_repo.list_evidence(pid)
    assert len(records) == 1
    assert records[0].excerpt == user_msg
    assert records[0].source_reference == "msg_01"


def test_direct_endpoint_bypass_defense_exact_tampered_vertex(
    api_test_env: ApiTestEnv,
) -> None:
    # Requirement 5: Direct endpoint bypass defense with exact (21,0) tampered point
    client = api_test_env["client"]
    pid = "proj_bypass_01"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    user_msg = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"
    tampered_prop = ProposedSiteGeometry(
        proposal_id="prop_tampered_exact",
        role=SiteGeometryRole.PARCEL_BOUNDARY,
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=21.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=30.0),
            SitePoint(x_m=0.0, y_m=30.0),
        ],
    )
    req = SiteGeometryApprovalRequest(
        proposed_geometry=tampered_prop,
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message=user_msg,
        source_reference="msg_01",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req.model_dump(mode="json"),
    )
    assert resp.status_code == 422
    assert "Kaynak doğrulama hatası" in resp.json()["error"]

    # Assert no authoritative PlanInputState created/updated
    plan_input_repo = api_test_env["plan_input_repo"]
    assert plan_input_repo.get_latest(pid) is None


def test_evidence_failure_order_leaves_state_unchanged(
    api_test_env: ApiTestEnv, monkeypatch: MonkeyPatch
) -> None:
    # Requirement 6: Force SiteApprovalEvidenceRepository persistence to fail
    client = api_test_env["client"]
    pid = "proj_evidence_fail_01"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    evidence_repo = api_test_env["site_evidence_repo"]

    def _mock_save(project_id: str, source_reference: str, user_message: str) -> Evidence:
        raise SiteEvidencePersistenceError("Simulated disk error during evidence save")

    monkeypatch.setattr(evidence_repo, "save_site_evidence", _mock_save)

    req = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        source_reference="msg_01",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req.model_dump(mode="json"),
    )
    assert resp.status_code == 500

    # PlanInputState latest version remains EXACTLY unchanged (none exists)
    plan_input_repo = api_test_env["plan_input_repo"]
    assert plan_input_repo.get_latest(pid) is None


def test_empty_brief_evidence_succeeds_independently(api_test_env: ApiTestEnv) -> None:
    # Requirement 7A: Site approval operates independently and does not mutate brief evidence
    client = api_test_env["client"]
    pid = "proj_empty_brief_ev"
    brief, _ = _seed_valid_brief_and_graph(
        api_test_env["brief_repo"], api_test_env["spatial_repo"], pid
    )

    # Verify site evidence repo is initially empty for this project
    assert api_test_env["site_evidence_repo"].list_evidence(pid) == []
    brief_evidence_before = list(brief.evidence)

    req = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        source_reference="msg_01",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req.model_dump(mode="json"),
    )
    assert resp.status_code == 200
    res_st = resp.json()["resulting_plan_input_state"]
    assert res_st["state_version"] == 1
    assert res_st["site_envelope"]["parcel_boundary"] is not None

    # Site evidence was persisted in SiteApprovalEvidenceRepository
    site_records = api_test_env["site_evidence_repo"].list_evidence(pid)
    assert len(site_records) == 1

    # BriefSnapshot was NOT mutated
    latest_brief = api_test_env["brief_repo"].get_latest(pid)
    assert latest_brief is not None
    assert latest_brief.evidence == brief_evidence_before


def test_unrelated_brief_evidence_not_reused_and_resolves_through_site_repo(
    api_test_env: ApiTestEnv,
) -> None:
    # Requirement 7B: Unrelated brief evidence not reused;
    # polygon evidence resolves through site repo
    client = api_test_env["client"]
    pid = "proj_unrelated_brief_ev"
    unrelated_ev = Evidence(
        id="ev_household_unrelated_123",
        source_type=EvidenceSource.CHAT,
        source_reference="msg_household_01",
        excerpt="4 kişilik aile yaşayacak.",
    )
    stk = Stakeholder(id="stk_1", display_name="Owner", role="CLIENT_OWNER", active=True)
    sr1 = SpaceRequest(
        id="sr_living_room",
        display_name="Salon",
        space_function=SpaceFunction.LIVING,
        minimum_quantity=1,
        mandatory=True,
        stakeholder_ids=["stk_1"],
        confirmation_status=ConfirmationStatus.CONFIRMED,
        evidence_ids=[unrelated_ev.id],
    )
    brief = BriefSnapshot(
        project_id=pid,
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime.now(UTC),
        stakeholders=[stk],
        brief_items=[],
        space_requests=[sr1],
        usage_scenarios=[],
        evidence=[unrelated_ev],
        contradictions=[],
        open_questions=_closed_topic_questions(),
    )
    api_test_env["brief_repo"].save(brief)

    node1 = SpatialNode(
        id="sn_living_room_01",
        display_name="Salon",
        function=SpaceFunction.LIVING,
        source_space_request_id="sr_living_room",
        instance_index=1,
    )
    graph = SpatialRelationshipGraph(
        project_id=pid,
        schema_version="spatial_graph.v0",
        source_brief_version=1,
        created_at=datetime.now(UTC),
        nodes=[node1],
        relationships=[],
    )
    api_test_env["spatial_repo"].save(graph)

    user_msg = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"
    req = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message=user_msg,
        source_reference="msg_site_01",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req.model_dump(mode="json"),
    )
    assert resp.status_code == 200
    res_st = resp.json()["resulting_plan_input_state"]
    parcel = res_st["site_envelope"]["parcel_boundary"]

    # Must NOT reuse unrelated brief evidence ID
    assert unrelated_ev.id not in parcel["evidence_ids"]
    assert len(parcel["evidence_ids"]) == 1
    site_ev_id = parcel["evidence_ids"][0]
    assert site_ev_id != unrelated_ev.id

    # Approved SitePolygon.evidence_ids must resolve through SiteApprovalEvidenceRepository
    site_ev = api_test_env["site_evidence_repo"].get_evidence(pid, site_ev_id)
    assert site_ev is not None
    assert site_ev.excerpt == user_msg
    assert site_ev.source_reference == "msg_site_01"


def test_buildable_envelope_rejected_if_parcel_not_user_confirmed_or_not_authoritative(
    api_test_env: ApiTestEnv,
) -> None:
    # Requirement 8: Authority tests
    client = api_test_env["client"]
    pid = "proj_authority_01"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    # 1. First create parcel with USER_CONFIRMED
    req_p1 = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        source_reference="msg_01",
    )
    resp_p1 = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve", json=req_p1.model_dump(mode="json")
    )
    assert resp_p1.status_code == 200

    # Test Case A: Corrupt parcel provenance = USER_STATED (not USER_CONFIRMED)
    state1 = api_test_env["plan_input_repo"].get_latest(pid)
    assert state1 is not None
    assert state1.site_envelope is not None
    assert state1.site_envelope.parcel_boundary is not None
    bad_parcel = state1.site_envelope.parcel_boundary.model_copy(
        update={"provenance": RelationshipProvenance.USER_STATED}
    )
    bad_envelope = state1.site_envelope.model_copy(
        update={"parcel_boundary": bad_parcel, "authoritative_geometry_ids": []}
    )
    bad_state = state1.model_copy(update={"state_version": 2, "site_envelope": bad_envelope})
    api_test_env["plan_input_repo"].save(bad_state)

    req_e1 = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="e1",
            role=SiteGeometryRole.BUILDABLE_ENVELOPE,
            vertices=[
                SitePoint(x_m=2.0, y_m=2.0),
                SitePoint(x_m=18.0, y_m=2.0),
                SitePoint(x_m=18.0, y_m=28.0),
                SitePoint(x_m=2.0, y_m=28.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=2,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Yapılaşma zarfı: (2;2), (18;2), (18;28), (2;28)",
        source_reference="msg_02",
    )
    resp_e1 = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve", json=req_e1.model_dump(mode="json")
    )
    assert resp_e1.status_code == 422
    assert "USER_CONFIRMED" in resp_e1.json()["error"]


def test_parcel_replay_with_existing_envelope_clears_envelope_and_advances_version(
    api_test_env: ApiTestEnv,
) -> None:
    # Requirement 9: Important parcel replay case
    client = api_test_env["client"]
    pid = "proj_parcel_replay_case"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    # 1. Approve Parcel P1 -> state_version 1
    req_p1 = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        source_reference="msg_01",
    )
    resp_p1 = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve", json=req_p1.model_dump(mode="json")
    )
    assert resp_p1.status_code == 200
    assert resp_p1.json()["resulting_plan_input_state"]["state_version"] == 1

    # 2. Approve Envelope E1 -> state_version 2
    req_e1 = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="e1",
            role=SiteGeometryRole.BUILDABLE_ENVELOPE,
            vertices=[
                SitePoint(x_m=2.0, y_m=2.0),
                SitePoint(x_m=18.0, y_m=2.0),
                SitePoint(x_m=18.0, y_m=28.0),
                SitePoint(x_m=2.0, y_m=28.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Yapılaşma zarfı: (2;2), (18;2), (18;28), (2;28)",
        source_reference="msg_02",
    )
    resp_e1 = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve", json=req_e1.model_dump(mode="json")
    )
    assert resp_e1.status_code == 200
    assert resp_e1.json()["resulting_plan_input_state"]["state_version"] == 2
    assert (
        resp_e1.json()["resulting_plan_input_state"]["site_envelope"]["buildable_envelope"]
        is not None
    )

    # 3. User re-approves exact same P1 coordinates.
    # MUST NOT be treated as semantic no-op because E1 must be cleared.
    req_p1_re = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1_re",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=2,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        source_reference="msg_03",
    )
    resp_p1_re = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve", json=req_p1_re.model_dump(mode="json")
    )
    assert resp_p1_re.status_code == 200
    st3 = resp_p1_re.json()["resulting_plan_input_state"]
    assert st3["state_version"] == 3
    assert st3["site_envelope"]["buildable_envelope"] is None

    # 4. Subsequent replay of P1 when envelope is already None returns
    # idempotent 200 without increment
    req_p1_idempotent = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1_idem",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=3,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        source_reference="msg_04",
    )
    resp_idem = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req_p1_idempotent.model_dump(mode="json"),
    )
    assert resp_idem.status_code == 200
    assert resp_idem.json()["resulting_plan_input_state"]["state_version"] == 3


def test_safe_internal_errors_do_not_leak_filesystem_paths(
    api_test_env: ApiTestEnv, monkeypatch: MonkeyPatch
) -> None:
    # Requirement 11: 500 error must not leak raw paths
    client = api_test_env["client"]
    pid = "proj_safe_error_01"
    _seed_valid_brief_and_graph(api_test_env["brief_repo"], api_test_env["spatial_repo"], pid)

    evidence_repo = api_test_env["site_evidence_repo"]

    def _mock_save(project_id: str, source_reference: str, user_message: str) -> Evidence:
        raise SiteEvidencePersistenceError(
            "Fatal write failure at C:\\secret\\site\\evidence.json [Errno 13]"
        )

    monkeypatch.setattr(evidence_repo, "save_site_evidence", _mock_save)

    req = SiteGeometryApprovalRequest(
        proposed_geometry=ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_01",
        current_fingerprint="fp_01",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        source_reference="msg_01",
    )
    resp = client.post(
        f"/api/v1/projects/{pid}/plan/input/site/approve",
        json=req.model_dump(mode="json"),
    )
    assert resp.status_code == 500
    body = resp.text
    assert "C:\\secret" not in body
    assert "evidence.json" not in body
    assert "Traceback" not in body
    assert "Errno" not in body
    assert resp.json()["error"] == "Kalıcı depolama hatası oluştu."
