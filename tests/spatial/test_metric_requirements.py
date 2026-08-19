"""Focused tests for BRIF.AI Metric Spatial Requirements V0 domain contracts and builder."""

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
from brif_ai.spatial.metrics.builder import MetricSpatialRequirementsBuilder
from brif_ai.spatial.metrics.errors import (
    DuplicateMetricRequirementError,
    MetricMissingInputError,
    MetricNonexistentSpaceError,
    MetricRangeConflictError,
    MetricSchemaVersionMismatchError,
)
from brif_ai.spatial.metrics.models import (
    MetricRequirement,
    MetricRequirementInput,
    MetricRequirementType,
    MetricSpatialRequirements,
    MetricUnit,
    SpaceMetricRequirements,
    generate_metric_requirement_id,
)
from brif_ai.spatial.models import RelationshipProvenance
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.program.models import SpatialProgram

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


def _evidence(ev_id: str = "ev_metric_01") -> Evidence:
    return Evidence(
        id=ev_id,
        source_type=EvidenceSource.CHAT,
        source_reference="chat:turn-1",
        excerpt="Client stated metric requirement.",
    )


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


def _ready_program(
    *,
    project_id: str = "proj_metric_test",
    brief_version: int = 1,
) -> SpatialProgram:
    ev = _evidence()
    spaces = [
        SpaceRequest(
            id="sr_living",
            display_name="Salon",
            space_function=SpaceFunction.LIVING,
            minimum_quantity=1,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_owner"],
            evidence_ids=[ev.id],
        ),
        SpaceRequest(
            id="sr_kitchen",
            display_name="Mutfak",
            space_function=SpaceFunction.COOKING,
            minimum_quantity=1,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_owner"],
            evidence_ids=[ev.id],
        ),
        SpaceRequest(
            id="sr_bed",
            display_name="Yatak Odası",
            space_function=SpaceFunction.SLEEPING,
            minimum_quantity=2,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_owner"],
            evidence_ids=[ev.id],
        ),
    ]
    snapshot = BriefSnapshot(
        project_id=project_id,
        schema_version="brief.v0",
        brief_version=brief_version,
        created_at=datetime(2026, 8, 19, 12, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(
                id="stk_owner",
                display_name="Ev Sahibi",
                role="CLIENT_OWNER",
                active=True,
            )
        ],
        evidence=[ev],
        brief_items=[],
        space_requests=spaces,
        usage_scenarios=[],
        contradictions=[],
        open_questions=_closed_topic_questions(),
    )
    graph = SpatialRelationshipGraphBuilder().build(
        snapshot,
        [],
        created_at=datetime(2026, 8, 19, 12, 5, tzinfo=UTC),
    )
    return SpatialProgramBuilder().build(snapshot, graph)


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_valid_metric_requirements_contract_created() -> None:
    program = _ready_program()
    inputs = [
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=35.0,
            unit=MetricUnit.SQUARE_METRE,
            priority=Priority.MUST,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
            rationale="Salon genis olmali.",
        ),
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.TARGET_AREA,
            value=45.0,
            unit=MetricUnit.SQUARE_METRE,
            priority=Priority.SHOULD,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
        MetricRequirementInput(
            space_id="sn_kitchen_01",
            requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
            value=2.8,
            unit=MetricUnit.METRE,
            priority=Priority.MUST,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
    ]

    builder = MetricSpatialRequirementsBuilder()
    req_set = builder.build(program, inputs)

    assert isinstance(req_set, MetricSpatialRequirements)
    assert req_set.schema_version == "metric_spatial_requirements.v0"
    assert req_set.project_id == program.project_id
    assert req_set.source_brief_version == program.source_brief_version
    assert req_set.source_program_schema_version == "spatial_program.v0"
    assert req_set.created_at == program.created_at

    # All 4 spaces from program are represented
    assert len(req_set.space_requirements) == 4
    living_req = next(sr for sr in req_set.space_requirements if sr.space_id == "sn_living_01")
    assert len(living_req.requirements) == 2
    kitchen_req = next(sr for sr in req_set.space_requirements if sr.space_id == "sn_kitchen_01")
    assert len(kitchen_req.requirements) == 1
    bed1_req = next(sr for sr in req_set.space_requirements if sr.space_id == "sn_bed_01")
    assert len(bed1_req.requirements) == 0

    assert len(req_set.authoritative_requirement_ids) == 3


def test_explicit_area_requirements_preserved_exactly() -> None:
    program = _ready_program()
    inputs = [
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
            priority=Priority.MUST,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MAX_AREA,
            value=60.0,
            unit=MetricUnit.SQUARE_METRE,
            priority=Priority.COULD,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.TARGET_AREA,
            value=45.0,
            unit=MetricUnit.SQUARE_METRE,
            priority=Priority.SHOULD,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
    ]

    req_set = MetricSpatialRequirementsBuilder().build(program, inputs)
    living_space = next(sr for sr in req_set.space_requirements if sr.space_id == "sn_living_01")

    type_to_req = {r.requirement_type: r for r in living_space.requirements}
    assert type_to_req[MetricRequirementType.MIN_AREA].value == 30.0
    assert type_to_req[MetricRequirementType.MIN_AREA].unit == MetricUnit.SQUARE_METRE
    assert type_to_req[MetricRequirementType.MAX_AREA].value == 60.0
    assert type_to_req[MetricRequirementType.MAX_AREA].unit == MetricUnit.SQUARE_METRE
    assert type_to_req[MetricRequirementType.TARGET_AREA].value == 45.0
    assert type_to_req[MetricRequirementType.TARGET_AREA].unit == MetricUnit.SQUARE_METRE


def test_explicit_clear_width_requirements_preserved_exactly() -> None:
    program = _ready_program()
    inputs = [
        MetricRequirementInput(
            space_id="sn_kitchen_01",
            requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
            value=2.40,
            unit=MetricUnit.METRE,
            priority=Priority.MUST,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        )
    ]
    req_set = MetricSpatialRequirementsBuilder().build(program, inputs)
    kitchen = next(sr for sr in req_set.space_requirements if sr.space_id == "sn_kitchen_01")
    assert len(kitchen.requirements) == 1
    assert kitchen.requirements[0].requirement_type == MetricRequirementType.MIN_CLEAR_WIDTH
    assert kitchen.requirements[0].value == 2.40
    assert kitchen.requirements[0].unit == MetricUnit.METRE


def test_no_space_function_defaults_are_generated() -> None:
    program = _ready_program()
    # Build with empty input requirements
    req_set = MetricSpatialRequirementsBuilder().build(program, [])

    for space_metric in req_set.space_requirements:
        # Every space must have exactly 0 requirements (no inferred defaults)
        assert space_metric.requirements == [], (
            f"Space {space_metric.space_id} received unexpected default requirements."
        )


def test_absence_of_metric_requirement_remains_absence() -> None:
    program = _ready_program()
    req_set = MetricSpatialRequirementsBuilder().build(program, [])
    # 4 discrete spaces in program
    assert len(req_set.space_requirements) == 4
    space_ids = [s.space_id for s in req_set.space_requirements]
    assert space_ids == ["sn_bed_01", "sn_bed_02", "sn_kitchen_01", "sn_living_01"]
    assert req_set.authoritative_requirement_ids == []


def test_positive_finite_value_validation() -> None:
    for bad_val in (0.0, -10.0, float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValidationError, match="finite and strictly positive"):
            MetricRequirementInput(
                space_id="sn_living_01",
                requirement_type=MetricRequirementType.MIN_AREA,
                value=bad_val,
                unit=MetricUnit.SQUARE_METRE,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                evidence_ids=["ev_metric_01"],
            )


def test_min_less_than_or_equal_max_validation() -> None:
    program = _ready_program()
    bad_inputs = [
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=50.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MAX_AREA,
            value=30.0,  # Invalid: min (50) > max (30)
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
    ]
    with pytest.raises(MetricRangeConflictError, match="exceeds MAX_AREA"):
        MetricSpatialRequirementsBuilder().build(program, bad_inputs)


def test_target_lies_within_min_max_bounds() -> None:
    program = _ready_program()

    # Target smaller than min
    bad_inputs_1 = [
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.TARGET_AREA,
            value=25.0,  # Invalid: target < min
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
    ]
    with pytest.raises(MetricRangeConflictError, match="less than MIN_AREA"):
        MetricSpatialRequirementsBuilder().build(program, bad_inputs_1)

    # Target greater than max
    bad_inputs_2 = [
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MAX_AREA,
            value=40.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.TARGET_AREA,
            value=45.0,  # Invalid: target > max
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
    ]
    with pytest.raises(MetricRangeConflictError, match="exceeds MAX_AREA"):
        MetricSpatialRequirementsBuilder().build(program, bad_inputs_2)


def test_target_can_exist_without_bounds() -> None:
    program = _ready_program()
    valid_target_only = [
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.TARGET_AREA,
            value=45.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        )
    ]
    req_set = MetricSpatialRequirementsBuilder().build(program, valid_target_only)
    living = next(sr for sr in req_set.space_requirements if sr.space_id == "sn_living_01")
    assert len(living.requirements) == 1
    assert living.requirements[0].requirement_type == MetricRequirementType.TARGET_AREA


def test_unknown_space_reference_rejected() -> None:
    program = _ready_program()
    bad_input = [
        MetricRequirementInput(
            space_id="sn_phantom_room",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=20.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        )
    ]
    with pytest.raises(MetricNonexistentSpaceError, match="unknown space_id"):
        MetricSpatialRequirementsBuilder().build(program, bad_input)


def test_duplicate_requirement_type_for_same_space_rejected() -> None:
    program = _ready_program()
    duplicate_inputs = [
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=35.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
    ]
    with pytest.raises(DuplicateMetricRequirementError, match="Duplicate requirement_type"):
        MetricSpatialRequirementsBuilder().build(program, duplicate_inputs)


def test_unit_compatibility_validation() -> None:
    with pytest.raises(ValidationError, match="requires unit SQUARE_METRE"):
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.METRE,  # Invalid unit for area
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        )

    with pytest.raises(ValidationError, match="requires unit METRE"):
        MetricRequirementInput(
            space_id="sn_kitchen_01",
            requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
            value=2.4,
            unit=MetricUnit.SQUARE_METRE,  # Invalid unit for width
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        )


def test_user_confirmed_requires_evidence() -> None:
    with pytest.raises(ValidationError, match="requires at least one evidence ID"):
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[],  # Missing evidence
        )


def test_authoritative_requirement_ids_invariant() -> None:
    program = _ready_program()
    inputs = [
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        ),
        MetricRequirementInput(
            space_id="sn_kitchen_01",
            requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
            value=2.5,
            unit=MetricUnit.METRE,
            provenance=RelationshipProvenance.USER_STATED,  # Not confirmed
            evidence_ids=[],
        ),
    ]

    req_set = MetricSpatialRequirementsBuilder().build(program, inputs)
    assert len(req_set.authoritative_requirement_ids) == 1
    living_req = next(sr for sr in req_set.space_requirements if sr.space_id == "sn_living_01")
    assert req_set.authoritative_requirement_ids == [living_req.requirements[0].id]


def test_deterministic_id_generation_and_value_independence() -> None:
    id1 = generate_metric_requirement_id(
        project_id="proj_1",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_AREA,
    )
    id2 = generate_metric_requirement_id(
        project_id="proj_1",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_AREA,
    )
    assert id1 == id2
    assert id1.startswith("mreq_")

    # ID is independent of value
    program = _ready_program()
    inp_v1 = MetricRequirementInput(
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_metric_01"],
    )
    inp_v2 = MetricRequirementInput(
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=50.0,  # Different value
        unit=MetricUnit.SQUARE_METRE,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_metric_01"],
    )

    req1 = MetricSpatialRequirementsBuilder().build(program, [inp_v1])
    req2 = MetricSpatialRequirementsBuilder().build(program, [inp_v2])

    living_req_1 = next(sr for sr in req1.space_requirements if sr.space_id == "sn_living_01")
    living_req_2 = next(sr for sr in req2.space_requirements if sr.space_id == "sn_living_01")

    assert living_req_1.requirements[0].id == living_req_2.requirements[0].id
    assert living_req_1.requirements[0].value == 30.0
    assert living_req_2.requirements[0].value == 50.0


def test_determinism_and_repeated_build_stability() -> None:
    program = _ready_program()
    inputs = [
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_metric_01"],
        )
    ]

    builder = MetricSpatialRequirementsBuilder()
    set1 = builder.build(program, inputs)
    set2 = builder.build(program, inputs)

    assert set1 == set2
    assert set1.model_dump_json() == set2.model_dump_json()
    assert set1.created_at == program.created_at
    assert set2.created_at == program.created_at


def test_strict_utc_timestamp_validation() -> None:
    program = _ready_program()
    builder = MetricSpatialRequirementsBuilder()

    naive_dt = datetime(2026, 8, 19, 12, 0, 0)
    with pytest.raises(ValidationError, match="created_at must be timezone-aware"):
        builder.build(program, [], created_at=naive_dt)

    non_utc_dt = datetime(2026, 8, 19, 15, 0, 0, tzinfo=timezone(timedelta(hours=3)))
    with pytest.raises(ValidationError, match="created_at must use UTC offset"):
        builder.build(program, [], created_at=non_utc_dt)


def test_missing_or_invalid_program_input() -> None:
    builder = MetricSpatialRequirementsBuilder()
    with pytest.raises(MetricMissingInputError):
        builder.build(None)  # type: ignore[arg-type]

    program = _ready_program()
    corrupted_program = SpatialProgram.model_construct(
        schema_version="spatial_program.v999",
        project_id=program.project_id,
        source_brief_version=program.source_brief_version,
        created_at=program.created_at,
        spaces=program.spaces,
        relationships=program.relationships,
        unconstrained_pairs=program.unconstrained_pairs,
        authoritative_relationship_ids=program.authoritative_relationship_ids,
    )
    with pytest.raises(MetricSchemaVersionMismatchError):
        builder.build(corrupted_program)


def test_zero_geometry_and_no_rect_assumptions() -> None:
    forbidden_terms = [
        "coord",
        "dimension",
        "width_m",
        "depth",
        "height",
        "polygon",
        "rectangle",
        "point",
        "bound",
        "floor",
        "door",
        "window",
        "wall",
        "corridor",
        "setback",
        "zoning",
        "x",
        "y",
    ]

    for model_cls in (
        MetricRequirementInput,
        MetricRequirement,
        SpaceMetricRequirements,
        MetricSpatialRequirements,
    ):
        for field_name in model_cls.model_fields:
            for forbidden in forbidden_terms:
                assert forbidden != field_name.lower(), (
                    f"Forbidden geometric field {field_name!r} found in {model_cls.__name__}"
                )


def test_provenance_is_strictly_required_with_no_default() -> None:
    # 1. MetricRequirementInput must reject omitted provenance
    with pytest.raises(ValidationError, match="Field required"):
        MetricRequirementInput.model_validate(
            {
                "space_id": "sn_living_01",
                "requirement_type": MetricRequirementType.MIN_AREA,
                "value": 30.0,
                "unit": MetricUnit.SQUARE_METRE,
                "evidence_ids": ["ev_metric_01"],
            }
        )

    # 2. MetricRequirement must reject omitted provenance
    with pytest.raises(ValidationError, match="Field required"):
        MetricRequirement.model_validate(
            {
                "id": "mreq_test_01",
                "space_id": "sn_living_01",
                "requirement_type": MetricRequirementType.MIN_AREA,
                "value": 30.0,
                "unit": MetricUnit.SQUARE_METRE,
                "evidence_ids": ["ev_metric_01"],
            }
        )
