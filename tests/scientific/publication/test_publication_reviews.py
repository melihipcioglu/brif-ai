"""Unit tests for expert and language review validation service."""

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
    ContentRevisionStatus,
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


def _make_evidence_link(
    link_id: str = "link_1",
    revision_id: str = "revision_1",
    construct_id: str = "construct_1",
    source_ids: list[str] | None = None,
    relation: EvidenceRelation = EvidenceRelation.QUESTION_WORDING_BASIS,
    claim: ClaimScope = ClaimScope.VALIDATED_ITEM,
    adaptation: AdaptationType = AdaptationType.ORIGINAL,
    locale: str = "tr-TR",
    adaptation_note: str | None = None,
) -> QuestionEvidenceLink:
    return QuestionEvidenceLink(
        id=link_id,
        question_content_revision_id=revision_id,
        construct_ids=[construct_id],
        source_ids=source_ids or ["source_1"],
        evidence_relation=relation,
        claim_scope=claim,
        rationale="Synthetic rationale for evidence link",
        source_locator="Page 12, Table 3",
        adaptation_type=adaptation,
        adaptation_note=adaptation_note,
        target_locale=locale,
    )


def _make_review(
    review_id: str = "review_1",
    revision_id: str = "revision_1",
    evidence_link_ids: list[str] | None = None,
    reviewer_reference: str = "Reviewer One",
    reviewer_role: str = "Senior Methodologist",
    review_area: ReviewArea = ReviewArea.LANGUAGE_AND_COMPREHENSION,
    decision: ReviewDecision = ReviewDecision.APPROVED,
    rationale: str | None = None,
    required_changes: str | None = None,
) -> ExpertReviewRecord:
    if decision is ReviewDecision.REJECTED and rationale is None:
        rationale = "Synthetic rejection rationale"
    if decision is ReviewDecision.CHANGES_REQUESTED and required_changes is None:
        required_changes = "Synthetic required changes"
    return ExpertReviewRecord(
        id=review_id,
        question_content_revision_id=revision_id,
        evidence_link_ids=evidence_link_ids if evidence_link_ids is not None else [],
        reviewer_reference=reviewer_reference,
        reviewer_role=reviewer_role,
        review_area=review_area,
        decision=decision,
        reviewed_at=UTC_TIME,
        rationale=rationale,
        required_changes=required_changes,
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
    evidence_links: list[QuestionEvidenceLink] | None = None,
    sources: list[ScientificSource] | None = None,
    constructs: list[ConstructDefinition] | None = None,
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


def test_selected_revision_none_skips_review_validation() -> None:
    q1 = _make_question("q1")
    request = _make_request(catalog=_make_catalog([q1]))
    selection = _QuestionContentSelection(question=q1, selected_revision=None)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 0


def test_original_revision_without_reviews_produces_no_issue() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link("link1", revision_id="rev1", adaptation=AdaptationType.ORIGINAL)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 0


def test_rejected_review_without_direct_evidence_still_produces_error() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    r1 = _make_review(
        "r1",
        revision_id="rev1",
        decision=ReviewDecision.REJECTED,
        rationale="Wording is unacceptable",
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[], expert_reviews=[r1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.REVIEW_REJECTED
    assert draft.severity is PublicationIssueSeverity.ERROR
    assert draft.severity.is_blocking is True
    assert draft.object_type is PublicationObjectType.EXPERT_REVIEW_RECORD
    assert draft.object_id == "r1"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id == "rev1"
    assert draft.related_object_ids == ()
    assert "r1" in draft.message
    assert "Wording is unacceptable" in draft.message


def test_changes_requested_review_without_direct_evidence_still_produces_error() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    r1 = _make_review(
        "r1",
        revision_id="rev1",
        decision=ReviewDecision.CHANGES_REQUESTED,
        required_changes="Fix typo in clause 2",
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[], expert_reviews=[r1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.REVIEW_CHANGES_REQUESTED
    assert draft.severity is PublicationIssueSeverity.ERROR
    assert draft.severity.is_blocking is True
    assert draft.object_type is PublicationObjectType.EXPERT_REVIEW_RECORD
    assert draft.object_id == "r1"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id == "rev1"
    assert draft.related_object_ids == ()
    assert "r1" in draft.message
    assert "Fix typo in clause 2" in draft.message


def test_approved_review_produces_no_decision_issue() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    r1 = _make_review("r1", revision_id="rev1", decision=ReviewDecision.APPROVED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], expert_reviews=[r1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 0


def test_review_for_other_revision_is_ignored() -> None:
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
    r1 = _make_review("r1", revision_id="rev1", decision=ReviewDecision.REJECTED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1, rev2], expert_reviews=[r1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev2)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 0


def test_rejected_review_related_ids_contain_only_review_evidence_links() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link("link1", revision_id="rev1")
    link2 = _make_evidence_link("link2", revision_id="rev1")
    r1 = _make_review(
        "r1",
        revision_id="rev1",
        evidence_link_ids=["link2", "link1"],
        decision=ReviewDecision.REJECTED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(
            revisions=[rev1], evidence_links=[link1, link2], expert_reviews=[r1]
        ),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.object_id == "r1"
    assert draft.related_object_ids == ("link1", "link2")
    assert "r1" not in draft.related_object_ids


def test_revision_level_rejected_review_has_empty_related_ids() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    r1 = _make_review(
        "r1", revision_id="rev1", evidence_link_ids=[], decision=ReviewDecision.REJECTED
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], expert_reviews=[r1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].related_object_ids == ()


def test_multiple_negative_reviews_produce_separate_drafts_in_review_id_order() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    r2 = _make_review(
        "r_b",
        revision_id="rev1",
        decision=ReviewDecision.CHANGES_REQUESTED,
        required_changes="Change wording",
    )
    r1 = _make_review(
        "r_a",
        revision_id="rev1",
        decision=ReviewDecision.REJECTED,
        rationale="Invalid construct",
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], expert_reviews=[r2, r1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 2
    assert drafts[0].object_id == "r_a"
    assert drafts[0].code is PublicationIssueCode.REVIEW_REJECTED

    assert drafts[1].object_id == "r_b"
    assert drafts[1].code is PublicationIssueCode.REVIEW_CHANGES_REQUESTED


def test_approved_review_does_not_cancel_rejected_review() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    r_app = _make_review("r_app", revision_id="rev1", decision=ReviewDecision.APPROVED)
    r_rej = _make_review("r_rej", revision_id="rev1", decision=ReviewDecision.REJECTED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], expert_reviews=[r_app, r_rej]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].object_id == "r_rej"
    assert drafts[0].code is PublicationIssueCode.REVIEW_REJECTED


def test_direct_translation_without_language_review_produces_missing_error() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        adaptation=AdaptationType.DIRECT_TRANSLATION,
        adaptation_note="Translated from EN",
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.TRANSLATED_ITEM_WITHOUT_LANGUAGE_REVIEW
    assert draft.severity is PublicationIssueSeverity.ERROR
    assert draft.severity.is_blocking is True
    assert draft.object_type is PublicationObjectType.QUESTION_CONTENT_REVISION
    assert draft.object_id == "rev1"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id == "rev1"
    assert draft.related_object_ids == ("link1",)
    assert "tr-TR" in draft.message
    assert "LANGUAGE_AND_COMPREHENSION" in draft.message


def test_forward_back_translation_without_language_review_produces_missing_error() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        adaptation=AdaptationType.FORWARD_BACK_TRANSLATION,
        adaptation_note="Forward-back translation",
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.TRANSLATED_ITEM_WITHOUT_LANGUAGE_REVIEW


def test_approved_language_review_with_empty_link_ids_covers_all_translation_links() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        adaptation=AdaptationType.DIRECT_TRANSLATION,
        adaptation_note="Note 1",
    )
    link2 = _make_evidence_link(
        "link2",
        revision_id="rev1",
        adaptation=AdaptationType.FORWARD_BACK_TRANSLATION,
        adaptation_note="Note 2",
    )
    r1 = _make_review(
        "r1",
        revision_id="rev1",
        evidence_link_ids=[],
        review_area=ReviewArea.LANGUAGE_AND_COMPREHENSION,
        decision=ReviewDecision.APPROVED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(
            revisions=[rev1], evidence_links=[link1, link2], expert_reviews=[r1]
        ),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 0


def test_approved_language_review_with_specific_ids_covers_only_listed_translation_links() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        adaptation=AdaptationType.DIRECT_TRANSLATION,
        adaptation_note="Note 1",
    )
    link2 = _make_evidence_link(
        "link2",
        revision_id="rev1",
        adaptation=AdaptationType.FORWARD_BACK_TRANSLATION,
        adaptation_note="Note 2",
    )
    r1 = _make_review(
        "r1",
        revision_id="rev1",
        evidence_link_ids=["link1"],
        review_area=ReviewArea.LANGUAGE_AND_COMPREHENSION,
        decision=ReviewDecision.APPROVED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(
            revisions=[rev1], evidence_links=[link1, link2], expert_reviews=[r1]
        ),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.TRANSLATED_ITEM_WITHOUT_LANGUAGE_REVIEW
    assert drafts[0].related_object_ids == ("link2",)


def test_multiple_approved_language_reviews_union_their_link_coverage() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link_a = _make_evidence_link(
        "translation_link_a",
        revision_id="rev1",
        adaptation=AdaptationType.DIRECT_TRANSLATION,
        adaptation_note="Note A",
    )
    link_b = _make_evidence_link(
        "translation_link_b",
        revision_id="rev1",
        adaptation=AdaptationType.FORWARD_BACK_TRANSLATION,
        adaptation_note="Note B",
    )
    review_a = _make_review(
        "review_a",
        revision_id="rev1",
        evidence_link_ids=["translation_link_a"],
        review_area=ReviewArea.LANGUAGE_AND_COMPREHENSION,
        decision=ReviewDecision.APPROVED,
    )
    review_b = _make_review(
        "review_b",
        revision_id="rev1",
        evidence_link_ids=["translation_link_b"],
        review_area=ReviewArea.LANGUAGE_AND_COMPREHENSION,
        decision=ReviewDecision.APPROVED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(
            revisions=[rev1],
            evidence_links=[link_b, link_a],
            expert_reviews=[review_b, review_a],
        ),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 0


def test_partial_language_review_reports_only_uncovered_translation_links() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        adaptation=AdaptationType.DIRECT_TRANSLATION,
        adaptation_note="Note 1",
    )
    link2 = _make_evidence_link(
        "link2",
        revision_id="rev1",
        adaptation=AdaptationType.DIRECT_TRANSLATION,
        adaptation_note="Note 2",
    )
    r1 = _make_review(
        "r1",
        revision_id="rev1",
        evidence_link_ids=["link1"],
        review_area=ReviewArea.LANGUAGE_AND_COMPREHENSION,
        decision=ReviewDecision.APPROVED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(
            revisions=[rev1], evidence_links=[link1, link2], expert_reviews=[r1]
        ),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].related_object_ids == ("link2",)


def test_rejected_language_review_produces_rejected_and_missing_language_issues() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        adaptation=AdaptationType.DIRECT_TRANSLATION,
        adaptation_note="Note 1",
    )
    r1 = _make_review(
        "r1",
        revision_id="rev1",
        evidence_link_ids=["link1"],
        review_area=ReviewArea.LANGUAGE_AND_COMPREHENSION,
        decision=ReviewDecision.REJECTED,
        rationale="Bad translation",
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], expert_reviews=[r1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 2
    assert drafts[0].code is PublicationIssueCode.REVIEW_REJECTED
    assert drafts[0].object_id == "r1"

    assert drafts[1].code is PublicationIssueCode.TRANSLATED_ITEM_WITHOUT_LANGUAGE_REVIEW
    assert drafts[1].object_id == "rev1"
    assert drafts[1].related_object_ids == ("link1",)


def test_changes_requested_language_review_produces_changes_and_missing_language_issues() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        adaptation=AdaptationType.DIRECT_TRANSLATION,
        adaptation_note="Note 1",
    )
    r1 = _make_review(
        "r1",
        revision_id="rev1",
        evidence_link_ids=["link1"],
        review_area=ReviewArea.LANGUAGE_AND_COMPREHENSION,
        decision=ReviewDecision.CHANGES_REQUESTED,
        required_changes="Rephrase sentence 2",
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], expert_reviews=[r1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 2
    assert drafts[0].code is PublicationIssueCode.REVIEW_CHANGES_REQUESTED
    assert drafts[1].code is PublicationIssueCode.TRANSLATED_ITEM_WITHOUT_LANGUAGE_REVIEW


def test_unrelated_approved_review_area_does_not_satisfy_language_review() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        adaptation=AdaptationType.DIRECT_TRANSLATION,
        adaptation_note="Note 1",
    )
    r1 = _make_review(
        "r1",
        revision_id="rev1",
        evidence_link_ids=["link1"],
        review_area=ReviewArea.ETHICS_AND_PRIVACY,
        decision=ReviewDecision.APPROVED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], expert_reviews=[r1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.TRANSLATED_ITEM_WITHOUT_LANGUAGE_REVIEW


def test_original_content_does_not_require_language_review() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        adaptation=AdaptationType.ORIGINAL,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 0


def test_conceptual_derivation_does_not_require_language_review() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        adaptation=AdaptationType.CONCEPTUAL_DERIVATION,
        adaptation_note="Conceptual derivation note",
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 0


def test_cultural_adaptation_not_checked_in_minimum_v0() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        adaptation=AdaptationType.CULTURAL_ADAPTATION,
        adaptation_note="Cultural adaptation note",
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 0


def test_old_revision_language_review_does_not_cover_selected_revision() -> None:
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
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev2",
        adaptation=AdaptationType.DIRECT_TRANSLATION,
        adaptation_note="Note 2",
    )
    r1 = _make_review(
        "r1",
        revision_id="rev1",
        review_area=ReviewArea.LANGUAGE_AND_COMPREHENSION,
        decision=ReviewDecision.APPROVED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(
            revisions=[rev1, rev2], evidence_links=[link1], expert_reviews=[r1]
        ),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev2)

    drafts = _collect_expert_reviews(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.TRANSLATED_ITEM_WITHOUT_LANGUAGE_REVIEW


def test_multiple_questions_preserve_selection_order() -> None:
    q1 = _make_question("q1", display_order=1)
    q2 = _make_question("q2", display_order=2)
    rev1 = _make_revision("rev1", question_id="q1")
    rev2 = _make_revision("rev2", question_id="q2")
    r1 = _make_review("r1", revision_id="rev1", decision=ReviewDecision.REJECTED)
    r2 = _make_review("r2", revision_id="rev2", decision=ReviewDecision.REJECTED)

    request = _make_request(
        catalog=_make_catalog([q1, q2]),
        registry=_make_registry(revisions=[rev1, rev2], expert_reviews=[r1, r2]),
    )
    sel1 = _QuestionContentSelection(question=q1, selected_revision=rev1)
    sel2 = _QuestionContentSelection(question=q2, selected_revision=rev2)

    drafts = _collect_expert_reviews(request, (sel1, sel2))
    assert len(drafts) == 2
    assert drafts[0].question_id == "q1"
    assert drafts[1].question_id == "q2"


def test_review_collector_does_not_mutate_request() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    r1 = _make_review("r1", revision_id="rev1", decision=ReviewDecision.REJECTED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], expert_reviews=[r1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    dump_before = request.model_dump()
    _collect_expert_reviews(request, (selection,))
    dump_after = request.model_dump()

    assert dump_before == dump_after


def test_review_collector_is_deterministic() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    r1 = _make_review("r1", revision_id="rev1", decision=ReviewDecision.REJECTED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], expert_reviews=[r1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts1 = _collect_expert_reviews(request, (selection,))
    drafts2 = _collect_expert_reviews(request, (selection,))
    assert drafts1 == drafts2


def test_review_collector_returns_issue_drafts_without_ids() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    r1 = _make_review("r1", revision_id="rev1", decision=ReviewDecision.REJECTED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], expert_reviews=[r1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_expert_reviews(request, (selection,))
    assert isinstance(drafts, tuple)
    assert len(drafts) == 1
    draft = drafts[0]
    assert isinstance(draft, _IssueDraft)
    assert not hasattr(draft, "id")
    assert not isinstance(draft, PublicationIssue)


def test_global_finalization_with_preflight_content_evidence_permission_and_reviews() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        source_ids=["s1"],
        adaptation=AdaptationType.DIRECT_TRANSLATION,
        adaptation_note="Translated from EN",
    )
    r1 = _make_review("r1", revision_id="rev1", decision=ReviewDecision.REJECTED)

    catalog = _make_catalog(questions=[q1])
    registry = _make_registry(
        revisions=[rev1], evidence_links=[link1], sources=[s1], expert_reviews=[r1]
    )
    request = _make_request(catalog=catalog, registry=registry)

    app_questions, preflight_drafts = _collect_publication_preflight(request)
    selections, content_drafts = _collect_target_locale_content(request, app_questions)
    evidence_drafts = _collect_question_evidence(request, selections)
    permission_drafts = _collect_source_permissions(request, selections)
    review_drafts = _collect_expert_reviews(request, selections)

    all_drafts = (
        list(preflight_drafts)
        + list(content_drafts)
        + list(evidence_drafts)
        + list(permission_drafts)
        + list(review_drafts)
    )
    final_issues = _finalize_issues(all_drafts)

    assert len(final_issues) >= 3
    issue_ids = [issue.id for issue in final_issues]
    assert issue_ids == [f"publication_issue_{i:04d}" for i in range(1, len(final_issues) + 1)]


def test_review_helper_is_not_public_export() -> None:
    pkg = brif_ai.scientific.publication
    assert not hasattr(pkg, "_collect_expert_reviews")
    assert "_collect_expert_reviews" not in pkg.__all__
