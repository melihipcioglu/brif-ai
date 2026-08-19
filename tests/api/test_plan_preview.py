"""API tests for Plan Preview API V0 (POST /api/v1/plan/preview)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import Any

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
from brif_ai.conversation.elicitation.models import ElicitationTopic
from brif_ai.core.models.common import SpaceFunction
from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    ConversationRequest,
    EntityTarget,
    IntentType,
    LocalModelInfo,
    ProviderHealth,
)
from brif_ai.llm.settings import LocalLLMSettings
from brif_ai.spatial.builder import SpatialRelationshipGraphBuilder
from brif_ai.spatial.floor_plate.builder import FloorPlateBuilder
from brif_ai.spatial.floor_plate.models import (
    FloorPlate,
    FloorPlateInput,
    generate_floor_plate_id,
)
from brif_ai.spatial.layout.compiler import LayoutProblemCompiler
from brif_ai.spatial.metrics.builder import MetricSpatialRequirementsBuilder
from brif_ai.spatial.metrics.models import (
    MetricRequirement,
    MetricRequirementInput,
    MetricRequirementType,
    MetricUnit,
    generate_metric_requirement_id,
)
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationshipInput,
    SpatialRelationType,
)
from brif_ai.spatial.plan_preview.models import (
    PlanPreviewRequest,
    PlanPreviewResponse,
)
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.room_solver.models import RoomGeometrySolverConfig
from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.models import (
    SitePoint,
    SitePolygonInput,
)
from brif_ai.spatial.solver_input import LayoutSolverInputAssembler
from brif_ai.spatial.solver_policy.compiler import SolverPolicyCompiler
from brif_ai.spatial.svg_plan.models import SvgPlanRenderConfig


class MockAPIProvider:
    async def health(self) -> ProviderHealth:
        return ProviderHealth(provider="ollama", reachable=True)

    async def list_models(self) -> list[LocalModelInfo]:
        return [LocalModelInfo(name="local-model:latest", size=42)]

    async def interpret(
        self, request: ConversationRequest, output_schema: dict[str, object]
    ) -> ArchitecturalIntentResult:
        return ArchitecturalIntentResult(
            assistant_message="Plan preview mock.",
            intent=IntentType.GATHER_REQUIREMENT,
            target=EntityTarget(project_id=request.active_context.project_id),
            user_requirements=[],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_brief_mutations=[],
            proposed_spatial_relationships=[],
            needs_follow_up=False,
            needs_user_confirmation=True,
            confidence=0.95,
            warnings=[],
        )


@pytest.fixture
def api_client() -> TestClient:
    settings = LocalLLMSettings(enabled=True, provider="ollama", model="local-model:latest")
    app = create_app(settings=settings, provider=MockAPIProvider())
    return TestClient(app)


def _build_two_room_preview_fixture(
    *,
    fp_origin_x: float = 4.0,
    fp_origin_y: float = 4.0,
    fp_width: float = 6.0,
    fp_depth: float = 6.0,
    living_min_area: float = 20.0,
    kitchen_min_area: float = 10.0,
    project_id: str = "proj_living_kitchen_01",
    brief_version: int = 1,
    fp_project_id: str | None = None,
    fp_brief_version: int | None = None,
    grid_step_m: float = 0.10,
    render_config: SvgPlanRenderConfig | None = None,
) -> PlanPreviewRequest:
    ev = Evidence(
        id="ev_01",
        source_type=EvidenceSource.CHAT,
        source_reference="chat:turn-1",
        excerpt="Client requested living room adjacent to kitchen.",
    )
    spaces = [
        SpaceRequest(
            id="sr_living",
            display_name="Living Room",
            space_function=SpaceFunction.LIVING,
            minimum_quantity=1,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_01"],
            evidence_ids=[ev.id],
        ),
        SpaceRequest(
            id="sr_kitchen",
            display_name="Kitchen",
            space_function=SpaceFunction.COOKING,
            minimum_quantity=1,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_01"],
            evidence_ids=[ev.id],
        ),
    ]
    all_topics = [
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
    open_questions = [
        OpenQuestion(
            id=f"oq_{t.value}",
            question=f"Question on {t.value}",
            reason="Ready fixture",
            related_brief_item_ids=[],
            status=OpenQuestionStatus.ANSWERED,
            resolution_note="Answered and confirmed",
            topic_key=t.value,
        )
        for t in all_topics
    ]
    snapshot = BriefSnapshot(
        project_id=project_id,
        schema_version="brief.v0",
        brief_version=brief_version,
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(
                id="stk_01",
                display_name="Client",
                role="CLIENT_OWNER",
                active=True,
            )
        ],
        evidence=[ev],
        brief_items=[],
        space_requests=spaces,
        usage_scenarios=[],
        contradictions=[],
        open_questions=open_questions,
    )
    relationships = [
        SpatialRelationshipInput(
            source_space_id="sn_living_01",
            target_space_id="sn_kitchen_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=[ev.id],
            rationale="Open-plan connection between living and kitchen",
        ),
    ]
    graph = SpatialRelationshipGraphBuilder().build(
        snapshot,
        relationships,
        created_at=datetime(2026, 8, 19, 12, 5, 0, tzinfo=UTC),
    )
    program = SpatialProgramBuilder().build(snapshot, graph)

    layout_problem = LayoutProblemCompiler().compile(program)
    directive_set = SolverPolicyCompiler().compile(layout_problem)

    metrics = MetricSpatialRequirementsBuilder().build(
        program,
        [
            MetricRequirementInput(
                space_id="sn_living_01",
                requirement_type=MetricRequirementType.MIN_AREA,
                value=living_min_area,
                unit=MetricUnit.SQUARE_METRE,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                priority=Priority.MUST,
                evidence_ids=[ev.id],
            ),
            MetricRequirementInput(
                space_id="sn_kitchen_01",
                requirement_type=MetricRequirementType.MIN_AREA,
                value=kitchen_min_area,
                unit=MetricUnit.SQUARE_METRE,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                priority=Priority.MUST,
                evidence_ids=[ev.id],
            ),
        ],
        created_at=datetime(2026, 8, 19, 12, 10, 0, tzinfo=UTC),
    )

    p_min_x = min(fp_origin_x, 0.0) - 10.0
    p_min_y = min(fp_origin_y, 0.0) - 10.0
    p_max_x = max(fp_origin_x + fp_width, 50.0) + 10.0
    p_max_y = max(fp_origin_y + fp_depth, 50.0) + 10.0

    site_env = SiteBuildableEnvelopeBuilder().build(
        program,
        parcel_boundary=SitePolygonInput(
            vertices=[
                SitePoint(x_m=p_min_x, y_m=p_min_y),
                SitePoint(x_m=p_max_x, y_m=p_min_y),
                SitePoint(x_m=p_max_x, y_m=p_max_y),
                SitePoint(x_m=p_min_x, y_m=p_max_y),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[ev.id],
        ),
        buildable_envelope=SitePolygonInput(
            vertices=[
                SitePoint(x_m=p_min_x + 2.0, y_m=p_min_y + 2.0),
                SitePoint(x_m=p_max_x - 2.0, y_m=p_min_y + 2.0),
                SitePoint(x_m=p_max_x - 2.0, y_m=p_max_y - 2.0),
                SitePoint(x_m=p_min_x + 2.0, y_m=p_max_y - 2.0),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[ev.id],
        ),
        created_at=datetime(2026, 8, 19, 12, 15, 0, tzinfo=UTC),
    )

    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    floor_plate = FloorPlateBuilder().build(
        solver_input,
        FloorPlateInput(
            vertices=[
                SitePoint(x_m=fp_origin_x, y_m=fp_origin_y),
                SitePoint(x_m=fp_origin_x + fp_width, y_m=fp_origin_y),
                SitePoint(x_m=fp_origin_x + fp_width, y_m=fp_origin_y + fp_depth),
                SitePoint(x_m=fp_origin_x, y_m=fp_origin_y + fp_depth),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[ev.id],
            rationale="Rectangular FloorPlate",
        ),
    )

    if fp_project_id is not None or fp_brief_version is not None:
        updates: dict[str, Any] = {}
        if fp_project_id is not None:
            updates["project_id"] = fp_project_id
            updates["id"] = generate_floor_plate_id(fp_project_id)
        if fp_brief_version is not None:
            updates["source_brief_version"] = fp_brief_version
        floor_plate = floor_plate.model_copy(update=updates)

    return PlanPreviewRequest(
        solver_input=solver_input,
        floor_plate=floor_plate,
        solver_config=RoomGeometrySolverConfig(grid_step_m=grid_step_m),
        render_config=render_config,
    )


# -----------------------------------------------------------------------------
# 1. Success & End-to-End Rendering Tests
# -----------------------------------------------------------------------------


def test_valid_two_room_preview_success_200(api_client: TestClient) -> None:
    req = _build_two_room_preview_fixture()
    response = api_client.post("/api/v1/plan/preview", json=req.model_dump(mode="json"))

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["error"] is None
    assert data["solution"] is not None
    assert data["document"] is not None

    sol = data["solution"]
    assert sol["schema_version"] == "room_geometry_solution.v0"
    assert sol["status"] == "FEASIBLE"
    assert len(sol["rooms"]) == 2

    doc = data["document"]
    assert doc["schema_version"] == "svg_plan_document.v0"
    assert doc["width_px"] == 560.0
    assert doc["height_px"] == 560.0

    # XML validation
    root = ET.fromstring(doc["svg"])
    assert root.tag.endswith("svg")
    assert "Living Room" in doc["svg"]
    assert "Kitchen" in doc["svg"]


def test_deterministic_repeated_request_response(api_client: TestClient) -> None:
    req = _build_two_room_preview_fixture()
    payload = req.model_dump(mode="json")

    res1 = api_client.post("/api/v1/plan/preview", json=payload)
    res2 = api_client.post("/api/v1/plan/preview", json=payload)

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json() == res2.json()
    assert res1.json()["document"]["svg"] == res2.json()["document"]["svg"]


def test_required_adjacency_and_min_area_satisfied_through_api(api_client: TestClient) -> None:
    req = _build_two_room_preview_fixture()
    response = api_client.post("/api/v1/plan/preview", json=req.model_dump(mode="json"))

    assert response.status_code == 200
    rooms = response.json()["solution"]["rooms"]
    rooms_by_id = {r["space_id"]: r for r in rooms}

    living = rooms_by_id["sn_living_01"]
    kitchen = rooms_by_id["sn_kitchen_01"]

    assert living["area_m2"] >= 20.0
    assert kitchen["area_m2"] >= 10.0

    # Adjacency check: shared vertical or horizontal edge with length > 0
    liv_x_min, liv_x_max = living["x_m"], living["x_m"] + living["width_m"]
    liv_y_min, liv_y_max = living["y_m"], living["y_m"] + living["depth_m"]
    kit_x_min, kit_x_max = kitchen["x_m"], kitchen["x_m"] + kitchen["width_m"]
    kit_y_min, kit_y_max = kitchen["y_m"], kitchen["y_m"] + kitchen["depth_m"]

    touch_x = abs(liv_x_max - kit_x_min) < 1e-6 or abs(kit_x_max - liv_x_min) < 1e-6
    overlap_y = max(0.0, min(liv_y_max, kit_y_max) - max(liv_y_min, kit_y_min))

    touch_y = abs(liv_y_max - kit_y_min) < 1e-6 or abs(kit_y_max - liv_y_min) < 1e-6
    overlap_x = max(0.0, min(liv_x_max, kit_x_max) - max(liv_x_min, kit_x_min))

    has_shared_edge = (touch_x and overlap_y > 0.0) or (touch_y and overlap_x > 0.0)
    assert has_shared_edge


# -----------------------------------------------------------------------------
# 2. Error Mapping Tests (409, 422, 500, etc.)
# -----------------------------------------------------------------------------


def test_project_id_mismatch_returns_409(api_client: TestClient) -> None:
    req = _build_two_room_preview_fixture(fp_project_id="proj_other_999")
    response = api_client.post("/api/v1/plan/preview", json=req.model_dump(mode="json"))

    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["solution"] is None
    assert data["document"] is None
    assert "project_id mismatch" in data["error"]


def test_brief_version_mismatch_returns_409(api_client: TestClient) -> None:
    req = _build_two_room_preview_fixture(fp_brief_version=2)
    response = api_client.post("/api/v1/plan/preview", json=req.model_dump(mode="json"))

    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["solution"] is None
    assert data["document"] is None
    assert "source_brief_version mismatch" in data["error"]


def test_unsupported_target_area_returns_422(api_client: TestClient) -> None:
    req = _build_two_room_preview_fixture()
    extra_metric = MetricRequirement(
        id=generate_metric_requirement_id(
            req.solver_input.project_id, "sn_living_01", MetricRequirementType.TARGET_AREA
        ),
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.TARGET_AREA,
        value=50.0,
        unit=MetricUnit.SQUARE_METRE,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.MUST,
        evidence_ids=["ev_01"],
    )
    new_smr = []
    for sm in req.solver_input.space_metric_requirements:
        if sm.space_id == "sn_living_01":
            new_smr.append(sm.model_copy(update={"requirements": [*sm.requirements, extra_metric]}))
        else:
            new_smr.append(sm)
    new_solver_input = req.solver_input.model_copy(update={"space_metric_requirements": new_smr})
    bad_req = req.model_copy(update={"solver_input": new_solver_input})

    response = api_client.post("/api/v1/plan/preview", json=bad_req.model_dump(mode="json"))
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["solution"] is None
    assert data["document"] is None
    assert "TARGET_AREA metric requirement" in data["error"]


def test_unsupported_floor_plate_returns_422(api_client: TestClient) -> None:
    req = _build_two_room_preview_fixture()
    # 5-vertex polygon floor plate
    poly_fp = FloorPlate(
        id=generate_floor_plate_id(req.solver_input.project_id),
        project_id=req.solver_input.project_id,
        source_brief_version=1,
        source_solver_input_schema_version="layout_solver_input_set.v0",
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        coordinate_system="LOCAL_CARTESIAN_METRES",
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=10.0),
            SitePoint(x_m=10.0, y_m=20.0),
            SitePoint(x_m=0.0, y_m=20.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )
    bad_req = req.model_copy(update={"floor_plate": poly_fp})
    response = api_client.post("/api/v1/plan/preview", json=bad_req.model_dump(mode="json"))

    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["solution"] is None
    assert data["document"] is None
    assert "requires exactly 4 vertices" in data["error"]


def test_infeasible_layout_returns_422(api_client: TestClient) -> None:
    # Floor plate 3m x 3m (9 m2) with total room min areas 30 m2
    req = _build_two_room_preview_fixture(fp_width=3.0, fp_depth=3.0)
    response = api_client.post("/api/v1/plan/preview", json=req.model_dump(mode="json"))

    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["solution"] is None
    assert data["document"] is None
    assert "infeasible" in data["error"].lower()


def test_invalid_grid_alignment_returns_422(api_client: TestClient) -> None:
    # FloorPlate width 6.05m not aligned to grid_step_m 0.10m
    req = _build_two_room_preview_fixture(fp_width=6.05)
    response = api_client.post("/api/v1/plan/preview", json=req.model_dump(mode="json"))

    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["solution"] is None
    assert data["document"] is None
    assert "not exact integer multiples of grid_step_m" in data["error"]


def test_no_partial_svg_or_solution_returned_on_failure(api_client: TestClient) -> None:
    req = _build_two_room_preview_fixture(fp_project_id="proj_mismatch")
    response = api_client.post("/api/v1/plan/preview", json=req.model_dump(mode="json"))

    assert response.status_code != 200
    data = response.json()
    assert data["success"] is False
    assert data["solution"] is None
    assert data["document"] is None
    assert isinstance(data["error"], str)
    assert len(data["error"]) > 0


def test_malformed_request_body_fastapi_validation_422(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/plan/preview", json={"invalid": "payload"})
    assert response.status_code == 422


# -----------------------------------------------------------------------------
# 3. Model Invariant & Regression Tests
# -----------------------------------------------------------------------------


def test_plan_preview_response_model_invariants() -> None:
    with pytest.raises(ValueError, match="must include solution"):
        PlanPreviewResponse(success=True, solution=None, document=None, error=None)

    with pytest.raises(ValueError, match="must include a non-empty error string"):
        PlanPreviewResponse(success=False, solution=None, document=None, error=None)


def test_existing_endpoints_unaffected(api_client: TestClient) -> None:
    health_res = api_client.get("/api/v1/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ok"
