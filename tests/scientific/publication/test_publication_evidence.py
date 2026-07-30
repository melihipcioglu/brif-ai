"""Unit tests for question evidence link validation service."""

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
    source_type: SourceType = SourceType.VALIDATED_INSTRUMENT,
) -> ScientificSource:
    return ScientificSource(
        id=source_id,
        source_type=source_type,
        title="Synthetic source title",
        authors=["Author One"],
        publication_year=2025,
        publication_or_publisher="Journal of Testing",
        identifier_type=IdentifierType.NONE,
        citation_text="Synthetic citation text",
        language="tr",
        usage_permission_status=UsagePermissionStatus.OPEN,
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
    source_id: str = "source_1",
    locale: str = "tr-TR",
) -> QuestionEvidenceLink:
    return QuestionEvidenceLink(
        id=link_id,
        question_content_revision_id=revision_id,
        construct_ids=[construct_id],
        source_ids=[source_id],
        evidence_relation=EvidenceRelation.QUESTION_WORDING_BASIS,
        claim_scope=ClaimScope.VALIDATED_ITEM,
        rationale="Synthetic rationale for evidence link",
        source_locator="Page 12, Table 3",
        adaptation_type=AdaptationType.ORIGINAL,
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


def test_evidence_present_for_selected_revision_produces_no_issue() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    link1 = _make_evidence_link("link1", revision_id="rev1")

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[link1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_question_evidence(request, (selection,))

    assert len(drafts) == 0


def test_direct_evidence_takes_precedence_over_other_revision_evidence() -> None:
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
    link1 = _make_evidence_link("link1", revision_id="rev1")
    link2 = _make_evidence_link("link2", revision_id="rev2")

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1, rev2], evidence_links=[link1, link2]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev2)

    drafts = _collect_question_evidence(request, (selection,))

    assert len(drafts) == 0


def test_missing_evidence_link_returns_error_draft() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1], evidence_links=[]),
        target_locale="tr-TR",
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_question_evidence(request, (selection,))

    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.EVIDENCE_LINK_MISSING
    assert draft.severity is PublicationIssueSeverity.ERROR
    assert draft.object_type is PublicationObjectType.QUESTION_CONTENT_REVISION
    assert draft.object_id == "rev1"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id == "rev1"
    assert draft.related_object_ids == ("q1",)
    assert "q1" in draft.message
    assert "rev1" in draft.message
    assert "tr-TR" in draft.message


def test_evidence_for_different_revision_returns_error_draft() -> None:
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
    link1 = _make_evidence_link("link1", revision_id="rev1")

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1, rev2], evidence_links=[link1]),
        target_locale="tr-TR",
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev2)

    drafts = _collect_question_evidence(request, (selection,))

    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.EVIDENCE_FOR_DIFFERENT_REVISION
    assert draft.severity is PublicationIssueSeverity.ERROR
    assert draft.object_type is PublicationObjectType.QUESTION_CONTENT_REVISION
    assert draft.object_id == "rev2"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id == "rev2"
    assert draft.related_object_ids == ("link1",)
    assert "q1" in draft.message
    assert "rev2" in draft.message
    assert "rev1" in draft.message
    assert "link1" in draft.message
    assert "tr-TR" in draft.message


def test_evidence_for_higher_numbered_draft_revision_is_still_detected() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision(
        "rev1", question_id="q1", revision_num=1, status=ContentRevisionStatus.APPROVED
    )
    rev2 = _make_revision(
        "rev2",
        question_id="q1",
        revision_num=2,
        status=ContentRevisionStatus.DRAFT,
        supersedes_revision_id="rev1",
    )
    link2 = _make_evidence_link("link2", revision_id="rev2")

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1, rev2], evidence_links=[link2]),
        target_locale="tr-TR",
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_question_evidence(request, (selection,))

    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.EVIDENCE_FOR_DIFFERENT_REVISION
    assert draft.object_id == "rev1"
    assert draft.related_object_ids == ("link2",)
    assert "rev2" in draft.message
    assert "link2" in draft.message


def test_other_question_evidence_does_not_count() -> None:
    q1 = _make_question("q1", display_order=1)
    q2 = _make_question("q2", display_order=2)
    rev1 = _make_revision("rev1", question_id="q1")
    rev2 = _make_revision("rev2", question_id="q2")
    link2 = _make_evidence_link("link2", revision_id="rev2")

    request = _make_request(
        catalog=_make_catalog([q1, q2]),
        registry=_make_registry(revisions=[rev1, rev2], evidence_links=[link2]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_question_evidence(request, (selection,))

    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.EVIDENCE_LINK_MISSING


def test_other_locale_revision_evidence_does_not_count() -> None:
    q1 = _make_question("q1")
    rev_tr = _make_revision("rev_tr", question_id="q1", locale="tr-TR")
    rev_en = _make_revision("rev_en", question_id="q1", locale="en-US")
    link_en = _make_evidence_link("link_en", revision_id="rev_en", locale="en-US")

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev_tr, rev_en], evidence_links=[link_en]),
        target_locale="tr-TR",
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev_tr)

    drafts = _collect_question_evidence(request, (selection,))

    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.EVIDENCE_LINK_MISSING


def test_multiple_other_revision_evidence_ids_are_sorted() -> None:
    q1 = _make_question("q1")
    rev_selected = _make_revision(
        "rev_selected",
        question_id="q1",
        revision_num=3,
        status=ContentRevisionStatus.APPROVED,
        supersedes_revision_id="rev_b",
    )
    rev_a = _make_revision(
        "rev_a", question_id="q1", revision_num=1, status=ContentRevisionStatus.RETIRED
    )
    rev_b = _make_revision(
        "rev_b",
        question_id="q1",
        revision_num=2,
        status=ContentRevisionStatus.RETIRED,
        supersedes_revision_id="rev_a",
    )
    link_z = _make_evidence_link("link_z", revision_id="rev_a")
    link_a = _make_evidence_link("link_a", revision_id="rev_b")

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(
            revisions=[rev_a, rev_b, rev_selected], evidence_links=[link_z, link_a]
        ),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev_selected)

    drafts = _collect_question_evidence(request, (selection,))

    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.EVIDENCE_FOR_DIFFERENT_REVISION
    assert drafts[0].related_object_ids == ("link_a", "link_z")


def test_different_revision_issue_replaces_generic_missing_issue() -> None:
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
    link1 = _make_evidence_link("link1", revision_id="rev1")

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(revisions=[rev1, rev2], evidence_links=[link1]),
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev2)

    drafts = _collect_question_evidence(request, (selection,))

    codes = [d.code for d in drafts]
    assert codes == [PublicationIssueCode.EVIDENCE_FOR_DIFFERENT_REVISION]
    assert PublicationIssueCode.EVIDENCE_LINK_MISSING not in codes


def test_missing_content_selection_skips_evidence_validation() -> None:
    q1 = _make_question("q1")
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry([]))
    selection = _QuestionContentSelection(question=q1, selected_revision=None)

    drafts = _collect_question_evidence(request, (selection,))

    assert len(drafts) == 0


def test_evidence_collector_preserves_selection_order() -> None:
    q1 = _make_question("q1", display_order=1)
    q2 = _make_question("q2", display_order=2)
    rev1 = _make_revision("rev1", question_id="q1")
    rev2 = _make_revision("rev2", question_id="q2")

    request = _make_request(
        catalog=_make_catalog([q1, q2]),
        registry=_make_registry(revisions=[rev1, rev2], evidence_links=[]),
    )
    sel1 = _QuestionContentSelection(question=q1, selected_revision=rev1)
    sel2 = _QuestionContentSelection(question=q2, selected_revision=rev2)

    drafts = _collect_question_evidence(request, (sel1, sel2))

    assert len(drafts) == 2
    assert drafts[0].question_id == "q1"
    assert drafts[1].question_id == "q2"


def test_evidence_collector_does_not_mutate_request() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry(revisions=[rev1]))
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    dump_before = request.model_dump()
    _collect_question_evidence(request, (selection,))
    dump_after = request.model_dump()

    assert dump_before == dump_after


def test_evidence_collector_is_deterministic() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry(revisions=[rev1]))
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts1 = _collect_question_evidence(request, (selection,))
    drafts2 = _collect_question_evidence(request, (selection,))

    assert drafts1 == drafts2


def test_evidence_collector_returns_issue_drafts_without_ids() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry(revisions=[rev1]))
    selection = _QuestionContentSelection(question=q1, selected_revision=rev1)

    drafts = _collect_question_evidence(request, (selection,))

    assert isinstance(drafts, tuple)
    assert len(drafts) == 1
    draft = drafts[0]
    assert isinstance(draft, _IssueDraft)
    assert not hasattr(draft, "id")
    assert not isinstance(draft, PublicationIssue)


def test_global_draft_finalization_with_preflight_content_and_evidence() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    # Catalog has q1, registry has rev1 (no evidence) plus a construct with unknown target
    construct_bad = _make_construct("c_bad", target_id="unknown_target")
    catalog = _make_catalog(questions=[q1])
    registry = _make_registry(revisions=[rev1], constructs=[construct_bad], evidence_links=[])
    request = _make_request(catalog=catalog, registry=registry)

    app_questions, preflight_drafts = _collect_publication_preflight(request)
    selections, content_drafts = _collect_target_locale_content(request, app_questions)
    evidence_drafts = _collect_question_evidence(request, selections)

    all_drafts = list(preflight_drafts) + list(content_drafts) + list(evidence_drafts)
    final_issues = _finalize_issues(all_drafts)

    assert len(final_issues) == 2
    assert final_issues[0].id == "publication_issue_0001"
    assert final_issues[1].id == "publication_issue_0002"
    assert {issue.code for issue in final_issues} == {
        PublicationIssueCode.CONSTRUCT_OUTPUT_TARGET_NOT_FOUND,
        PublicationIssueCode.EVIDENCE_LINK_MISSING,
    }


def test_evidence_helper_is_not_public_export() -> None:
    pkg = brif_ai.scientific.publication
    assert not hasattr(pkg, "_collect_question_evidence")
    assert "_collect_question_evidence" not in pkg.__all__


def test_different_revision_message_lists_only_revisions_with_evidence() -> None:
    q1 = _make_question("q1")
    rev_without_evidence = _make_revision(
        "rev_without_evidence",
        question_id="q1",
        revision_num=1,
        status=ContentRevisionStatus.RETIRED,
    )
    rev_with_evidence = _make_revision(
        "rev_with_evidence",
        question_id="q1",
        revision_num=2,
        status=ContentRevisionStatus.RETIRED,
        supersedes_revision_id="rev_without_evidence",
    )
    rev_selected = _make_revision(
        "rev_selected",
        question_id="q1",
        revision_num=3,
        status=ContentRevisionStatus.APPROVED,
        supersedes_revision_id="rev_with_evidence",
    )
    link = _make_evidence_link("evidence_link_with_evidence", revision_id="rev_with_evidence")

    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry(
            revisions=[rev_without_evidence, rev_with_evidence, rev_selected],
            evidence_links=[link],
        ),
        target_locale="tr-TR",
    )
    selection = _QuestionContentSelection(question=q1, selected_revision=rev_selected)

    drafts = _collect_question_evidence(request, (selection,))

    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.code is PublicationIssueCode.EVIDENCE_FOR_DIFFERENT_REVISION
    assert draft.related_object_ids == ("evidence_link_with_evidence",)
    assert "q1" in draft.message
    assert "rev_selected" in draft.message
    assert "rev_with_evidence" in draft.message
    assert "evidence_link_with_evidence" in draft.message
    assert "tr-TR" in draft.message
    assert "rev_without_evidence" not in draft.message
