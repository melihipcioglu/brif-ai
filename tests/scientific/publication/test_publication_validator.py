"""Unit tests for full publication validation composition service."""

from datetime import datetime, timezone

import brif_ai.scientific.publication
from brif_ai.conversation.models import (
    AnswerType,
    ConversationModule,
    FulfillmentPolicy,
    InformationTargetDefinition,
    QuestionCatalog,
    QuestionDefinition,
    QuestionStatus,
)
from brif_ai.scientific.models import (
    AdaptationType,
    ClaimScope,
    ConstructDefinition,
    ContentEvaluationRecord,
    ContentRevisionStatus,
    EvaluationResult,
    EvaluationType,
    EvidenceRelation,
    ExpertReviewRecord,
    IdentifierType,
    QuestionContentRevision,
    QuestionEvidenceLink,
    ReviewArea,
    ReviewDecision,
    ScientificContentRegistry,
    ScientificSource,
    SourceType,
    UsagePermissionStatus,
)
from brif_ai.scientific.publication import (
    PublicationValidationReport,
    PublicationValidationRequest,
    run_publication_preflight,
    validate_publication,
)
from brif_ai.scientific.publication.common import PublicationIssueCode

UTC_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)  # noqa: UP017


def _rebuild_catalog(catalog: QuestionCatalog, **updates: object) -> QuestionCatalog:
    data = catalog.model_dump()
    data.update(updates)
    return QuestionCatalog.model_validate(data)


def _rebuild_registry(
    registry: ScientificContentRegistry, **updates: object
) -> ScientificContentRegistry:
    data = registry.model_dump()
    data.update(updates)
    return ScientificContentRegistry.model_validate(data)


def _rebuild_request(
    request: PublicationValidationRequest, **updates: object
) -> PublicationValidationRequest:
    data = request.model_dump()
    data.update(updates)
    return PublicationValidationRequest.model_validate(data)


def _rebuild_question(question: QuestionDefinition, **updates: object) -> QuestionDefinition:
    data = question.model_dump()
    data.update(updates)
    return QuestionDefinition.model_validate(data)


def _rebuild_construct(construct: ConstructDefinition, **updates: object) -> ConstructDefinition:
    data = construct.model_dump()
    data.update(updates)
    return ConstructDefinition.model_validate(data)


def _make_clean_baseline(
    question_id: str = "q1",
    target_id: str = "target_1",
    locale: str = "tr-TR",
    catalog_id: str = "catalog_1",
    registry_id: str = "registry_1",
    catalog_version: int = 1,
) -> tuple[QuestionCatalog, ScientificContentRegistry, PublicationValidationRequest]:
    target = InformationTargetDefinition(
        id=target_id,
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="Target purpose",
        required=True,
        fulfillment_policy=FulfillmentPolicy.VALID_ANSWER,
    )
    question = QuestionDefinition(
        id=question_id,
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="Question purpose",
        content_key=f"question.{question_id}",
        answer_type=AnswerType.FREE_TEXT,
        required=True,
        output_target_ids=[target_id],
        allowed_follow_up_question_ids=[],
        applicable_stakeholder_roles=["owner"],
        display_order=1,
        source_metadata="source metadata",
        status=QuestionStatus.APPROVED,
        options=[],
    )
    catalog = QuestionCatalog(
        id=catalog_id,
        schema_version="v0",
        catalog_version=catalog_version,
        modules=[ConversationModule.PROJECT_CONTEXT],
        information_targets=[target],
        questions=[question],
        transition_rules=[],
    )
    source = ScientificSource(
        id="source_1",
        source_type=SourceType.VALIDATED_INSTRUMENT,
        title="Source title",
        authors=["Author One"],
        publication_year=2025,
        publication_or_publisher="Publisher",
        identifier_type=IdentifierType.NONE,
        citation_text="Citation text",
        language="tr",
        usage_permission_status=UsagePermissionStatus.OPEN,
    )
    construct = ConstructDefinition(
        id="construct_1",
        name="Construct name",
        definition="Construct definition",
        conversation_module=ConversationModule.PROJECT_CONTEXT,
        architectural_relevance="Relevance",
        expected_output_target_ids=[target_id],
    )
    revision = QuestionContentRevision(
        id="rev1",
        question_id=question_id,
        locale=locale,
        revision=1,
        content_key=f"question.{question_id}",
        wording="Question wording",
        status=ContentRevisionStatus.APPROVED,
        created_at=UTC_TIME,
    )
    link = QuestionEvidenceLink(
        id="link1",
        question_content_revision_id="rev1",
        construct_ids=["construct_1"],
        source_ids=["source_1"],
        evidence_relation=EvidenceRelation.QUESTION_WORDING_BASIS,
        claim_scope=ClaimScope.VALIDATED_ITEM,
        rationale="Rationale",
        source_locator="Page 1",
        adaptation_type=AdaptationType.ORIGINAL,
        target_locale=locale,
    )
    registry = ScientificContentRegistry(
        id=registry_id,
        schema_version="v0",
        registry_version=1,
        question_catalog_id=catalog_id,
        question_catalog_version=catalog_version,
        content_bundle_version=1,
        created_at=UTC_TIME,
        sources=[source],
        constructs=[construct],
        question_content_revisions=[revision],
        evidence_links=[link],
        expert_reviews=[],
        evaluations=[],
    )
    request = PublicationValidationRequest(
        catalog=catalog,
        registry=registry,
        target_locale=locale,
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
    )
    return catalog, registry, request


# 1. test_validate_publication_clean_single_question_is_ready
def test_validate_publication_clean_single_question_is_ready() -> None:
    _, _, request = _make_clean_baseline()
    report = validate_publication(request)

    assert isinstance(report, PublicationValidationReport)
    assert len(report.question_results) == 1
    res = report.question_results[0]
    assert res.question_id == "q1"
    assert res.selected_content_revision_id == "rev1"
    assert res.issue_ids == []
    assert res.blocking_issue_ids == []
    assert res.ready_for_publication is True
    assert report.issues == []
    assert report.ready_for_publication is True


# 2. test_validate_publication_warning_only_question_remains_ready
def test_validate_publication_warning_only_question_remains_ready() -> None:
    catalog, registry, request = _make_clean_baseline()
    e1 = ContentEvaluationRecord(
        id="e1",
        question_content_revision_id="rev1",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.PASSED_WITH_NOTES,
        summary="Summary",
        identified_issues=["Note 1"],
        revision_required=False,
    )
    new_registry = _rebuild_registry(registry, evaluations=[e1])
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    assert len(report.question_results) == 1
    res = report.question_results[0]
    assert len(res.issue_ids) == 1
    assert res.blocking_issue_ids == []
    assert res.ready_for_publication is True
    assert report.ready_for_publication is True
    assert report.issues[0].code is PublicationIssueCode.EVALUATION_PASSED_WITH_NOTES


# 3. test_validate_publication_blocking_question_is_not_ready
def test_validate_publication_blocking_question_is_not_ready() -> None:
    catalog, registry, request = _make_clean_baseline()
    e1 = ContentEvaluationRecord(
        id="e1",
        question_content_revision_id="rev1",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.REVISION_REQUIRED,
        summary="Summary",
        identified_issues=["Fix wording"],
        revision_required=True,
    )
    new_registry = _rebuild_registry(registry, evaluations=[e1])
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    assert len(report.question_results) == 1
    res = report.question_results[0]
    assert len(res.blocking_issue_ids) == 1
    assert res.ready_for_publication is False
    assert report.ready_for_publication is False


# 4. test_validate_publication_missing_selected_revision_is_not_ready
def test_validate_publication_missing_selected_revision_is_not_ready() -> None:
    catalog, registry, request = _make_clean_baseline()
    new_registry = _rebuild_registry(
        registry,
        question_content_revisions=[],
        evidence_links=[],
        expert_reviews=[],
        evaluations=[],
    )
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    assert len(report.question_results) == 1
    res = report.question_results[0]
    assert res.selected_content_revision_id is None
    assert len(res.blocking_issue_ids) == 1
    assert res.ready_for_publication is False
    assert report.ready_for_publication is False
    assert report.issues[0].code is PublicationIssueCode.APPROVED_CONTENT_REVISION_MISSING


# 5. test_validate_publication_missing_revision_skips_downstream_diagnostics
def test_validate_publication_missing_revision_skips_downstream_diagnostics() -> None:
    catalog, registry, request = _make_clean_baseline()
    new_registry = _rebuild_registry(
        registry,
        question_content_revisions=[],
        evidence_links=[],
        expert_reviews=[],
        evaluations=[],
    )
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    issue_codes = [issue.code for issue in report.issues]
    assert issue_codes == [PublicationIssueCode.APPROVED_CONTENT_REVISION_MISSING]


# 6. test_validate_publication_two_questions_preserve_approved_order
def test_validate_publication_two_questions_preserve_approved_order() -> None:
    catalog, registry, request = _make_clean_baseline("q1")
    q2 = QuestionDefinition(
        id="q2",
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="Purpose 2",
        content_key="question.q2",
        answer_type=AnswerType.FREE_TEXT,
        required=True,
        output_target_ids=["target_1"],
        allowed_follow_up_question_ids=[],
        applicable_stakeholder_roles=["owner"],
        display_order=2,
        source_metadata="meta",
        status=QuestionStatus.APPROVED,
        options=[],
    )
    rev2 = QuestionContentRevision(
        id="rev2",
        question_id="q2",
        locale="tr-TR",
        revision=1,
        content_key="question.q2",
        wording="Wording 2",
        status=ContentRevisionStatus.APPROVED,
        created_at=UTC_TIME,
    )
    link2 = QuestionEvidenceLink(
        id="link2",
        question_content_revision_id="rev2",
        construct_ids=["construct_1"],
        source_ids=["source_1"],
        evidence_relation=EvidenceRelation.QUESTION_WORDING_BASIS,
        claim_scope=ClaimScope.VALIDATED_ITEM,
        rationale="Rationale 2",
        source_locator="Page 2",
        adaptation_type=AdaptationType.ORIGINAL,
        target_locale="tr-TR",
    )

    new_catalog = _rebuild_catalog(catalog, questions=[q2, catalog.questions[0]])
    new_registry = _rebuild_registry(
        registry,
        question_content_revisions=[registry.question_content_revisions[0], rev2],
        evidence_links=[registry.evidence_links[0], link2],
    )
    new_request = _rebuild_request(request, catalog=new_catalog, registry=new_registry)

    report = validate_publication(new_request)
    assert len(report.question_results) == 2
    assert report.question_results[0].question_id == "q1"
    assert report.question_results[1].question_id == "q2"


# 7. test_validate_publication_maps_only_matching_question_issues
def test_validate_publication_maps_only_matching_question_issues() -> None:
    catalog, registry, request = _make_clean_baseline("q1")
    q2 = QuestionDefinition(
        id="q2",
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="Purpose 2",
        content_key="question.q2",
        answer_type=AnswerType.FREE_TEXT,
        required=True,
        output_target_ids=["target_1"],
        allowed_follow_up_question_ids=[],
        applicable_stakeholder_roles=["owner"],
        display_order=2,
        source_metadata="meta",
        status=QuestionStatus.APPROVED,
        options=[],
    )
    rev2 = QuestionContentRevision(
        id="rev2",
        question_id="q2",
        locale="tr-TR",
        revision=1,
        content_key="question.q2",
        wording="Wording 2",
        status=ContentRevisionStatus.APPROVED,
        created_at=UTC_TIME,
    )
    link2 = QuestionEvidenceLink(
        id="link2",
        question_content_revision_id="rev2",
        construct_ids=["construct_1"],
        source_ids=["source_1"],
        evidence_relation=EvidenceRelation.QUESTION_WORDING_BASIS,
        claim_scope=ClaimScope.VALIDATED_ITEM,
        rationale="Rationale 2",
        source_locator="Page 2",
        adaptation_type=AdaptationType.ORIGINAL,
        target_locale="tr-TR",
    )
    e1 = ContentEvaluationRecord(
        id="e1",
        question_content_revision_id="rev1",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.PASSED_WITH_NOTES,
        summary="Summary",
        identified_issues=["Note 1"],
        revision_required=False,
    )
    e2 = ContentEvaluationRecord(
        id="e2",
        question_content_revision_id="rev2",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.REVISION_REQUIRED,
        summary="Summary 2",
        identified_issues=["Fix clause"],
        revision_required=True,
    )

    new_catalog = _rebuild_catalog(catalog, questions=[catalog.questions[0], q2])
    new_registry = _rebuild_registry(
        registry,
        question_content_revisions=[registry.question_content_revisions[0], rev2],
        evidence_links=[registry.evidence_links[0], link2],
        evaluations=[e1, e2],
    )
    new_request = _rebuild_request(request, catalog=new_catalog, registry=new_registry)

    report = validate_publication(new_request)
    assert len(report.question_results) == 2
    res1 = report.question_results[0]
    res2 = report.question_results[1]

    assert res1.question_id == "q1"
    assert len(res1.issue_ids) == 1
    assert res1.blocking_issue_ids == []

    assert res2.question_id == "q2"
    assert len(res2.blocking_issue_ids) == 1


# 8. test_validate_publication_one_blocked_question_blocks_report
def test_validate_publication_one_blocked_question_blocks_report() -> None:
    catalog, registry, request = _make_clean_baseline("q1")
    q2 = QuestionDefinition(
        id="q2",
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="Purpose 2",
        content_key="question.q2",
        answer_type=AnswerType.FREE_TEXT,
        required=True,
        output_target_ids=["target_1"],
        allowed_follow_up_question_ids=[],
        applicable_stakeholder_roles=["owner"],
        display_order=2,
        source_metadata="meta",
        status=QuestionStatus.APPROVED,
        options=[],
    )
    rev2 = QuestionContentRevision(
        id="rev2",
        question_id="q2",
        locale="tr-TR",
        revision=1,
        content_key="question.q2",
        wording="Wording 2",
        status=ContentRevisionStatus.APPROVED,
        created_at=UTC_TIME,
    )
    link2 = QuestionEvidenceLink(
        id="link2",
        question_content_revision_id="rev2",
        construct_ids=["construct_1"],
        source_ids=["source_1"],
        evidence_relation=EvidenceRelation.QUESTION_WORDING_BASIS,
        claim_scope=ClaimScope.VALIDATED_ITEM,
        rationale="Rationale 2",
        source_locator="Page 2",
        adaptation_type=AdaptationType.ORIGINAL,
        target_locale="tr-TR",
    )
    e2 = ContentEvaluationRecord(
        id="e2",
        question_content_revision_id="rev2",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.REVISION_REQUIRED,
        summary="Summary 2",
        identified_issues=["Fix clause"],
        revision_required=True,
    )

    new_catalog = _rebuild_catalog(catalog, questions=[catalog.questions[0], q2])
    new_registry = _rebuild_registry(
        registry,
        question_content_revisions=[registry.question_content_revisions[0], rev2],
        evidence_links=[registry.evidence_links[0], link2],
        evaluations=[e2],
    )
    new_request = _rebuild_request(request, catalog=new_catalog, registry=new_registry)

    report = validate_publication(new_request)
    assert report.question_results[0].ready_for_publication is True
    assert report.question_results[1].ready_for_publication is False
    assert report.ready_for_publication is False


# 9. test_validate_publication_binding_id_mismatch_short_circuits
def test_validate_publication_binding_id_mismatch_short_circuits() -> None:
    catalog, registry, request = _make_clean_baseline()
    new_registry = _rebuild_registry(registry, question_catalog_id="other_catalog")
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    assert report.question_results == []
    assert len(report.issues) == 1
    assert report.issues[0].code is PublicationIssueCode.REGISTRY_CATALOG_ID_MISMATCH
    assert report.ready_for_publication is False


# 10. test_validate_publication_binding_version_mismatch_short_circuits
def test_validate_publication_binding_version_mismatch_short_circuits() -> None:
    catalog, registry, request = _make_clean_baseline()
    new_registry = _rebuild_registry(registry, question_catalog_version=99)
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    assert report.question_results == []
    assert len(report.issues) == 1
    assert report.issues[0].code is PublicationIssueCode.REGISTRY_CATALOG_VERSION_MISMATCH
    assert report.ready_for_publication is False


# 11. test_validate_publication_both_binding_mismatches_have_global_ids
def test_validate_publication_both_binding_mismatches_have_global_ids() -> None:
    catalog, registry, request = _make_clean_baseline()
    new_registry = _rebuild_registry(
        registry, question_catalog_id="other_catalog", question_catalog_version=99
    )
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    assert report.question_results == []
    assert len(report.issues) == 2
    assert report.issues[0].id == "publication_issue_0001"
    assert report.issues[1].id == "publication_issue_0002"


# 12. test_validate_publication_no_approved_questions_returns_empty_results
def test_validate_publication_no_approved_questions_returns_empty_results() -> None:
    catalog, registry, request = _make_clean_baseline()
    q_draft = _rebuild_question(catalog.questions[0], status=QuestionStatus.DRAFT)
    new_catalog = _rebuild_catalog(catalog, questions=[q_draft])
    new_request = _rebuild_request(request, catalog=new_catalog)

    report = validate_publication(new_request)
    assert report.question_results == []
    assert len(report.issues) == 1
    assert report.issues[0].code is PublicationIssueCode.NO_APPROVED_QUESTIONS
    assert report.ready_for_publication is False


# 13. test_validate_publication_registry_unknown_question_short_circuits
def test_validate_publication_registry_unknown_question_short_circuits() -> None:
    catalog, registry, request = _make_clean_baseline()
    rev_unknown = QuestionContentRevision(
        id="rev_unk",
        question_id="unknown_question",
        locale="tr-TR",
        revision=1,
        content_key="question.unknown",
        wording="Wording unknown",
        status=ContentRevisionStatus.APPROVED,
        created_at=UTC_TIME,
    )
    new_registry = _rebuild_registry(
        registry,
        question_content_revisions=[
            registry.question_content_revisions[0],
            rev_unknown,
        ],
    )
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    assert report.question_results == []
    assert len(report.issues) == 1
    assert report.issues[0].code is PublicationIssueCode.REGISTRY_QUESTION_NOT_FOUND_IN_CATALOG
    assert report.ready_for_publication is False


# 14. test_validate_publication_construct_target_error_short_circuits_safely
def test_validate_publication_construct_target_error_short_circuits_safely() -> None:
    catalog, registry, request = _make_clean_baseline()
    c_bad = _rebuild_construct(
        registry.constructs[0], expected_output_target_ids=["non_existent_target"]
    )
    new_registry = _rebuild_registry(registry, constructs=[c_bad])
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    assert report.question_results == []
    assert len(report.issues) == 1
    assert report.issues[0].code is PublicationIssueCode.CONSTRUCT_OUTPUT_TARGET_NOT_FOUND
    assert report.ready_for_publication is False


# 15. test_validate_publication_finalizes_all_stage_drafts_once
def test_validate_publication_finalizes_all_stage_drafts_once() -> None:
    catalog, registry, request = _make_clean_baseline()
    e1 = ContentEvaluationRecord(
        id="e1",
        question_content_revision_id="rev1",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.PASSED_WITH_NOTES,
        summary="Summary",
        identified_issues=["Note 1"],
        revision_required=False,
    )
    new_registry = _rebuild_registry(registry, evaluations=[e1])
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    assert len(report.issues) == 1
    assert report.issues[0].id == "publication_issue_0001"


# 16. test_validate_publication_issue_ids_are_globally_deterministic
def test_validate_publication_issue_ids_are_globally_deterministic() -> None:
    catalog, registry, request = _make_clean_baseline()
    e1 = ContentEvaluationRecord(
        id="e1",
        question_content_revision_id="rev1",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.PASSED_WITH_NOTES,
        summary="Summary 1",
        identified_issues=["Note 1"],
        revision_required=False,
    )
    e2 = ContentEvaluationRecord(
        id="e2",
        question_content_revision_id="rev1",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.REVISION_REQUIRED,
        summary="Summary 2",
        identified_issues=["Fix issue"],
        revision_required=True,
    )
    new_registry = _rebuild_registry(registry, evaluations=[e1, e2])
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    assert len(report.issues) == 2
    assert report.issues[0].id == "publication_issue_0001"
    assert report.issues[1].id == "publication_issue_0002"


# 17. test_validate_publication_question_issue_ids_preserve_final_issue_order
def test_validate_publication_question_issue_ids_preserve_final_issue_order() -> None:
    catalog, registry, request = _make_clean_baseline()
    e1 = ContentEvaluationRecord(
        id="e1",
        question_content_revision_id="rev1",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.PASSED_WITH_NOTES,
        summary="Summary 1",
        identified_issues=["Note 1"],
        revision_required=False,
    )
    e2 = ContentEvaluationRecord(
        id="e2",
        question_content_revision_id="rev1",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.REVISION_REQUIRED,
        summary="Summary 2",
        identified_issues=["Fix issue"],
        revision_required=True,
    )
    new_registry = _rebuild_registry(registry, evaluations=[e1, e2])
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    res = report.question_results[0]
    final_issue_ids_list = [issue.id for issue in report.issues]
    assert res.issue_ids == final_issue_ids_list


# 18. test_validate_publication_blocking_ids_match_blocking_subset_in_order
def test_validate_publication_blocking_ids_match_blocking_subset_in_order() -> None:
    catalog, registry, request = _make_clean_baseline()
    e1 = ContentEvaluationRecord(
        id="e1",
        question_content_revision_id="rev1",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.PASSED_WITH_NOTES,
        summary="Summary 1",
        identified_issues=["Note 1"],
        revision_required=False,
    )
    e2 = ContentEvaluationRecord(
        id="e2",
        question_content_revision_id="rev1",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.REVISION_REQUIRED,
        summary="Summary 2",
        identified_issues=["Fix issue"],
        revision_required=True,
    )
    new_registry = _rebuild_registry(registry, evaluations=[e1, e2])
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    res = report.question_results[0]

    blocking_subset = [issue.id for issue in report.issues if issue.severity.is_blocking]
    assert res.blocking_issue_ids == blocking_subset


# 19. test_validate_publication_uses_request_metadata_exactly
def test_validate_publication_uses_request_metadata_exactly() -> None:
    catalog, registry, request = _make_clean_baseline()
    report = validate_publication(request)

    assert report.catalog_id == request.catalog.id
    assert report.catalog_version == request.catalog.catalog_version
    assert report.registry_id == request.registry.id
    assert report.registry_version == request.registry.registry_version
    assert report.target_locale == request.target_locale
    assert report.checked_at == request.checked_at
    assert report.validator_version == request.validator_version


# 20. test_validate_publication_does_not_mutate_request
def test_validate_publication_does_not_mutate_request() -> None:
    _, _, request = _make_clean_baseline()
    dump_before = request.model_dump()
    validate_publication(request)
    dump_after = request.model_dump()
    assert dump_before == dump_after


# 21. test_validate_publication_is_deterministic
def test_validate_publication_is_deterministic() -> None:
    _, _, request = _make_clean_baseline()
    report1 = validate_publication(request)
    report2 = validate_publication(request)
    assert report1 == report2


# 22. test_validate_publication_result_serializes_computed_fields
def test_validate_publication_result_serializes_computed_fields() -> None:
    _, _, request = _make_clean_baseline()
    report = validate_publication(request)
    dumped = report.model_dump()

    assert "ready_for_publication" in dumped
    assert dumped["ready_for_publication"] is True
    assert "ready_for_publication" in dumped["question_results"][0]
    assert dumped["question_results"][0]["ready_for_publication"] is True


# 23. test_validate_publication_public_export
def test_validate_publication_public_export() -> None:
    pkg = brif_ai.scientific.publication
    assert hasattr(pkg, "validate_publication")
    assert "validate_publication" in pkg.__all__
    assert pkg.validate_publication is validate_publication


# 24. test_existing_run_publication_preflight_remains_compatible
def test_existing_run_publication_preflight_remains_compatible() -> None:
    _, _, request = _make_clean_baseline()
    res = run_publication_preflight(request)
    assert res.can_continue is True
    assert len(res.approved_questions) == 1
    assert res.issues == ()


# 25. test_validate_publication_multiple_stage_issues_for_one_question
def test_validate_publication_multiple_stage_issues_for_one_question() -> None:
    catalog, registry, request = _make_clean_baseline()
    s_req = ScientificSource(
        id="s_req",
        source_type=SourceType.VALIDATED_INSTRUMENT,
        title="Title",
        authors=["Author"],
        publication_year=2025,
        publication_or_publisher="Publisher",
        identifier_type=IdentifierType.NONE,
        citation_text="Citation",
        language="tr",
        usage_permission_status=UsagePermissionStatus.PERMISSION_REQUIRED,
    )
    link = QuestionEvidenceLink(
        id="link1",
        question_content_revision_id="rev1",
        construct_ids=["construct_1"],
        source_ids=["s_req"],
        evidence_relation=EvidenceRelation.QUESTION_WORDING_BASIS,
        claim_scope=ClaimScope.VALIDATED_ITEM,
        rationale="Rationale",
        source_locator="Page 1",
        adaptation_type=AdaptationType.ORIGINAL,
        target_locale="tr-TR",
    )
    r1 = ExpertReviewRecord(
        id="r1",
        question_content_revision_id="rev1",
        evidence_link_ids=["link1"],
        reviewer_reference="Reviewer 1",
        reviewer_role="Role 1",
        review_area=ReviewArea.ETHICS_AND_PRIVACY,
        decision=ReviewDecision.REJECTED,
        reviewed_at=UTC_TIME,
        rationale="Rejected rationale",
    )
    e1 = ContentEvaluationRecord(
        id="e1",
        question_content_revision_id="rev1",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.REVISION_REQUIRED,
        summary="Summary 1",
        identified_issues=["Fix issue"],
        revision_required=True,
    )

    new_registry = _rebuild_registry(
        registry,
        sources=[s_req],
        evidence_links=[link],
        expert_reviews=[r1],
        evaluations=[e1],
    )
    new_request = _rebuild_request(request, registry=new_registry)

    report = validate_publication(new_request)
    assert len(report.question_results) == 1
    res = report.question_results[0]
    assert len(res.issue_ids) == 3
    assert len(res.blocking_issue_ids) == 3
    assert res.ready_for_publication is False
    assert report.ready_for_publication is False

    issue_codes = [issue.code for issue in report.issues]
    assert PublicationIssueCode.SOURCE_PERMISSION_REQUIRED in issue_codes
    assert PublicationIssueCode.REVIEW_REJECTED in issue_codes
    assert PublicationIssueCode.EVALUATION_REVISION_REQUIRED in issue_codes


# 26. test_validate_publication_composes_all_six_collectors_with_one_global_finalization
def test_validate_publication_composes_all_six_collectors_with_one_global_finalization() -> None:
    target = InformationTargetDefinition(
        id="target_1",
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="Target purpose",
        required=True,
        fulfillment_policy=FulfillmentPolicy.VALID_ANSWER,
    )
    q_content = QuestionDefinition(
        id="q_content",
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="P1",
        content_key="q.content",
        answer_type=AnswerType.FREE_TEXT,
        required=True,
        output_target_ids=["target_1"],
        allowed_follow_up_question_ids=[],
        applicable_stakeholder_roles=["owner"],
        display_order=1,
        source_metadata="meta",
        status=QuestionStatus.APPROVED,
        options=[],
    )
    q_evidence = QuestionDefinition(
        id="q_evidence",
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="P2",
        content_key="q.evidence",
        answer_type=AnswerType.FREE_TEXT,
        required=True,
        output_target_ids=["target_1"],
        allowed_follow_up_question_ids=[],
        applicable_stakeholder_roles=["owner"],
        display_order=2,
        source_metadata="meta",
        status=QuestionStatus.APPROVED,
        options=[],
    )
    q_permission = QuestionDefinition(
        id="q_permission",
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="P3",
        content_key="q.permission",
        answer_type=AnswerType.FREE_TEXT,
        required=True,
        output_target_ids=["target_1"],
        allowed_follow_up_question_ids=[],
        applicable_stakeholder_roles=["owner"],
        display_order=3,
        source_metadata="meta",
        status=QuestionStatus.APPROVED,
        options=[],
    )
    q_review = QuestionDefinition(
        id="q_review",
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="P4",
        content_key="q.review",
        answer_type=AnswerType.FREE_TEXT,
        required=True,
        output_target_ids=["target_1"],
        allowed_follow_up_question_ids=[],
        applicable_stakeholder_roles=["owner"],
        display_order=4,
        source_metadata="meta",
        status=QuestionStatus.APPROVED,
        options=[],
    )
    q_evaluation = QuestionDefinition(
        id="q_evaluation",
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="P5",
        content_key="q.evaluation",
        answer_type=AnswerType.FREE_TEXT,
        required=True,
        output_target_ids=["target_1"],
        allowed_follow_up_question_ids=[],
        applicable_stakeholder_roles=["owner"],
        display_order=5,
        source_metadata="meta",
        status=QuestionStatus.APPROVED,
        options=[],
    )

    catalog = QuestionCatalog(
        id="catalog_1",
        schema_version="v0",
        catalog_version=1,
        modules=[ConversationModule.PROJECT_CONTEXT],
        information_targets=[target],
        questions=[q_content, q_evidence, q_permission, q_review, q_evaluation],
        transition_rules=[],
    )

    s_open = ScientificSource(
        id="s_open",
        source_type=SourceType.VALIDATED_INSTRUMENT,
        title="Title",
        authors=["Author"],
        publication_year=2025,
        publication_or_publisher="Publisher",
        identifier_type=IdentifierType.NONE,
        citation_text="Citation",
        language="tr",
        usage_permission_status=UsagePermissionStatus.OPEN,
    )
    s_perm = ScientificSource(
        id="s_perm",
        source_type=SourceType.VALIDATED_INSTRUMENT,
        title="Title",
        authors=["Author"],
        publication_year=2025,
        publication_or_publisher="Publisher",
        identifier_type=IdentifierType.NONE,
        citation_text="Citation",
        language="tr",
        usage_permission_status=UsagePermissionStatus.PERMISSION_REQUIRED,
    )
    construct = ConstructDefinition(
        id="construct_1",
        name="Construct",
        definition="Definition",
        conversation_module=ConversationModule.PROJECT_CONTEXT,
        architectural_relevance="Relevance",
        expected_output_target_ids=["target_1"],
    )

    rev_evidence = QuestionContentRevision(
        id="rev_evidence",
        question_id="q_evidence",
        locale="tr-TR",
        revision=1,
        content_key="q.evidence",
        wording="Wording",
        status=ContentRevisionStatus.APPROVED,
        created_at=UTC_TIME,
    )
    rev_permission = QuestionContentRevision(
        id="rev_permission",
        question_id="q_permission",
        locale="tr-TR",
        revision=1,
        content_key="q.permission",
        wording="Wording",
        status=ContentRevisionStatus.APPROVED,
        created_at=UTC_TIME,
    )
    rev_review = QuestionContentRevision(
        id="rev_review",
        question_id="q_review",
        locale="tr-TR",
        revision=1,
        content_key="q.review",
        wording="Wording",
        status=ContentRevisionStatus.APPROVED,
        created_at=UTC_TIME,
    )
    rev_evaluation = QuestionContentRevision(
        id="rev_evaluation",
        question_id="q_evaluation",
        locale="tr-TR",
        revision=1,
        content_key="q.evaluation",
        wording="Wording",
        status=ContentRevisionStatus.APPROVED,
        created_at=UTC_TIME,
    )

    link_permission = QuestionEvidenceLink(
        id="link_permission",
        question_content_revision_id="rev_permission",
        construct_ids=["construct_1"],
        source_ids=["s_perm"],
        evidence_relation=EvidenceRelation.QUESTION_WORDING_BASIS,
        claim_scope=ClaimScope.VALIDATED_ITEM,
        rationale="Rationale",
        source_locator="Page 1",
        adaptation_type=AdaptationType.ORIGINAL,
        target_locale="tr-TR",
    )
    link_review = QuestionEvidenceLink(
        id="link_review",
        question_content_revision_id="rev_review",
        construct_ids=["construct_1"],
        source_ids=["s_open"],
        evidence_relation=EvidenceRelation.QUESTION_WORDING_BASIS,
        claim_scope=ClaimScope.VALIDATED_ITEM,
        rationale="Rationale",
        source_locator="Page 1",
        adaptation_type=AdaptationType.ORIGINAL,
        target_locale="tr-TR",
    )
    link_evaluation = QuestionEvidenceLink(
        id="link_evaluation",
        question_content_revision_id="rev_evaluation",
        construct_ids=["construct_1"],
        source_ids=["s_open"],
        evidence_relation=EvidenceRelation.QUESTION_WORDING_BASIS,
        claim_scope=ClaimScope.VALIDATED_ITEM,
        rationale="Rationale",
        source_locator="Page 1",
        adaptation_type=AdaptationType.ORIGINAL,
        target_locale="tr-TR",
    )

    r_review = ExpertReviewRecord(
        id="r_review",
        question_content_revision_id="rev_review",
        evidence_link_ids=["link_review"],
        reviewer_reference="Reviewer 1",
        reviewer_role="Role 1",
        review_area=ReviewArea.ETHICS_AND_PRIVACY,
        decision=ReviewDecision.REJECTED,
        reviewed_at=UTC_TIME,
        rationale="Rejected",
    )
    e_evaluation = ContentEvaluationRecord(
        id="e_evaluation",
        question_content_revision_id="rev_evaluation",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        locale="tr-TR",
        conducted_at=UTC_TIME,
        participant_count=None,
        result=EvaluationResult.REVISION_REQUIRED,
        summary="Summary",
        identified_issues=["Fix issue"],
        revision_required=True,
    )

    registry = ScientificContentRegistry(
        id="registry_1",
        schema_version="v0",
        registry_version=1,
        question_catalog_id="catalog_1",
        question_catalog_version=1,
        content_bundle_version=1,
        created_at=UTC_TIME,
        sources=[s_open, s_perm],
        constructs=[construct],
        question_content_revisions=[rev_evidence, rev_permission, rev_review, rev_evaluation],
        evidence_links=[link_permission, link_review, link_evaluation],
        expert_reviews=[r_review],
        evaluations=[e_evaluation],
    )
    request = PublicationValidationRequest(
        catalog=catalog,
        registry=registry,
        target_locale="tr-TR",
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
    )

    report = validate_publication(request)
    assert len(report.question_results) == 5

    issue_codes = [issue.code for issue in report.issues]
    assert PublicationIssueCode.APPROVED_CONTENT_REVISION_MISSING in issue_codes
    assert PublicationIssueCode.EVIDENCE_LINK_MISSING in issue_codes
    assert PublicationIssueCode.SOURCE_PERMISSION_REQUIRED in issue_codes
    assert PublicationIssueCode.REVIEW_REJECTED in issue_codes
    assert PublicationIssueCode.EVALUATION_REVISION_REQUIRED in issue_codes

    global_ids = [issue.id for issue in report.issues]
    expected_ids = [f"publication_issue_{i:04d}" for i in range(1, len(report.issues) + 1)]
    assert global_ids == expected_ids
    assert report.ready_for_publication is False
