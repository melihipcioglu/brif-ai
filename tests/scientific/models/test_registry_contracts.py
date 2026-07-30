from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from brif_ai.conversation.models import ConversationModule
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

UTC_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)  # noqa: UP017
NON_UTC_TIME = datetime(2026, 1, 1, 15, 0, tzinfo=timezone(timedelta(hours=3)))


def _source(
    source_id: str = "source_1",
    *,
    source_type: SourceType = SourceType.PEER_REVIEWED_ARTICLE,
    authors: list[str] | None = None,
    identifier_type: IdentifierType = IdentifierType.DOI,
    identifier_value: str | None = "placeholder-identifier",
) -> ScientificSource:
    return ScientificSource(
        id=source_id,
        source_type=source_type,
        title="Placeholder source title",
        authors=authors if authors is not None else ["Placeholder Author"],
        publication_year=2026,
        publication_or_publisher="Placeholder publisher",
        identifier_type=identifier_type,
        identifier_value=identifier_value,
        citation_text="Placeholder citation text.",
        language="en",
        usage_permission_status=UsagePermissionStatus.OPEN,
        notes=None,
    )


def _construct(
    construct_id: str = "construct_1",
    *,
    expected_output_target_ids: list[str] | None = None,
) -> ConstructDefinition:
    return ConstructDefinition(
        id=construct_id,
        name="Placeholder construct",
        definition="Placeholder construct definition.",
        conversation_module=ConversationModule.PROJECT_CONTEXT,
        architectural_relevance="Placeholder architectural relevance.",
        expected_output_target_ids=(
            expected_output_target_ids if expected_output_target_ids is not None else ["target_1"]
        ),
        scope_note=None,
    )


def _revision(
    revision_id: str = "revision_1",
    *,
    question_id: str = "question_1",
    locale: str = "tr-TR",
    revision: int = 1,
    status: ContentRevisionStatus = ContentRevisionStatus.APPROVED,
    created_at: datetime = UTC_TIME,
    supersedes_revision_id: str | None = None,
) -> QuestionContentRevision:
    return QuestionContentRevision(
        id=revision_id,
        question_id=question_id,
        locale=locale,
        revision=revision,
        content_key=f"scientific.placeholder.{revision_id}",
        wording="Placeholder wording for contract tests only.",
        respondent_instruction=None,
        status=status,
        created_at=created_at,
        supersedes_revision_id=supersedes_revision_id,
    )


def _evidence_link(
    link_id: str = "evidence_link_1",
    *,
    revision_id: str = "revision_1",
    construct_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
    claim_scope: ClaimScope = ClaimScope.CONCEPT_SUPPORTED,
    adaptation_type: AdaptationType = AdaptationType.NOT_APPLICABLE,
    adaptation_note: str | None = None,
    target_locale: str = "tr-TR",
    source_locator: str = "placeholder section",
) -> QuestionEvidenceLink:
    return QuestionEvidenceLink(
        id=link_id,
        question_content_revision_id=revision_id,
        construct_ids=construct_ids if construct_ids is not None else ["construct_1"],
        source_ids=source_ids if source_ids is not None else ["source_1"],
        evidence_relation=EvidenceRelation.CONSTRUCT_BASIS,
        claim_scope=claim_scope,
        rationale="Placeholder rationale.",
        source_locator=source_locator,
        adaptation_type=adaptation_type,
        adaptation_note=adaptation_note,
        target_locale=target_locale,
    )


def _review(
    review_id: str = "review_1",
    *,
    revision_id: str = "revision_1",
    evidence_link_ids: list[str] | None = None,
    decision: ReviewDecision = ReviewDecision.APPROVED,
    reviewed_at: datetime = UTC_TIME,
    rationale: str | None = "Placeholder review rationale.",
    required_changes: str | None = None,
) -> ExpertReviewRecord:
    return ExpertReviewRecord(
        id=review_id,
        question_content_revision_id=revision_id,
        evidence_link_ids=(
            evidence_link_ids if evidence_link_ids is not None else ["evidence_link_1"]
        ),
        reviewer_reference="reviewer_ref",
        reviewer_role="reviewer_role",
        review_area=ReviewArea.ARCHITECTURAL_PROGRAMMING,
        decision=decision,
        reviewed_at=reviewed_at,
        rationale=rationale,
        required_changes=required_changes,
    )


def _evaluation(
    evaluation_id: str = "evaluation_1",
    *,
    revision_id: str = "revision_1",
    locale: str = "tr-TR",
    evaluation_type: EvaluationType = EvaluationType.READABILITY_REVIEW,
    conducted_at: datetime = UTC_TIME,
    participant_count: int | None = None,
    result: EvaluationResult = EvaluationResult.PASSED,
    identified_issues: list[str] | None = None,
    revision_required: bool = False,
) -> ContentEvaluationRecord:
    return ContentEvaluationRecord(
        id=evaluation_id,
        question_content_revision_id=revision_id,
        evaluation_type=evaluation_type,
        locale=locale,
        conducted_at=conducted_at,
        participant_count=participant_count,
        result=result,
        summary="Placeholder evaluation summary.",
        identified_issues=identified_issues if identified_issues is not None else [],
        revision_required=revision_required,
    )


def _registry(
    *,
    registry_id: str = "registry_1",
    created_at: datetime = UTC_TIME,
    sources: list[ScientificSource] | None = None,
    constructs: list[ConstructDefinition] | None = None,
    revisions: list[QuestionContentRevision] | None = None,
    evidence_links: list[QuestionEvidenceLink] | None = None,
    expert_reviews: list[ExpertReviewRecord] | None = None,
    evaluations: list[ContentEvaluationRecord] | None = None,
) -> ScientificContentRegistry:
    return ScientificContentRegistry(
        id=registry_id,
        schema_version="scientific.registry.v0",
        registry_version=1,
        question_catalog_id="catalog_1",
        question_catalog_version=1,
        content_bundle_version=1,
        created_at=created_at,
        sources=sources if sources is not None else [_source()],
        constructs=constructs if constructs is not None else [_construct()],
        question_content_revisions=revisions if revisions is not None else [_revision()],
        evidence_links=evidence_links if evidence_links is not None else [_evidence_link()],
        expert_reviews=expert_reviews if expert_reviews is not None else [_review()],
        evaluations=evaluations if evaluations is not None else [_evaluation()],
    )


def test_valid_minimum_scientific_content_registry() -> None:
    registry = _registry()

    assert registry.id == "registry_1"
    assert registry.question_catalog_id == "catalog_1"
    assert registry.sources[0].source_type is SourceType.PEER_REVIEWED_ARTICLE


def test_rejects_invalid_registry_id() -> None:
    with pytest.raises(ValidationError) as error:
        _registry(registry_id="Registry 1")

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("id",)
    assert first_error["type"] == "string_pattern_mismatch"


def test_rejects_duplicate_id_across_registry_object_types() -> None:
    with pytest.raises(ValidationError) as error:
        _registry(sources=[_source("construct_1")])

    assert "duplicate object id 'construct_1'" in str(error.value)


def test_rejects_duplicate_source_authors() -> None:
    with pytest.raises(ValidationError) as error:
        _source(authors=["Placeholder Author", "Placeholder Author"])

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("authors",)
    assert "duplicate author 'Placeholder Author'" in str(error.value)


def test_identifier_none_rejects_identifier_value() -> None:
    with pytest.raises(ValidationError) as error:
        _source(identifier_type=IdentifierType.NONE, identifier_value="placeholder")

    assert "identifier_value is not allowed" in str(error.value)


def test_non_none_identifier_requires_value() -> None:
    with pytest.raises(ValidationError) as error:
        _source(identifier_type=IdentifierType.DOI, identifier_value=None)

    assert "identifier_value is required" in str(error.value)


def test_rejects_unknown_source_reference() -> None:
    with pytest.raises(ValidationError) as error:
        _registry(evidence_links=[_evidence_link(source_ids=["missing_source"])])

    assert "source_id 'missing_source'" in str(error.value)


def test_rejects_unknown_construct_reference() -> None:
    with pytest.raises(ValidationError) as error:
        _registry(evidence_links=[_evidence_link(construct_ids=["missing_construct"])])

    assert "construct_id 'missing_construct'" in str(error.value)


def test_rejects_unknown_question_content_revision_reference() -> None:
    with pytest.raises(ValidationError) as error:
        _registry(evidence_links=[_evidence_link(revision_id="missing_revision")])

    assert "question_content_revision_id 'missing_revision'" in str(error.value)


def test_rejects_unknown_expert_review_evidence_link() -> None:
    with pytest.raises(ValidationError) as error:
        _registry(expert_reviews=[_review(evidence_link_ids=["missing_link"])])

    assert "evidence_link_id 'missing_link'" in str(error.value)


def test_rejects_review_link_for_different_revision() -> None:
    revisions = [
        _revision("revision_1"),
        _revision(
            "revision_2",
            revision=2,
            status=ContentRevisionStatus.DRAFT,
            supersedes_revision_id="revision_1",
        ),
    ]

    with pytest.raises(ValidationError) as error:
        _registry(
            revisions=revisions,
            expert_reviews=[
                _review(revision_id="revision_2", evidence_link_ids=["evidence_link_1"])
            ],
        )

    assert "different question_content_revision_id" in str(error.value)


def test_rejects_naive_registry_created_at() -> None:
    with pytest.raises(ValidationError) as error:
        _registry(created_at=datetime(2026, 1, 1, 12, 0))

    assert "created_at must be timezone-aware" in str(error.value)


def test_rejects_non_utc_registry_created_at() -> None:
    with pytest.raises(ValidationError) as error:
        _registry(created_at=NON_UTC_TIME)

    assert "created_at must use UTC offset" in str(error.value)


def test_rejects_naive_revision_created_at() -> None:
    with pytest.raises(ValidationError) as error:
        _revision(created_at=datetime(2026, 1, 1, 12, 0))

    assert "created_at must be timezone-aware" in str(error.value)


def test_rejects_non_utc_reviewed_at() -> None:
    with pytest.raises(ValidationError) as error:
        _review(reviewed_at=NON_UTC_TIME)

    assert "reviewed_at must use UTC offset" in str(error.value)


def test_rejects_non_utc_evaluation_conducted_at() -> None:
    with pytest.raises(ValidationError) as error:
        _evaluation(conducted_at=NON_UTC_TIME)

    assert "conducted_at must use UTC offset" in str(error.value)


def test_revision_one_rejects_supersedes_reference() -> None:
    with pytest.raises(ValidationError) as error:
        _revision(supersedes_revision_id="revision_0")

    assert "revision 1 cannot define supersedes_revision_id" in str(error.value)


def test_later_revision_requires_supersedes_reference() -> None:
    with pytest.raises(ValidationError) as error:
        _revision("revision_2", revision=2)

    assert "revision greater than 1 requires supersedes_revision_id" in str(error.value)


def test_rejects_unknown_superseded_revision() -> None:
    revisions = [
        _revision("revision_1"),
        _revision(
            "revision_2",
            revision=2,
            status=ContentRevisionStatus.DRAFT,
            supersedes_revision_id="missing_revision",
        ),
    ]

    with pytest.raises(ValidationError) as error:
        _registry(revisions=revisions)

    assert "supersedes_revision_id 'missing_revision'" in str(error.value)


def test_rejects_superseding_revision_for_different_question() -> None:
    revisions = [
        _revision("revision_1"),
        _revision(
            "revision_2",
            question_id="question_2",
            revision=2,
            status=ContentRevisionStatus.DRAFT,
            supersedes_revision_id="revision_1",
        ),
    ]

    with pytest.raises(ValidationError) as error:
        _registry(revisions=revisions)

    assert "different question_id" in str(error.value)


def test_rejects_superseding_revision_for_different_locale() -> None:
    revisions = [
        _revision("revision_1"),
        _revision(
            "revision_2",
            locale="en-GB",
            revision=2,
            status=ContentRevisionStatus.DRAFT,
            supersedes_revision_id="revision_1",
        ),
    ]

    with pytest.raises(ValidationError) as error:
        _registry(revisions=revisions)

    assert "different locale" in str(error.value)


def test_rejects_superseding_newer_or_same_revision_number() -> None:
    revisions = [
        _revision("revision_1"),
        _revision(
            "revision_2",
            revision=3,
            status=ContentRevisionStatus.RETIRED,
            supersedes_revision_id="revision_1",
        ),
        _revision(
            "revision_3",
            revision=2,
            status=ContentRevisionStatus.DRAFT,
            supersedes_revision_id="revision_2",
        ),
    ]

    with pytest.raises(ValidationError) as error:
        _registry(revisions=revisions)

    assert "must supersede a lower revision number" in str(error.value)


def test_rejects_duplicate_question_locale_revision() -> None:
    revisions = [
        _revision("revision_1"),
        _revision("revision_2", status=ContentRevisionStatus.DRAFT),
    ]

    with pytest.raises(ValidationError) as error:
        _registry(revisions=revisions)

    assert "question_id 'question_1', locale 'tr-TR', revision 1" in str(error.value)


def test_rejects_multiple_approved_revisions_for_same_question_and_locale() -> None:
    revisions = [
        _revision("revision_1"),
        _revision("revision_2", revision=2, supersedes_revision_id="revision_1"),
    ]

    with pytest.raises(ValidationError) as error:
        _registry(revisions=revisions)

    assert "multiple APPROVED revisions" in str(error.value)


def test_item_adapted_requires_adaptation_note() -> None:
    with pytest.raises(ValidationError) as error:
        _evidence_link(
            claim_scope=ClaimScope.ITEM_ADAPTED,
            adaptation_type=AdaptationType.NOT_APPLICABLE,
        )

    assert "ITEM_ADAPTED evidence requires adaptation_note" in str(error.value)


def test_translation_requires_adaptation_note() -> None:
    with pytest.raises(ValidationError) as error:
        _evidence_link(
            claim_scope=ClaimScope.QUESTION_DERIVED,
            adaptation_type=AdaptationType.DIRECT_TRANSLATION,
        )

    assert "DIRECT_TRANSLATION evidence requires adaptation_note" in str(error.value)


def test_validated_item_requires_validated_instrument_source() -> None:
    with pytest.raises(ValidationError) as error:
        _registry(evidence_links=[_evidence_link(claim_scope=ClaimScope.VALIDATED_ITEM)])

    assert "VALIDATED_ITEM without a VALIDATED_INSTRUMENT source" in str(error.value)


def test_validated_item_accepts_validated_instrument_source() -> None:
    registry = _registry(
        sources=[_source(source_type=SourceType.VALIDATED_INSTRUMENT)],
        evidence_links=[_evidence_link(claim_scope=ClaimScope.VALIDATED_ITEM)],
    )

    assert registry.evidence_links[0].claim_scope is ClaimScope.VALIDATED_ITEM
    assert registry.sources[0].source_type is SourceType.VALIDATED_INSTRUMENT


def test_rejects_evidence_link_locale_different_from_revision() -> None:
    with pytest.raises(ValidationError) as error:
        _registry(evidence_links=[_evidence_link(target_locale="en-GB")])

    assert "target_locale 'en-GB' does not match revision locale 'tr-TR'" in str(error.value)


def test_changes_requested_requires_required_changes() -> None:
    with pytest.raises(ValidationError) as error:
        _review(decision=ReviewDecision.CHANGES_REQUESTED)

    assert "CHANGES_REQUESTED review requires required_changes" in str(error.value)


def test_rejected_review_requires_rationale() -> None:
    with pytest.raises(ValidationError) as error:
        _review(decision=ReviewDecision.REJECTED, rationale=None)

    assert "REJECTED review requires rationale" in str(error.value)


def test_participant_evaluation_requires_participant_count() -> None:
    with pytest.raises(ValidationError) as error:
        _evaluation(evaluation_type=EvaluationType.COGNITIVE_INTERVIEW)

    assert "COGNITIVE_INTERVIEW requires participant_count" in str(error.value)


def test_readability_review_allows_missing_participant_count() -> None:
    evaluation = _evaluation(evaluation_type=EvaluationType.READABILITY_REVIEW)

    assert evaluation.participant_count is None
    assert evaluation.evaluation_type is EvaluationType.READABILITY_REVIEW


def test_revision_required_result_requires_revision_required_true() -> None:
    with pytest.raises(ValidationError) as error:
        _evaluation(
            result=EvaluationResult.REVISION_REQUIRED,
            identified_issues=["Placeholder issue"],
            revision_required=False,
        )

    assert "REVISION_REQUIRED result requires revision_required true" in str(error.value)


def test_revision_required_true_requires_matching_result() -> None:
    with pytest.raises(ValidationError) as error:
        _evaluation(result=EvaluationResult.PASSED, revision_required=True)

    assert "revision_required true requires REVISION_REQUIRED result" in str(error.value)


def test_passed_with_notes_requires_identified_issues() -> None:
    with pytest.raises(ValidationError) as error:
        _evaluation(result=EvaluationResult.PASSED_WITH_NOTES)

    assert "PASSED_WITH_NOTES requires identified_issues" in str(error.value)


def test_rejects_evaluation_locale_different_from_revision() -> None:
    with pytest.raises(ValidationError) as error:
        _registry(evaluations=[_evaluation(locale="en-GB")])

    assert "locale 'en-GB' does not match revision locale 'tr-TR'" in str(error.value)


def test_rejects_duplicate_construct_output_target_ids() -> None:
    with pytest.raises(ValidationError) as error:
        _construct(expected_output_target_ids=["target_1", "target_1"])

    assert "duplicate expected_output_target_id 'target_1'" in str(error.value)


def test_rejects_self_superseding_revision() -> None:
    with pytest.raises(ValidationError) as error:
        _revision("revision_2", revision=2, supersedes_revision_id="revision_2")

    assert "supersedes_revision_id cannot reference the same revision" in str(error.value)


def test_rejects_duplicate_evidence_link_references() -> None:
    with pytest.raises(ValidationError) as error:
        _evidence_link(source_ids=["source_1", "source_1"])

    assert "duplicate reference id 'source_1'" in str(error.value)


def test_expert_authored_claim_requires_matching_adaptation_type() -> None:
    with pytest.raises(ValidationError) as error:
        _evidence_link(
            claim_scope=ClaimScope.EXPERT_AUTHORED,
            adaptation_type=AdaptationType.NOT_APPLICABLE,
        )

    assert "EXPERT_AUTHORED claim requires EXPERT_AUTHORED adaptation_type" in str(error.value)


def test_expert_authored_adaptation_requires_matching_claim_scope() -> None:
    with pytest.raises(ValidationError) as error:
        _evidence_link(
            claim_scope=ClaimScope.QUESTION_DERIVED,
            adaptation_type=AdaptationType.EXPERT_AUTHORED,
        )

    assert "EXPERT_AUTHORED adaptation_type requires EXPERT_AUTHORED claim" in str(error.value)


def test_rejects_duplicate_review_evidence_link_ids() -> None:
    with pytest.raises(ValidationError) as error:
        _review(evidence_link_ids=["evidence_link_1", "evidence_link_1"])

    assert "duplicate evidence_link_id 'evidence_link_1'" in str(error.value)


def test_rejects_duplicate_evaluation_identified_issues() -> None:
    with pytest.raises(ValidationError) as error:
        _evaluation(
            result=EvaluationResult.PASSED_WITH_NOTES,
            identified_issues=["Placeholder issue", "Placeholder issue"],
        )

    assert "duplicate identified issue 'Placeholder issue'" in str(error.value)


def test_rejects_expert_review_unknown_revision() -> None:
    with pytest.raises(ValidationError) as error:
        _registry(expert_reviews=[_review(revision_id="missing_revision", evidence_link_ids=[])])

    assert "expert review 'review_1' references unknown" in str(error.value)
    assert "question_content_revision_id 'missing_revision'" in str(error.value)


def test_rejects_unknown_evaluation_revision() -> None:
    with pytest.raises(ValidationError) as error:
        _registry(evaluations=[_evaluation(revision_id="missing_revision")])

    assert "evaluation 'evaluation_1' references unknown" in str(error.value)
    assert "question_content_revision_id 'missing_revision'" in str(error.value)


def test_rejects_extra_fields() -> None:
    payload = _source().model_dump()
    payload["unexpected"] = "field"

    with pytest.raises(ValidationError) as error:
        ScientificSource.model_validate(payload)

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("unexpected",)
    assert first_error["type"] == "extra_forbidden"


def test_serializes_scientific_registry() -> None:
    registry = _registry()

    dumped = registry.model_dump(mode="json")
    json_output = registry.model_dump_json()
    round_trip = ScientificContentRegistry.model_validate(dumped)

    assert dumped["sources"][0]["source_type"] == "PEER_REVIEWED_ARTICLE"
    assert dumped["evidence_links"][0]["claim_scope"] == "CONCEPT_SUPPORTED"
    assert '"question_catalog_id":"catalog_1"' in json_output
    assert round_trip.sources[0].usage_permission_status is UsagePermissionStatus.OPEN
