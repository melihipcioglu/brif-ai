"""End-to-end tests for Conversational Metric Plan Revision V0."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest
from apps.api.main import create_app
from fastapi.testclient import TestClient

from brif_ai.llm.contracts import (
    ActiveContextSnapshot,
    ArchitecturalIntentResult,
    ConversationRequest,
    EntityTarget,
    IntentType,
    LocalModelInfo,
    ProviderHealth,
)
from brif_ai.llm.settings import LocalLLMSettings
from brif_ai.spatial.metrics.builder import MetricSpatialRequirementsBuilder
from brif_ai.spatial.metrics.models import (
    MetricRequirementInput,
    MetricRequirementType,
    MetricUnit,
    ProposedMetricRequirement,
)
from brif_ai.spatial.plan_input import (
    AuthoritativePlanInputState,
    PlanInputApprovalEvidenceRepository,
    PlanInputStateService,
)
from brif_ai.spatial.plan_preview import PlanPreviewService
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.room_solver.solver import RoomGeometrySolver

from .test_conversational_plan_preview_flow import _setup_test_project


class RevisionInterpretationProvider:
    """Controlled provider returning a source-verifiable Salon MIN_AREA proposal."""

    call_count: int

    def __init__(self) -> None:
        self.call_count = 0

    async def health(self) -> ProviderHealth:
        return ProviderHealth(provider="ollama", reachable=True)

    async def list_models(self) -> list[LocalModelInfo]:
        return [LocalModelInfo(name="local-model:latest", size=42)]

    async def interpret(
        self,
        request: ConversationRequest,
        output_schema: dict[str, object],
        *,
        metric_context: object | None = None,
    ) -> ArchitecturalIntentResult:
        del output_schema, metric_context
        self.call_count += 1
        proposal = ProposedMetricRequirement(
            proposal_id="prop_revision_35",
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=35.0,
            unit=MetricUnit.SQUARE_METRE,
            rationale="Kullanıcının açık minimum alan revizyonu.",
        )
        return ArchitecturalIntentResult(
            assistant_message="Salonun minimum alanını 35 m² olarak güncelleyelim mi?",
            intent=IntentType.GATHER_REQUIREMENT,
            target=EntityTarget(project_id=request.active_context.project_id),
            user_requirements=[request.message],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_brief_mutations=[],
            proposed_spatial_relationships=[],
            proposed_metric_requirements=[proposal],
            needs_follow_up=False,
            needs_user_confirmation=True,
            confidence=0.98,
            warnings=[],
        )


def _seed_living_minimum(
    brief_repo: Any,
    spatial_repo: Any,
    plan_repo: Any,
    *,
    value: float = 25.0,
) -> AuthoritativePlanInputState:
    project_id = "proj_preview_conv_01"
    brief = brief_repo.get_latest(project_id)
    graph = spatial_repo.get_latest(project_id)
    current = plan_repo.get_latest(project_id)
    assert brief is not None and graph is not None and current is not None
    assert current.metric_requirements is not None
    program = SpatialProgramBuilder().build(brief, graph)

    inputs: list[MetricRequirementInput] = []
    for space_requirements in current.metric_requirements.space_requirements:
        for requirement in space_requirements.requirements:
            inputs.append(
                MetricRequirementInput(
                    space_id=requirement.space_id,
                    requirement_type=requirement.requirement_type,
                    value=(
                        value
                        if requirement.space_id == "sn_living_01"
                        and requirement.requirement_type == MetricRequirementType.MIN_AREA
                        else requirement.value
                    ),
                    unit=requirement.unit,
                    provenance=requirement.provenance,
                    priority=requirement.priority,
                    evidence_ids=requirement.evidence_ids,
                    rationale=requirement.rationale,
                )
            )
    metrics = MetricSpatialRequirementsBuilder().build(
        program,
        inputs,
        created_at=datetime(2026, 8, 25, 8, 0, tzinfo=UTC),
    )
    return PlanInputStateService(plan_repo).update_state(
        project_id=project_id,
        expected_state_version=current.state_version,
        source_brief_version=brief.brief_version,
        metric_requirements=metrics,
        created_at=datetime(2026, 8, 25, 8, 0, tzinfo=UTC),
    )


def _setup_revision_client(
    tmp_path: Path,
) -> tuple[
    TestClient,
    Any,
    Any,
    Any,
    PlanInputApprovalEvidenceRepository,
    RevisionInterpretationProvider,
    AuthoritativePlanInputState,
]:
    brief_repo, spatial_repo, plan_repo, _, _ = _setup_test_project(
        tmp_path,
        living_display_name="Salon",
        kitchen_display_name="Mutfak",
    )
    state = _seed_living_minimum(brief_repo, spatial_repo, plan_repo)
    evidence_repo = PlanInputApprovalEvidenceRepository(root_dir=plan_repo.root_dir)
    provider = RevisionInterpretationProvider()
    app = create_app(
        settings=LocalLLMSettings(enabled=True, provider="ollama", model="local-model:latest"),
        provider=provider,
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_repo,
        plan_input_evidence_repository=evidence_repo,
    )
    return (
        TestClient(app),
        brief_repo,
        spatial_repo,
        plan_repo,
        evidence_repo,
        provider,
        state,
    )


def _interpret_revision(client: TestClient, brief: Any) -> dict[str, Any]:
    request = ConversationRequest(
        message="Salonu en az 35 m² yap.",
        active_context=ActiveContextSnapshot(
            project_id=brief.project_id,
            context_fingerprint="fp_revision_35",
            generation_id=7,
        ),
        brief_snapshot=brief,
    )
    response = client.post(
        "/api/v1/conversation/interpret",
        json=request.model_dump(mode="json"),
    )
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def _approval_payload(
    interpretation: dict[str, Any],
    *,
    source_reference: str = "chatmsg_35",
    user_message: str = "Salonu en az 35 m² yap.",
) -> dict[str, Any]:
    result = interpretation["result"]
    assert result is not None
    return {
        "proposed_requirement": result["proposed_metric_requirements"][0].copy(),
        "current_project_id": "proj_preview_conv_01",
        "expected_brief_version": interpretation["authoritative_brief_version"],
        "expected_plan_input_state_version": interpretation[
            "authoritative_plan_input_state_version"
        ],
        "proposal_fingerprint": interpretation["context_fingerprint"],
        "current_fingerprint": interpretation["context_fingerprint"],
        "proposal_generation_id": interpretation["generation_id"],
        "current_generation_id": interpretation["generation_id"],
        "user_message": user_message,
        "source_reference": source_reference,
    }


def _metric_map(state: AuthoritativePlanInputState) -> dict[tuple[str, str], dict[str, Any]]:
    assert state.metric_requirements is not None
    return {
        (requirement.space_id, requirement.requirement_type.value): requirement.model_dump(
            mode="json"
        )
        for space_requirements in state.metric_requirements.space_requirements
        for requirement in space_requirements.requirements
    }


def test_interpretation_is_structured_and_has_zero_authoritative_side_effects(
    tmp_path: Path,
) -> None:
    client, brief_repo, spatial_repo, plan_repo, evidence_repo, provider, state_before = (
        _setup_revision_client(tmp_path)
    )
    brief_before = brief_repo.get_latest("proj_preview_conv_01")
    graph_before = spatial_repo.get_latest("proj_preview_conv_01")
    assert brief_before is not None

    with (
        patch.object(PlanPreviewService, "generate", wraps=PlanPreviewService.generate) as preview,
        patch.object(RoomGeometrySolver, "solve", wraps=RoomGeometrySolver.solve) as solver,
    ):
        interpretation = _interpret_revision(client, brief_before)

    proposal = interpretation["result"]["proposed_metric_requirements"][0]
    assert proposal["space_id"] == "sn_living_01"
    assert proposal["requirement_type"] == "MIN_AREA"
    assert proposal["value"] == 35.0
    assert proposal["unit"] == "SQUARE_METRE"
    assert interpretation["authoritative_brief_version"] == brief_before.brief_version
    assert interpretation["authoritative_plan_input_state_version"] == state_before.state_version
    assert provider.call_count == 1
    assert plan_repo.get_latest("proj_preview_conv_01") == state_before
    assert brief_repo.get_latest("proj_preview_conv_01") == brief_before
    assert spatial_repo.get_latest("proj_preview_conv_01") == graph_before
    assert evidence_repo.list_evidence("proj_preview_conv_01") == []
    assert preview.call_count == 0
    assert solver.call_count == 0


def test_confirm_replaces_only_metric_and_never_previews_or_solves(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_repo, evidence_repo, _, state_before = (
        _setup_revision_client(tmp_path)
    )
    brief_before = brief_repo.get_latest("proj_preview_conv_01")
    graph_before = spatial_repo.get_latest("proj_preview_conv_01")
    assert brief_before is not None
    interpretation = _interpret_revision(client, brief_before)
    payload = _approval_payload(interpretation)
    before_metrics = _metric_map(state_before)

    with (
        patch.object(PlanPreviewService, "generate", wraps=PlanPreviewService.generate) as preview,
        patch.object(RoomGeometrySolver, "solve", wraps=RoomGeometrySolver.solve) as solver,
    ):
        response = client.post(
            "/api/v1/projects/proj_preview_conv_01/plan/input/metrics/approve",
            json=payload,
        )

    assert response.status_code == 200
    data = response.json()
    record = data["approval_record"]
    assert record["operation"] == "replaced"
    assert record["state_changed"] is True
    assert record["previous_value"] == 25.0
    assert data["resulting_plan_input_state"]["state_version"] == state_before.state_version + 1
    assert preview.call_count == 0
    assert solver.call_count == 0

    state_after = plan_repo.get_latest("proj_preview_conv_01")
    assert state_after is not None
    after_metrics = _metric_map(state_after)
    living_key = ("sn_living_01", "MIN_AREA")
    assert after_metrics[living_key]["value"] == 35.0
    assert after_metrics[living_key]["provenance"] == "USER_CONFIRMED"
    assert after_metrics[living_key]["priority"] == "MUST"
    assert after_metrics[living_key]["evidence_ids"] == [record["resulting_evidence_id"]]
    assert {key: value for key, value in after_metrics.items() if key != living_key} == {
        key: value for key, value in before_metrics.items() if key != living_key
    }
    assert state_after.site_envelope == state_before.site_envelope
    assert state_after.floor_plate_input == state_before.floor_plate_input
    assert state_after.solver_config == state_before.solver_config
    assert brief_repo.get_latest("proj_preview_conv_01") == brief_before
    assert spatial_repo.get_latest("proj_preview_conv_01") == graph_before

    evidence = evidence_repo.get_evidence("proj_preview_conv_01", record["resulting_evidence_id"])
    assert evidence is not None
    assert evidence.source_reference == "chatmsg_35"
    assert evidence.user_message == "Salonu en az 35 m² yap."

    historical = plan_repo.get_version("proj_preview_conv_01", state_before.state_version)
    assert historical is not None
    assert _metric_map(historical)[living_key]["value"] == 25.0
    assert _metric_map(historical)[living_key]["evidence_ids"] != [record["resulting_evidence_id"]]


def test_replay_evidence_merge_and_stale_write_operation_matrix(tmp_path: Path) -> None:
    client, brief_repo, _, plan_repo, evidence_repo, _, state_before = _setup_revision_client(
        tmp_path
    )
    brief = brief_repo.get_latest("proj_preview_conv_01")
    assert brief is not None
    interpretation = _interpret_revision(client, brief)
    original_payload = _approval_payload(interpretation)

    replaced = client.post(
        "/api/v1/projects/proj_preview_conv_01/plan/input/metrics/approve",
        json=original_payload,
    )
    assert replaced.status_code == 200
    replaced_state_version = replaced.json()["resulting_plan_input_state"]["state_version"]
    assert replaced_state_version == state_before.state_version + 1

    replayed = client.post(
        "/api/v1/projects/proj_preview_conv_01/plan/input/metrics/approve",
        json=original_payload,
    )
    assert replayed.status_code == 200
    assert replayed.json()["approval_record"]["operation"] == "replayed"
    assert replayed.json()["approval_record"]["state_changed"] is False
    assert replayed.json()["resulting_plan_input_state"]["state_version"] == replaced_state_version
    assert len(evidence_repo.list_evidence("proj_preview_conv_01")) == 1

    merge_payload = _approval_payload(
        interpretation,
        source_reference="chatmsg_35_second",
        user_message="Salon minimum 35 m² olsun.",
    )
    merge_payload["expected_plan_input_state_version"] = replaced_state_version
    merged = client.post(
        "/api/v1/projects/proj_preview_conv_01/plan/input/metrics/approve",
        json=merge_payload,
    )
    assert merged.status_code == 200
    assert merged.json()["approval_record"]["operation"] == "evidence_merged"
    assert merged.json()["approval_record"]["state_changed"] is True
    merged_version = merged.json()["resulting_plan_input_state"]["state_version"]
    assert merged_version == replaced_state_version + 1
    merged_state = plan_repo.get_latest("proj_preview_conv_01")
    assert merged_state is not None
    merged_evidence_ids = _metric_map(merged_state)[("sn_living_01", "MIN_AREA")]["evidence_ids"]
    assert len(merged_evidence_ids) == 2
    assert len(evidence_repo.list_evidence("proj_preview_conv_01")) == 2

    winning_payload = _approval_payload(
        interpretation,
        source_reference="chatmsg_37",
        user_message="Salonu en az 37 m² yap.",
    )
    winning_payload["proposed_requirement"]["value"] = 37.0
    winning_payload["expected_plan_input_state_version"] = merged_version
    stale_payload = _approval_payload(
        interpretation,
        source_reference="chatmsg_36",
        user_message="Salonu en az 36 m² yap.",
    )
    stale_payload["proposed_requirement"]["value"] = 36.0
    stale_payload["expected_plan_input_state_version"] = merged_version

    winner = client.post(
        "/api/v1/projects/proj_preview_conv_01/plan/input/metrics/approve",
        json=winning_payload,
    )
    assert winner.status_code == 200
    assert winner.json()["approval_record"]["operation"] == "replaced"
    winning_version = winner.json()["resulting_plan_input_state"]["state_version"]
    assert winning_version == merged_version + 1

    stale = client.post(
        "/api/v1/projects/proj_preview_conv_01/plan/input/metrics/approve",
        json=stale_payload,
    )
    assert stale.status_code == 409
    final_state = plan_repo.get_latest("proj_preview_conv_01")
    assert final_state is not None
    assert final_state.state_version == winning_version
    assert _metric_map(final_state)[("sn_living_01", "MIN_AREA")]["value"] == 37.0
    assert (
        evidence_repo.get_evidence(
            "proj_preview_conv_01",
            PlanInputApprovalEvidenceRepository.build_chat_evidence(
                project_id="proj_preview_conv_01",
                source_reference="chatmsg_36",
                user_message="Salonu en az 36 m² yap.",
                created_at=datetime(2026, 8, 25, 8, 0, tzinfo=UTC),
            ).id,
        )
        is None
    )


@pytest.mark.parametrize(
    ("proposal_update", "user_message"),
    [
        ({"value": 40.0}, "Salonu en az 35 m² yap."),
        ({"requirement_type": "MAX_AREA"}, "Salonu en az 35 m² yap."),
        ({"unit": "METRE"}, "Salonu en az 35 m² yap."),
    ],
)
def test_forged_metric_value_type_or_unit_is_rejected_at_approval(
    tmp_path: Path,
    proposal_update: dict[str, Any],
    user_message: str,
) -> None:
    client, brief_repo, _, plan_repo, evidence_repo, _, state_before = _setup_revision_client(
        tmp_path
    )
    brief = brief_repo.get_latest("proj_preview_conv_01")
    assert brief is not None
    interpretation = _interpret_revision(client, brief)
    payload = _approval_payload(interpretation, user_message=user_message)
    payload["proposed_requirement"].update(proposal_update)

    response = client.post(
        "/api/v1/projects/proj_preview_conv_01/plan/input/metrics/approve",
        json=payload,
    )

    assert response.status_code == 422
    assert plan_repo.get_latest("proj_preview_conv_01") == state_before
    assert evidence_repo.list_evidence("proj_preview_conv_01") == []


def test_explicit_preview_uses_revised_value_and_solves_once(tmp_path: Path) -> None:
    client, brief_repo, _, _, _, _, _ = _setup_revision_client(tmp_path)
    brief = brief_repo.get_latest("proj_preview_conv_01")
    assert brief is not None
    interpretation = _interpret_revision(client, brief)
    approval = client.post(
        "/api/v1/projects/proj_preview_conv_01/plan/input/metrics/approve",
        json=_approval_payload(interpretation),
    )
    assert approval.status_code == 200

    captured_values: list[float] = []
    original_solve = RoomGeometrySolver.solve

    def capture_solve(*, solver_input: Any, floor_plate: Any, config: Any) -> Any:
        captured_values.extend(
            requirement.value
            for space_requirements in solver_input.space_metric_requirements
            if space_requirements.space_id == "sn_living_01"
            for requirement in space_requirements.requirements
            if requirement.requirement_type == MetricRequirementType.MIN_AREA
        )
        return original_solve(
            solver_input=solver_input,
            floor_plate=floor_plate,
            config=config,
        )

    with (
        patch.object(PlanPreviewService, "generate", wraps=PlanPreviewService.generate) as service,
        patch.object(RoomGeometrySolver, "solve", side_effect=capture_solve) as solver,
    ):
        preview = client.post("/api/v1/projects/proj_preview_conv_01/plan/preview")

    assert preview.status_code == 200
    assert service.call_count == 1
    assert solver.call_count == 1
    assert captured_values == [35.0]
    living_room = next(
        room for room in preview.json()["solution"]["rooms"] if room["space_id"] == "sn_living_01"
    )
    assert living_room["area_m2"] >= 35.0
