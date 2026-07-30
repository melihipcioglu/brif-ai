"""Unit tests for Publication Validation v0 catalog-registry preflight service."""

from datetime import datetime, timezone

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
    ConstructDefinition,
    ContentRevisionStatus,
    QuestionContentRevision,
    ScientificContentRegistry,
)
from brif_ai.scientific.publication import (
    PublicationIssueCode,
    PublicationIssueSeverity,
    PublicationObjectType,
    PublicationValidationRequest,
    run_publication_preflight,
)
from brif_ai.scientific.publication.preflight import _finalize_issues, _IssueDraft

UTC_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)  # noqa: UP017


def _make_target(target_id: str = "target_1") -> InformationTargetDefinition:
    return InformationTargetDefinition(
        id=target_id,
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="Synthetic target purpose",
        required=True,
        fulfillment_policy=FulfillmentPolicy.VALID_ANSWER,
    )


def _make_question(
    question_id: str = "question_1",
    status: QuestionStatus = QuestionStatus.APPROVED,
    display_order: int = 1,
    source_metadata: str = "synthetic source metadata",
    output_target_ids: list[str] | None = None,
    module: ConversationModule = ConversationModule.PROJECT_CONTEXT,
) -> QuestionDefinition:
    return QuestionDefinition(
        id=question_id,
        module=module,
        purpose="Synthetic question purpose",
        content_key=f"question.{question_id}",
        answer_type=AnswerType.FREE_TEXT,
        required=True,
        output_target_ids=output_target_ids or ["target_1"],
        allowed_follow_up_question_ids=[],
        applicable_stakeholder_roles=["owner"],
        display_order=display_order,
        source_metadata=source_metadata,
        status=status,
        options=[],
    )


def _make_catalog(
    catalog_id: str = "catalog_1",
    catalog_version: int = 1,
    targets: list[InformationTargetDefinition] | None = None,
    questions: list[QuestionDefinition] | None = None,
) -> QuestionCatalog:
    if targets is None:
        targets = [_make_target("target_1")]
    if questions is None:
        questions = [_make_question("question_1")]
    modules = list({t.module for t in targets} | {q.module for q in questions})
    return QuestionCatalog(
        id=catalog_id,
        schema_version="v0",
        catalog_version=catalog_version,
        modules=modules,
        information_targets=targets,
        questions=questions,
        transition_rules=[],
    )


def _make_construct(
    construct_id: str = "construct_1",
    expected_output_target_ids: list[str] | None = None,
) -> ConstructDefinition:
    return ConstructDefinition(
        id=construct_id,
        name="Synthetic Construct",
        definition="Synthetic definition for construct",
        conversation_module=ConversationModule.PROJECT_CONTEXT,
        architectural_relevance="Synthetic relevance description",
        expected_output_target_ids=expected_output_target_ids or ["target_1"],
    )


def _make_revision(
    revision_id: str = "revision_1",
    question_id: str = "question_1",
    status: ContentRevisionStatus = ContentRevisionStatus.APPROVED,
    revision_num: int = 1,
    supersedes_revision_id: str | None = None,
) -> QuestionContentRevision:
    return QuestionContentRevision(
        id=revision_id,
        question_id=question_id,
        locale="tr-TR",
        revision=revision_num,
        content_key=f"question.{question_id}",
        wording="Synthetic question wording",
        status=status,
        created_at=UTC_TIME,
        supersedes_revision_id=supersedes_revision_id,
    )


def _make_registry(
    registry_id: str = "registry_1",
    catalog_id: str = "catalog_1",
    catalog_version: int = 1,
    constructs: list[ConstructDefinition] | None = None,
    revisions: list[QuestionContentRevision] | None = None,
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
        constructs=constructs or [],
        question_content_revisions=revisions or [],
        evidence_links=[],
        expert_reviews=[],
        evaluations=[],
    )


def _make_request(
    catalog: QuestionCatalog | None = None,
    registry: ScientificContentRegistry | None = None,
    target_locale: str = "tr-TR",
) -> PublicationValidationRequest:
    return PublicationValidationRequest(
        catalog=catalog or _make_catalog(),
        registry=registry or _make_registry(),
        target_locale=target_locale,
        checked_at=UTC_TIME,
        validator_version="v0.1.0",
    )


def test_valid_preflight_returns_approved_questions() -> None:
    request = _make_request()
    result = run_publication_preflight(request)

    assert len(result.approved_questions) == 1
    assert result.approved_questions[0].id == "question_1"
    assert len(result.issues) == 0
    assert result.can_continue is True


def test_approved_questions_are_sorted_by_display_order_then_id() -> None:
    q3 = _make_question("q3", display_order=2, module=ConversationModule.PROJECT_CONTEXT)
    q1 = _make_question("q1", display_order=1, module=ConversationModule.PROJECT_CONTEXT)
    q0_a = _make_question("q0_a", display_order=1, module=ConversationModule.STAKEHOLDERS)

    catalog = _make_catalog(questions=[q3, q1, q0_a])
    request = _make_request(catalog=catalog)
    result = run_publication_preflight(request)

    ordered_ids = [q.id for q in result.approved_questions]
    assert ordered_ids == ["q0_a", "q1", "q3"]


def test_draft_and_retired_questions_are_not_candidates() -> None:
    q_approved = _make_question("q_approved", status=QuestionStatus.APPROVED, display_order=1)
    q_draft = _make_question("q_draft", status=QuestionStatus.DRAFT, display_order=2)
    q_retired = _make_question("q_retired", status=QuestionStatus.RETIRED, display_order=3)

    catalog = _make_catalog(questions=[q_approved, q_draft, q_retired])
    request = _make_request(catalog=catalog)
    result = run_publication_preflight(request)

    assert len(result.approved_questions) == 1
    assert result.approved_questions[0].id == "q_approved"


def test_no_approved_questions_returns_error() -> None:
    q_draft = _make_question("q_draft", status=QuestionStatus.DRAFT)
    catalog = _make_catalog(questions=[q_draft])
    request = _make_request(catalog=catalog)
    result = run_publication_preflight(request)

    assert len(result.approved_questions) == 0
    assert result.can_continue is False
    assert len(result.issues) == 1

    issue = result.issues[0]
    assert issue.id == "publication_issue_0001"
    assert issue.code is PublicationIssueCode.NO_APPROVED_QUESTIONS
    assert issue.severity is PublicationIssueSeverity.ERROR
    assert issue.blocking is True
    assert issue.object_type is PublicationObjectType.QUESTION_CATALOG
    assert issue.object_id == catalog.id
    assert issue.question_id is None
    assert issue.question_content_revision_id is None
    assert issue.related_object_ids == []
    assert catalog.id in issue.message


def test_catalog_id_mismatch_returns_critical_issue() -> None:
    catalog = _make_catalog(catalog_id="cat_a")
    registry = _make_registry(catalog_id="cat_b")
    request = _make_request(catalog=catalog, registry=registry)

    result = run_publication_preflight(request)

    assert result.approved_questions == ()
    assert result.can_continue is False
    assert len(result.issues) == 1

    issue = result.issues[0]
    assert issue.id == "publication_issue_0001"
    assert issue.code is PublicationIssueCode.REGISTRY_CATALOG_ID_MISMATCH
    assert issue.severity is PublicationIssueSeverity.CRITICAL
    assert issue.blocking is True
    assert issue.object_type is PublicationObjectType.SCIENTIFIC_CONTENT_REGISTRY
    assert issue.object_id == registry.id
    assert issue.question_id is None
    assert issue.question_content_revision_id is None
    assert issue.related_object_ids == ["cat_a", "cat_b"]
    assert "cat_a" in issue.message
    assert "cat_b" in issue.message


def test_catalog_version_mismatch_returns_critical_issue() -> None:
    catalog = _make_catalog(catalog_version=1)
    registry = _make_registry(catalog_version=2)
    request = _make_request(catalog=catalog, registry=registry)

    result = run_publication_preflight(request)

    assert result.approved_questions == ()
    assert result.can_continue is False
    assert len(result.issues) == 1

    issue = result.issues[0]
    assert issue.id == "publication_issue_0001"
    assert issue.code is PublicationIssueCode.REGISTRY_CATALOG_VERSION_MISMATCH
    assert issue.severity is PublicationIssueSeverity.CRITICAL
    assert issue.blocking is True
    assert issue.object_type is PublicationObjectType.SCIENTIFIC_CONTENT_REGISTRY
    assert issue.object_id == registry.id
    assert issue.question_id is None
    assert issue.question_content_revision_id is None
    assert issue.related_object_ids == []
    assert "1" in issue.message
    assert "2" in issue.message


def test_both_catalog_binding_mismatches_return_two_issues() -> None:
    catalog = _make_catalog(catalog_id="cat_a", catalog_version=1)
    registry = _make_registry(catalog_id="cat_b", catalog_version=2)
    request = _make_request(catalog=catalog, registry=registry)

    result = run_publication_preflight(request)

    assert result.approved_questions == ()
    assert result.can_continue is False
    assert len(result.issues) == 2

    codes = {issue.code for issue in result.issues}
    assert codes == {
        PublicationIssueCode.REGISTRY_CATALOG_ID_MISMATCH,
        PublicationIssueCode.REGISTRY_CATALOG_VERSION_MISMATCH,
    }


def test_binding_mismatch_stops_other_preflight_checks() -> None:
    q_draft = _make_question("q_draft", status=QuestionStatus.DRAFT)
    catalog = _make_catalog(catalog_id="cat_a", questions=[q_draft])
    unknown_rev = _make_revision("rev_unknown", question_id="non_existent_q")
    registry = _make_registry(catalog_id="cat_b", revisions=[unknown_rev])

    request = _make_request(catalog=catalog, registry=registry)
    result = run_publication_preflight(request)

    assert result.approved_questions == ()
    assert result.can_continue is False
    assert len(result.issues) == 1
    assert result.issues[0].code is PublicationIssueCode.REGISTRY_CATALOG_ID_MISMATCH


def test_unknown_registry_question_revision_returns_critical_issue() -> None:
    revision = _make_revision("rev_unknown", question_id="missing_q")
    registry = _make_registry(revisions=[revision])
    catalog = _make_catalog()

    request = _make_request(catalog=catalog, registry=registry)
    result = run_publication_preflight(request)

    assert result.can_continue is False

    rev_issues = [
        issue
        for issue in result.issues
        if issue.code is PublicationIssueCode.REGISTRY_QUESTION_NOT_FOUND_IN_CATALOG
    ]
    assert len(rev_issues) == 1

    issue = rev_issues[0]
    assert issue.severity is PublicationIssueSeverity.CRITICAL
    assert issue.blocking is True
    assert issue.object_type is PublicationObjectType.QUESTION_CONTENT_REVISION
    assert issue.object_id == "rev_unknown"
    assert issue.question_id == "missing_q"
    assert issue.question_content_revision_id == "rev_unknown"
    assert issue.related_object_ids == [catalog.id]
    assert "rev_unknown" in issue.message
    assert "missing_q" in issue.message


def test_each_unknown_revision_gets_separate_issue() -> None:
    rev1 = _make_revision(
        "rev_1",
        question_id="missing_q",
        revision_num=1,
        status=ContentRevisionStatus.RETIRED,
    )
    rev2 = _make_revision(
        "rev_2",
        question_id="missing_q",
        revision_num=2,
        supersedes_revision_id="rev_1",
        status=ContentRevisionStatus.APPROVED,
    )
    registry = _make_registry(revisions=[rev1, rev2])
    catalog = _make_catalog()

    request = _make_request(catalog=catalog, registry=registry)
    result = run_publication_preflight(request)

    rev_issues = [
        issue
        for issue in result.issues
        if issue.code is PublicationIssueCode.REGISTRY_QUESTION_NOT_FOUND_IN_CATALOG
    ]
    assert len(rev_issues) == 2
    assert {issue.object_id for issue in rev_issues} == {"rev_1", "rev_2"}


def test_known_registry_question_revision_is_accepted() -> None:
    rev = _make_revision("rev_1", question_id="question_1")
    registry = _make_registry(revisions=[rev])
    catalog = _make_catalog(questions=[_make_question("question_1")])

    request = _make_request(catalog=catalog, registry=registry)
    result = run_publication_preflight(request)

    rev_issues = [
        issue
        for issue in result.issues
        if issue.code is PublicationIssueCode.REGISTRY_QUESTION_NOT_FOUND_IN_CATALOG
    ]
    assert len(rev_issues) == 0


def test_unknown_construct_output_target_returns_error() -> None:
    construct = _make_construct("c_1", expected_output_target_ids=["unknown_target"])
    registry = _make_registry(constructs=[construct])
    catalog = _make_catalog()

    request = _make_request(catalog=catalog, registry=registry)
    result = run_publication_preflight(request)

    assert result.can_continue is False

    construct_issues = [
        issue
        for issue in result.issues
        if issue.code is PublicationIssueCode.CONSTRUCT_OUTPUT_TARGET_NOT_FOUND
    ]
    assert len(construct_issues) == 1

    issue = construct_issues[0]
    assert issue.severity is PublicationIssueSeverity.ERROR
    assert issue.blocking is True
    assert issue.object_type is PublicationObjectType.CONSTRUCT_DEFINITION
    assert issue.object_id == "c_1"
    assert issue.question_id is None
    assert issue.question_content_revision_id is None
    assert issue.related_object_ids == ["unknown_target"]
    assert "c_1" in issue.message
    assert "unknown_target" in issue.message


def test_multiple_unknown_targets_for_same_construct_create_one_issue() -> None:
    construct = _make_construct(
        "c_1", expected_output_target_ids=["unknown_z", "unknown_a", "target_1"]
    )
    registry = _make_registry(constructs=[construct])
    catalog = _make_catalog(targets=[_make_target("target_1")])

    request = _make_request(catalog=catalog, registry=registry)
    result = run_publication_preflight(request)

    construct_issues = [
        issue
        for issue in result.issues
        if issue.code is PublicationIssueCode.CONSTRUCT_OUTPUT_TARGET_NOT_FOUND
    ]
    assert len(construct_issues) == 1

    issue = construct_issues[0]
    assert issue.related_object_ids == ["unknown_a", "unknown_z"]
    assert "unknown_a" in issue.message
    assert "unknown_z" in issue.message


def test_known_construct_output_targets_are_accepted() -> None:
    construct = _make_construct("c_1", expected_output_target_ids=["target_1"])
    registry = _make_registry(constructs=[construct])
    catalog = _make_catalog(targets=[_make_target("target_1")])

    request = _make_request(catalog=catalog, registry=registry)
    result = run_publication_preflight(request)

    construct_issues = [
        issue
        for issue in result.issues
        if issue.code is PublicationIssueCode.CONSTRUCT_OUTPUT_TARGET_NOT_FOUND
    ]
    assert len(construct_issues) == 0


def test_preflight_can_continue_when_no_blocking_issue_exists() -> None:
    request = _make_request()
    result = run_publication_preflight(request)

    assert result.can_continue is True
    assert len(result.issues) == 0


def test_preflight_cannot_continue_without_approved_question() -> None:
    catalog = _make_catalog(questions=[_make_question("q1", status=QuestionStatus.DRAFT)])
    request = _make_request(catalog=catalog)
    result = run_publication_preflight(request)

    assert result.can_continue is False


def test_preflight_cannot_continue_with_unknown_registry_question() -> None:
    rev = _make_revision("r1", question_id="unknown_q")
    registry = _make_registry(revisions=[rev])
    request = _make_request(registry=registry)

    result = run_publication_preflight(request)
    assert result.can_continue is False


def test_preflight_cannot_continue_with_unknown_construct_target() -> None:
    construct = _make_construct("c1", expected_output_target_ids=["unknown_t"])
    registry = _make_registry(constructs=[construct])
    request = _make_request(registry=registry)

    result = run_publication_preflight(request)
    assert result.can_continue is False


def test_issue_ids_are_deterministic() -> None:
    rev = _make_revision("r1", question_id="unknown_q")
    construct = _make_construct("c1", expected_output_target_ids=["unknown_t"])
    registry = _make_registry(constructs=[construct], revisions=[rev])
    request = _make_request(registry=registry)

    result1 = run_publication_preflight(request)
    result2 = run_publication_preflight(request)

    ids1 = [issue.id for issue in result1.issues]
    ids2 = [issue.id for issue in result2.issues]

    assert ids1 == ids2
    assert len(ids1) == 2


def test_issue_order_is_deterministic() -> None:
    rev = _make_revision("r1", question_id="unknown_q")
    construct = _make_construct("c1", expected_output_target_ids=["unknown_t"])
    registry = _make_registry(constructs=[construct], revisions=[rev])
    request = _make_request(registry=registry)

    result = run_publication_preflight(request)

    assert len(result.issues) == 2
    # CRITICAL (unknown revision) must come before ERROR (unknown construct target)
    assert result.issues[0].code is PublicationIssueCode.REGISTRY_QUESTION_NOT_FOUND_IN_CATALOG
    assert result.issues[0].severity is PublicationIssueSeverity.CRITICAL
    assert result.issues[1].code is PublicationIssueCode.CONSTRUCT_OUTPUT_TARGET_NOT_FOUND
    assert result.issues[1].severity is PublicationIssueSeverity.ERROR


def test_same_input_produces_equal_preflight_result() -> None:
    request = _make_request()
    res1 = run_publication_preflight(request)
    res2 = run_publication_preflight(request)

    assert res1 == res2


def test_issue_ids_use_four_digit_sequence() -> None:
    rev = _make_revision("r1", question_id="unknown_q")
    registry = _make_registry(revisions=[rev])
    request = _make_request(registry=registry)

    result = run_publication_preflight(request)

    assert result.issues[0].id == "publication_issue_0001"


def test_duplicate_issue_drafts_are_deduplicated() -> None:
    draft1 = _IssueDraft(
        code=PublicationIssueCode.REGISTRY_QUESTION_NOT_FOUND_IN_CATALOG,
        severity=PublicationIssueSeverity.CRITICAL,
        object_type=PublicationObjectType.QUESTION_CONTENT_REVISION,
        object_id="r1",
        question_id="q1",
        question_content_revision_id="r1",
        message="Draft 1",
        related_object_ids=("cat1",),
    )
    draft2 = _IssueDraft(
        code=PublicationIssueCode.REGISTRY_QUESTION_NOT_FOUND_IN_CATALOG,
        severity=PublicationIssueSeverity.CRITICAL,
        object_type=PublicationObjectType.QUESTION_CONTENT_REVISION,
        object_id="r1",
        question_id="q1",
        question_content_revision_id="r1",
        message="Draft 2 (duplicate key)",
        related_object_ids=("cat1",),
    )

    issues = _finalize_issues([draft1, draft2])

    assert len(issues) == 1
    assert issues[0].id == "publication_issue_0001"


def test_preflight_does_not_mutate_request() -> None:
    request = _make_request()
    dump_before = request.model_dump()

    run_publication_preflight(request)

    dump_after = request.model_dump()
    assert dump_before == dump_after


def test_source_metadata_does_not_affect_preflight_result() -> None:
    q1 = _make_question("q1", source_metadata="meta 1")
    q2 = _make_question("q1", source_metadata="meta 2 (different)")

    catalog1 = _make_catalog(questions=[q1])
    catalog2 = _make_catalog(questions=[q2])

    req1 = _make_request(catalog=catalog1)
    req2 = _make_request(catalog=catalog2)

    res1 = run_publication_preflight(req1)
    res2 = run_publication_preflight(req2)

    assert res1.can_continue == res2.can_continue
    assert len(res1.issues) == len(res2.issues)
    assert len(res1.approved_questions) == len(res2.approved_questions)
    assert res1.approved_questions[0].id == res2.approved_questions[0].id
