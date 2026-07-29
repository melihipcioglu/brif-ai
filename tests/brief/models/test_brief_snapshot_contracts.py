from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from brif_ai.brief.models import (
    BriefItem,
    BriefItemKind,
    BriefSnapshot,
    ConfirmationStatus,
    Contradiction,
    ContradictionStatus,
    Evidence,
    EvidenceSource,
    OpenQuestion,
    OpenQuestionStatus,
    Priority,
    SpaceRequest,
    Stakeholder,
    UsageScenario,
)
from brif_ai.core.models import SpaceFunction

UTC_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)  # noqa: UP017


def _stakeholder(stakeholder_id: str = "stakeholder_1") -> Stakeholder:
    return Stakeholder(
        id=stakeholder_id,
        display_name="Owner",
        role="decision maker",
        active=True,
    )


def _evidence(
    evidence_id: str = "evidence_1",
    source_type: EvidenceSource = EvidenceSource.CHAT,
    stimulus_id: str | None = None,
) -> Evidence:
    return Evidence(
        id=evidence_id,
        source_type=source_type,
        source_reference="chat:turn-1",
        excerpt="User asked for a quiet home office.",
        stimulus_id=stimulus_id,
    )


def _brief_item(
    item_id: str = "brief_item_1",
    *,
    stakeholder_ids: list[str] | None = None,
    evidence_ids: list[str] | None = None,
    confirmation_status: ConfirmationStatus = ConfirmationStatus.PROPOSED,
) -> BriefItem:
    return BriefItem(
        id=item_id,
        kind=BriefItemKind.NEED,
        normalized_statement="Provide a quiet workspace.",
        priority=Priority.MUST,
        stakeholder_ids=stakeholder_ids if stakeholder_ids is not None else ["stakeholder_1"],
        evidence_ids=evidence_ids if evidence_ids is not None else ["evidence_1"],
        confirmation_status=confirmation_status,
    )


def _space_request(
    request_id: str = "space_request_1",
    *,
    evidence_ids: list[str] | None = None,
    minimum_quantity: int = 1,
    maximum_quantity: int | None = 1,
) -> SpaceRequest:
    return SpaceRequest(
        id=request_id,
        display_name="Home office",
        space_function=SpaceFunction.WORK,
        minimum_quantity=minimum_quantity,
        maximum_quantity=maximum_quantity,
        mandatory=True,
        stakeholder_ids=["stakeholder_1"],
        evidence_ids=evidence_ids if evidence_ids is not None else ["evidence_1"],
        confirmation_status=ConfirmationStatus.PROPOSED,
    )


def _usage_scenario(scenario_id: str = "usage_scenario_1") -> UsageScenario:
    return UsageScenario(
        id=scenario_id,
        title="Weekday work",
        description="One stakeholder works from home during weekdays.",
        stakeholder_ids=["stakeholder_1"],
        evidence_ids=["evidence_1"],
        confirmation_status=ConfirmationStatus.CONFIRMED,
    )


def _contradiction(
    contradiction_id: str = "contradiction_1",
    *,
    brief_item_ids: list[str] | None = None,
    status: ContradictionStatus = ContradictionStatus.OPEN,
    resolution_note: str | None = None,
) -> Contradiction:
    return Contradiction(
        id=contradiction_id,
        brief_item_ids=brief_item_ids
        if brief_item_ids is not None
        else ["brief_item_1", "brief_item_2"],
        description="The requested workspace is both separate and open to living areas.",
        status=status,
        resolution_note=resolution_note,
    )


def _open_question(
    question_id: str = "open_question_1",
    *,
    related_brief_item_ids: list[str] | None = None,
    status: OpenQuestionStatus = OpenQuestionStatus.OPEN,
    resolution_note: str | None = None,
) -> OpenQuestion:
    return OpenQuestion(
        id=question_id,
        question="Should the workspace be acoustically separated?",
        reason="The user mentioned both quiet work and visual connection.",
        related_brief_item_ids=(
            related_brief_item_ids if related_brief_item_ids is not None else ["brief_item_1"]
        ),
        status=status,
        resolution_note=resolution_note,
    )


def _snapshot(
    *,
    stakeholders: list[Stakeholder] | None = None,
    evidence: list[Evidence] | None = None,
    brief_items: list[BriefItem] | None = None,
    space_requests: list[SpaceRequest] | None = None,
    usage_scenarios: list[UsageScenario] | None = None,
    contradictions: list[Contradiction] | None = None,
    open_questions: list[OpenQuestion] | None = None,
    created_at: datetime = UTC_TIME,
) -> BriefSnapshot:
    return BriefSnapshot(
        project_id="project_1",
        schema_version="brief.v0",
        brief_version=1,
        created_at=created_at,
        stakeholders=stakeholders if stakeholders is not None else [_stakeholder()],
        evidence=evidence if evidence is not None else [],
        brief_items=brief_items if brief_items is not None else [],
        space_requests=space_requests if space_requests is not None else [],
        usage_scenarios=usage_scenarios if usage_scenarios is not None else [],
        contradictions=contradictions if contradictions is not None else [],
        open_questions=open_questions if open_questions is not None else [],
    )


def test_valid_minimum_brief_snapshot() -> None:
    snapshot = _snapshot()

    assert snapshot.project_id == "project_1"
    assert snapshot.brief_version == 1
    assert snapshot.stakeholders[0].active is True
    assert snapshot.brief_items == []


def test_allows_multiple_stakeholders() -> None:
    snapshot = _snapshot(
        stakeholders=[
            _stakeholder("stakeholder_1"),
            Stakeholder(
                id="stakeholder_2",
                display_name="Operations team",
                role="user group",
                active=True,
            ),
        ]
    )

    assert [stakeholder.id for stakeholder in snapshot.stakeholders] == [
        "stakeholder_1",
        "stakeholder_2",
    ]


def test_rejects_invalid_internal_id() -> None:
    with pytest.raises(ValidationError) as error:
        _stakeholder("Stakeholder 1")

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("id",)
    assert first_error["type"] == "string_pattern_mismatch"


def test_rejects_duplicate_id_across_brief_object_types() -> None:
    with pytest.raises(ValidationError) as error:
        _snapshot(evidence=[_evidence("stakeholder_1")])

    assert "duplicate object id 'stakeholder_1'" in str(error.value)


def test_rejects_unknown_stakeholder_reference() -> None:
    with pytest.raises(ValidationError) as error:
        _snapshot(
            evidence=[_evidence()],
            brief_items=[_brief_item(stakeholder_ids=["missing_stakeholder"])],
        )

    assert "stakeholder_id 'missing_stakeholder'" in str(error.value)


def test_rejects_unknown_evidence_reference() -> None:
    with pytest.raises(ValidationError) as error:
        _snapshot(brief_items=[_brief_item(evidence_ids=["missing_evidence"])])

    assert "evidence_id 'missing_evidence'" in str(error.value)


def test_rejects_brief_item_without_evidence() -> None:
    with pytest.raises(ValidationError) as error:
        _brief_item(evidence_ids=[])

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("evidence_ids",)
    assert first_error["type"] == "too_short"


def test_rejects_duplicate_brief_item_references() -> None:
    with pytest.raises(ValidationError) as error:
        _brief_item(stakeholder_ids=["stakeholder_1", "stakeholder_1"])

    assert "duplicate reference id 'stakeholder_1'" in str(error.value)


def test_allows_confirmed_brief_item() -> None:
    brief_item = _brief_item(confirmation_status=ConfirmationStatus.CONFIRMED)
    snapshot = _snapshot(evidence=[_evidence()], brief_items=[brief_item])

    assert snapshot.brief_items[0].confirmation_status is ConfirmationStatus.CONFIRMED


def test_preserves_rejected_brief_item() -> None:
    brief_item = _brief_item(confirmation_status=ConfirmationStatus.REJECTED)
    snapshot = _snapshot(evidence=[_evidence()], brief_items=[brief_item])

    assert len(snapshot.brief_items) == 1
    assert snapshot.brief_items[0].confirmation_status is ConfirmationStatus.REJECTED


def test_valid_space_request() -> None:
    space_request = _space_request()
    snapshot = _snapshot(evidence=[_evidence()], space_requests=[space_request])

    assert snapshot.space_requests[0].space_function is SpaceFunction.WORK
    assert snapshot.space_requests[0].minimum_quantity == 1


def test_rejects_space_request_without_evidence() -> None:
    with pytest.raises(ValidationError) as error:
        _space_request(evidence_ids=[])

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("evidence_ids",)
    assert first_error["type"] == "too_short"


def test_rejects_duplicate_space_request_references() -> None:
    with pytest.raises(ValidationError) as error:
        SpaceRequest(
            id="space_request_1",
            display_name="Home office",
            space_function=SpaceFunction.WORK,
            minimum_quantity=1,
            maximum_quantity=1,
            mandatory=True,
            stakeholder_ids=["stakeholder_1"],
            evidence_ids=["evidence_1", "evidence_1"],
            confirmation_status=ConfirmationStatus.PROPOSED,
        )

    assert "duplicate reference id 'evidence_1'" in str(error.value)


def test_rejects_maximum_quantity_below_minimum() -> None:
    with pytest.raises(ValidationError) as error:
        _space_request(minimum_quantity=2, maximum_quantity=1)

    assert "maximum_quantity cannot be less than minimum_quantity" in str(error.value)


def test_visual_stimulus_requires_stimulus_id() -> None:
    with pytest.raises(ValidationError) as error:
        _evidence(source_type=EvidenceSource.VISUAL_STIMULUS)

    assert "visual stimulus evidence requires stimulus_id" in str(error.value)


def test_rejects_stimulus_id_for_non_visual_evidence() -> None:
    with pytest.raises(ValidationError) as error:
        _evidence(stimulus_id="stimulus_1")

    assert "stimulus_id is only allowed for visual stimulus evidence" in str(error.value)


def test_rejects_contradiction_with_fewer_than_two_items() -> None:
    with pytest.raises(ValidationError) as error:
        _contradiction(brief_item_ids=["brief_item_1"])

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("brief_item_ids",)
    assert first_error["type"] == "too_short"


def test_rejects_duplicate_brief_item_in_contradiction() -> None:
    with pytest.raises(ValidationError) as error:
        _contradiction(brief_item_ids=["brief_item_1", "brief_item_1"])

    assert "duplicate brief_item_id 'brief_item_1'" in str(error.value)


def test_rejects_unknown_brief_item_in_contradiction() -> None:
    first_item = _brief_item("brief_item_1")
    with pytest.raises(ValidationError) as error:
        _snapshot(
            evidence=[_evidence()],
            brief_items=[first_item],
            contradictions=[_contradiction(brief_item_ids=["brief_item_1", "missing_brief_item"])],
        )

    assert "brief_item_id 'missing_brief_item'" in str(error.value)


def test_resolved_contradiction_requires_resolution_note() -> None:
    with pytest.raises(ValidationError) as error:
        _contradiction(status=ContradictionStatus.RESOLVED)

    assert "resolved contradiction requires resolution_note" in str(error.value)


def test_valid_open_question() -> None:
    brief_item = _brief_item("brief_item_1")
    open_question = _open_question()
    snapshot = _snapshot(
        evidence=[_evidence()],
        brief_items=[brief_item],
        open_questions=[open_question],
    )

    assert snapshot.open_questions[0].status is OpenQuestionStatus.OPEN
    assert snapshot.open_questions[0].related_brief_item_ids == ["brief_item_1"]


def test_rejects_duplicate_brief_item_in_open_question() -> None:
    with pytest.raises(ValidationError) as error:
        _open_question(related_brief_item_ids=["brief_item_1", "brief_item_1"])

    assert "duplicate related_brief_item_id 'brief_item_1'" in str(error.value)


def test_answered_open_question_requires_resolution_note() -> None:
    with pytest.raises(ValidationError) as error:
        _open_question(status=OpenQuestionStatus.ANSWERED)

    assert "answered or dismissed open question requires resolution_note" in str(error.value)


def test_rejects_naive_created_at() -> None:
    with pytest.raises(ValidationError) as error:
        _snapshot(created_at=datetime(2026, 1, 1, 12, 0))

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("created_at",)
    assert "timezone-aware" in first_error["msg"]


def test_rejects_non_utc_created_at() -> None:
    with pytest.raises(ValidationError) as error:
        _snapshot(created_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=3))))

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("created_at",)
    assert "UTC offset" in first_error["msg"]


def test_rejects_extra_fields() -> None:
    payload = _stakeholder().model_dump()
    payload["email"] = "owner@example.com"

    with pytest.raises(ValidationError) as error:
        Stakeholder.model_validate(payload)

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("email",)
    assert first_error["type"] == "extra_forbidden"


def test_serializes_json_enums_and_references() -> None:
    brief_item = _brief_item(confirmation_status=ConfirmationStatus.CONFIRMED)
    space_request = _space_request()
    usage_scenario = _usage_scenario()
    snapshot = _snapshot(
        evidence=[_evidence()],
        brief_items=[brief_item],
        space_requests=[space_request],
        usage_scenarios=[usage_scenario],
    )

    dumped = snapshot.model_dump(mode="json")
    json_output = snapshot.model_dump_json()

    assert dumped["brief_items"][0]["kind"] == "NEED"
    assert dumped["brief_items"][0]["stakeholder_ids"] == ["stakeholder_1"]
    assert dumped["brief_items"][0]["confirmation_status"] == "CONFIRMED"
    assert dumped["space_requests"][0]["space_function"] == "WORK"
    assert dumped["usage_scenarios"][0]["evidence_ids"] == ["evidence_1"]
    assert '"kind":"NEED"' in json_output
    assert '"space_function":"WORK"' in json_output


def test_rejects_duplicate_usage_scenario_references() -> None:
    with pytest.raises(ValidationError) as error:
        UsageScenario(
            id="usage_scenario_1",
            title="Weekday work",
            description="One stakeholder works from home during weekdays.",
            stakeholder_ids=["stakeholder_1", "stakeholder_1"],
            evidence_ids=["evidence_1"],
            confirmation_status=ConfirmationStatus.CONFIRMED,
        )

    assert "duplicate reference id 'stakeholder_1'" in str(error.value)
