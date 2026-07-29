from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from brif_ai.core.models import (
    IssueSeverity,
    ObjectReference,
    ObjectType,
    RuleMetadata,
    ValidationIssue,
    ValidationReport,
    ValidationStatus,
)

UTC_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)  # noqa: UP017


def _rule() -> RuleMetadata:
    return RuleMetadata(
        rulepack_id="tr-core",
        rulepack_version="0.1.0",
        rule_id="core.access.primary",
        rule_version="0.1.0",
    )


def _object_reference() -> ObjectReference:
    return ObjectReference(object_type=ObjectType.DOOR, object_id="door_1")


def _issue(severity: IssueSeverity = IssueSeverity.ERROR) -> ValidationIssue:
    return ValidationIssue(
        severity=severity,
        message="A contract issue",
        rule=_rule(),
        object_references=[_object_reference()],
    )


def _report(
    *, issues: list[ValidationIssue] | None = None, validated_at: datetime = UTC_TIME
) -> ValidationReport:
    return ValidationReport(
        project_id="project_1",
        schema_version="core.v0",
        rulepack_id="tr-core",
        rulepack_version="0.1.0",
        validator_version="0.1.0",
        validated_at=validated_at,
        issues=issues if issues is not None else [],
    )


def test_validation_issue_object_reference() -> None:
    issue = _issue()

    assert issue.object_references[0].object_type is ObjectType.DOOR
    assert issue.object_references[0].object_id == "door_1"
    assert issue.severity is IssueSeverity.ERROR


def test_rejects_naive_validated_at() -> None:
    with pytest.raises(ValidationError) as error:
        _report(validated_at=datetime(2026, 1, 1, 12, 0))

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("validated_at",)
    assert "timezone-aware" in first_error["msg"]


def test_rejects_non_utc_validated_at() -> None:
    with pytest.raises(ValidationError) as error:
        _report(validated_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=3))))

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("validated_at",)
    assert "UTC offset" in first_error["msg"]


def test_report_status_blocked_with_critical_issue() -> None:
    report = _report(issues=[_issue(IssueSeverity.CRITICAL)])

    assert report.status is ValidationStatus.BLOCKED
    assert report.critical_count == 1


def test_report_is_not_showable_with_critical_issue() -> None:
    report = _report(issues=[_issue(IssueSeverity.CRITICAL)])

    assert report.is_showable is False


def test_report_revision_required_with_noncritical_issue() -> None:
    report = _report(issues=[_issue(IssueSeverity.WARNING)])

    assert report.status is ValidationStatus.REVISION_REQUIRED
    assert report.critical_count == 0
    assert report.is_showable is True


def test_report_pass_without_issues() -> None:
    report = _report()

    assert report.status is ValidationStatus.PASS
    assert report.critical_count == 0
    assert report.is_showable is True


def test_report_rejects_input_derived_fields() -> None:
    payload = _report().model_dump()
    payload["status"] = ValidationStatus.PASS
    payload["critical_count"] = 0
    payload["is_showable"] = True

    with pytest.raises(ValidationError) as error:
        ValidationReport.model_validate(payload)

    locations = {item["loc"][0] for item in error.value.errors()}
    assert {"status", "critical_count", "is_showable"}.issubset(locations)


def test_report_serializes_derived_fields() -> None:
    report = _report(issues=[_issue(IssueSeverity.WARNING)])

    dumped = report.model_dump(mode="json")
    json_output = report.model_dump_json()

    assert dumped["status"] == "REVISION_REQUIRED"
    assert dumped["critical_count"] == 0
    assert dumped["is_showable"] is True
    assert '"status":"REVISION_REQUIRED"' in json_output
    assert '"critical_count":0' in json_output
    assert '"is_showable":true' in json_output
