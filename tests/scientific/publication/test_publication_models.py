"""Unit tests for Publication Validation v0 data contracts and Pydantic models."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from brif_ai.conversation.models import (
    AnswerType,
    ConversationModule,
    FulfillmentPolicy,
    InformationTargetDefinition,
    QuestionCatalog,
    QuestionDefinition,
    QuestionStatus,
)
from brif_ai.scientific.models import ScientificContentRegistry
from brif_ai.scientific.publication import (
    PublicationIssue,
    PublicationIssueCode,
    PublicationIssueSeverity,
    PublicationObjectType,
    PublicationValidationReport,
    PublicationValidationRequest,
    QuestionPublicationResult,
)

UTC_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)  # noqa: UP017
NON_UTC_TIME = datetime(2026, 1, 1, 15, 0, tzinfo=timezone(timedelta(hours=3)))
NAIVE_TIME = datetime(2026, 1, 1, 12, 0)


def _synthetic_catalog(catalog_id: str = "catalog_1", catalog_version: int = 1) -> QuestionCatalog:
    target = InformationTargetDefinition(
        id="target_1",
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="Test purpose",
        required=True,
        fulfillment_policy=FulfillmentPolicy.VALID_ANSWER,
    )
    question = QuestionDefinition(
        id="question_1",
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="Test question purpose",
        content_key="question.test_1",
        answer_type=AnswerType.FREE_TEXT,
        required=True,
        output_target_ids=["target_1"],
        allowed_follow_up_question_ids=[],
        applicable_stakeholder_roles=["owner"],
        display_order=1,
        source_metadata="synthetic test metadata",
        status=QuestionStatus.APPROVED,
        options=[],
    )
    return QuestionCatalog(
        id=catalog_id,
        schema_version="v0",
        catalog_version=catalog_version,
        modules=[ConversationModule.PROJECT_CONTEXT],
        information_targets=[target],
        questions=[question],
        transition_rules=[],
    )


def _synthetic_registry(
    registry_id: str = "registry_1",
    catalog_id: str = "catalog_1",
    catalog_version: int = 1,
) -> ScientificContentRegistry:
    return ScientificContentRegistry(
        id=registry_id,
        schema_version="v0",
        registry_version=1,
        question_catalog_id=catalog_id,
        question_catalog_version=catalog_version,
        content_bundle_version=1,
        created_at=UTC_TIME,
        sources=[],
        constructs=[],
        question_content_revisions=[],
        evidence_links=[],
        expert_reviews=[],
        evaluations=[],
    )


def _synthetic_issue(
    issue_id: str = "issue_1",
    *,
    code: PublicationIssueCode = PublicationIssueCode.NO_APPROVED_QUESTIONS,
    severity: PublicationIssueSeverity = PublicationIssueSeverity.ERROR,
    object_type: PublicationObjectType = PublicationObjectType.QUESTION_CATALOG,
    object_id: str = "catalog_1",
    question_id: str | None = None,
    question_content_revision_id: str | None = None,
    message: str = "Synthetic test issue message.",
    related_object_ids: list[str] | None = None,
) -> PublicationIssue:
    return PublicationIssue(
        id=issue_id,
        code=code,
        severity=severity,
        object_type=object_type,
        object_id=object_id,
        question_id=question_id,
        question_content_revision_id=question_content_revision_id,
        message=message,
        related_object_ids=related_object_ids if related_object_ids is not None else [],
    )


def _synthetic_question_result(
    question_id: str = "question_1",
    *,
    target_locale: str = "en-US",
    selected_content_revision_id: str | None = "revision_1",
    issue_ids: list[str] | None = None,
    blocking_issue_ids: list[str] | None = None,
) -> QuestionPublicationResult:
    return QuestionPublicationResult(
        question_id=question_id,
        target_locale=target_locale,
        selected_content_revision_id=selected_content_revision_id,
        issue_ids=issue_ids if issue_ids is not None else [],
        blocking_issue_ids=blocking_issue_ids if blocking_issue_ids is not None else [],
    )


# 1. test_valid_publication_validation_request
def test_valid_publication_validation_request() -> None:
    catalog = _synthetic_catalog()
    registry = _synthetic_registry()
    request = PublicationValidationRequest(
        catalog=catalog,
        registry=registry,
        target_locale="en-US",
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
    )
    assert request.catalog.id == "catalog_1"
    assert request.registry.id == "registry_1"
    assert request.target_locale == "en-US"
    assert request.checked_at == UTC_TIME
    assert request.validator_version == "v0.1.0"


# 2. test_request_allows_catalog_registry_id_mismatch
def test_request_allows_catalog_registry_id_mismatch() -> None:
    catalog = _synthetic_catalog(catalog_id="catalog_a")
    registry = _synthetic_registry(catalog_id="catalog_b")
    request = PublicationValidationRequest(
        catalog=catalog,
        registry=registry,
        target_locale="en-US",
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
    )
    assert request.catalog.id == "catalog_a"
    assert request.registry.question_catalog_id == "catalog_b"


# 3. test_request_allows_catalog_registry_version_mismatch
def test_request_allows_catalog_registry_version_mismatch() -> None:
    catalog = _synthetic_catalog(catalog_version=1)
    registry = _synthetic_registry(catalog_version=2)
    request = PublicationValidationRequest(
        catalog=catalog,
        registry=registry,
        target_locale="en-US",
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
    )
    assert request.catalog.catalog_version == 1
    assert request.registry.question_catalog_version == 2


# 4. test_request_rejects_naive_checked_at
def test_request_rejects_naive_checked_at() -> None:
    catalog = _synthetic_catalog()
    registry = _synthetic_registry()
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationRequest(
            catalog=catalog,
            registry=registry,
            target_locale="en-US",
            checked_at=NAIVE_TIME,
            validator_version="v0.1.0",
        )
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("checked_at",)
    assert "timezone-aware" in str(errors[0]["msg"])


# 5. test_request_rejects_non_utc_checked_at
def test_request_rejects_non_utc_checked_at() -> None:
    catalog = _synthetic_catalog()
    registry = _synthetic_registry()
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationRequest(
            catalog=catalog,
            registry=registry,
            target_locale="en-US",
            checked_at=NON_UTC_TIME,
            validator_version="v0.1.0",
        )
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("checked_at",)
    assert "UTC offset" in str(errors[0]["msg"])


# 6. test_request_rejects_unexpected_field
def test_request_rejects_unexpected_field() -> None:
    catalog = _synthetic_catalog()
    registry = _synthetic_registry()
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationRequest(
            catalog=catalog,
            registry=registry,
            target_locale="en-US",
            checked_at=UTC_TIME,
            validator_version="v0.1.0",
            extra_field="invalid",  # type: ignore[call-arg]
        )
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("extra_field",)


# 7. test_info_issue_is_not_blocking
def test_info_issue_is_not_blocking() -> None:
    issue = _synthetic_issue(severity=PublicationIssueSeverity.INFO)
    assert issue.severity == PublicationIssueSeverity.INFO
    assert issue.blocking is False


# 8. test_warning_issue_is_not_blocking
def test_warning_issue_is_not_blocking() -> None:
    issue = _synthetic_issue(severity=PublicationIssueSeverity.WARNING)
    assert issue.severity == PublicationIssueSeverity.WARNING
    assert issue.blocking is False


# 9. test_error_issue_is_blocking
def test_error_issue_is_blocking() -> None:
    issue = _synthetic_issue(severity=PublicationIssueSeverity.ERROR)
    assert issue.severity == PublicationIssueSeverity.ERROR
    assert issue.blocking is True


# 10. test_critical_issue_is_blocking
def test_critical_issue_is_blocking() -> None:
    issue = _synthetic_issue(severity=PublicationIssueSeverity.CRITICAL)
    assert issue.severity == PublicationIssueSeverity.CRITICAL
    assert issue.blocking is True


# 11. test_issue_rejects_duplicate_related_object_ids
def test_issue_rejects_duplicate_related_object_ids() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _synthetic_issue(related_object_ids=["obj_1", "obj_1"])
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("related_object_ids",)
    assert "duplicate related_object_id 'obj_1'" in str(errors[0]["msg"])


# 12. test_issue_rejects_external_blocking_value
def test_issue_rejects_external_blocking_value() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PublicationIssue(
            id="issue_1",
            code=PublicationIssueCode.NO_APPROVED_QUESTIONS,
            severity=PublicationIssueSeverity.ERROR,
            object_type=PublicationObjectType.QUESTION_CATALOG,
            object_id="catalog_1",
            message="Test message",
            blocking=False,  # type: ignore[call-arg]
        )
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("blocking",)


# 13. test_issue_serializes_computed_blocking
def test_issue_serializes_computed_blocking() -> None:
    issue_info = _synthetic_issue(severity=PublicationIssueSeverity.INFO)
    issue_err = _synthetic_issue(severity=PublicationIssueSeverity.ERROR)
    assert issue_info.model_dump()["blocking"] is False
    assert issue_err.model_dump()["blocking"] is True
    assert '"blocking":false' in issue_info.model_dump_json().replace(" ", "")
    assert '"blocking":true' in issue_err.model_dump_json().replace(" ", "")


# 14. test_question_result_ready_without_blocking_issues
def test_question_result_ready_without_blocking_issues() -> None:
    res = _synthetic_question_result(
        selected_content_revision_id="revision_1",
        issue_ids=[],
        blocking_issue_ids=[],
    )
    assert res.ready_for_publication is True


# 15. test_question_result_warning_does_not_block_readiness
def test_question_result_warning_does_not_block_readiness() -> None:
    res = _synthetic_question_result(
        selected_content_revision_id="revision_1",
        issue_ids=["issue_warn"],
        blocking_issue_ids=[],
    )
    assert res.ready_for_publication is True


# 16. test_question_result_not_ready_without_selected_revision
def test_question_result_not_ready_without_selected_revision() -> None:
    res = _synthetic_question_result(
        selected_content_revision_id=None,
        issue_ids=[],
        blocking_issue_ids=[],
    )
    assert res.ready_for_publication is False


# 17. test_question_result_not_ready_with_blocking_issue
def test_question_result_not_ready_with_blocking_issue() -> None:
    res = _synthetic_question_result(
        selected_content_revision_id="revision_1",
        issue_ids=["issue_err"],
        blocking_issue_ids=["issue_err"],
    )
    assert res.ready_for_publication is False


# 18. test_question_result_rejects_duplicate_issue_ids
def test_question_result_rejects_duplicate_issue_ids() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _synthetic_question_result(issue_ids=["issue_1", "issue_1"])
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("issue_ids",)
    assert "duplicate issue_id 'issue_1'" in str(errors[0]["msg"])


# 19. test_question_result_rejects_duplicate_blocking_issue_ids
def test_question_result_rejects_duplicate_blocking_issue_ids() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _synthetic_question_result(issue_ids=["issue_1"], blocking_issue_ids=["issue_1", "issue_1"])
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("blocking_issue_ids",)
    assert "duplicate blocking_issue_id 'issue_1'" in str(errors[0]["msg"])


# 20. test_question_result_rejects_blocking_id_not_in_issue_ids
def test_question_result_rejects_blocking_id_not_in_issue_ids() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _synthetic_question_result(issue_ids=["issue_1"], blocking_issue_ids=["issue_2"])
    errors = exc_info.value.errors()
    assert "blocking_issue_ids must be a subset of issue_ids" in str(errors[0]["msg"])


# 21. test_valid_publication_report
def test_valid_publication_report() -> None:
    issue_info = _synthetic_issue(
        issue_id="issue_1",
        severity=PublicationIssueSeverity.INFO,
        question_id="question_1",
    )
    q_result = _synthetic_question_result(
        question_id="question_1",
        selected_content_revision_id="revision_1",
        issue_ids=["issue_1"],
        blocking_issue_ids=[],
    )
    report = PublicationValidationReport(
        catalog_id="catalog_1",
        catalog_version=1,
        registry_id="registry_1",
        registry_version=1,
        target_locale="en-US",
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
        question_results=[q_result],
        issues=[issue_info],
    )
    assert report.catalog_id == "catalog_1"
    assert len(report.question_results) == 1
    assert len(report.issues) == 1
    assert report.ready_for_publication is True


# 22. test_report_rejects_naive_checked_at
def test_report_rejects_naive_checked_at() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationReport(
            catalog_id="catalog_1",
            catalog_version=1,
            registry_id="registry_1",
            registry_version=1,
            target_locale="en-US",
            checked_at=NAIVE_TIME,
            validator_version="v0.1.0",
        )
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("checked_at",)
    assert "timezone-aware" in str(errors[0]["msg"])


# 23. test_report_rejects_non_utc_checked_at
def test_report_rejects_non_utc_checked_at() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationReport(
            catalog_id="catalog_1",
            catalog_version=1,
            registry_id="registry_1",
            registry_version=1,
            target_locale="en-US",
            checked_at=NON_UTC_TIME,
            validator_version="v0.1.0",
        )
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("checked_at",)
    assert "UTC offset" in str(errors[0]["msg"])


# 24. test_report_rejects_duplicate_issue_ids
def test_report_rejects_duplicate_issue_ids() -> None:
    issue_1 = _synthetic_issue(issue_id="issue_1")
    issue_1_dup = _synthetic_issue(issue_id="issue_1")
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationReport(
            catalog_id="catalog_1",
            catalog_version=1,
            registry_id="registry_1",
            registry_version=1,
            target_locale="en-US",
            checked_at=UTC_TIME,
            validator_version="v0.1.0",
            issues=[issue_1, issue_1_dup],
        )
    errors = exc_info.value.errors()
    assert "duplicate issue id 'issue_1' in report" in str(errors[0]["msg"])


# 25. test_report_rejects_duplicate_question_results
def test_report_rejects_duplicate_question_results() -> None:
    q1 = _synthetic_question_result(question_id="question_1")
    q1_dup = _synthetic_question_result(question_id="question_1")
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationReport(
            catalog_id="catalog_1",
            catalog_version=1,
            registry_id="registry_1",
            registry_version=1,
            target_locale="en-US",
            checked_at=UTC_TIME,
            validator_version="v0.1.0",
            question_results=[q1, q1_dup],
        )
    errors = exc_info.value.errors()
    assert "duplicate question_id 'question_1' in question_results" in str(errors[0]["msg"])


# 26. test_report_rejects_unknown_question_issue_id
def test_report_rejects_unknown_question_issue_id() -> None:
    q1 = _synthetic_question_result(question_id="question_1", issue_ids=["issue_unknown"])
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationReport(
            catalog_id="catalog_1",
            catalog_version=1,
            registry_id="registry_1",
            registry_version=1,
            target_locale="en-US",
            checked_at=UTC_TIME,
            validator_version="v0.1.0",
            question_results=[q1],
            issues=[],
        )
    errors = exc_info.value.errors()
    assert "references unknown issue_id 'issue_unknown'" in str(errors[0]["msg"])


# 28. test_report_rejects_nonblocking_issue_in_blocking_ids
def test_report_rejects_nonblocking_issue_in_blocking_ids() -> None:
    issue_info = _synthetic_issue(
        issue_id="issue_1",
        severity=PublicationIssueSeverity.INFO,
        question_id="question_1",
    )
    q1 = _synthetic_question_result(
        question_id="question_1",
        issue_ids=["issue_1"],
        blocking_issue_ids=["issue_1"],
    )
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationReport(
            catalog_id="catalog_1",
            catalog_version=1,
            registry_id="registry_1",
            registry_version=1,
            target_locale="en-US",
            checked_at=UTC_TIME,
            validator_version="v0.1.0",
            question_results=[q1],
            issues=[issue_info],
        )
    errors = exc_info.value.errors()
    assert "blocking_issue_ids" in str(errors[0]["msg"])


# 29. test_report_rejects_missing_blocking_issue_reference
def test_report_rejects_missing_blocking_issue_reference() -> None:
    issue_err = _synthetic_issue(
        issue_id="issue_1",
        severity=PublicationIssueSeverity.ERROR,
        question_id="question_1",
    )
    q1 = _synthetic_question_result(
        question_id="question_1",
        issue_ids=["issue_1"],
        blocking_issue_ids=[],
    )
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationReport(
            catalog_id="catalog_1",
            catalog_version=1,
            registry_id="registry_1",
            registry_version=1,
            target_locale="en-US",
            checked_at=UTC_TIME,
            validator_version="v0.1.0",
            question_results=[q1],
            issues=[issue_err],
        )
    errors = exc_info.value.errors()
    assert "does not match expected blocking issues" in str(errors[0]["msg"])


# 30. test_report_rejects_issue_linked_to_different_question
def test_report_rejects_issue_linked_to_different_question() -> None:
    issue_q1 = _synthetic_issue(
        issue_id="issue_1",
        severity=PublicationIssueSeverity.INFO,
        question_id="question_1",
    )
    q2 = _synthetic_question_result(
        question_id="question_2",
        issue_ids=["issue_1"],
        blocking_issue_ids=[],
    )
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationReport(
            catalog_id="catalog_1",
            catalog_version=1,
            registry_id="registry_1",
            registry_version=1,
            target_locale="en-US",
            checked_at=UTC_TIME,
            validator_version="v0.1.0",
            question_results=[q2],
            issues=[issue_q1],
        )
    errors = exc_info.value.errors()
    assert "belongs to question_id 'question_1'" in str(errors[0]["msg"])


# 31. test_report_rejects_report_level_issue_linked_to_question_result
def test_report_rejects_report_level_issue_linked_to_question_result() -> None:
    report_issue = _synthetic_issue(
        issue_id="issue_report",
        severity=PublicationIssueSeverity.INFO,
        question_id=None,
    )
    q1 = _synthetic_question_result(
        question_id="question_1",
        issue_ids=["issue_report"],
        blocking_issue_ids=[],
    )
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationReport(
            catalog_id="catalog_1",
            catalog_version=1,
            registry_id="registry_1",
            registry_version=1,
            target_locale="en-US",
            checked_at=UTC_TIME,
            validator_version="v0.1.0",
            question_results=[q1],
            issues=[report_issue],
        )
    errors = exc_info.value.errors()
    assert "report-level issue 'issue_report' (question_id=None) cannot be linked" in str(
        errors[0]["msg"]
    )


# 32. test_report_rejects_result_locale_different_from_report
def test_report_rejects_result_locale_different_from_report() -> None:
    q1 = _synthetic_question_result(question_id="question_1", target_locale="tr-TR")
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationReport(
            catalog_id="catalog_1",
            catalog_version=1,
            registry_id="registry_1",
            registry_version=1,
            target_locale="en-US",
            checked_at=UTC_TIME,
            validator_version="v0.1.0",
            question_results=[q1],
            issues=[],
        )
    errors = exc_info.value.errors()
    assert "does not match report target_locale 'en-US'" in str(errors[0]["msg"])


# 33. test_report_not_ready_without_question_results
def test_report_not_ready_without_question_results() -> None:
    report = PublicationValidationReport(
        catalog_id="catalog_1",
        catalog_version=1,
        registry_id="registry_1",
        registry_version=1,
        target_locale="en-US",
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
        question_results=[],
        issues=[],
    )
    assert report.ready_for_publication is False


# 34. test_report_ready_with_warning_only
def test_report_ready_with_warning_only() -> None:
    issue_warn = _synthetic_issue(
        issue_id="issue_1",
        severity=PublicationIssueSeverity.WARNING,
        question_id="question_1",
    )
    q1 = _synthetic_question_result(
        question_id="question_1",
        selected_content_revision_id="revision_1",
        issue_ids=["issue_1"],
        blocking_issue_ids=[],
    )
    report = PublicationValidationReport(
        catalog_id="catalog_1",
        catalog_version=1,
        registry_id="registry_1",
        registry_version=1,
        target_locale="en-US",
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
        question_results=[q1],
        issues=[issue_warn],
    )
    assert report.ready_for_publication is True


# 35. test_report_not_ready_with_error
def test_report_not_ready_with_error() -> None:
    issue_err = _synthetic_issue(
        issue_id="issue_1",
        severity=PublicationIssueSeverity.ERROR,
        question_id=None,
    )
    report = PublicationValidationReport(
        catalog_id="catalog_1",
        catalog_version=1,
        registry_id="registry_1",
        registry_version=1,
        target_locale="en-US",
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
        question_results=[],
        issues=[issue_err],
    )
    assert report.ready_for_publication is False


# 36. test_report_not_ready_when_one_question_is_not_ready
def test_report_not_ready_when_one_question_is_not_ready() -> None:
    q1 = _synthetic_question_result(question_id="question_1", selected_content_revision_id="rev_1")
    q2 = _synthetic_question_result(question_id="question_2", selected_content_revision_id=None)
    report = PublicationValidationReport(
        catalog_id="catalog_1",
        catalog_version=1,
        registry_id="registry_1",
        registry_version=1,
        target_locale="en-US",
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
        question_results=[q1, q2],
        issues=[],
    )
    assert report.ready_for_publication is False


# 37. test_report_ready_when_all_questions_are_ready
def test_report_ready_when_all_questions_are_ready() -> None:
    q1 = _synthetic_question_result(question_id="question_1", selected_content_revision_id="rev_1")
    q2 = _synthetic_question_result(question_id="question_2", selected_content_revision_id="rev_2")
    report = PublicationValidationReport(
        catalog_id="catalog_1",
        catalog_version=1,
        registry_id="registry_1",
        registry_version=1,
        target_locale="en-US",
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
        question_results=[q1, q2],
        issues=[],
    )
    assert report.ready_for_publication is True


# 38. test_report_rejects_external_ready_for_publication_value
def test_report_rejects_external_ready_for_publication_value() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PublicationValidationReport(
            catalog_id="catalog_1",
            catalog_version=1,
            registry_id="registry_1",
            registry_version=1,
            target_locale="en-US",
            checked_at=UTC_TIME,
            validator_version="v0.1.0",
            question_results=[],
            issues=[],
            ready_for_publication=True,  # type: ignore[call-arg]
        )
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("ready_for_publication",)


# 39. test_report_serializes_computed_readiness
def test_report_serializes_computed_readiness() -> None:
    report = PublicationValidationReport(
        catalog_id="catalog_1",
        catalog_version=1,
        registry_id="registry_1",
        registry_version=1,
        target_locale="en-US",
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
        question_results=[],
        issues=[],
    )
    assert report.model_dump()["ready_for_publication"] is False
    assert '"ready_for_publication":false' in report.model_dump_json().replace(" ", "")


# 40. test_publication_models_json_round_trip
def test_publication_models_json_round_trip() -> None:
    catalog = _synthetic_catalog()
    registry = _synthetic_registry()
    request = PublicationValidationRequest(
        catalog=catalog,
        registry=registry,
        target_locale="en-US",
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
    )
    request_payload = request.model_dump(mode="json")
    request_reloaded = PublicationValidationRequest.model_validate(request_payload)
    assert request_reloaded == request

    issue = _synthetic_issue()
    issue_payload = issue.model_dump(mode="json")
    issue_payload.pop("blocking", None)
    issue_reloaded = PublicationIssue.model_validate(issue_payload)
    assert issue_reloaded == issue

    q_res = _synthetic_question_result()
    q_res_payload = q_res.model_dump(mode="json")
    q_res_payload.pop("ready_for_publication", None)
    q_res_reloaded = QuestionPublicationResult.model_validate(q_res_payload)
    assert q_res_reloaded == q_res

    report = PublicationValidationReport(
        catalog_id="catalog_1",
        catalog_version=1,
        registry_id="registry_1",
        registry_version=1,
        target_locale="en-US",
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
        question_results=[q_res],
        issues=[issue],
    )
    report_payload = report.model_dump(mode="json")
    report_payload.pop("ready_for_publication", None)
    for q_item in report_payload.get("question_results", []):
        q_item.pop("ready_for_publication", None)
    for issue_item in report_payload.get("issues", []):
        issue_item.pop("blocking", None)
    report_reloaded = PublicationValidationReport.model_validate(report_payload)
    assert report_reloaded == report


# 41. test_publication_models_reject_unexpected_fields
def test_publication_models_reject_unexpected_fields() -> None:
    with pytest.raises(ValidationError) as exc_info_issue:
        PublicationIssue(
            id="issue_1",
            code=PublicationIssueCode.NO_APPROVED_QUESTIONS,
            severity=PublicationIssueSeverity.ERROR,
            object_type=PublicationObjectType.QUESTION_CATALOG,
            object_id="catalog_1",
            message="Test message",
            extra_field="invalid",  # type: ignore[call-arg]
        )
    assert exc_info_issue.value.errors()[0]["loc"] == ("extra_field",)

    with pytest.raises(ValidationError) as exc_info_res:
        QuestionPublicationResult(
            question_id="question_1",
            target_locale="en-US",
            extra_field="invalid",  # type: ignore[call-arg]
        )
    assert exc_info_res.value.errors()[0]["loc"] == ("extra_field",)

    with pytest.raises(ValidationError) as exc_info_rep:
        PublicationValidationReport(
            catalog_id="catalog_1",
            catalog_version=1,
            registry_id="registry_1",
            registry_version=1,
            target_locale="en-US",
            checked_at=UTC_TIME,
            validator_version="v0.1.0",
            extra_field="invalid",  # type: ignore[call-arg]
        )
    assert exc_info_rep.value.errors()[0]["loc"] == ("extra_field",)
