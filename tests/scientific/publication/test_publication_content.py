"""Unit tests for target-locale question content revision selection service."""

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
    ContentRevisionStatus,
    QuestionContentRevision,
    ScientificContentRegistry,
)
from brif_ai.scientific.publication._content import (
    _collect_target_locale_content,
)
from brif_ai.scientific.publication._issues import _finalize_issues, _IssueDraft
from brif_ai.scientific.publication.common import (
    PublicationIssueCode,
    PublicationIssueSeverity,
    PublicationObjectType,
)
from brif_ai.scientific.publication.models import PublicationIssue, PublicationValidationRequest
from brif_ai.scientific.publication.preflight import _collect_publication_preflight

UTC_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)  # noqa: UP017


def _make_question(
    question_id: str = "question_1",
    content_key: str = "question.test_1",
    status: QuestionStatus = QuestionStatus.APPROVED,
    display_order: int = 1,
    source_metadata: str = "synthetic source metadata",
    module: ConversationModule = ConversationModule.PROJECT_CONTEXT,
) -> QuestionDefinition:
    return QuestionDefinition(
        id=question_id,
        module=module,
        purpose="Synthetic question purpose",
        content_key=content_key,
        answer_type=AnswerType.FREE_TEXT,
        required=True,
        output_target_ids=["target_1"],
        allowed_follow_up_question_ids=[],
        applicable_stakeholder_roles=["owner"],
        display_order=display_order,
        source_metadata=source_metadata,
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


def _make_catalog(
    questions: list[QuestionDefinition] | None = None,
) -> QuestionCatalog:
    target = InformationTargetDefinition(
        id="target_1",
        module=ConversationModule.PROJECT_CONTEXT,
        purpose="Synthetic target purpose",
        required=True,
        fulfillment_policy=FulfillmentPolicy.VALID_ANSWER,
    )
    if questions is None:
        questions = [_make_question("question_1")]
    modules = list({target.module} | {q.module for q in questions})
    return QuestionCatalog(
        id="catalog_1",
        schema_version="v0",
        catalog_version=1,
        modules=modules,
        information_targets=[target],
        questions=questions,
        transition_rules=[],
    )


def _make_registry(
    revisions: list[QuestionContentRevision] | None = None,
) -> ScientificContentRegistry:
    return ScientificContentRegistry(
        id="registry_1",
        schema_version="v0",
        registry_version=1,
        question_catalog_id="catalog_1",
        question_catalog_version=1,
        content_bundle_version=1,
        created_at=UTC_TIME,
        sources=[],
        constructs=[],
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


def test_selects_approved_revision_for_target_locale() -> None:
    q1 = _make_question("q1", content_key="question.q1")
    rev1 = _make_revision("rev1", question_id="q1", locale="tr-TR", content_key="question.q1")
    catalog = _make_catalog(questions=[q1])
    registry = _make_registry(revisions=[rev1])
    request = _make_request(catalog=catalog, registry=registry, target_locale="tr-TR")

    selections, drafts = _collect_target_locale_content(request, (q1,))

    assert len(selections) == 1
    assert selections[0].question is q1
    assert selections[0].selected_revision is rev1
    assert len(drafts) == 0


def test_selection_preserves_approved_question_order() -> None:
    q1 = _make_question("q1", display_order=1)
    q2 = _make_question("q2", display_order=2)
    rev1 = _make_revision("rev1", question_id="q1", locale="tr-TR")
    rev2 = _make_revision("rev2", question_id="q2", locale="tr-TR")
    catalog = _make_catalog(questions=[q1, q2])
    registry = _make_registry(revisions=[rev1, rev2])
    request = _make_request(catalog=catalog, registry=registry)

    selections, _ = _collect_target_locale_content(request, (q1, q2))

    assert len(selections) == 2
    assert selections[0].question is q1
    assert selections[1].question is q2


def test_returns_original_question_and_revision_objects() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry([rev1]))

    selections, _ = _collect_target_locale_content(request, (q1,))

    assert selections[0].question is q1
    assert selections[0].selected_revision is rev1


def test_missing_target_locale_revision_returns_error_draft() -> None:
    q1 = _make_question("q1")
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry([]))

    selections, drafts = _collect_target_locale_content(request, (q1,))

    assert len(selections) == 1
    assert selections[0].selected_revision is None
    assert len(drafts) == 1

    draft = drafts[0]
    assert draft.code is PublicationIssueCode.APPROVED_CONTENT_REVISION_MISSING
    assert draft.severity is PublicationIssueSeverity.ERROR
    assert draft.object_type is PublicationObjectType.QUESTION_DEFINITION
    assert draft.object_id == "q1"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id is None
    assert draft.related_object_ids == ()
    assert "q1" in draft.message
    assert "tr-TR" in draft.message


def test_approved_revision_in_other_locale_does_not_satisfy_target_locale() -> None:
    q1 = _make_question("q1")
    rev_en = _make_revision("rev_en", question_id="q1", locale="en-US")
    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry([rev_en]),
        target_locale="tr-TR",
    )

    selections, drafts = _collect_target_locale_content(request, (q1,))

    assert selections[0].selected_revision is None
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.APPROVED_CONTENT_REVISION_MISSING


def test_draft_target_locale_revision_is_not_selected() -> None:
    q1 = _make_question("q1")
    rev_draft = _make_revision(
        "rev_draft",
        question_id="q1",
        locale="tr-TR",
        status=ContentRevisionStatus.DRAFT,
    )
    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry([rev_draft]),
        target_locale="tr-TR",
    )

    selections, drafts = _collect_target_locale_content(request, (q1,))

    assert selections[0].selected_revision is None
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.APPROVED_CONTENT_REVISION_MISSING
    assert drafts[0].related_object_ids == ("rev_draft",)


def test_under_review_target_locale_revision_is_not_selected() -> None:
    q1 = _make_question("q1")
    rev_ur = _make_revision(
        "rev_ur",
        question_id="q1",
        locale="tr-TR",
        status=ContentRevisionStatus.UNDER_REVIEW,
    )
    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry([rev_ur]),
        target_locale="tr-TR",
    )

    selections, drafts = _collect_target_locale_content(request, (q1,))

    assert selections[0].selected_revision is None
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.APPROVED_CONTENT_REVISION_MISSING
    assert drafts[0].related_object_ids == ("rev_ur",)


def test_retired_target_locale_revision_is_not_selected() -> None:
    q1 = _make_question("q1")
    rev_ret = _make_revision(
        "rev_ret",
        question_id="q1",
        locale="tr-TR",
        status=ContentRevisionStatus.RETIRED,
    )
    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry([rev_ret]),
        target_locale="tr-TR",
    )

    selections, drafts = _collect_target_locale_content(request, (q1,))

    assert selections[0].selected_revision is None
    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.APPROVED_CONTENT_REVISION_MISSING
    assert drafts[0].related_object_ids == ("rev_ret",)


def test_nonapproved_target_locale_revision_ids_are_sorted_in_missing_issue() -> None:
    q1 = _make_question("q1")
    rev_z = _make_revision(
        "rev_z",
        question_id="q1",
        locale="tr-TR",
        revision_num=1,
        status=ContentRevisionStatus.RETIRED,
    )
    rev_a = _make_revision(
        "rev_a",
        question_id="q1",
        locale="tr-TR",
        revision_num=2,
        status=ContentRevisionStatus.DRAFT,
        supersedes_revision_id="rev_z",
    )
    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry([rev_z, rev_a]),
        target_locale="tr-TR",
    )

    selections, drafts = _collect_target_locale_content(request, (q1,))

    assert selections[0].selected_revision is None
    assert len(drafts) == 1
    assert drafts[0].related_object_ids == ("rev_a", "rev_z")


def test_missing_revision_without_any_target_locale_content_has_empty_related_ids() -> None:
    q1 = _make_question("q1")
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry([]))

    _, drafts = _collect_target_locale_content(request, (q1,))

    assert drafts[0].related_object_ids == ()


def test_matching_content_key_produces_no_issue() -> None:
    q1 = _make_question("q1", content_key="question.match")
    rev1 = _make_revision("rev1", question_id="q1", content_key="question.match")
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry([rev1]))

    selections, drafts = _collect_target_locale_content(request, (q1,))

    assert selections[0].selected_revision is rev1
    assert len(drafts) == 0


def test_content_key_mismatch_returns_error_draft() -> None:
    q1 = _make_question("q1", content_key="question.q1")
    rev1 = _make_revision("rev1", question_id="q1", content_key="question.mismatch")
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry([rev1]))

    selections, drafts = _collect_target_locale_content(request, (q1,))

    assert selections[0].selected_revision is rev1
    assert len(drafts) == 1

    draft = drafts[0]
    assert draft.code is PublicationIssueCode.CONTENT_KEY_MISMATCH
    assert draft.severity is PublicationIssueSeverity.ERROR
    assert draft.object_type is PublicationObjectType.QUESTION_CONTENT_REVISION
    assert draft.object_id == "rev1"
    assert draft.question_id == "q1"
    assert draft.question_content_revision_id == "rev1"
    assert draft.related_object_ids == ("q1",)
    assert "q1" in draft.message
    assert "question.q1" in draft.message
    assert "rev1" in draft.message
    assert "question.mismatch" in draft.message


def test_content_key_comparison_is_case_sensitive() -> None:
    q1 = _make_question("q1", content_key="question.q1")
    rev1 = _make_revision("rev1", question_id="q1", content_key="QUESTION.Q1")
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry([rev1]))

    _, drafts = _collect_target_locale_content(request, (q1,))

    assert len(drafts) == 1
    assert drafts[0].code is PublicationIssueCode.CONTENT_KEY_MISMATCH


def test_content_key_mismatch_still_returns_selected_revision() -> None:
    q1 = _make_question("q1", content_key="question.q1")
    rev1 = _make_revision("rev1", question_id="q1", content_key="question.different")
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry([rev1]))

    selections, _ = _collect_target_locale_content(request, (q1,))

    assert selections[0].selected_revision is rev1


def test_empty_approved_question_input_returns_empty_results() -> None:
    request = _make_request()

    selections, drafts = _collect_target_locale_content(request, ())

    assert selections == ()
    assert drafts == ()


def test_collector_does_not_mutate_request() -> None:
    q1 = _make_question("q1")
    rev1 = _make_revision("rev1", question_id="q1")
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry([rev1]))

    dump_before = request.model_dump()
    _collect_target_locale_content(request, (q1,))
    dump_after = request.model_dump()

    assert dump_before == dump_after


def test_other_locale_content_does_not_change_selected_target_revision() -> None:
    q1 = _make_question("q1")
    rev_tr = _make_revision("rev_tr", question_id="q1", locale="tr-TR")
    rev_en = _make_revision("rev_en", question_id="q1", locale="en-US")
    request = _make_request(
        catalog=_make_catalog([q1]),
        registry=_make_registry([rev_tr, rev_en]),
        target_locale="tr-TR",
    )

    selections, drafts = _collect_target_locale_content(request, (q1,))

    assert selections[0].selected_revision is rev_tr
    assert len(drafts) == 0


def test_source_metadata_does_not_affect_content_selection() -> None:
    q1 = _make_question("q1", source_metadata="meta A")
    q2 = _make_question("q1", source_metadata="meta B (different)")
    rev1 = _make_revision("rev1", question_id="q1")

    req1 = _make_request(catalog=_make_catalog([q1]), registry=_make_registry([rev1]))
    req2 = _make_request(catalog=_make_catalog([q2]), registry=_make_registry([rev1]))

    sel1, draft1 = _collect_target_locale_content(req1, (q1,))
    sel2, draft2 = _collect_target_locale_content(req2, (q2,))

    assert sel1[0].selected_revision is sel2[0].selected_revision
    assert draft1 == draft2


def test_collector_returns_issue_drafts_without_final_ids() -> None:
    q1 = _make_question("q1")
    request = _make_request(catalog=_make_catalog([q1]), registry=_make_registry([]))

    selections, drafts = _collect_target_locale_content(request, (q1,))

    assert isinstance(drafts, tuple)
    assert len(drafts) == 1
    draft = drafts[0]
    assert isinstance(draft, _IssueDraft)
    assert not hasattr(draft, "id")
    assert not isinstance(draft, PublicationIssue)


def test_content_drafts_can_be_combined_with_preflight_drafts_and_finalized_globally() -> None:
    q1 = _make_question("q1")
    rev_missing = _make_revision("rev_unknown", question_id="missing_q")
    registry = _make_registry(revisions=[rev_missing])
    catalog = _make_catalog(questions=[q1])
    request = _make_request(catalog=catalog, registry=registry)

    app_questions, preflight_drafts = _collect_publication_preflight(request)
    selections, content_drafts = _collect_target_locale_content(request, app_questions)

    all_drafts = list(preflight_drafts) + list(content_drafts)
    final_issues = _finalize_issues(all_drafts)

    assert len(final_issues) == 2
    assert final_issues[0].id == "publication_issue_0001"
    assert final_issues[1].id == "publication_issue_0002"
    assert {issue.code for issue in final_issues} == {
        PublicationIssueCode.REGISTRY_QUESTION_NOT_FOUND_IN_CATALOG,
        PublicationIssueCode.APPROVED_CONTENT_REVISION_MISSING,
    }


def test_content_helpers_are_not_public_exports() -> None:
    pkg = brif_ai.scientific.publication
    private_symbols = ["_QuestionContentSelection", "_collect_target_locale_content"]
    for symbol in private_symbols:
        assert not hasattr(pkg, symbol)
        assert symbol not in pkg.__all__
