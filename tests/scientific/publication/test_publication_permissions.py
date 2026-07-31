"""Unit tests for source usage permission validation service."""

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
    IdentifierType,
    QuestionContentRevision,
    QuestionEvidenceLink,
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
    notes: str | None = None,
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
        notes=notes,
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


def test_open_permission_source_produces_no_issue() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.OPEN)
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s1"])

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 0


def test_permission_granted_source_produces_no_issue() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_GRANTED)
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s1"])

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 0


def test_not_applicable_permission_source_produces_no_issue() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.NOT_APPLICABLE)
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s1"])

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 0


def test_permission_required_item_use_produces_error_draft() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s1"])

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.SOURCE_PERMISSION_REQUIRED
    assert draft.severity is PublicationIssueSeverity.ERROR
    assert draft.severity.is_blocking is True
    assert draft.object_type is PublicationObjectType.SCIENTIFIC_SOURCE
    assert draft.object_id == "s1"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id == "rev1"
    assert draft.related_object_ids == ("link1",)
    assert "s1" in draft.message
    assert "PERMISSION_REQUIRED" in draft.message
    assert "publication-safety policy" in draft.message


def test_permission_required_concept_use_produces_error_draft() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.CONSTRUCT_BASIS,
        claim=ClaimScope.CONCEPT_SUPPORTED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.SOURCE_PERMISSION_REQUIRED
    assert draft.severity is PublicationIssueSeverity.ERROR
    assert draft.severity.is_blocking is True
    assert draft.related_object_ids == ("link1",)


def test_unknown_wording_basis_produces_item_error() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.UNKNOWN)
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.QUESTION_WORDING_BASIS,
        claim=ClaimScope.CONCEPT_SUPPORTED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_ITEM_USE
    assert draft.severity is PublicationIssueSeverity.ERROR
    assert draft.severity.is_blocking is True
    assert draft.object_type is PublicationObjectType.SCIENTIFIC_SOURCE
    assert draft.object_id == "s1"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id == "rev1"
    assert draft.related_object_ids == ("link1",)
    assert "item-sensitive" in draft.message


def test_unknown_response_format_basis_produces_item_error() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.UNKNOWN)
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.RESPONSE_FORMAT_BASIS,
        claim=ClaimScope.CONCEPT_SUPPORTED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_ITEM_USE
    assert drafts[0].severity is PublicationIssueSeverity.ERROR


def test_unknown_concept_use_produces_warning_draft() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.UNKNOWN)
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.CONSTRUCT_BASIS,
        claim=ClaimScope.CONCEPT_SUPPORTED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_CONCEPT_USE
    assert draft.severity is PublicationIssueSeverity.WARNING
    assert draft.severity.is_blocking is False
    assert draft.object_type is PublicationObjectType.SCIENTIFIC_SOURCE
    assert draft.object_id == "s1"
    assert draft.related_object_ids == ("link1",)
    assert "concept-sensitive" in draft.message


def test_expert_authored_construct_basis_unknown_source_produces_concept_warning() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.UNKNOWN)
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.CONSTRUCT_BASIS,
        claim=ClaimScope.EXPERT_AUTHORED,
        adaptation=AdaptationType.EXPERT_AUTHORED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_CONCEPT_USE
    assert drafts[0].severity is PublicationIssueSeverity.WARNING


def test_expert_authored_wording_basis_unknown_source_produces_item_error() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.UNKNOWN)
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.QUESTION_WORDING_BASIS,
        claim=ClaimScope.EXPERT_AUTHORED,
        adaptation=AdaptationType.EXPERT_AUTHORED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_ITEM_USE
    assert drafts[0].severity is PublicationIssueSeverity.ERROR


def test_question_derived_claim_with_concept_relation_is_item_sensitive() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.UNKNOWN)
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.CONSTRUCT_BASIS,
        claim=ClaimScope.QUESTION_DERIVED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_ITEM_USE


def test_direct_translation_with_concept_relation_is_item_sensitive() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.UNKNOWN)
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.CONSTRUCT_BASIS,
        claim=ClaimScope.CONCEPT_SUPPORTED,
        adaptation=AdaptationType.DIRECT_TRANSLATION,
        adaptation_note="Translation note",
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_ITEM_USE


def test_same_source_item_and_concept_links_defaults_to_one_item_error() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.UNKNOWN)
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.CONSTRUCT_BASIS,
        claim=ClaimScope.CONCEPT_SUPPORTED,
    )
    link2 = _make_evidence_link(
        "link2",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.QUESTION_WORDING_BASIS,
        claim=ClaimScope.VALIDATED_ITEM,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1, link2], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_ITEM_USE
    assert draft.related_object_ids == ("link1", "link2")


def test_ambiguous_risk_screening_relation_defaults_to_item_error() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.UNKNOWN)
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.RISK_OR_SCREENING_BASIS,
        claim=ClaimScope.EXPERT_AUTHORED,
        adaptation=AdaptationType.EXPERT_AUTHORED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_ITEM_USE


def test_validated_instrument_source_type_alone_does_not_force_item_use() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source(
        "s1", status=UsagePermissionStatus.UNKNOWN, source_type=SourceType.VALIDATED_INSTRUMENT
    )
    link1 = _make_evidence_link(
        "link1",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.CONSTRUCT_BASIS,
        claim=ClaimScope.CONCEPT_SUPPORTED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_CONCEPT_USE
    assert drafts[0].severity is PublicationIssueSeverity.WARNING


def test_missing_content_selection_skips_permission_validation() -> None:
    q1 = _make_question("q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry(sources=[s1]))
    selection = _QuestionContentSelection(question=q1, selected_revision=None)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 0


def test_revision_without_direct_evidence_skips_permission_validation() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 0


def test_evidence_only_for_other_revision_is_ignored() -> None:
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
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s1"])

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1, rev2], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev2)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 0


def test_multiple_links_same_source_deduplicates_drafts_and_sorts_related_ids() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    link2 = _make_evidence_link("link2", revision_id="rev1", source_ids=["s1"])
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s1"])

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link2, link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    assert drafts[0].related_object_ids == ("link1", "link2")
    assert "s1" not in drafts[0].related_object_ids


def test_different_questions_same_source_produces_separate_drafts() -> None:
    q1 = _make_question("q1", display_order=1)
    q2 = _make_question("q2", display_order=2)
    rev1 = _make_revision("rev1", question_id="q1")
    rev2 = _make_revision("rev2", question_id="q2")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s1"])
    link2 = _make_evidence_link("link2", revision_id="rev2", source_ids=["s1"])

    request = _make_request(
        catalog=_make_catalog([q1, q2]),
        registry=_make_registry(
            revisions=[rev1, rev2], evidence_links=[link1, link2], sources=[s1]
        ),
    )
    sel1 = _QuestionContentSelection(question=q1, selected_revision=rev1)
    sel2 = _QuestionContentSelection(question=q2, selected_revision=rev2)

    drafts = _collect_source_permissions(request, (sel1, sel2))
    assert len(drafts) == 2
    assert drafts[0].question_id == "q1"
    assert drafts[0].related_object_ids == ("link1",)
    assert drafts[1].question_id == "q2"
    assert drafts[1].related_object_ids == ("link2",)


def test_multiple_sources_in_same_link_are_evaluated_independently_in_source_id_order() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    sb = _make_source("s_b", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    sa = _make_source("s_a", status=UsagePermissionStatus.UNKNOWN)
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s_b", "s_a"])

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[sb, sa]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 2
    assert drafts[0].object_id == "s_a"
    assert drafts[0].code is PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_ITEM_USE
    assert drafts[0].related_object_ids == ("link1",)

    assert drafts[1].object_id == "s_b"
    assert drafts[1].code is PublicationIssueCode.SOURCE_PERMISSION_REQUIRED
    assert drafts[1].related_object_ids == ("link1",)


def test_permission_collector_preserves_selection_order() -> None:
    q1 = _make_question("q1", display_order=1)
    q2 = _make_question("q2", display_order=2)
    rev1 = _make_revision("rev1", question_id="q1")
    rev2 = _make_revision("rev2", question_id="q2")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    s2 = _make_source("s2", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s1"])
    link2 = _make_evidence_link("link2", revision_id="rev2", source_ids=["s2"])

    request = _make_request(
        catalog=_make_catalog([q1, q2]),
        registry=_make_registry(
            revisions=[rev1, rev2], evidence_links=[link1, link2], sources=[s1, s2]
        ),
    )
    sel1 = _QuestionContentSelection(question=q1, selected_revision=rev1)
    sel2 = _QuestionContentSelection(question=q2, selected_revision=rev2)

    drafts = _collect_source_permissions(request, (sel1, sel2))
    assert len(drafts) == 2
    assert drafts[0].question_id == "q1"
    assert drafts[1].question_id == "q2"


def test_permission_collector_does_not_mutate_request() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s1"])

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    dump_before = request.model_dump()
    _collect_source_permissions(request, (selection,))
    dump_after = request.model_dump()

    assert dump_before == dump_after


def test_permission_collector_is_deterministic() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s1"])

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts1 = _collect_source_permissions(request, (selection,))
    drafts2 = _collect_source_permissions(request, (selection,))
    assert drafts1 == drafts2


def test_permission_collector_returns_issue_drafts_without_ids() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s1"])

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert isinstance(drafts, tuple)
    assert len(drafts) == 1
    draft = drafts[0]
    assert isinstance(draft, _IssueDraft)
    assert not hasattr(draft, "id")
    assert not isinstance(draft, PublicationIssue)


def test_source_notes_do_not_override_permission_status() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source(
        "s1",
        status=UsagePermissionStatus.PERMISSION_GRANTED,
        notes="Note stating permission expired or is required",
    )
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s1"])

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 0


def test_global_draft_finalization_with_preflight_content_evidence_and_permissions() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.PERMISSION_REQUIRED)
    link1 = _make_evidence_link("link1", revision_id="rev1", source_ids=["s1"])

    catalog = _make_catalog(questions=[q1])
    registry = _make_registry(revisions=[rev1], evidence_links=[link1], sources=[s1])
    request = _make_request(catalog=catalog, registry=registry)

    app_questions, preflight_drafts = _collect_publication_preflight(request)
    selections, content_drafts = _collect_target_locale_content(request, app_questions)
    evidence_drafts = _collect_question_evidence(request, selections)
    permission_drafts = _collect_source_permissions(request, selections)

    all_drafts = (
        list(preflight_drafts)
        + list(content_drafts)
        + list(evidence_drafts)
        + list(permission_drafts)
    )
    final_issues = _finalize_issues(all_drafts)

    assert len(final_issues) == 1
    assert final_issues[0].id == "publication_issue_0001"
    assert final_issues[0].code is PublicationIssueCode.SOURCE_PERMISSION_REQUIRED


def test_permission_helper_is_not_public_export() -> None:
    pkg = brif_ai.scientific.publication
    assert not hasattr(pkg, "_collect_source_permissions")
    assert "_collect_source_permissions" not in pkg.__all__


def test_same_source_concept_and_ambiguous_links_defaults_to_item_error() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    s1 = _make_source("s1", status=UsagePermissionStatus.UNKNOWN)
    link_concept = _make_evidence_link(
        "link_concept",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.CONSTRUCT_BASIS,
        claim=ClaimScope.CONCEPT_SUPPORTED,
        adaptation=AdaptationType.ORIGINAL,
    )
    link_ambiguous = _make_evidence_link(
        "link_ambiguous",
        revision_id="rev1",
        source_ids=["s1"],
        relation=EvidenceRelation.RISK_OR_SCREENING_BASIS,
        claim=ClaimScope.EXPERT_AUTHORED,
        adaptation=AdaptationType.EXPERT_AUTHORED,
    )

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(
            revisions=[rev1],
            evidence_links=[link_concept, link_ambiguous],
            sources=[s1],
        ),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_source_permissions(request, (selection,))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_ITEM_USE
    assert draft.severity is PublicationIssueSeverity.ERROR
    assert draft.severity.is_blocking is True
    assert draft.object_type is PublicationObjectType.SCIENTIFIC_SOURCE
    assert draft.object_id == "s1"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id == "rev1"
    assert draft.related_object_ids == ("link_ambiguous", "link_concept")
    assert "item-sensitive" in draft.message
