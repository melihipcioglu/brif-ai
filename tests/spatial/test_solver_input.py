"""Comprehensive test suite for BRIF.AI Layout Solver Input Set V0."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

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
from brif_ai.spatial.layout.compiler import LayoutProblemCompiler
from brif_ai.spatial.metrics.builder import MetricSpatialRequirementsBuilder
from brif_ai.spatial.metrics.models import (
    MetricRequirement,
    MetricRequirementInput,
    MetricRequirementType,
    MetricSpatialRequirements,
    MetricUnit,
)
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationshipInput,
    SpatialRelationType,
    UnconstrainedPair,
)
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.program.models import SpatialProgram
from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.models import (
    SiteBuildableEnvelope,
    SiteGeometryRole,
    SitePoint,
    SitePolygonInput,
)
from brif_ai.spatial.solver_input import (
    LayoutSolverInputAssembler,
    LayoutSolverInputSet,
    SolverInputBriefVersionMismatchError,
    SolverInputMissingBuildableEnvelopeError,
    SolverInputMissingInputError,
    SolverInputNonAuthoritativeBuildableEnvelopeError,
    SolverInputProjectMismatchError,
    SolverInputSchemaVersionMismatchError,
    SolverInputSpaceMismatchError,
    SolverSpaceMetricRequirements,
)
from brif_ai.spatial.solver_policy.compiler import SolverPolicyCompiler
from brif_ai.spatial.solver_policy.models import (
    ConstraintEnforcement,
    SolverDirectiveSet,
    SolverRelationOperator,
)


def _ready_program() -> SpatialProgram:
    ev = Evidence(
        id="ev_01",
        source_type=EvidenceSource.CHAT,
        source_reference="chat:turn-1",
        excerpt="Client wants living room connected to kitchen and garden.",
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
        SpaceRequest(
            id="sr_bedroom",
            display_name="Master Bedroom",
            space_function=SpaceFunction.SLEEPING,
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
        project_id="proj_101",
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(id="stk_01", display_name="Owner", role="CLIENT_OWNER", active=True)
        ],
        evidence=[ev],
        brief_items=[],
        space_requests=spaces,
        usage_scenarios=[],
        contradictions=[],
        open_questions=open_questions,
    )
    rel_inputs = [
        SpatialRelationshipInput(
            source_space_id="sn_living_01",
            target_space_id="sn_kitchen_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=[ev.id],
            rationale="Open plan living/kitchen",
        )
    ]
    graph = SpatialRelationshipGraphBuilder().build(
        snapshot, rel_inputs, created_at=datetime(2026, 8, 19, 12, 5, 0, tzinfo=UTC)
    )
    return SpatialProgramBuilder().build(snapshot, graph)


def _sample_three_sources() -> tuple[
    SolverDirectiveSet, MetricSpatialRequirements, SiteBuildableEnvelope
]:
    program = _ready_program()
    ev_id = "ev_01"

    # 1. DirectiveSet
    layout_problem = LayoutProblemCompiler().compile(program)
    directive_set = SolverPolicyCompiler().compile(layout_problem)

    # 2. MetricRequirements
    metric_inputs = [
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=35.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=[ev_id],
            rationale="Confirmed living room size",
        ),
        MetricRequirementInput(
            space_id="sn_kitchen_01",
            requirement_type=MetricRequirementType.TARGET_AREA,
            value=15.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.SHOULD,
            evidence_ids=[ev_id],
            rationale="Confirmed kitchen target area",
        ),
        # Unconfirmed metric on bedroom (USER_STATED)
        MetricRequirementInput(
            space_id="sn_bedroom_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=20.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_STATED,
            priority=Priority.COULD,
            evidence_ids=[],
            rationale="Client casually mentioned master bedroom size",
        ),
    ]
    metrics = MetricSpatialRequirementsBuilder().build(
        program, metric_inputs, created_at=datetime(2026, 8, 19, 12, 10, 0, tzinfo=UTC)
    )

    # 3. SiteBuildableEnvelope
    parcel_inp = SitePolygonInput(
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=50.0, y_m=0.0),
            SitePoint(x_m=50.0, y_m=40.0),
            SitePoint(x_m=0.0, y_m=40.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=[ev_id],
        rationale="Cadastral boundary",
    )
    envelope_inp = SitePolygonInput(
        vertices=[
            SitePoint(x_m=5.0, y_m=5.0),
            SitePoint(x_m=45.0, y_m=5.0),
            SitePoint(x_m=45.0, y_m=35.0),
            SitePoint(x_m=5.0, y_m=35.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=[ev_id],
        rationale="Zoning setback envelope",
    )
    site_env = SiteBuildableEnvelopeBuilder().build(
        program,
        parcel_boundary=parcel_inp,
        buildable_envelope=envelope_inp,
        created_at=datetime(2026, 8, 19, 12, 15, 0, tzinfo=UTC),
    )

    return directive_set, metrics, site_env


def test_valid_three_source_assembly_succeeds() -> None:
    directive_set, metrics, site_env = _sample_three_sources()

    solver_input = LayoutSolverInputAssembler.assemble(
        directive_set=directive_set,
        metric_requirements=metrics,
        site_envelope=site_env,
    )

    assert isinstance(solver_input, LayoutSolverInputSet)
    assert solver_input.schema_version == "layout_solver_input_set.v0"
    assert solver_input.project_id == "proj_101"
    assert solver_input.source_brief_version == 1
    assert solver_input.source_directive_set_schema_version == "solver_directive_set.v0"
    assert (
        solver_input.source_metric_requirements_schema_version == "metric_spatial_requirements.v0"
    )
    assert solver_input.source_site_envelope_schema_version == "site_buildable_envelope.v0"
    assert solver_input.coordinate_system == "LOCAL_CARTESIAN_METRES"
    assert len(solver_input.spaces) == 3
    assert len(solver_input.directives) == 1
    assert len(solver_input.space_metric_requirements) == 3
    assert solver_input.buildable_envelope.role == SiteGeometryRole.BUILDABLE_ENVELOPE


def test_missing_input_raises_error() -> None:
    directive_set, metrics, site_env = _sample_three_sources()

    with pytest.raises(SolverInputMissingInputError, match="directive_set must not be None"):
        LayoutSolverInputAssembler.assemble(None, metrics, site_env)  # type: ignore[arg-type]

    with pytest.raises(SolverInputMissingInputError, match="metric_requirements must not be None"):
        LayoutSolverInputAssembler.assemble(directive_set, None, site_env)  # type: ignore[arg-type]

    with pytest.raises(SolverInputMissingInputError, match="site_envelope must not be None"):
        LayoutSolverInputAssembler.assemble(directive_set, metrics, None)  # type: ignore[arg-type]


def test_mismatched_project_ids_rejected() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    # Create metrics with different project_id
    bad_metrics = metrics.model_copy(update={"project_id": "proj_diff"})

    with pytest.raises(SolverInputProjectMismatchError, match="Project ID mismatch"):
        LayoutSolverInputAssembler.assemble(directive_set, bad_metrics, site_env)


def test_mismatched_source_brief_version_rejected() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    bad_site = site_env.model_copy(update={"source_brief_version": 2})

    with pytest.raises(SolverInputBriefVersionMismatchError, match="Source brief version mismatch"):
        LayoutSolverInputAssembler.assemble(directive_set, metrics, bad_site)


def test_incompatible_schema_versions_rejected() -> None:
    directive_set, metrics, site_env = _sample_three_sources()

    bad_directives = directive_set.model_copy(update={"schema_version": "solver_directive_set.v1"})
    with pytest.raises(
        SolverInputSchemaVersionMismatchError, match="Unsupported directive_set schema_version"
    ):
        LayoutSolverInputAssembler.assemble(bad_directives, metrics, site_env)

    bad_metrics = metrics.model_copy(update={"schema_version": "metric_spatial_requirements.v1"})
    with pytest.raises(
        SolverInputSchemaVersionMismatchError,
        match="Unsupported metric_requirements schema_version",
    ):
        LayoutSolverInputAssembler.assemble(directive_set, bad_metrics, site_env)

    bad_site = site_env.model_copy(update={"schema_version": "site_buildable_envelope.v1"})
    with pytest.raises(
        SolverInputSchemaVersionMismatchError, match="Unsupported site_envelope schema_version"
    ):
        LayoutSolverInputAssembler.assemble(directive_set, metrics, bad_site)


def test_exact_solver_space_metric_space_set_matching_enforced() -> None:
    directive_set, metrics, site_env = _sample_three_sources()

    # Drop one space container from metrics
    bad_smr = [s for s in metrics.space_requirements if s.space_id != "sn_bedroom_01"]
    bad_metrics = metrics.model_copy(update={"space_requirements": bad_smr})

    with pytest.raises(
        SolverInputSpaceMismatchError,
        match="Space mismatch between solver directives and metric requirements",
    ):
        LayoutSolverInputAssembler.assemble(directive_set, bad_metrics, site_env)


def test_space_identity_invariant_enforced() -> None:
    directive_set, metrics, site_env = _sample_three_sources()

    # Tamper with space to violate id == source_program_space_id
    bad_spaces = list(directive_set.spaces)
    bad_spaces[0] = bad_spaces[0].model_copy(update={"source_program_space_id": "sp_other"})
    bad_directives = directive_set.model_copy(update={"spaces": bad_spaces})

    with pytest.raises(
        SolverInputSpaceMismatchError, match="does not match source_program_space_id"
    ):
        LayoutSolverInputAssembler.assemble(bad_directives, metrics, site_env)


def test_authoritative_metrics_filtering_and_provenance_segregation() -> None:
    directive_set, metrics, site_env = _sample_three_sources()

    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    smr_map = {smr.space_id: smr for smr in solver_input.space_metric_requirements}

    # sn_living_01 had USER_CONFIRMED MIN_AREA -> must be included
    living_reqs = smr_map["sn_living_01"].requirements
    assert len(living_reqs) == 1
    assert living_reqs[0].requirement_type == MetricRequirementType.MIN_AREA
    assert living_reqs[0].value == 35.0
    assert living_reqs[0].provenance == RelationshipProvenance.USER_CONFIRMED

    # sn_kitchen_01 had USER_CONFIRMED TARGET_AREA -> must be included
    kitchen_reqs = smr_map["sn_kitchen_01"].requirements
    assert len(kitchen_reqs) == 1
    assert kitchen_reqs[0].requirement_type == MetricRequirementType.TARGET_AREA
    assert kitchen_reqs[0].value == 15.0

    # sn_bedroom_01 had only USER_STATED MIN_AREA -> MUST BE FILTERED OUT, EXPOSING []
    bedroom_reqs = smr_map["sn_bedroom_01"].requirements
    assert bedroom_reqs == []


def test_missing_buildable_envelope_rejected() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    assert site_env.parcel_boundary is not None
    bad_site = site_env.model_copy(
        update={
            "buildable_envelope": None,
            "authoritative_geometry_ids": [site_env.parcel_boundary.id],
        }
    )

    with pytest.raises(
        SolverInputMissingBuildableEnvelopeError,
        match="does not contain a buildable envelope",
    ):
        LayoutSolverInputAssembler.assemble(directive_set, metrics, bad_site)


def test_confirmed_parcel_with_missing_envelope_does_not_become_buildable_envelope() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    assert site_env.parcel_boundary is not None
    # Parcel alone
    parcel_only = site_env.model_copy(
        update={
            "buildable_envelope": None,
            "authoritative_geometry_ids": [site_env.parcel_boundary.id],
        }
    )

    with pytest.raises(SolverInputMissingBuildableEnvelopeError):
        LayoutSolverInputAssembler.assemble(directive_set, metrics, parcel_only)


def test_non_authoritative_buildable_envelope_rejected() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    assert site_env.parcel_boundary is not None
    assert site_env.buildable_envelope is not None

    # 1. USER_STATED buildable envelope
    unconfirmed_env = site_env.buildable_envelope.model_copy(
        update={"provenance": RelationshipProvenance.USER_STATED, "evidence_ids": []}
    )
    bad_site_1 = site_env.model_copy(
        update={
            "buildable_envelope": unconfirmed_env,
            "authoritative_geometry_ids": [site_env.parcel_boundary.id],
        }
    )

    with pytest.raises(
        SolverInputNonAuthoritativeBuildableEnvelopeError,
        match="non-authoritative provenance",
    ):
        LayoutSolverInputAssembler.assemble(directive_set, metrics, bad_site_1)

    # 2. AI_INFERRED buildable envelope
    inferred_env = site_env.buildable_envelope.model_copy(
        update={"provenance": RelationshipProvenance.AI_INFERRED, "evidence_ids": []}
    )
    bad_site_2 = site_env.model_copy(
        update={
            "buildable_envelope": inferred_env,
            "authoritative_geometry_ids": [site_env.parcel_boundary.id],
        }
    )

    with pytest.raises(
        SolverInputNonAuthoritativeBuildableEnvelopeError,
        match="non-authoritative provenance",
    ):
        LayoutSolverInputAssembler.assemble(directive_set, metrics, bad_site_2)


def test_buildable_envelope_vertices_and_id_preserved_without_mutation() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    assert site_env.buildable_envelope is not None
    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    assert solver_input.buildable_envelope.id == site_env.buildable_envelope.id
    assert len(solver_input.buildable_envelope.vertices) == 4
    for orig_v, out_v in zip(
        site_env.buildable_envelope.vertices,
        solver_input.buildable_envelope.vertices,
        strict=True,
    ):
        assert orig_v.x_m == out_v.x_m
        assert orig_v.y_m == out_v.y_m


def test_relational_directives_and_unconstrained_pairs_preserved() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    assert len(solver_input.directives) == 1
    assert solver_input.directives[0].id == directive_set.directives[0].id
    assert solver_input.directives[0].operator == SolverRelationOperator.ADJACENCY
    assert solver_input.directives[0].enforcement == ConstraintEnforcement.REQUIRED

    assert len(solver_input.unconstrained_pairs) == len(directive_set.unconstrained_pairs)


def test_direct_construction_rejects_non_confirmed_metrics() -> None:
    unconfirmed_req = MetricRequirement(
        id="mreq_bad",
        space_id="sn_bedroom_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=20.0,
        unit=MetricUnit.SQUARE_METRE,
        provenance=RelationshipProvenance.USER_STATED,
        evidence_ids=[],
    )

    with pytest.raises(ValidationError, match="only USER_CONFIRMED is permitted"):
        SolverSpaceMetricRequirements(
            space_id="sn_bedroom_01",
            requirements=[unconfirmed_req],
        )


def test_direct_construction_rejects_non_confirmed_buildable_envelope() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    bad_env = solver_input.buildable_envelope.model_copy(
        update={"provenance": RelationshipProvenance.USER_STATED, "evidence_ids": []}
    )

    with pytest.raises(
        ValidationError,
        match="buildable_envelope must have USER_CONFIRMED provenance",
    ):
        LayoutSolverInputSet(
            project_id=solver_input.project_id,
            source_brief_version=solver_input.source_brief_version,
            created_at=solver_input.created_at,
            spaces=solver_input.spaces,
            directives=solver_input.directives,
            space_metric_requirements=solver_input.space_metric_requirements,
            buildable_envelope=bad_env,
            unconstrained_pairs=solver_input.unconstrained_pairs,
        )


def test_direct_construction_rejects_duplicate_space_ids() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    dup_spaces = list(solver_input.spaces) + [solver_input.spaces[0]]

    with pytest.raises(ValidationError, match="duplicate space id"):
        LayoutSolverInputSet(
            project_id=solver_input.project_id,
            source_brief_version=solver_input.source_brief_version,
            created_at=solver_input.created_at,
            spaces=dup_spaces,
            directives=solver_input.directives,
            space_metric_requirements=solver_input.space_metric_requirements,
            buildable_envelope=solver_input.buildable_envelope,
            unconstrained_pairs=solver_input.unconstrained_pairs,
        )


def test_direct_construction_rejects_duplicate_directive_ids() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    dup_directives = list(solver_input.directives) + [solver_input.directives[0]]

    with pytest.raises(ValidationError, match="duplicate directive id"):
        LayoutSolverInputSet(
            project_id=solver_input.project_id,
            source_brief_version=solver_input.source_brief_version,
            created_at=solver_input.created_at,
            spaces=solver_input.spaces,
            directives=dup_directives,
            space_metric_requirements=solver_input.space_metric_requirements,
            buildable_envelope=solver_input.buildable_envelope,
            unconstrained_pairs=solver_input.unconstrained_pairs,
        )


def test_direct_construction_rejects_duplicate_metric_space_containers() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    dup_smr = list(solver_input.space_metric_requirements) + [
        solver_input.space_metric_requirements[0]
    ]

    with pytest.raises(
        ValidationError,
        match="duplicate SolverSpaceMetricRequirements container",
    ):
        LayoutSolverInputSet(
            project_id=solver_input.project_id,
            source_brief_version=solver_input.source_brief_version,
            created_at=solver_input.created_at,
            spaces=solver_input.spaces,
            directives=solver_input.directives,
            space_metric_requirements=dup_smr,
            buildable_envelope=solver_input.buildable_envelope,
            unconstrained_pairs=solver_input.unconstrained_pairs,
        )


def test_direct_construction_rejects_duplicate_unconstrained_pairs() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    dup_pairs = [
        UnconstrainedPair(space_a_id="sn_bedroom_01", space_b_id="sn_kitchen_01"),
        UnconstrainedPair(space_a_id="sn_bedroom_01", space_b_id="sn_kitchen_01"),
    ]

    with pytest.raises(ValidationError, match="duplicate unconstrained pair"):
        LayoutSolverInputSet(
            project_id=solver_input.project_id,
            source_brief_version=solver_input.source_brief_version,
            created_at=solver_input.created_at,
            spaces=solver_input.spaces,
            directives=solver_input.directives,
            space_metric_requirements=solver_input.space_metric_requirements,
            buildable_envelope=solver_input.buildable_envelope,
            unconstrained_pairs=dup_pairs,
        )


def test_direct_construction_rejects_invalid_project_id() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    with pytest.raises(ValidationError):
        LayoutSolverInputSet(
            project_id="",
            source_brief_version=solver_input.source_brief_version,
            created_at=solver_input.created_at,
            spaces=solver_input.spaces,
            directives=solver_input.directives,
            space_metric_requirements=solver_input.space_metric_requirements,
            buildable_envelope=solver_input.buildable_envelope,
            unconstrained_pairs=solver_input.unconstrained_pairs,
        )


def test_direct_construction_rejects_invalid_source_brief_version() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    with pytest.raises(ValidationError):
        LayoutSolverInputSet(
            project_id=solver_input.project_id,
            source_brief_version=0,
            created_at=solver_input.created_at,
            spaces=solver_input.spaces,
            directives=solver_input.directives,
            space_metric_requirements=solver_input.space_metric_requirements,
            buildable_envelope=solver_input.buildable_envelope,
            unconstrained_pairs=solver_input.unconstrained_pairs,
        )

    with pytest.raises(ValidationError):
        LayoutSolverInputSet(
            project_id=solver_input.project_id,
            source_brief_version=-1,
            created_at=solver_input.created_at,
            spaces=solver_input.spaces,
            directives=solver_input.directives,
            space_metric_requirements=solver_input.space_metric_requirements,
            buildable_envelope=solver_input.buildable_envelope,
            unconstrained_pairs=solver_input.unconstrained_pairs,
        )


def test_direct_construction_rejects_empty_spaces() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    with pytest.raises(ValidationError):
        LayoutSolverInputSet(
            project_id=solver_input.project_id,
            source_brief_version=solver_input.source_brief_version,
            created_at=solver_input.created_at,
            spaces=[],
            directives=[],
            space_metric_requirements=[],
            buildable_envelope=solver_input.buildable_envelope,
            unconstrained_pairs=[],
        )


def test_direct_construction_rejects_invalid_source_schema_versions() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    with pytest.raises(ValidationError):
        LayoutSolverInputSet(
            project_id=solver_input.project_id,
            source_brief_version=solver_input.source_brief_version,
            source_directive_set_schema_version="invalid_schema.v1",  # type: ignore[arg-type]
            created_at=solver_input.created_at,
            spaces=solver_input.spaces,
            directives=solver_input.directives,
            space_metric_requirements=solver_input.space_metric_requirements,
            buildable_envelope=solver_input.buildable_envelope,
            unconstrained_pairs=solver_input.unconstrained_pairs,
        )

    with pytest.raises(ValidationError):
        LayoutSolverInputSet(
            project_id=solver_input.project_id,
            source_brief_version=solver_input.source_brief_version,
            source_metric_requirements_schema_version="invalid_schema.v1",  # type: ignore[arg-type]
            created_at=solver_input.created_at,
            spaces=solver_input.spaces,
            directives=solver_input.directives,
            space_metric_requirements=solver_input.space_metric_requirements,
            buildable_envelope=solver_input.buildable_envelope,
            unconstrained_pairs=solver_input.unconstrained_pairs,
        )

    with pytest.raises(ValidationError):
        LayoutSolverInputSet(
            project_id=solver_input.project_id,
            source_brief_version=solver_input.source_brief_version,
            source_site_envelope_schema_version="invalid_schema.v1",  # type: ignore[arg-type]
            created_at=solver_input.created_at,
            spaces=solver_input.spaces,
            directives=solver_input.directives,
            space_metric_requirements=solver_input.space_metric_requirements,
            buildable_envelope=solver_input.buildable_envelope,
            unconstrained_pairs=solver_input.unconstrained_pairs,
        )


def test_direct_construction_rejects_duplicate_metric_requirement_types_in_one_space() -> None:
    req1 = MetricRequirement(
        id="mreq_area_1",
        space_id="sn_bedroom_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=15.0,
        unit=MetricUnit.SQUARE_METRE,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )
    req2 = MetricRequirement(
        id="mreq_area_2",
        space_id="sn_bedroom_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=20.0,
        unit=MetricUnit.SQUARE_METRE,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )

    with pytest.raises(ValidationError, match="Duplicate requirement_type 'MIN_AREA'"):
        SolverSpaceMetricRequirements(
            space_id="sn_bedroom_01",
            requirements=[req1, req2],
        )


def test_deterministic_ordering_and_serialization_stability() -> None:
    directive_set, metrics, site_env = _sample_three_sources()

    input1 = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)
    input2 = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    json1 = input1.model_dump_json(indent=2)
    json2 = input2.model_dump_json(indent=2)

    assert json1 == json2


def test_timestamp_determinism_and_utc_enforcement() -> None:
    directive_set, metrics, site_env = _sample_three_sources()

    # 1. Default picks max timestamp
    default_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)
    expected_max = max(directive_set.created_at, metrics.created_at, site_env.created_at)
    assert default_input.created_at == expected_max

    # 2. Explicit UTC override
    override_dt = datetime(2026, 8, 19, 14, 0, 0, tzinfo=UTC)
    explicit_input = LayoutSolverInputAssembler.assemble(
        directive_set, metrics, site_env, created_at=override_dt
    )
    assert explicit_input.created_at == override_dt

    # 3. Naive datetime rejected
    naive_dt = datetime(2026, 8, 19, 14, 0, 0)
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env, created_at=naive_dt)

    # 4. Non-UTC datetime rejected
    non_utc_dt = datetime(2026, 8, 19, 17, 0, 0, tzinfo=timezone(timedelta(hours=3)))
    with pytest.raises(ValueError, match="created_at must use UTC offset"):
        LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env, created_at=non_utc_dt)


def test_zero_solver_execution_and_geometry_generation_invariant() -> None:
    forbidden_terms = [
        "room_x",
        "room_y",
        "room_width",
        "room_height",
        "footprint",
        "floor_plate",
        "circulation",
        "corridor",
        "wall",
        "door",
        "window",
        "cp_sat",
        "or_tools",
        "milp",
        "solver_penalty",
        "solver_weight",
    ]

    for model_cls in (
        SolverSpaceMetricRequirements,
        LayoutSolverInputSet,
    ):
        for field_name in model_cls.model_fields:
            for forbidden in forbidden_terms:
                assert forbidden not in field_name.lower(), (
                    f"Forbidden solver execution / geometry field {field_name!r} "
                    f"found in {model_cls.__name__}"
                )


def test_no_heuristic_space_matching() -> None:
    directive_set, metrics, site_env = _sample_three_sources()

    # Create metrics where space has identical display_name and function but different ID
    tampered_smr = [
        s if s.space_id != "sn_bedroom_01" else s.model_copy(update={"space_id": "sn_bedroom_99"})
        for s in metrics.space_requirements
    ]
    bad_metrics = metrics.model_copy(update={"space_requirements": tampered_smr})

    with pytest.raises(
        SolverInputSpaceMismatchError,
        match="Space mismatch between solver directives and metric requirements",
    ):
        LayoutSolverInputAssembler.assemble(directive_set, bad_metrics, site_env)


def test_ai_inferred_metric_requirements_excluded() -> None:
    directive_set, metrics, site_env = _sample_three_sources()

    # Add an AI_INFERRED metric requirement to living room
    ai_inferred_req = MetricRequirement(
        id="mreq_inferred_01",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
        value=3.5,
        unit=MetricUnit.METRE,
        provenance=RelationshipProvenance.AI_INFERRED,
        evidence_ids=[],
    )
    living_smr = [
        s
        if s.space_id != "sn_living_01"
        else s.model_copy(update={"requirements": list(s.requirements) + [ai_inferred_req]})
        for s in metrics.space_requirements
    ]
    # Update metrics with non-authoritative requirement included in space_requirements
    metrics_with_ai = metrics.model_copy(update={"space_requirements": living_smr})

    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics_with_ai, site_env)
    living_out = next(
        s for s in solver_input.space_metric_requirements if s.space_id == "sn_living_01"
    )

    # Only USER_CONFIRMED min_area is present, AI_INFERRED min_clear_width is excluded
    assert len(living_out.requirements) == 1
    assert living_out.requirements[0].requirement_type == MetricRequirementType.MIN_AREA
    assert living_out.requirements[0].id != "mreq_inferred_01"


def test_metric_fields_preserved_exactly() -> None:
    directive_set, metrics, site_env = _sample_three_sources()
    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    living_req = next(
        r
        for s in solver_input.space_metric_requirements
        if s.space_id == "sn_living_01"
        for r in s.requirements
    )

    orig_req = next(
        r
        for s in metrics.space_requirements
        if s.space_id == "sn_living_01"
        for r in s.requirements
        if r.provenance == RelationshipProvenance.USER_CONFIRMED
    )

    assert living_req.id == orig_req.id
    assert living_req.space_id == orig_req.space_id
    assert living_req.requirement_type == orig_req.requirement_type
    assert living_req.value == orig_req.value
    assert living_req.unit == orig_req.unit
    assert living_req.provenance == orig_req.provenance
    assert living_req.priority == orig_req.priority
    assert living_req.evidence_ids == orig_req.evidence_ids
    assert living_req.rationale == orig_req.rationale


def test_canonical_ordering_across_all_collections() -> None:
    directive_set, metrics, site_env = _sample_three_sources()

    # Pass unsorted spaces in directive_set
    unsorted_spaces = list(reversed(directive_set.spaces))
    unsorted_directives = directive_set.model_copy(update={"spaces": unsorted_spaces})

    solver_input = LayoutSolverInputAssembler.assemble(unsorted_directives, metrics, site_env)

    # Output spaces must be canonically sorted by id
    space_ids = [s.id for s in solver_input.spaces]
    assert space_ids == sorted(space_ids)

    # Output metric containers must be canonically sorted by space_id
    metric_space_ids = [s.space_id for s in solver_input.space_metric_requirements]
    assert metric_space_ids == sorted(metric_space_ids)

    # Output directives must be canonically sorted by id
    directive_ids = [d.id for d in solver_input.directives]
    assert directive_ids == sorted(directive_ids)


def test_v0_scope_and_buildable_envelope_documentation() -> None:
    # Ensure docstrings explicitly clarify the V0 site-based new-build scope
    # and that buildable_envelope is not a room layout container.
    doc = LayoutSolverInputSet.__doc__ or ""
    assert "SITE-BASED NEW-BUILD SCHEMATIC WORKFLOW" in doc
    assert "building-placement region" in doc
    assert "room-layout" in doc
    assert "container" in doc
