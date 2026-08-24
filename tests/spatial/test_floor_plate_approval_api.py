"""API tests for Floor Plate Approval and Plan Input State integration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

import pytest
from apps.api.main import create_app
from fastapi.testclient import TestClient

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
    FloorPlateApprovalRequest,
    LocalModelInfo,
    ProposedFloorPlate,
    ProviderHealth,
)
from brif_ai.llm.settings import LocalLLMSettings
from brif_ai.spatial.floor_plate.models import FloorPlateInput, generate_floor_plate_id
from brif_ai.spatial.metrics.models import (
    MetricRequirement,
    MetricRequirementType,
    MetricSpatialRequirements,
    MetricUnit,
    SpaceMetricRequirements,
)
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
from brif_ai.spatial.plan_preview import ProjectPlanPreviewReadinessService
from brif_ai.spatial.room_solver.models import RoomGeometrySolverConfig
from brif_ai.spatial.site.approval_evidence import (
    SiteApprovalEvidenceRepository,
)
from brif_ai.spatial.site.models import (
    SiteBuildableEnvelope,
    SiteGeometryRole,
    SitePoint,
    SitePolygon,
)

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
            LocalModelInfo(
                name="qwen2.5:7b-instruct",
            )
        ]

    async def generate_response(
        self,
        request: Any,
        model_name: str,
        system_prompt: str,
        settings: LocalLLMSettings,
    ) -> ArchitecturalIntentResult:
        raise AssertionError("Not called in approval tests")


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
        provider=provider,  # type: ignore[arg-type]
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


def _seed_valid_brief_and_graph(
    brief_repo: JSONBriefRepository,
    spatial_repo: JSONSpatialRelationshipRepository,
    project_id: str = "proj_house_2story",
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


def test_approve_floor_plate_success_explicit_coordinates(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(
        api_test_env["brief_repo"], api_test_env["spatial_repo"], project_id, brief_version=1
    )

    payload = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_1",
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=18.0),
                SitePoint(x_m=0.0, y_m=18.0),
            ],
            rationale="Taban oturumu.",
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_test_123",
        current_fingerprint="fp_test_123",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu: (0;0), (12;0), (12;18), (0;18)",
        source_reference="chatmsg_101",
    )

    response = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload.model_dump(mode="json"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["error"] is None
    assert data["resulting_plan_input_state"]["state_version"] == 1
    assert data["resulting_plan_input_state"]["floor_plate_input"] is not None
    assert data["resulting_plan_input_state"]["floor_plate_input"]["provenance"] == "USER_CONFIRMED"
    assert len(data["resulting_plan_input_state"]["floor_plate_input"]["evidence_ids"]) == 1
    assert data["approval_record"]["proposal_status"] == "user_approved"
    assert data["approval_record"]["floor_plate_id"] == generate_floor_plate_id(project_id)


def test_dimension_only_input_rejects_arbitrary_origin_placement_422(
    api_test_env: ApiTestEnv,
) -> None:
    client = api_test_env["client"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(
        api_test_env["brief_repo"], api_test_env["spatial_repo"], project_id, brief_version=1
    )

    # User gave dimension only: "Taban oturumu 12x18 metre olsun." without explicit coordinates.
    # LLM proposed arbitrary (0,0) origin vertices [(0,0),(12,0),(12,18),(0,18)].
    # MUST BE REJECTED because placement/origin is underconstrained!
    payload = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_2",
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=18.0),
                SitePoint(x_m=0.0, y_m=18.0),
            ],
            rationale="12x18 dikdörtgen taban oturumu.",
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_test_123",
        current_fingerprint="fp_test_123",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu 12 metreye 18 metre dikdörtgen olsun.",
        source_reference="chatmsg_102",
    )

    response = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload.model_dump(mode="json"),
    )
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "açık köşe koordinatları belirtilmelidir" in data["error"]


def test_approve_floor_plate_exact_replay_idempotence(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(
        api_test_env["brief_repo"], api_test_env["spatial_repo"], project_id, brief_version=1
    )

    payload = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_1",
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=18.0),
                SitePoint(x_m=0.0, y_m=18.0),
            ],
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_test_123",
        current_fingerprint="fp_test_123",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu: (0;0), (12;0), (12;18), (0;18)",
        source_reference="chatmsg_101",
    )

    # First approval -> version 1
    resp1 = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload.model_dump(mode="json"),
    )
    assert resp1.status_code == 200
    assert resp1.json()["resulting_plan_input_state"]["state_version"] == 1

    # Second approval (replay) -> version stays 1 (N -> N)
    payload_replay = payload.model_copy(update={"expected_plan_input_state_version": 1})
    resp2 = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload_replay.model_dump(mode="json"),
    )
    assert resp2.status_code == 200
    assert resp2.json()["resulting_plan_input_state"]["state_version"] == 1


def test_approve_floor_plate_replacement_mutation_n_to_n_plus_1(
    api_test_env: ApiTestEnv,
) -> None:
    client = api_test_env["client"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(
        api_test_env["brief_repo"], api_test_env["spatial_repo"], project_id, brief_version=1
    )

    payload1 = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_1",
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=18.0),
                SitePoint(x_m=0.0, y_m=18.0),
            ],
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_test_1",
        current_fingerprint="fp_test_1",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu: (0;0), (12;0), (12;18), (0;18)",
        source_reference="chatmsg_101",
    )

    # Initial approval -> state version 1
    resp1 = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload1.model_dump(mode="json"),
    )
    assert resp1.status_code == 200
    assert resp1.json()["resulting_plan_input_state"]["state_version"] == 1

    # Replacement approval with different vertices -> state version advances 1 -> 2
    payload2 = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_2",
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=14.0, y_m=0.0),
                SitePoint(x_m=14.0, y_m=20.0),
                SitePoint(x_m=0.0, y_m=20.0),
            ],
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_test_2",
        current_fingerprint="fp_test_2",
        proposal_generation_id=2,
        current_generation_id=2,
        user_message="Taban oturumu: (0;0), (14;0), (14;20), (0;20)",
        source_reference="chatmsg_102",
    )

    resp2 = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload2.model_dump(mode="json"),
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["resulting_plan_input_state"]["state_version"] == 2
    assert data2["approval_record"]["resulting_state_version"] == 2
    # Verify canonical floor_plate_input vertices were replaced
    assert data2["resulting_plan_input_state"]["floor_plate_input"]["vertices"] == [
        {"x_m": 0.0, "y_m": 0.0},
        {"x_m": 14.0, "y_m": 0.0},
        {"x_m": 14.0, "y_m": 20.0},
        {"x_m": 0.0, "y_m": 20.0},
    ]


def test_approve_floor_plate_stale_state_version_conflict_409(
    api_test_env: ApiTestEnv,
) -> None:
    client = api_test_env["client"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(
        api_test_env["brief_repo"], api_test_env["spatial_repo"], project_id, brief_version=1
    )

    payload = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_1",
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=18.0),
                SitePoint(x_m=0.0, y_m=18.0),
            ],
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=5,  # Stale!
        proposal_fingerprint="fp_test_123",
        current_fingerprint="fp_test_123",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu: (0;0), (12;0), (12;18), (0;18)",
        source_reference="chatmsg_101",
    )

    resp = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload.model_dump(mode="json"),
    )
    assert resp.status_code == 409
    assert resp.json()["success"] is False


def test_approve_floor_plate_stale_brief_conflict_409(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(
        api_test_env["brief_repo"], api_test_env["spatial_repo"], project_id, brief_version=1
    )

    payload = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_1",
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=18.0),
                SitePoint(x_m=0.0, y_m=18.0),
            ],
        ),
        current_project_id=project_id,
        expected_brief_version=99,  # Brief conflict!
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_test_123",
        current_fingerprint="fp_test_123",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu: (0;0), (12;0), (12;18), (0;18)",
        source_reference="chatmsg_101",
    )

    resp = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload.model_dump(mode="json"),
    )
    assert resp.status_code == 409
    assert resp.json()["success"] is False


def test_approve_floor_plate_fingerprint_mismatch_409(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(
        api_test_env["brief_repo"], api_test_env["spatial_repo"], project_id, brief_version=1
    )

    payload = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_1",
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=18.0),
                SitePoint(x_m=0.0, y_m=18.0),
            ],
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_old",
        current_fingerprint="fp_new",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu: (0;0), (12;0), (12;18), (0;18)",
        source_reference="chatmsg_101",
    )

    resp = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload.model_dump(mode="json"),
    )
    assert resp.status_code == 409
    assert resp.json()["success"] is False


def test_approve_floor_plate_missing_brief_404(api_test_env: ApiTestEnv) -> None:
    client = api_test_env["client"]
    project_id = "proj_house_2story"

    payload = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_1",
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=18.0),
                SitePoint(x_m=0.0, y_m=18.0),
            ],
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_test",
        current_fingerprint="fp_test",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu: (0;0), (12;0), (12;18), (0;18)",
        source_reference="chatmsg_101",
    )

    resp = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload.model_dump(mode="json"),
    )
    assert resp.status_code == 404


def test_approve_floor_plate_source_binding_coordinate_mismatch_422(
    api_test_env: ApiTestEnv,
) -> None:
    client = api_test_env["client"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(
        api_test_env["brief_repo"], api_test_env["spatial_repo"], project_id, brief_version=1
    )

    payload = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_1",
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=18.0),
                SitePoint(x_m=0.0, y_m=18.0),
            ],
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_test",
        current_fingerprint="fp_test",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu: (0;0), (10;0), (10;15), (0;15)",  # Mismatch!
        source_reference="chatmsg_101",
    )

    resp = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload.model_dump(mode="json"),
    )
    assert resp.status_code == 422
    assert resp.json()["success"] is False


def test_approve_floor_plate_source_binding_dimension_mismatch_422(
    api_test_env: ApiTestEnv,
) -> None:
    client = api_test_env["client"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(
        api_test_env["brief_repo"], api_test_env["spatial_repo"], project_id, brief_version=1
    )

    payload = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_1",
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=18.0),
                SitePoint(x_m=0.0, y_m=18.0),
            ],
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_test",
        current_fingerprint="fp_test",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu 8 metreye 10 metre dikdörtgen olsun.",  # 8x10 != 12x18
        source_reference="chatmsg_101",
    )

    resp = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload.model_dump(mode="json"),
    )
    assert resp.status_code == 422
    assert resp.json()["success"] is False


def test_approve_floor_plate_outside_buildable_envelope_422(
    api_test_env: ApiTestEnv,
) -> None:
    client = api_test_env["client"]
    brief_repo = api_test_env["brief_repo"]
    spatial_repo = api_test_env["spatial_repo"]
    plan_input_repo = api_test_env["plan_input_repo"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(brief_repo, spatial_repo, project_id, brief_version=1)

    # Initialize plan input state with a small buildable envelope (0,0) to (10,10)
    parcel_poly = SitePolygon(
        id="sp_parcel_1",
        role=SiteGeometryRole.PARCEL_BOUNDARY,
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=10.0, y_m=0.0),
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=0.0, y_m=10.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_chat_01"],
    )
    envelope_poly = SitePolygon(
        id="sp_env_1",
        role=SiteGeometryRole.BUILDABLE_ENVELOPE,
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=10.0, y_m=0.0),
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=0.0, y_m=10.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_chat_01"],
    )
    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id=project_id,
            state_version=1,
            source_brief_version=1,
            created_at=datetime.now(UTC),
            site_envelope=SiteBuildableEnvelope(
                schema_version="site_buildable_envelope.v0",
                project_id=project_id,
                source_brief_version=1,
                created_at=datetime.now(UTC),
                parcel_boundary=parcel_poly,
                buildable_envelope=envelope_poly,
                authoritative_geometry_ids=["sp_env_1", "sp_parcel_1"],
            ),
        )
    )

    # Attempt to approve a 12x18 floor plate which extends beyond (10,10)
    payload = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_1",
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=18.0),
                SitePoint(x_m=0.0, y_m=18.0),
            ],
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_test",
        current_fingerprint="fp_test",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu: (0;0), (12;0), (12;18), (0;18)",
        source_reference="chatmsg_101",
    )

    resp = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload.model_dump(mode="json"),
    )
    assert resp.status_code == 422
    assert resp.json()["success"] is False


def test_floor_plate_approval_unblocks_plan_preview_readiness(
    api_test_env: ApiTestEnv,
) -> None:
    client = api_test_env["client"]
    brief_repo = api_test_env["brief_repo"]
    spatial_repo = api_test_env["spatial_repo"]
    plan_input_repo = api_test_env["plan_input_repo"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(brief_repo, spatial_repo, project_id, brief_version=1)

    readiness_service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    # Initialize empty plan input state (version 1)
    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id=project_id,
            state_version=1,
            source_brief_version=1,
            created_at=datetime.now(UTC),
        )
    )

    # Check readiness before floor plate approval -> FLOOR_PLATE_INPUT_MISSING is among blockers
    before_result = readiness_service.evaluate(project_id)
    assert before_result.ready_for_preview is False
    assert before_result.preparation is not None
    blocker_codes_before = [b.code.value for b in before_result.preparation.blockers]
    assert "FLOOR_PLATE_INPUT_MISSING" in blocker_codes_before

    # Approve floor plate via API
    payload = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_1",
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=0.0),
                SitePoint(x_m=12.0, y_m=18.0),
                SitePoint(x_m=0.0, y_m=18.0),
            ],
            rationale="Taban oturumu.",
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_test_123",
        current_fingerprint="fp_test_123",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu: (0;0), (12;0), (12;18), (0;18)",
        source_reference="chatmsg_101",
    )
    resp = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload.model_dump(mode="json"),
    )
    assert resp.status_code == 200

    # Check readiness after floor plate approval ->
    # FLOOR_PLATE_INPUT_MISSING is NO LONGER among blockers
    after_result = readiness_service.evaluate(project_id)
    assert after_result.preparation is not None
    blocker_codes_after = [b.code.value for b in after_result.preparation.blockers]
    assert "FLOOR_PLATE_INPUT_MISSING" not in blocker_codes_after


def test_floor_plate_approval_coordinates_reach_solver_preview_request(
    api_test_env: ApiTestEnv,
) -> None:
    """Proves approved FloorPlate coordinates reach the assembled PlanPreviewRequest."""
    client = api_test_env["client"]
    brief_repo = api_test_env["brief_repo"]
    spatial_repo = api_test_env["spatial_repo"]
    plan_input_repo = api_test_env["plan_input_repo"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(brief_repo, spatial_repo, project_id, brief_version=1)

    readiness_service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    # Setup fully populated PlanInputState with site envelope, metrics, and solver config
    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id=project_id,
            state_version=1,
            source_brief_version=1,
            created_at=datetime.now(UTC),
            metric_requirements=MetricSpatialRequirements(
                schema_version="metric_spatial_requirements.v0",
                project_id=project_id,
                source_brief_version=1,
                created_at=datetime.now(UTC),
                space_requirements=[
                    SpaceMetricRequirements(space_id="sn_living_room_01", requirements=[]),
                    SpaceMetricRequirements(space_id="sn_kitchen_01", requirements=[]),
                ],
                authoritative_requirement_ids=[],
            ),
            site_envelope=SiteBuildableEnvelope(
                schema_version="site_buildable_envelope.v0",
                project_id=project_id,
                source_brief_version=1,
                created_at=datetime.now(UTC),
                authoritative_geometry_ids=["poly_envelope_1", "poly_parcel_1"],
                parcel_boundary=SitePolygon(
                    id="poly_parcel_1",
                    role=SiteGeometryRole.PARCEL_BOUNDARY,
                    vertices=[
                        SitePoint(x_m=0.0, y_m=0.0),
                        SitePoint(x_m=30.0, y_m=0.0),
                        SitePoint(x_m=30.0, y_m=30.0),
                        SitePoint(x_m=0.0, y_m=30.0),
                    ],
                    provenance=RelationshipProvenance.USER_CONFIRMED,
                    evidence_ids=["ev_site_1"],
                ),
                buildable_envelope=SitePolygon(
                    id="poly_envelope_1",
                    role=SiteGeometryRole.BUILDABLE_ENVELOPE,
                    vertices=[
                        SitePoint(x_m=0.0, y_m=0.0),
                        SitePoint(x_m=20.0, y_m=0.0),
                        SitePoint(x_m=20.0, y_m=25.0),
                        SitePoint(x_m=0.0, y_m=25.0),
                    ],
                    provenance=RelationshipProvenance.USER_CONFIRMED,
                    evidence_ids=["ev_site_2"],
                ),
            ),
            solver_config=RoomGeometrySolverConfig(grid_step_m=0.5),
        )
    )

    approved_vertices = [
        SitePoint(x_m=2.0, y_m=2.0),
        SitePoint(x_m=16.0, y_m=2.0),
        SitePoint(x_m=16.0, y_m=20.0),
        SitePoint(x_m=2.0, y_m=20.0),
    ]

    # Approve floor plate via API
    payload = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_preview_test",
            vertices=approved_vertices,
            rationale="Onaylanan özel taban oturumu.",
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_preview_test",
        current_fingerprint="fp_preview_test",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu: (2;2), (16;2), (16;20), (2;20)",
        source_reference="chatmsg_200",
    )
    resp = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload.model_dump(mode="json"),
    )
    assert resp.status_code == 200

    # Evaluate readiness
    readiness_result = readiness_service.evaluate(project_id)
    assert readiness_result.ready_for_preview is True
    assert readiness_result.preparation is not None
    assert readiness_result.preparation.ready_for_preview is True
    assert readiness_result.preparation.request is not None

    preview_req = readiness_result.preparation.request
    assert preview_req.floor_plate is not None
    # Verify exact approved coordinates reached the PlanPreviewRequest / solver input floor plate
    assert preview_req.floor_plate.vertices == approved_vertices
    assert preview_req.floor_plate.provenance == RelationshipProvenance.USER_CONFIRMED
    assert preview_req.floor_plate.rationale == "Onaylanan özel taban oturumu."


def test_approve_floor_plate_rationale_exact_replay_vs_mutation(
    api_test_env: ApiTestEnv,
) -> None:
    """Proves same geometry + same rationale is exact replay (N -> N),

    while same geometry + different rationale is state mutation (N -> N+1).
    """
    client = api_test_env["client"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(
        api_test_env["brief_repo"], api_test_env["spatial_repo"], project_id, brief_version=1
    )

    initial_vertices = [
        SitePoint(x_m=0.0, y_m=0.0),
        SitePoint(x_m=12.0, y_m=0.0),
        SitePoint(x_m=12.0, y_m=18.0),
        SitePoint(x_m=0.0, y_m=18.0),
    ]

    payload1 = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_1",
            vertices=initial_vertices,
            rationale="Gerekçe 1",
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_test_1",
        current_fingerprint="fp_test_1",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu: (0;0), (12;0), (12;18), (0;18)",
        source_reference="chatmsg_101",
    )

    # 1. First approval -> version 1
    resp1 = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload1.model_dump(mode="json"),
    )
    assert resp1.status_code == 200
    state1 = resp1.json()["resulting_plan_input_state"]
    assert state1["state_version"] == 1
    assert state1["floor_plate_input"]["rationale"] == "Gerekçe 1"
    evidence_count_1 = len(state1["floor_plate_input"]["evidence_ids"])

    # 2. Exact replay: same vertices AND same rationale -> stays version 1 (N -> N), no new evidence
    payload_exact_replay = payload1.model_copy(update={"expected_plan_input_state_version": 1})
    resp2 = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload_exact_replay.model_dump(mode="json"),
    )
    assert resp2.status_code == 200
    state2 = resp2.json()["resulting_plan_input_state"]
    assert state2["state_version"] == 1
    assert len(state2["floor_plate_input"]["evidence_ids"]) == evidence_count_1

    # 3. Same vertices but DIFFERENT rationale -> state mutation (N -> N+1)
    payload_diff_rationale = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_2",
            vertices=initial_vertices,
            rationale="Güncellenmiş mimari gerekçe 2",
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_test_2",
        current_fingerprint="fp_test_2",
        proposal_generation_id=2,
        current_generation_id=2,
        user_message="Taban oturumu: (0;0), (12;0), (12;18), (0;18)",
        source_reference="chatmsg_102",
    )
    resp3 = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload_diff_rationale.model_dump(mode="json"),
    )
    assert resp3.status_code == 200
    state3 = resp3.json()["resulting_plan_input_state"]
    assert state3["state_version"] == 2
    assert state3["floor_plate_input"]["rationale"] == "Güncellenmiş mimari gerekçe 2"


def test_approve_floor_plate_preserves_unrelated_authoritative_plan_input_fields(
    api_test_env: ApiTestEnv,
) -> None:
    """Proves approving a floor plate mutation preserves metric_requirements, site_envelope,

    solver_config, BriefSnapshot, and SpatialRelationshipGraph without mutation.
    """
    client = api_test_env["client"]
    brief_repo = api_test_env["brief_repo"]
    spatial_repo = api_test_env["spatial_repo"]
    plan_input_repo = api_test_env["plan_input_repo"]
    project_id = "proj_house_2story"
    _seed_valid_brief_and_graph(brief_repo, spatial_repo, project_id, brief_version=1)

    initial_metrics = MetricSpatialRequirements(
        schema_version="metric_spatial_requirements.v0",
        project_id=project_id,
        source_brief_version=1,
        created_at=datetime.now(UTC),
        space_requirements=[
            SpaceMetricRequirements(
                space_id="sn_living_room_01",
                requirements=[
                    MetricRequirement(
                        id="req_metric_1",
                        space_id="sn_living_room_01",
                        requirement_type=MetricRequirementType.MIN_AREA,
                        value=35.0,
                        unit=MetricUnit.SQUARE_METRE,
                        provenance=RelationshipProvenance.USER_CONFIRMED,
                        evidence_ids=["ev_metric_1"],
                    )
                ],
            ),
        ],
        authoritative_requirement_ids=["req_metric_1"],
    )

    initial_site = SiteBuildableEnvelope(
        schema_version="site_buildable_envelope.v0",
        project_id=project_id,
        source_brief_version=1,
        created_at=datetime.now(UTC),
        authoritative_geometry_ids=["poly_envelope_1", "poly_parcel_1"],
        parcel_boundary=SitePolygon(
            id="poly_parcel_1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=30.0, y_m=0.0),
                SitePoint(x_m=30.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_site_1"],
        ),
        buildable_envelope=SitePolygon(
            id="poly_envelope_1",
            role=SiteGeometryRole.BUILDABLE_ENVELOPE,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=25.0),
                SitePoint(x_m=0.0, y_m=25.0),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_site_2"],
        ),
    )

    initial_solver_config = RoomGeometrySolverConfig(grid_step_m=0.25)

    initial_floor_plate = FloorPlateInput(
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=10.0, y_m=0.0),
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=0.0, y_m=10.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_fp_initial"],
        rationale="İlk taban oturumu",
    )

    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id=project_id,
            state_version=1,
            source_brief_version=1,
            created_at=datetime.now(UTC),
            metric_requirements=initial_metrics,
            site_envelope=initial_site,
            floor_plate_input=initial_floor_plate,
            solver_config=initial_solver_config,
        )
    )

    # Capture initial brief snapshot and spatial graph states
    initial_brief_snapshot = brief_repo.get_latest(project_id)
    initial_spatial_graph = spatial_repo.get_latest(project_id)

    # Approve replacement floor plate causing N -> N+1 (1 -> 2)
    replacement_vertices = [
        SitePoint(x_m=2.0, y_m=2.0),
        SitePoint(x_m=15.0, y_m=2.0),
        SitePoint(x_m=15.0, y_m=18.0),
        SitePoint(x_m=2.0, y_m=18.0),
    ]
    payload = FloorPlateApprovalRequest(
        proposed_floor_plate=ProposedFloorPlate(
            proposal_id="prop_fp_replace",
            vertices=replacement_vertices,
            rationale="Yeni taban oturumu",
        ),
        current_project_id=project_id,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_preservation_test",
        current_fingerprint="fp_preservation_test",
        proposal_generation_id=1,
        current_generation_id=1,
        user_message="Taban oturumu: (2;2), (15;2), (15;18), (2;18)",
        source_reference="chatmsg_300",
    )
    resp = client.post(
        f"/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        json=payload.model_dump(mode="json"),
    )
    assert resp.status_code == 200

    # Reload AuthoritativePlanInputState directly from repo
    reloaded_state = plan_input_repo.get_latest(project_id)
    assert reloaded_state is not None
    assert reloaded_state.state_version == 2

    # 1. FloorPlateInput is updated
    assert reloaded_state.floor_plate_input is not None
    assert reloaded_state.floor_plate_input.vertices == replacement_vertices
    assert reloaded_state.floor_plate_input.rationale == "Yeni taban oturumu"

    # 2. Metric requirements preserved model-equal
    assert reloaded_state.metric_requirements == initial_metrics

    # 3. Site envelope preserved model-equal
    assert reloaded_state.site_envelope == initial_site

    # 4. Solver config preserved model-equal
    assert reloaded_state.solver_config == initial_solver_config

    # 5. BriefSnapshot unchanged
    latest_brief = brief_repo.get_latest(project_id)
    assert latest_brief == initial_brief_snapshot

    # 6. SpatialRelationshipGraph unchanged
    latest_graph = spatial_repo.get_latest(project_id)
    assert latest_graph == initial_spatial_graph
