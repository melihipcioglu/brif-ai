"""API tests for Metric Requirement Approval and Plan Input State integration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

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
    ActiveContextSnapshot,
    ArchitecturalIntentResult,
    ConversationRequest,
    EntityTarget,
    IntentType,
    LocalModelInfo,
    MetricConversationContext,
    MetricRequirementApprovalRequest,
    ProviderHealth,
)
from brif_ai.llm.settings import LocalLLMSettings
from brif_ai.spatial.metrics.models import (
    MetricRequirement,
    MetricRequirementType,
    MetricSpatialRequirements,
    MetricUnit,
    ProposedMetricRequirement,
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


class MockMetricInterpretationProvider:
    def __init__(self) -> None:
        self.last_request: ConversationRequest | None = None
        self.last_metric_context: MetricConversationContext | None = None
        self.call_count: int = 0

    async def health(self) -> ProviderHealth:
        return ProviderHealth(provider="ollama", reachable=True)

    async def list_models(self) -> list[LocalModelInfo]:
        return [LocalModelInfo(name="local-model:latest", size=42)]

    async def interpret(
        self,
        request: ConversationRequest,
        output_schema: dict[str, object],
        *,
        metric_context: MetricConversationContext | None = None,
    ) -> ArchitecturalIntentResult:
        self.last_request = request
        self.last_metric_context = metric_context
        self.call_count += 1

        metric_reqs = []
        if "30" in request.message or "m²" in request.message:
            metric_reqs = [
                ProposedMetricRequirement(
                    proposal_id="prop_metric_01",
                    space_id="sn_living_room_01",
                    requirement_type=MetricRequirementType.MIN_AREA,
                    value=30.0,
                    unit=MetricUnit.SQUARE_METRE,
                    rationale="Salon en az 30 m² olmalı",
                    requires_user_confirmation=True,
                )
            ]

        return ArchitecturalIntentResult(
            assistant_message="Salon için en az 30 m² alan gereksinimi öneriyorum.",
            intent=IntentType.GATHER_REQUIREMENT,
            target=EntityTarget(project_id=request.active_context.project_id),
            user_requirements=["Salon en az 30 m² olsun"],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_brief_mutations=[],
            proposed_spatial_relationships=[],
            proposed_metric_requirements=metric_reqs,
            needs_follow_up=False,
            needs_user_confirmation=bool(metric_reqs),
            confidence=0.95,
            warnings=[],
        )


ApiClientFixture = tuple[
    TestClient,
    JSONBriefRepository,
    JSONSpatialRelationshipRepository,
    JSONPlanInputStateRepository,
    MockMetricInterpretationProvider,
]


def _init_test_brief(
    repo: JSONBriefRepository, project_id: str = "proj_test_metrics"
) -> BriefSnapshot:
    snapshot = BriefSnapshot(
        project_id=project_id,
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(id="stk_1", display_name="Owner", role="CLIENT_OWNER", active=True)
        ],
        evidence=[
            Evidence(
                id="ev_init_1",
                source_type=EvidenceSource.CHAT,
                source_reference="chat_init",
                excerpt="Salon ve mutfak olsun.",
            )
        ],
        brief_items=[],
        usage_scenarios=[],
        contradictions=[],
        open_questions=_closed_topic_questions(),
        space_requests=[
            SpaceRequest(
                id="sr_living_room",
                display_name="Salon",
                space_function=SpaceFunction.LIVING,
                minimum_quantity=1,
                maximum_quantity=1,
                mandatory=True,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_init_1"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            ),
            SpaceRequest(
                id="sr_kitchen",
                display_name="Mutfak",
                space_function=SpaceFunction.COOKING,
                minimum_quantity=1,
                maximum_quantity=1,
                mandatory=True,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_init_1"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            ),
        ],
    )
    return repo.save(snapshot)


def _init_test_graph(
    repo: JSONSpatialRelationshipRepository, project_id: str = "proj_test_metrics"
) -> SpatialRelationshipGraph:
    graph = SpatialRelationshipGraph(
        project_id=project_id,
        schema_version="spatial_graph.v0",
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
        nodes=[
            SpatialNode(
                id="sn_living_room_01",
                display_name="Salon",
                function=SpaceFunction.LIVING,
                source_space_request_id="sr_living_room",
                instance_index=1,
            ),
            SpatialNode(
                id="sn_kitchen_01",
                display_name="Mutfak",
                function=SpaceFunction.COOKING,
                source_space_request_id="sr_kitchen",
                instance_index=1,
            ),
        ],
        relationships=[
            SpatialRelationship(
                id="edge_1",
                source_space_id="sn_living_room_01",
                target_space_id="sn_kitchen_01",
                relation_type=SpatialRelationType.ADJACENT_TO,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                priority=Priority.MUST,
                evidence_ids=["ev_init_1"],
            )
        ],
    )
    return repo.save(graph)


@pytest.fixture
def api_client(tmp_path: Path) -> ApiClientFixture:
    brief_repo = JSONBriefRepository(root_dir=tmp_path / "briefs")
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path / "spatial")
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path / "plan_input")
    mock_provider = MockMetricInterpretationProvider()
    settings = LocalLLMSettings(enabled=True, provider="ollama", model="llama3.2")
    app = create_app(
        settings=settings,
        provider=mock_provider,
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )
    return TestClient(app), brief_repo, spatial_repo, plan_input_repo, mock_provider


def test_approve_metric_requirement_initializes_state(api_client: ApiClientFixture) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
            rationale="Salon en az 30 m2",
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_test",
        current_fingerprint="fp_test",
        proposal_generation_id=1,
        current_generation_id=1,
    )

    response = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve",
        json=req.model_dump(mode="json"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["resulting_plan_input_state"] is not None
    assert data["resulting_plan_input_state"]["state_version"] == 1
    assert data["approval_record"]["resulting_state_version"] == 1
    assert data["approval_record"]["proposal_status"] == "user_approved"

    # Verify space requirement details
    metrics = data["resulting_plan_input_state"]["metric_requirements"]
    assert metrics is not None
    space_reqs = metrics["space_requirements"]
    living_space = next(s for s in space_reqs if s["space_id"] == "sn_living_room_01")
    req_item = living_space["requirements"][0]
    assert req_item["requirement_type"] == "MIN_AREA"
    assert req_item["value"] == 30.0
    assert req_item["provenance"] == "USER_CONFIRMED"
    assert req_item["evidence_ids"] == ["ev_init_1"]


def test_approve_metric_requirement_advances_existing_state(api_client: ApiClientFixture) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    # First approve living room MIN_AREA
    req1 = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    r1 = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req1.model_dump(mode="json")
    )
    assert r1.status_code == 200
    assert r1.json()["resulting_plan_input_state"]["state_version"] == 1

    # Second approve kitchen MAX_AREA on expected_state_version=1
    req2 = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_2",
            space_id="sn_kitchen_01",
            requirement_type=MetricRequirementType.MAX_AREA,
            value=20.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_2",
        current_fingerprint="fp_2",
        proposal_generation_id=2,
        current_generation_id=2,
    )
    r2 = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req2.model_dump(mode="json")
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["resulting_plan_input_state"]["state_version"] == 2
    assert data2["approval_record"]["resulting_state_version"] == 2

    # Verify both requirements exist
    space_reqs = data2["resulting_plan_input_state"]["metric_requirements"]["space_requirements"]
    assert len(space_reqs) == 2


def test_approve_metric_requirement_replaces_same_requirement_type(
    api_client: ApiClientFixture,
) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    # Initial MIN_AREA = 25.0
    req1 = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=25.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req1.model_dump(mode="json")
    )

    # Replace with MIN_AREA = 35.0
    req2 = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_2",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=35.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_2",
        current_fingerprint="fp_2",
        proposal_generation_id=2,
        current_generation_id=2,
    )
    r2 = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req2.model_dump(mode="json")
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["resulting_plan_input_state"]["state_version"] == 2
    space_reqs = data2["resulting_plan_input_state"]["metric_requirements"]["space_requirements"]
    living_space = next(s for s in space_reqs if s["space_id"] == "sn_living_room_01")
    living_reqs = living_space["requirements"]
    assert len(living_reqs) == 1
    assert living_reqs[0]["value"] == 35.0


def test_approve_metric_requirement_idempotent_replay(
    api_client: ApiClientFixture,
) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    req1 = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    r1 = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req1.model_dump(mode="json")
    )
    assert r1.status_code == 200
    assert r1.json()["resulting_plan_input_state"]["state_version"] == 1

    # Replay with same state version expected and same proposal
    req_replay = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    r2 = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve",
        json=req_replay.model_dump(mode="json"),
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["success"] is True
    # State version MUST NOT advance
    assert data2["resulting_plan_input_state"]["state_version"] == 1
    assert data2["approval_record"]["resulting_state_version"] == 1


def test_approve_metric_requirement_stale_fingerprint_rejected(
    api_client: ApiClientFixture,
) -> None:
    client, brief_repo, spatial_repo, _, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_old",
        current_fingerprint="fp_new",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    response = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert response.status_code == 409


def test_approve_metric_requirement_stale_generation_rejected(api_client: ApiClientFixture) -> None:
    client, brief_repo, spatial_repo, _, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=2,
    )
    response = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert response.status_code == 409


def test_approve_metric_requirement_stale_brief_version_rejected(
    api_client: ApiClientFixture,
) -> None:
    client, brief_repo, spatial_repo, _, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=99,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    response = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert response.status_code == 409


def test_approve_metric_requirement_stale_state_version_rejected(
    api_client: ApiClientFixture,
) -> None:
    client, brief_repo, spatial_repo, _, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    # Initialize state to v1
    req1 = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req1.model_dump(mode="json")
    )

    # Attempt approve expecting None when v1 already exists
    req_stale = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_2",
            space_id="sn_kitchen_01",
            requirement_type=MetricRequirementType.MAX_AREA,
            value=20.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_2",
        current_fingerprint="fp_2",
        proposal_generation_id=2,
        current_generation_id=2,
    )
    response = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req_stale.model_dump(mode="json")
    )
    assert response.status_code == 409


def test_approve_metric_requirement_uninitialized_brief_404(api_client: ApiClientFixture) -> None:
    client, _, _, _, _ = api_client
    pid = "proj_uninitialized"

    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    response = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert response.status_code == 404


def test_approve_metric_requirement_missing_spatial_graph_409(api_client: ApiClientFixture) -> None:
    client, brief_repo, _, _, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    # Spatial graph NOT initialized

    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    response = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert response.status_code == 409


def test_approve_metric_requirement_nonexistent_space_409(api_client: ApiClientFixture) -> None:
    client, brief_repo, spatial_repo, _, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_nonexistent_room",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    response = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert response.status_code == 409


def test_approve_metric_requirement_route_project_mismatch_422(
    api_client: ApiClientFixture,
) -> None:
    client, brief_repo, spatial_repo, _, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id="proj_other",
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    response = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert response.status_code == 422


def test_approve_metric_requirement_invalid_project_id_422(api_client: ApiClientFixture) -> None:
    client, _, _, _, _ = api_client
    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id="bad id with spaces",
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    response = client.post(
        "/api/v1/projects/bad%20id%20with%20spaces/plan/input/metrics/approve",
        json=req.model_dump(mode="json"),
    )
    assert response.status_code == 422


def test_approve_metric_requirement_range_conflict_422(api_client: ApiClientFixture) -> None:
    client, brief_repo, spatial_repo, _, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    # Set MIN_AREA = 40.0
    req1 = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=40.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req1.model_dump(mode="json")
    )

    # Attempt MAX_AREA = 30.0 (less than min area 40)
    req2 = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_2",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MAX_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_2",
        current_fingerprint="fp_2",
        proposal_generation_id=2,
        current_generation_id=2,
    )
    response = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req2.model_dump(mode="json")
    )
    assert response.status_code == 422


def test_conversation_interpret_populates_metric_context_and_state_version(
    api_client: ApiClientFixture,
) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, mock_provider = api_client
    pid = "proj_test_metrics"
    brief = _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    # Pre-populate plan input state (version 1)
    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id=pid,
            state_version=1,
            source_brief_version=1,
            created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
            metric_requirements=MetricSpatialRequirements(
                project_id=pid,
                source_brief_version=1,
                created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
                space_requirements=[
                    SpaceMetricRequirements(
                        space_id="sn_living_room_01",
                        requirements=[
                            MetricRequirement(
                                id="mr_1",
                                space_id="sn_living_room_01",
                                requirement_type=MetricRequirementType.MIN_AREA,
                                value=25.0,
                                unit=MetricUnit.SQUARE_METRE,
                                provenance=RelationshipProvenance.USER_CONFIRMED,
                                priority=Priority.MUST,
                                evidence_ids=["ev_init_1"],
                            )
                        ],
                    )
                ],
                authoritative_requirement_ids=["mr_1"],
            ),
        )
    )

    conv_req = ConversationRequest(
        message="Salon en az 30 m² olsun",
        active_context=ActiveContextSnapshot(
            project_id=pid,
            context_fingerprint="fp_conv_1",
            generation_id=1,
        ),
        brief_snapshot=brief,
        visible_entities=[],
    )

    response = client.post("/api/v1/conversation/interpret", json=conv_req.model_dump(mode="json"))
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["authoritative_plan_input_state_version"] == 1

    # Verify provider received server-derived metric_context
    assert mock_provider.last_metric_context is not None
    assert mock_provider.last_metric_context.source_brief_version == 1
    assert mock_provider.last_metric_context.source_plan_input_state_version == 1
    assert len(mock_provider.last_metric_context.spaces) == 2


def test_conversation_interpret_rejects_forged_metric_context_and_state_version(
    api_client: ApiClientFixture,
) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, _ = api_client
    pid = "proj_test_metrics"
    brief = _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    # 1. Attempt sending forged metric_context -> must be rejected with 422
    forged_payload_1 = {
        "message": "Salon 30 m² olsun",
        "active_context": {
            "project_id": pid,
            "context_fingerprint": "fp_1",
            "generation_id": 1,
        },
        "brief_snapshot": brief.model_dump(mode="json"),
        "visible_entities": [],
        "metric_context": {
            "spaces": [
                {
                    "space_id": "invented_space",
                    "display_name": "Invented Room",
                    "function": "LIVING",
                    "existing_requirements": [],
                }
            ],
            "source_brief_version": 1,
        },
    }
    r1 = client.post("/api/v1/conversation/interpret", json=forged_payload_1)
    assert r1.status_code == 422

    # 2. Attempt sending forged authoritative_plan_input_state_version -> must be rejected with 422
    forged_payload_2 = {
        "message": "Salon 30 m² olsun",
        "active_context": {
            "project_id": pid,
            "context_fingerprint": "fp_1",
            "generation_id": 1,
        },
        "brief_snapshot": brief.model_dump(mode="json"),
        "visible_entities": [],
        "authoritative_plan_input_state_version": 999,
    }
    r2 = client.post("/api/v1/conversation/interpret", json=forged_payload_2)
    assert r2.status_code == 422


def test_conversation_interpret_continues_when_spatial_program_unavailable(
    api_client: ApiClientFixture,
) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, mock_provider = api_client
    pid = "proj_test_metrics"
    brief = _init_test_brief(brief_repo, pid)
    # Note: no graph initialized, so SpatialProgram cannot be constructed

    conv_req = ConversationRequest(
        message="Merhaba, projeye başlamak istiyorum.",
        active_context=ActiveContextSnapshot(
            project_id=pid,
            context_fingerprint="fp_1",
            generation_id=1,
        ),
        brief_snapshot=brief,
        visible_entities=[],
    )
    response = client.post("/api/v1/conversation/interpret", json=conv_req.model_dump(mode="json"))
    # Normal conversation continues without 500 error
    assert response.status_code == 200
    # metric_context passed to provider is None
    assert mock_provider.last_metric_context is None


def test_idempotent_approval_replay_exact_state_version(api_client: ApiClientFixture) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
            rationale="Salon 30 m2",
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )

    # First POST: creates state version 1
    r1 = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["success"] is True
    assert d1["resulting_plan_input_state"]["state_version"] == 1

    # Replay THE EXACT SAME REQUEST (still has expected_plan_input_state_version=None)
    r2 = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["success"] is True
    assert d2["resulting_plan_input_state"]["state_version"] == 1

    # Verify repository contains only version 1 (no extra state version created)
    all_versions = plan_input_repo.list_versions(pid)
    assert all_versions == [1]


def test_stale_approval_replay_after_later_semantic_change_returns_conflict(
    api_client: ApiClientFixture,
) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    # 1. First approval: Salon MIN_AREA 30 -> resulting state version 1
    req_30 = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    r1 = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req_30.model_dump(mode="json")
    )
    assert r1.status_code == 200
    assert r1.json()["resulting_plan_input_state"]["state_version"] == 1

    # 2. Second approval: Salon MIN_AREA changed to 35 -> resulting state version 2
    req_35 = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_2",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=35.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_2",
        current_fingerprint="fp_2",
        proposal_generation_id=2,
        current_generation_id=2,
    )
    r2 = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req_35.model_dump(mode="json")
    )
    assert r2.status_code == 200
    assert r2.json()["resulting_plan_input_state"]["state_version"] == 2

    # 3. Stale replay of the old 30 approval request:
    # Current authoritative value is 35, so 30 is not identical.
    # It must NOT overwrite the 35 m² requirement and MUST return 409 Conflict.
    r_stale = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req_30.model_dump(mode="json")
    )
    assert r_stale.status_code == 409

    # Verify latest authoritative state still has MIN_AREA = 35
    latest_state = plan_input_repo.get_latest(pid)
    assert latest_state is not None
    assert latest_state.state_version == 2
    assert latest_state.metric_requirements is not None
    living_reqs = next(
        sr
        for sr in latest_state.metric_requirements.space_requirements
        if sr.space_id == "sn_living_room_01"
    )
    assert len(living_reqs.requirements) == 1
    assert living_reqs.requirements[0].value == 35.0


def test_approval_evidence_and_provenance_strictly_authoritative(
    api_client: ApiClientFixture,
) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    r = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert r.status_code == 200
    state = plan_input_repo.get_latest(pid)
    assert state is not None
    assert state.metric_requirements is not None
    living_reqs = next(
        sr
        for sr in state.metric_requirements.space_requirements
        if sr.space_id == "sn_living_room_01"
    )
    approved_req = living_reqs.requirements[0]
    # Invariant: Evidence IDs come strictly from authoritative ProgramSpace (ev_init_1)
    assert approved_req.evidence_ids == ["ev_init_1"]
    # Invariant: Provenance is USER_CONFIRMED
    assert approved_req.provenance == RelationshipProvenance.USER_CONFIRMED


def test_metric_replacement_and_preservation_across_spaces(api_client: ApiClientFixture) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    # Initial state with:
    # - Salon MIN_AREA 25
    # - Kitchen MIN_AREA 12
    # - Kitchen MIN_CLEAR_WIDTH 1.10
    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id=pid,
            state_version=1,
            source_brief_version=1,
            created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
            metric_requirements=MetricSpatialRequirements(
                project_id=pid,
                source_brief_version=1,
                created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
                space_requirements=[
                    SpaceMetricRequirements(
                        space_id="sn_living_room_01",
                        requirements=[
                            MetricRequirement(
                                id="mr_living_min",
                                space_id="sn_living_room_01",
                                requirement_type=MetricRequirementType.MIN_AREA,
                                value=25.0,
                                unit=MetricUnit.SQUARE_METRE,
                                provenance=RelationshipProvenance.USER_CONFIRMED,
                                priority=Priority.MUST,
                                evidence_ids=["ev_init_1"],
                            )
                        ],
                    ),
                    SpaceMetricRequirements(
                        space_id="sn_kitchen_01",
                        requirements=[
                            MetricRequirement(
                                id="mr_kitchen_min",
                                space_id="sn_kitchen_01",
                                requirement_type=MetricRequirementType.MIN_AREA,
                                value=12.0,
                                unit=MetricUnit.SQUARE_METRE,
                                provenance=RelationshipProvenance.USER_CONFIRMED,
                                priority=Priority.MUST,
                                evidence_ids=["ev_init_1"],
                            ),
                            MetricRequirement(
                                id="mr_kitchen_width",
                                space_id="sn_kitchen_01",
                                requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
                                value=1.10,
                                unit=MetricUnit.METRE,
                                provenance=RelationshipProvenance.USER_CONFIRMED,
                                priority=Priority.MUST,
                                evidence_ids=["ev_init_1"],
                            ),
                        ],
                    ),
                ],
                authoritative_requirement_ids=[
                    "mr_kitchen_min",
                    "mr_kitchen_width",
                    "mr_living_min",
                ],
            ),
        )
    )

    # Approve Salon MIN_AREA 30
    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_replace",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    r = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert r.status_code == 200

    latest_state = plan_input_repo.get_latest(pid)
    assert latest_state is not None
    assert latest_state.state_version == 2
    assert latest_state.metric_requirements is not None
    living_reqs = next(
        sr
        for sr in latest_state.metric_requirements.space_requirements
        if sr.space_id == "sn_living_room_01"
    )
    # There must be only ONE Salon MIN_AREA requirement (value 30, replaced 25)
    assert len(living_reqs.requirements) == 1
    assert living_reqs.requirements[0].value == 30.0

    kitchen_reqs = next(
        sr
        for sr in latest_state.metric_requirements.space_requirements
        if sr.space_id == "sn_kitchen_01"
    )
    # Kitchen requirements must be exactly preserved
    assert len(kitchen_reqs.requirements) == 2
    kitchen_min = next(
        r for r in kitchen_reqs.requirements if r.requirement_type == MetricRequirementType.MIN_AREA
    )
    assert kitchen_min.value == 12.0
    kitchen_width = next(
        r
        for r in kitchen_reqs.requirements
        if r.requirement_type == MetricRequirementType.MIN_CLEAR_WIDTH
    )
    assert kitchen_width.value == 1.10


def test_approval_preserves_site_envelope_floor_plate_and_solver_config(
    api_client: ApiClientFixture,
) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, _ = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    from brif_ai.spatial.floor_plate.models import FloorPlateInput
    from brif_ai.spatial.room_solver.models import RoomGeometrySolverConfig
    from brif_ai.spatial.site.models import (
        SiteBuildableEnvelope,
        SiteGeometryRole,
        SitePoint,
        SitePolygon,
    )

    site = SiteBuildableEnvelope(
        project_id=pid,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
        parcel_boundary=SitePolygon(
            id="site_poly_1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=20.0),
                SitePoint(x_m=0.0, y_m=20.0),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_init_1"],
        ),
        authoritative_geometry_ids=["site_poly_1"],
    )
    fp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=3.0, y_m=3.0),
            SitePoint(x_m=15.0, y_m=3.0),
            SitePoint(x_m=15.0, y_m=15.0),
            SitePoint(x_m=3.0, y_m=15.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_init_1"],
    )
    solver_cfg = RoomGeometrySolverConfig(
        grid_step_m=1.0,
        max_time_seconds=10.0,
    )

    initial_state = AuthoritativePlanInputState(
        project_id=pid,
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=solver_cfg,
    )
    plan_input_repo.save(initial_state)

    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=1,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    r = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert r.status_code == 200

    latest_state = plan_input_repo.get_latest(pid)
    assert latest_state is not None
    assert latest_state.state_version == 2
    # Invariant: site_envelope, floor_plate_input, solver_config are preserved exactly
    assert latest_state.site_envelope == site
    assert latest_state.floor_plate_input == fp
    assert latest_state.solver_config == solver_cfg


def test_approval_does_not_mutate_brief_or_graph_reload_equality(
    api_client: ApiClientFixture,
) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, _ = api_client
    pid = "proj_test_metrics"
    initial_brief = _init_test_brief(brief_repo, pid)
    initial_graph = _init_test_graph(spatial_repo, pid)

    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    r = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert r.status_code == 200

    # Reload brief and graph and assert exact equality
    reloaded_brief = brief_repo.get_latest(pid)
    reloaded_graph = spatial_repo.get_latest(pid)
    assert reloaded_brief is not None
    assert reloaded_graph is not None
    assert reloaded_brief.model_dump() == initial_brief.model_dump()
    assert reloaded_graph.model_dump() == initial_graph.model_dump()


def test_zero_llm_during_approval(api_client: ApiClientFixture) -> None:
    client, brief_repo, spatial_repo, plan_input_repo, mock_provider = api_client
    pid = "proj_test_metrics"
    _init_test_brief(brief_repo, pid)
    _init_test_graph(spatial_repo, pid)

    mock_provider.call_count = 0

    req = MetricRequirementApprovalRequest(
        proposed_requirement=ProposedMetricRequirement(
            proposal_id="prop_m_1",
            space_id="sn_living_room_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
        ),
        current_project_id=pid,
        expected_brief_version=1,
        expected_plan_input_state_version=None,
        proposal_fingerprint="fp_1",
        current_fingerprint="fp_1",
        proposal_generation_id=1,
        current_generation_id=1,
    )
    r = client.post(
        f"/api/v1/projects/{pid}/plan/input/metrics/approve", json=req.model_dump(mode="json")
    )
    assert r.status_code == 200

    # Invariant: zero LLM calls during approval
    assert mock_provider.call_count == 0
