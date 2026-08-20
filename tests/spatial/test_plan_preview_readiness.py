"""Unit and invariant tests for Plan Preview Readiness & Preparation Service V0."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import ValidationError

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
from brif_ai.spatial.builder import SpatialRelationshipGraphBuilder
from brif_ai.spatial.floor_plate.builder import FloorPlateBuilder
from brif_ai.spatial.floor_plate.models import (
    FloorPlateInput,
)
from brif_ai.spatial.layout.compiler import LayoutProblemCompiler
from brif_ai.spatial.metrics.builder import MetricSpatialRequirementsBuilder
from brif_ai.spatial.metrics.models import (
    MetricRequirementInput,
    MetricRequirementType,
    MetricSpatialRequirements,
    MetricUnit,
)
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationshipInput,
    SpatialRelationType,
)
from brif_ai.spatial.plan_preview.models import (
    PlanPreviewRequest,
)
from brif_ai.spatial.plan_preview.readiness import (
    PlanPreviewPreparationService,
    PlanPreviewReadinessBlocker,
    PlanPreviewReadinessBlockerCode,
    PlanPreviewReadinessResult,
)
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.room_solver.models import RoomGeometrySolverConfig
from brif_ai.spatial.room_solver.solver import RoomGeometrySolver
from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.models import (
    SiteBuildableEnvelope,
    SitePoint,
    SitePolygonInput,
)
from brif_ai.spatial.solver_input import LayoutSolverInputAssembler
from brif_ai.spatial.solver_policy.compiler import SolverPolicyCompiler
from brif_ai.spatial.solver_policy.models import SolverDirectiveSet
from brif_ai.spatial.svg_plan.models import SvgPlanRenderConfig
from brif_ai.spatial.svg_plan.renderer import SvgPlanRenderer


def _build_two_room_scenario_artifacts(
    *,
    project_id: str = "proj_living_kitchen_01",
    brief_version: int = 1,
    fp_origin_x: float = 4.0,
    fp_origin_y: float = 4.0,
    fp_width: float = 6.0,
    fp_depth: float = 6.0,
    living_min_area: float = 20.0,
    kitchen_min_area: float = 10.0,
    grid_step_m: float = 0.10,
) -> tuple[
    SolverDirectiveSet,
    MetricSpatialRequirements,
    SiteBuildableEnvelope,
    FloorPlateInput,
    RoomGeometrySolverConfig,
    SvgPlanRenderConfig,
]:
    """Helper constructing authoritative source artifacts for a 2-room layout scenario."""
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
        )
    ]
    graph = SpatialRelationshipGraphBuilder().build(
        snapshot,
        relationships,
        created_at=datetime(2026, 8, 19, 12, 5, 0, tzinfo=UTC),
    )
    program = SpatialProgramBuilder().build(snapshot, graph)
    layout_problem = LayoutProblemCompiler().compile(program)
    directive_set = SolverPolicyCompiler().compile(layout_problem)

    metric_builder = MetricSpatialRequirementsBuilder()
    metric_reqs = metric_builder.build(
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

    site_builder = SiteBuildableEnvelopeBuilder()
    site_envelope = site_builder.build(
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

    fp_input = FloorPlateInput(
        vertices=[
            SitePoint(x_m=fp_origin_x, y_m=fp_origin_y),
            SitePoint(x_m=fp_origin_x + fp_width, y_m=fp_origin_y),
            SitePoint(x_m=fp_origin_x + fp_width, y_m=fp_origin_y + fp_depth),
            SitePoint(x_m=fp_origin_x, y_m=fp_origin_y + fp_depth),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=[ev.id],
        rationale="Rectangular FloorPlate",
    )

    solver_config = RoomGeometrySolverConfig(
        grid_step_m=grid_step_m,
        max_time_seconds=10.0,
    )
    render_config = SvgPlanRenderConfig(
        scale_px_per_m=80.0,
        margin_px=40.0,
    )

    return directive_set, metric_reqs, site_envelope, fp_input, solver_config, render_config


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_all_required_inputs_missing_returns_full_canonical_blocker_list() -> None:
    """When all 5 required source artifacts are None, return all 5 blockers in canonical order."""
    result = PlanPreviewPreparationService.prepare(
        directive_set=None,
        metric_requirements=None,
        site_envelope=None,
        floor_plate_input=None,
        solver_config=None,
    )

    assert result.ready_for_preview is False
    assert result.request is None
    assert len(result.blockers) == 5

    expected_codes = [
        PlanPreviewReadinessBlockerCode.DIRECTIVE_SET_MISSING,
        PlanPreviewReadinessBlockerCode.METRIC_REQUIREMENTS_MISSING,
        PlanPreviewReadinessBlockerCode.SITE_ENVELOPE_MISSING,
        PlanPreviewReadinessBlockerCode.FLOOR_PLATE_INPUT_MISSING,
        PlanPreviewReadinessBlockerCode.SOLVER_CONFIG_MISSING,
    ]
    assert [b.code for b in result.blockers] == expected_codes
    for blocker in result.blockers:
        assert isinstance(blocker.message, str)
        assert len(blocker.message.strip()) > 0


@pytest.mark.parametrize(
    ("missing_idx", "expected_code"),
    [
        (0, PlanPreviewReadinessBlockerCode.DIRECTIVE_SET_MISSING),
        (1, PlanPreviewReadinessBlockerCode.METRIC_REQUIREMENTS_MISSING),
        (2, PlanPreviewReadinessBlockerCode.SITE_ENVELOPE_MISSING),
        (3, PlanPreviewReadinessBlockerCode.FLOOR_PLATE_INPUT_MISSING),
        (4, PlanPreviewReadinessBlockerCode.SOLVER_CONFIG_MISSING),
    ],
)
def test_each_required_artifact_missing_individually(
    missing_idx: int,
    expected_code: PlanPreviewReadinessBlockerCode,
) -> None:
    """When exactly one required artifact is None, return single blocker for that artifact."""
    artifacts: list[Any] = list(_build_two_room_scenario_artifacts()[:5])
    artifacts[missing_idx] = None

    result = PlanPreviewPreparationService.prepare(
        directive_set=artifacts[0],
        metric_requirements=artifacts[1],
        site_envelope=artifacts[2],
        floor_plate_input=artifacts[3],
        solver_config=artifacts[4],
    )

    assert result.ready_for_preview is False
    assert result.request is None
    assert len(result.blockers) == 1
    assert result.blockers[0].code == expected_code
    assert isinstance(result.blockers[0].message, str)


def test_render_config_is_optional_and_does_not_block_readiness() -> None:
    """render_config is optional; omitting it leaves request.render_config as None."""
    d_set, m_reqs, site_env, fp_input, s_cfg, r_cfg = _build_two_room_scenario_artifacts()

    # With render_config = None
    res_none = PlanPreviewPreparationService.prepare(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=fp_input,
        solver_config=s_cfg,
        render_config=None,
    )
    assert res_none.ready_for_preview is True
    assert res_none.blockers == []
    assert res_none.request is not None
    assert res_none.request.render_config is None

    # With render_config present
    res_with = PlanPreviewPreparationService.prepare(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=fp_input,
        solver_config=s_cfg,
        render_config=r_cfg,
    )
    assert res_with.ready_for_preview is True
    assert res_with.blockers == []
    assert res_with.request is not None
    assert res_with.request.render_config == r_cfg


def test_valid_authoritative_two_room_scenario_returns_ready_result() -> None:
    """Valid authoritative two-room scenario evaluates to ready_for_preview=True."""
    d_set, m_reqs, site_env, fp_input, s_cfg, r_cfg = _build_two_room_scenario_artifacts()

    result = PlanPreviewPreparationService.prepare(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=fp_input,
        solver_config=s_cfg,
        render_config=r_cfg,
    )

    assert result.ready_for_preview is True
    assert result.blockers == []
    assert isinstance(result.request, PlanPreviewRequest)


def test_valid_scenario_returns_complete_plan_preview_request() -> None:
    """Prepared PlanPreviewRequest contains complete, authoritative solver input and floor plate."""
    d_set, m_reqs, site_env, fp_input, s_cfg, r_cfg = _build_two_room_scenario_artifacts()

    result = PlanPreviewPreparationService.prepare(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=fp_input,
        solver_config=s_cfg,
        render_config=r_cfg,
    )

    assert result.request is not None
    req = result.request
    assert req.solver_input.project_id == "proj_living_kitchen_01"
    assert len(req.solver_input.spaces) == 2
    assert len(req.solver_input.space_metric_requirements) == 2
    assert req.floor_plate.project_id == "proj_living_kitchen_01"
    assert len(req.floor_plate.vertices) == 4
    assert req.solver_config.grid_step_m == 0.10


def test_resulting_solver_input_matches_layout_solver_input_assembler_output() -> None:
    """The solver_input inside request is identical to direct assembler output."""
    d_set, m_reqs, site_env, fp_input, s_cfg, _ = _build_two_room_scenario_artifacts()

    expected_si = LayoutSolverInputAssembler.assemble(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
    )

    result = PlanPreviewPreparationService.prepare(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=fp_input,
        solver_config=s_cfg,
    )

    assert result.request is not None
    assert result.request.solver_input == expected_si


def test_resulting_floor_plate_matches_floor_plate_builder_output() -> None:
    """The floor_plate inside request is identical to direct builder output."""
    d_set, m_reqs, site_env, fp_input, s_cfg, _ = _build_two_room_scenario_artifacts()

    expected_si = LayoutSolverInputAssembler.assemble(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
    )
    expected_fp = FloorPlateBuilder().build(
        solver_input=expected_si,
        floor_plate=fp_input,
    )

    result = PlanPreviewPreparationService.prepare(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=fp_input,
        solver_config=s_cfg,
    )

    assert result.request is not None
    assert result.request.floor_plate == expected_fp


def test_project_mismatch_returns_solver_input_invalid() -> None:
    """Mismatched project ID across source contracts produces SOLVER_INPUT_INVALID blocker."""
    d_set, m_reqs, site_env, fp_input, s_cfg, _ = _build_two_room_scenario_artifacts()

    # Mutate directive_set with different project_id
    mismatched_d_set = d_set.model_copy(update={"project_id": "proj_other_99"})

    result = PlanPreviewPreparationService.prepare(
        directive_set=mismatched_d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=fp_input,
        solver_config=s_cfg,
    )

    assert result.ready_for_preview is False
    assert result.request is None
    assert len(result.blockers) == 1
    assert result.blockers[0].code == PlanPreviewReadinessBlockerCode.SOLVER_INPUT_INVALID
    assert "Traceback" not in result.blockers[0].message


def test_brief_version_mismatch_returns_solver_input_invalid() -> None:
    """Mismatched brief version across source contracts produces SOLVER_INPUT_INVALID blocker."""
    d_set, m_reqs, site_env, fp_input, s_cfg, _ = _build_two_room_scenario_artifacts()

    mismatched_d_set = d_set.model_copy(update={"source_brief_version": 99})

    result = PlanPreviewPreparationService.prepare(
        directive_set=mismatched_d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=fp_input,
        solver_config=s_cfg,
    )

    assert result.ready_for_preview is False
    assert result.request is None
    assert len(result.blockers) == 1
    assert result.blockers[0].code == PlanPreviewReadinessBlockerCode.SOLVER_INPUT_INVALID


def test_non_authoritative_buildable_envelope_returns_solver_input_invalid() -> None:
    """Non-authoritative (e.g. AI_INFERRED) buildable envelope produces SOLVER_INPUT_INVALID."""
    d_set, m_reqs, site_env, fp_input, s_cfg, _ = _build_two_room_scenario_artifacts()

    assert site_env.buildable_envelope is not None
    non_auth_env = site_env.buildable_envelope.model_copy(
        update={"provenance": RelationshipProvenance.AI_INFERRED}
    )
    non_auth_site_env = site_env.model_copy(update={"buildable_envelope": non_auth_env})

    result = PlanPreviewPreparationService.prepare(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=non_auth_site_env,
        floor_plate_input=fp_input,
        solver_config=s_cfg,
    )

    assert result.ready_for_preview is False
    assert result.request is None
    assert len(result.blockers) == 1
    assert result.blockers[0].code == PlanPreviewReadinessBlockerCode.SOLVER_INPUT_INVALID


def test_non_authoritative_floor_plate_input_returns_floor_plate_invalid() -> None:
    """FloorPlateInput with non-authoritative provenance produces FLOOR_PLATE_INVALID blocker."""
    d_set, m_reqs, site_env, fp_input, s_cfg, _ = _build_two_room_scenario_artifacts()

    non_auth_fp = fp_input.model_copy(update={"provenance": RelationshipProvenance.AI_INFERRED})

    result = PlanPreviewPreparationService.prepare(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=non_auth_fp,
        solver_config=s_cfg,
    )

    assert result.ready_for_preview is False
    assert result.request is None
    assert len(result.blockers) == 1
    assert result.blockers[0].code == PlanPreviewReadinessBlockerCode.FLOOR_PLATE_INVALID
    assert "Traceback" not in result.blockers[0].message


def test_floor_plate_outside_buildable_envelope_returns_floor_plate_invalid() -> None:
    """Floor plate placed outside site buildable envelope produces FLOOR_PLATE_INVALID blocker."""
    d_set, m_reqs, site_env, fp_input, s_cfg, _ = _build_two_room_scenario_artifacts()

    # Shift floor plate completely outside buildable envelope [-8, 58]x[-8, 58]
    outside_fp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=100.0, y_m=100.0),
            SitePoint(x_m=106.0, y_m=100.0),
            SitePoint(x_m=106.0, y_m=106.0),
            SitePoint(x_m=100.0, y_m=106.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
        rationale="Outside FloorPlate",
    )

    result = PlanPreviewPreparationService.prepare(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=outside_fp,
        solver_config=s_cfg,
    )

    assert result.ready_for_preview is False
    assert result.request is None
    assert len(result.blockers) == 1
    assert result.blockers[0].code == PlanPreviewReadinessBlockerCode.FLOOR_PLATE_INVALID


def test_missing_source_artifacts_do_not_invoke_assembler_or_builder() -> None:
    """Missing input must return blockers immediately without calling assembler or builder."""
    with (
        patch.object(LayoutSolverInputAssembler, "assemble") as mock_assemble,
        patch.object(FloorPlateBuilder, "build") as mock_build,
    ):
        result = PlanPreviewPreparationService.prepare(
            directive_set=None,
            metric_requirements=None,
            site_envelope=None,
            floor_plate_input=None,
            solver_config=None,
        )

        assert result.ready_for_preview is False
        mock_assemble.assert_not_called()
        mock_build.assert_not_called()


def test_service_never_executes_room_geometry_solver() -> None:
    """PlanPreviewPreparationService must NEVER invoke RoomGeometrySolver.solve."""
    d_set, m_reqs, site_env, fp_input, s_cfg, r_cfg = _build_two_room_scenario_artifacts()

    with patch.object(RoomGeometrySolver, "solve") as mock_solve:
        # Valid execution
        res_valid = PlanPreviewPreparationService.prepare(
            directive_set=d_set,
            metric_requirements=m_reqs,
            site_envelope=site_env,
            floor_plate_input=fp_input,
            solver_config=s_cfg,
            render_config=r_cfg,
        )
        assert res_valid.ready_for_preview is True

        # Missing inputs execution
        res_invalid = PlanPreviewPreparationService.prepare(
            directive_set=None,
            metric_requirements=m_reqs,
            site_envelope=site_env,
            floor_plate_input=fp_input,
            solver_config=s_cfg,
        )
        assert res_invalid.ready_for_preview is False

        mock_solve.assert_not_called()


def test_service_never_executes_svg_plan_renderer() -> None:
    """PlanPreviewPreparationService must NEVER invoke SvgPlanRenderer.render."""
    d_set, m_reqs, site_env, fp_input, s_cfg, r_cfg = _build_two_room_scenario_artifacts()

    with patch.object(SvgPlanRenderer, "render") as mock_render:
        res = PlanPreviewPreparationService.prepare(
            directive_set=d_set,
            metric_requirements=m_reqs,
            site_envelope=site_env,
            floor_plate_input=fp_input,
            solver_config=s_cfg,
            render_config=r_cfg,
        )
        assert res.ready_for_preview is True
        mock_render.assert_not_called()


def test_inputs_are_not_mutated() -> None:
    """Source artifact inputs must remain completely unmutated across prepare() call."""
    d_set, m_reqs, site_env, fp_input, s_cfg, r_cfg = _build_two_room_scenario_artifacts()

    d_set_dump = d_set.model_dump()
    m_reqs_dump = m_reqs.model_dump()
    site_env_dump = site_env.model_dump()
    fp_input_dump = fp_input.model_dump()
    s_cfg_dump = s_cfg.model_dump()
    r_cfg_dump = r_cfg.model_dump()

    _ = PlanPreviewPreparationService.prepare(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=fp_input,
        solver_config=s_cfg,
        render_config=r_cfg,
    )

    assert d_set.model_dump() == d_set_dump
    assert m_reqs.model_dump() == m_reqs_dump
    assert site_env.model_dump() == site_env_dump
    assert fp_input.model_dump() == fp_input_dump
    assert s_cfg.model_dump() == s_cfg_dump
    assert r_cfg.model_dump() == r_cfg_dump


def test_output_is_deterministic_across_repeated_calls() -> None:
    """Calling prepare() repeatedly with identical inputs yields identical serialized outputs."""
    d_set, m_reqs, site_env, fp_input, s_cfg, r_cfg = _build_two_room_scenario_artifacts()

    res1 = PlanPreviewPreparationService.prepare(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=fp_input,
        solver_config=s_cfg,
        render_config=r_cfg,
    )
    res2 = PlanPreviewPreparationService.prepare(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=fp_input,
        solver_config=s_cfg,
        render_config=r_cfg,
    )

    assert res1.model_dump() == res2.model_dump()


def test_readiness_result_state_invariants_enforced() -> None:
    """PlanPreviewReadinessResult strictly forbids invalid state combinations."""
    d_set, m_reqs, site_env, fp_input, s_cfg, r_cfg = _build_two_room_scenario_artifacts()
    res = PlanPreviewPreparationService.prepare(
        directive_set=d_set,
        metric_requirements=m_reqs,
        site_envelope=site_env,
        floor_plate_input=fp_input,
        solver_config=s_cfg,
        render_config=r_cfg,
    )
    assert res.request is not None
    sample_request = res.request
    sample_blocker = PlanPreviewReadinessBlocker(
        code=PlanPreviewReadinessBlockerCode.DIRECTIVE_SET_MISSING,
        message="Blocker test",
    )

    # 1. ready=True with blockers -> ERROR
    with pytest.raises(
        ValidationError, match="ready_for_preview=True must have empty blockers"
    ):
        PlanPreviewReadinessResult(
            ready_for_preview=True,
            blockers=[sample_blocker],
            request=sample_request,
        )

    # 2. ready=True with request=None -> ERROR
    with pytest.raises(
        ValidationError, match="ready_for_preview=True must include request"
    ):
        PlanPreviewReadinessResult(
            ready_for_preview=True,
            blockers=[],
            request=None,
        )

    # 3. ready=False with empty blockers -> ERROR
    with pytest.raises(
        ValidationError, match="ready_for_preview=False must include at least one blocker"
    ):
        PlanPreviewReadinessResult(
            ready_for_preview=False,
            blockers=[],
            request=None,
        )

    # 4. ready=False with request present -> ERROR
    with pytest.raises(
        ValidationError, match="ready_for_preview=False cannot include request"
    ):
        PlanPreviewReadinessResult(
            ready_for_preview=False,
            blockers=[sample_blocker],
            request=sample_request,
        )
