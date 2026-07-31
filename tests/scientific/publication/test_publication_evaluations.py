"""Unit tests for content evaluation validation service."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

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
from brif_ai.scientific.publication._content import (
    _collect_target_locale_content,
    _QuestionContentSelection,
)
from brif_ai.scientific.publication._evaluations import _collect_content_evaluations
from brif_ai.scientific.publication._evidence import _collect_question_evidence
from brif_ai.scientific.publication._issues import _finalize_issues, _IssueDraft
from brif_ai.scientific.publication._permissions import _collect_source_permissions
from brif_ai.scientific.publication._reviews import _collect_expert_reviews
from brif_ai.scientific.publication.common import (
    PublicationIssueCode,
    PublicationIssueSeverity,
    PublicationObjectType,
)
from brif_ai.scientific.publication.models import PublicationIssue, PublicationValidationRequest
from brif_ai.scientific.publication.preflight import _collect_publication_preflight

UTC_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)  # noqa: UP017


def _make_source(
    source_id: str = "source_1",
    status: UsagePermissionStatus = UsagePermissionStatus.OPEN,
    source_type: SourceType = SourceType.VALIDATED_INSTRUMENT,
) -> ScientificSource:
    return ScientificSource(
        id=source_id,
        source_type=source_type,
        title=f"Synthetic source title {source_id}",
        authors=["Author One"],
        publication_year=2025,
        publication_or_publisher="Journal of Testing",
        identifier_type=IdentifierType.NONE,
        citation_text="Synthetic citation text",
        language="tr",
        usage_permission_status=status,
    )


def _make_construct(
    construct_id: str = "construct_1",
    target_id: str = "target_1",
) -> ConstructDefinition:
    return ConstructDefinition(
        id=construct_id,
        name="Synthetic construct",
        definition="Synthetic definition",
        conversation_module=ConversationModule.PROJECT_CONTEXT,
        architectural_relevance="Synthetic relevance",
        expected_output_target_ids=[target_id],
    )


def _make_question(
    question_id: str = "question_1",
    content_key: str = "question.test_1",
    status: QuestionStatus = QuestionStatus.APPROVED,
    display_order: int = 1,
    target_id: str = "target_1",
) -> QuestionDefinition:
    return QuestionDefinition(
        id=question_id,
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="Synthetic question purpose",
        content_key=content_key,
        answer_type=AnswerType.FREE_TEXT,
        required=True,
        output_target_ids=[target_id],
        allowed_follow_up_question_ids=[],
        applicable_stakeholder_roles=["owner"],
        display_order=display_order,
        source_metadata="synthetic source metadata",
        status=status,
        options=[],
    )


def _make_revision(
    revision_id: str = "revision_1",
    question_id: str = "question_1",
    locale: str = "tr-TR",
    revision_num: int = 1,
    content_key: str = "question.test_1",
    status: ContentRevisionStatus = ContentRevisionStatus.APPROVED,
    supersedes_revision_id: str | None = None,
) -> QuestionContentRevision:
    return QuestionContentRevision(
        id=revision_id,
        question_id=question_id,
        locale=locale,
        revision=revision_num,
        content_key=content_key,
        wording="Synthetic question wording",
        status=status,
        created_at=UTC_TIME,
        supersedes_revision_id=supersedes_revision_id,
    )


def _make_evaluation(
    evaluation_id: str = "eval_1",
    revision_id: str = "revision_1",
    evaluation_type: EvaluationType = EvaluationType.READABILITY_REVIEW,
    locale: str = "tr-TR",
    participant_count: int | None = None,
    result: EvaluationResult = EvaluationResult.PASSED,
    summary: str = "Synthetic evaluation summary",
    identified_issues: list[str] | None = None,
    revision_required: bool = False,
) -> ContentEvaluationRecord:
    if result is EvaluationResult.REVISION_REQUIRED:
        revision_required = True
        if identified_issues is None:
            identified_issues = ["Required revision issue"]
    elif result is EvaluationResult.PASSED_WITH_NOTES:
        revision_required = False
        if identified_issues is None:
            identified_issues = ["Note issue 1"]
    else:
        revision_required = False
        if identified_issues is None:
            identified_issues = []

    participant_types = {
        EvaluationType.COGNITIVE_INTERVIEW,
        EvaluationType.PILOT_INTERVIEW,
        EvaluationType.EXPERT_PANEL,
        EvaluationType.USABILITY_TEST,
        EvaluationType.PSYCHOMETRIC_STUDY,
    }
    if evaluation_type in participant_types and participant_count is None:
        participant_count = 10

    return ContentEvaluationRecord(
        id=evaluation_id,
        question_content_revision_id=revision_id,
        evaluation_type=evaluation_type,
        locale=locale,
        conducted_at=UTC_TIME,
        participant_count=participant_count,
        result=result,
        summary=summary,
        identified_issues=identified_issues,
        revision_required=revision_required,
    )


def _make_catalog(
    questions: list[QuestionDefinition] | None = None,
    target_id: str = "target_1",
) -> QuestionCatalog:
    target = InformationTargetDefinition(
        id=target_id,
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="Synthetic target purpose",
        required=True,
        fulfillment_policy=FulfillmentPolicy.VALID_ANSWER,
    )
    if questions is None:
        questions = [_make_question("question_1", target_id=target_id)]
    return QuestionCatalog(
        id="catalog_1",
        schema_version="v0",
        catalog_version=1,
        modules=[ConversationModule.PROJECT_CONTEXT],
        information_targets=[target],
        questions=questions,
        transition_rules=[],
    )


def _make_registry(
    revisions: list[QuestionContentRevision] | None = None,
    evaluations: list[ContentEvaluationRecord] | None = None,
    sources: list[ScientificSource] | None = None,
    constructs: list[ConstructDefinition] | None = None,
    evidence_links: list[QuestionEvidenceLink] | None = None,
    expert_reviews: list[ExpertReviewRecord] | None = None,
) -> ScientificContentRegistry:
    return ScientificContentRegistry(
        id="registry_1",
        schema_version="v0",
        registry_version=1,
        question_catalog_id="catalog_1",
        question_catalog_version=1,
        content_bundle_version=1,
        created_at=UTC_TIME,
        sources=sources if sources is not None else [_make_source()],
        constructs=constructs if constructs is not None else [_make_construct()],
        question_content_revisions=revisions or [],
        evidence_links=evidence_links or [],
        expert_reviews=expert_reviews or [],
        evaluations=evaluations or [],
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


# 1. test_selected_revision_none_skips_evaluation_validation
def test_selected_revision_none_skips_evaluation_validation() -> None:
    q1 = _make_question("q1")
    request = _make_request(catalog=_make_catalog([q1]))
    selection = _QuestionContentSelection(question=q1, selected_revision=None)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 0


# 2. test_revision_without_evaluations_produces_no_issue
def test_revision_without_evaluations_produces_no_issue() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 0


# 3. test_passed_evaluation_without_identified_issues_produces_no_issue
def test_passed_evaluation_without_identified_issues_produces_no_issue() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e1 = _make_evaluation("e1", revision_id="rev1", result=EvaluationResult.PASSED)
    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 0


# 4. test_passed_evaluation_with_identified_issues_produces_warning
def test_passed_evaluation_with_identified_issues_produces_warning() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e1 = _make_evaluation(
        "e1",
        revision_id="rev1",
        result=EvaluationResult.PASSED,
        identified_issues=["Minor wording note"],
    )
    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.EVALUATION_PASSED_WITH_NOTES
    assert draft.severity is PublicationIssueSeverity.WARNING
    assert draft.severity.is_blocking is False
    assert draft.object_type is PublicationObjectType.CONTENT_EVALUATION_RECORD
    assert draft.object_id == "e1"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id == "rev1"
    assert draft.related_object_ids == ()
    assert "PASSED" in draft.message
    assert "Minor wording note" in draft.message
    assert e1.result is EvaluationResult.PASSED


# 5. test_passed_with_notes_evaluation_produces_warning_draft
def test_passed_with_notes_evaluation_produces_warning_draft() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e1 = _make_evaluation(
        "e1",
        revision_id="rev1",
        result=EvaluationResult.PASSED_WITH_NOTES,
        summary="Panel identified minor clarifications",
        identified_issues=["Clarify option B"],
    )
    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.EVALUATION_PASSED_WITH_NOTES
    assert draft.severity is PublicationIssueSeverity.WARNING
    assert draft.severity.is_blocking is False
    assert draft.object_type is PublicationObjectType.CONTENT_EVALUATION_RECORD
    assert draft.object_id == "e1"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id == "rev1"
    assert draft.related_object_ids == ()
    assert "passed with notes" in draft.message
    assert "Clarify option B" in draft.message


# 6. test_revision_required_evaluation_produces_error_draft
def test_revision_required_evaluation_produces_error_draft() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e1 = _make_evaluation(
        "e1",
        revision_id="rev1",
        result=EvaluationResult.REVISION_REQUIRED,
        summary="Cognitive interview revealed misunderstanding",
        identified_issues=["Clause 1 is ambiguous"],
    )
    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.EVALUATION_REVISION_REQUIRED
    assert draft.severity is PublicationIssueSeverity.ERROR
    assert draft.severity.is_blocking is True
    assert draft.object_type is PublicationObjectType.CONTENT_EVALUATION_RECORD
    assert draft.object_id == "e1"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id == "rev1"
    assert draft.related_object_ids == ()
    assert "REVISION_REQUIRED" in draft.message
    assert "Clause 1 is ambiguous" in draft.message
    assert len(draft.message) <= 1000


# 7. test_inconclusive_evaluation_produces_warning_draft
def test_inconclusive_evaluation_produces_warning_draft() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e1 = _make_evaluation(
        "e1",
        revision_id="rev1",
        result=EvaluationResult.INCONCLUSIVE,
        summary="Sample size was insufficient for statistical power",
        identified_issues=[],
    )
    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.EVALUATION_INCONCLUSIVE
    assert draft.severity is PublicationIssueSeverity.WARNING
    assert draft.severity.is_blocking is False
    assert draft.object_type is PublicationObjectType.CONTENT_EVALUATION_RECORD
    assert draft.object_id == "e1"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id == "rev1"
    assert draft.related_object_ids == ()
    assert "INCONCLUSIVE" in draft.message


# 8. test_evaluation_for_other_revision_is_ignored
def test_evaluation_for_other_revision_is_ignored() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision(
        "rev1", question_id="q1", revision_num=1, status=ContentRevisionStatus.RETIRED
    )
    rev2 = _make_revision(
        "rev2",
        question_id="q1",
        revision_num=2,
        status=ContentRevisionStatus.APPROVED,
        supersedes_revision_id="rev1",
    )
    e1 = _make_evaluation("e1", revision_id="rev1", result=EvaluationResult.REVISION_REQUIRED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1, rev2], evaluations=[e1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev2)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 0


# 9. test_passed_does_not_cancel_revision_required_evaluation
def test_passed_does_not_cancel_revision_required_evaluation() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e_pass = _make_evaluation("e_pass", revision_id="rev1", result=EvaluationResult.PASSED)
    e_rev = _make_evaluation("e_rev", revision_id="rev1", result=EvaluationResult.REVISION_REQUIRED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e_pass, e_rev]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].object_id == "e_rev"
    assert drafts[0].code is PublicationIssueCode.EVALUATION_REVISION_REQUIRED


# 10. test_multiple_negative_and_warning_evaluations_produce_separate_drafts_in_id_order
def test_multiple_negative_and_warning_evaluations_produce_separate_drafts_in_id_order() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e_b = _make_evaluation("e_b", revision_id="rev1", result=EvaluationResult.PASSED_WITH_NOTES)
    e_a = _make_evaluation("e_a", revision_id="rev1", result=EvaluationResult.REVISION_REQUIRED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e_b, e_a]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 2
    assert drafts[0].object_id == "e_a"
    assert drafts[0].code is PublicationIssueCode.EVALUATION_REVISION_REQUIRED

    assert drafts[1].object_id == "e_b"
    assert drafts[1].code is PublicationIssueCode.EVALUATION_PASSED_WITH_NOTES


# 11. test_different_evaluation_types_are_evaluated_independently
def test_different_evaluation_types_are_evaluated_independently() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e1 = _make_evaluation(
        "e1",
        revision_id="rev1",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        result=EvaluationResult.PASSED,
    )
    e2 = _make_evaluation(
        "e2",
        revision_id="rev1",
        evaluation_type=EvaluationType.COGNITIVE_INTERVIEW,
        result=EvaluationResult.REVISION_REQUIRED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e1, e2]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].object_id == "e2"


# 12. test_same_evaluation_type_multiple_records_are_evaluated_independently
def test_same_evaluation_type_multiple_records_are_evaluated_independently() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e1 = _make_evaluation(
        "e1",
        revision_id="rev1",
        evaluation_type=EvaluationType.PILOT_INTERVIEW,
        result=EvaluationResult.PASSED_WITH_NOTES,
    )
    e2 = _make_evaluation(
        "e2",
        revision_id="rev1",
        evaluation_type=EvaluationType.PILOT_INTERVIEW,
        result=EvaluationResult.REVISION_REQUIRED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e1, e2]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 2
    assert drafts[0].object_id == "e1"
    assert drafts[1].object_id == "e2"


# 13. test_readability_review_without_participant_count_is_valid
def test_readability_review_without_participant_count_is_valid() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e1 = _make_evaluation(
        "e1",
        revision_id="rev1",
        evaluation_type=EvaluationType.READABILITY_REVIEW,
        participant_count=None,
        result=EvaluationResult.REVISION_REQUIRED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].object_id == "e1"


# 14. test_participant_based_evaluations_require_participant_count
def test_participant_based_evaluations_require_participant_count() -> None:
    with pytest.raises(ValidationError, match="requires participant_count"):
        ContentEvaluationRecord(
            id="e1",
            question_content_revision_id="rev1",
            evaluation_type=EvaluationType.COGNITIVE_INTERVIEW,
            locale="tr-TR",
            conducted_at=UTC_TIME,
            participant_count=None,
            result=EvaluationResult.PASSED,
            summary="Summary",
            identified_issues=[],
            revision_required=False,
        )


# 15. test_old_revision_passed_does_not_affect_selected_revision
def test_old_revision_passed_does_not_affect_selected_revision() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision(
        "rev1", question_id="q1", revision_num=1, status=ContentRevisionStatus.RETIRED
    )
    rev2 = _make_revision(
        "rev2",
        question_id="q1",
        revision_num=2,
        status=ContentRevisionStatus.APPROVED,
        supersedes_revision_id="rev1",
    )
    e1 = _make_evaluation("e1", revision_id="rev1", result=EvaluationResult.PASSED)
    e2 = _make_evaluation("e2", revision_id="rev2", result=EvaluationResult.REVISION_REQUIRED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1, rev2], evaluations=[e1, e2]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev2)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].object_id == "e2"


# 16. test_old_revision_revision_required_does_not_affect_selected_revision
def test_old_revision_revision_required_does_not_affect_selected_revision() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision(
        "rev1", question_id="q1", revision_num=1, status=ContentRevisionStatus.RETIRED
    )
    rev2 = _make_revision(
        "rev2",
        question_id="q1",
        revision_num=2,
        status=ContentRevisionStatus.APPROVED,
        supersedes_revision_id="rev1",
    )
    e1 = _make_evaluation("e1", revision_id="rev1", result=EvaluationResult.REVISION_REQUIRED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1, rev2], evaluations=[e1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev2)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 0


# 17. test_multiple_questions_preserve_selection_order
def test_multiple_questions_preserve_selection_order() -> None:
    q1 = _make_question("q1", display_order=1)
    q2 = _make_question("q2", display_order=2)
    rev1 = _make_revision("rev1", question_id="q1")
    rev2 = _make_revision("rev2", question_id="q2")
    e1 = _make_evaluation("e1", revision_id="rev1", result=EvaluationResult.REVISION_REQUIRED)
    e2 = _make_evaluation("e2", revision_id="rev2", result=EvaluationResult.REVISION_REQUIRED)

    request = _make_request(
        catalog=_make_catalog([q1, q2]),
        registry=_make_registry(revisions=[rev1, rev2], evaluations=[e1, e2]),
    )
    sel1 = _QuestionContentSelection(question=q1, selected_revision=rev1)
    sel2 = _QuestionContentSelection(question=q2, selected_revision=rev2)

    drafts = _collect_content_evaluations(request, (sel1, sel2))
    assert len(drafts) == 2
    assert drafts[0].question_id == "q1"
    assert drafts[1].question_id == "q2"


# 18. test_evaluation_collector_does_not_mutate_request
def test_evaluation_collector_does_not_mutate_request() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e1 = _make_evaluation("e1", revision_id="rev1", result=EvaluationResult.REVISION_REQUIRED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    dump_before = request.model_dump()
    _collect_content_evaluations(request, (selection,))
    dump_after = request.model_dump()

    assert dump_before == dump_after


# 19. test_evaluation_collector_is_deterministic
def test_evaluation_collector_is_deterministic() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e1 = _make_evaluation("e1", revision_id="rev1", result=EvaluationResult.REVISION_REQUIRED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts1 = _collect_content_evaluations(request, (selection,))
    drafts2 = _collect_content_evaluations(request, (selection,))
    assert drafts1 == drafts2


# 20. test_evaluation_collector_returns_issue_drafts_without_ids
def test_evaluation_collector_returns_issue_drafts_without_ids() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e1 = _make_evaluation("e1", revision_id="rev1", result=EvaluationResult.REVISION_REQUIRED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert isinstance(drafts, tuple)
    assert len(drafts) == 1
    draft = drafts[0]
    assert isinstance(draft, _IssueDraft)
    assert not hasattr(draft, "id")
    assert not isinstance(draft, PublicationIssue)


# 21. test_evaluation_issue_related_object_ids_are_empty
def test_evaluation_issue_related_object_ids_are_empty() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    e1 = _make_evaluation("e1", revision_id="rev1", result=EvaluationResult.REVISION_REQUIRED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].related_object_ids == ()


# 22. test_long_evaluation_content_produces_bounded_finalizable_message
def test_long_evaluation_content_produces_bounded_finalizable_message() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")

    long_summary = "S" * 900
    long_issues = ["I1_" + "A" * 200, "I2_" + "B" * 200]

    e1 = _make_evaluation(
        "e1",
        revision_id="rev1",
        result=EvaluationResult.REVISION_REQUIRED,
        summary=long_summary,
        identified_issues=long_issues,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evaluations=[e1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_content_evaluations(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]

    assert len(draft.message) <= 1000
    assert draft.message.endswith("...[truncated]")
    assert "e1" in draft.message
    assert "REVISION_REQUIRED" in draft.message
    assert "q1" in draft.message
    assert "rev1" in draft.message

    final_issues = _finalize_issues([draft])
    assert len(final_issues) == 1
    assert final_issues[0].id == "publication_issue_0001"
    assert len(final_issues[0].message) <= 1000


# 23. test_global_finalization_with_preflight_content_evidence_permission_review_and_evaluation
def test_global_finalization_with_preflight_content_evidence_permission_review_and_evaluation() -> (
    None
):
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    link1 = QuestionEvidenceLink(
        id="link1",
        question_content_revision_id="rev1",
        construct_ids=["construct_1"],
        source_ids=["s1"],
        evidence_relation=EvidenceRelation.QUESTION_WORDING_BASIS,
        claim_scope=ClaimScope.VALIDATED_ITEM,
        rationale="Synthetic rationale",
        source_locator="Page 12",
        adaptation_type=AdaptationType.DIRECT_TRANSLATION,
        adaptation_note="Translated from EN",
        target_locale="tr-TR",
    )
    r1 = ExpertReviewRecord(
        id="r1",
        question_content_revision_id="rev1",
        evidence_link_ids=["link1"],
        reviewer_reference="Reviewer 1",
        reviewer_role="Methodologist",
        review_area=ReviewArea.ETHICS_AND_PRIVACY,
        decision=ReviewDecision.REJECTED,
        reviewed_at=UTC_TIME,
        rationale="Ethics rejection rationale",
    )
    e1 = _make_evaluation(
        "e1",
        revision_id="rev1",
        result=EvaluationResult.REVISION_REQUIRED,
        summary="Evaluation revision required",
    )

    catalog = _make_catalog(questions=[q1])
    registry = _make_registry(
        revisions=[rev1],
        evidence_links=[link1],
        sources=[s1],
        expert_reviews=[r1],
        evaluations=[e1],
    )
    request = _make_request(catalog=catalog, registry=registry)

    app_questions, preflight_drafts = _collect_publication_preflight(request)
    selections, content_drafts = _collect_target_locale_content(request, app_questions)
    evidence_drafts = _collect_question_evidence(request, selections)
    permission_drafts = _collect_source_permissions(request, selections)
    review_drafts = _collect_expert_reviews(request, selections)
    evaluation_drafts = _collect_content_evaluations(request, selections)

    all_drafts = (
        list(preflight_drafts)
        + list(content_drafts)
        + list(evidence_drafts)
        + list(permission_drafts)
        + list(review_drafts)
        + list(evaluation_drafts)
    )
    final_issues = _finalize_issues(all_drafts)

    assert len(final_issues) >= 4
    issue_ids = [issue.id for issue in final_issues]
    assert issue_ids == [f"publication_issue_{i:04d}" for i in range(1, len(final_issues) + 1)]


# 24. test_evaluation_helper_is_not_public_export
def test_evaluation_helper_is_not_public_export() -> None:
    pkg = brif_ai.scientific.publication
    assert not hasattr(pkg, "_collect_content_evaluations")
    assert "_collect_content_evaluations" not in pkg.__all__
