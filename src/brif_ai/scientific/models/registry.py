"""Scientific content registry contracts for BRIF.AI v0.

The registry is pinned to a specific QuestionCatalog id and version. It does
not validate question_id or expected_output_target_ids against that catalog;
that belongs to a later publication validation service. QuestionDefinition
source_metadata is not used for any registry integrity check.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator, model_validator

from brif_ai.conversation.models.common import ConversationModule
from brif_ai.core.models.common import ContractModel, NonEmptyString, ObjectId
from brif_ai.scientific.models.common import (
    AdaptationType,
    ClaimScope,
    ContentRevisionStatus,
    EvaluationResult,
    EvaluationType,
    EvidenceRelation,
    IdentifierType,
    LanguageCode,
    LocaleCode,
    ReviewArea,
    ReviewDecision,
    SourceType,
    UsagePermissionStatus,
)

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
MediumText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
CitationText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]
SourceLocator = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=250)
]


def _first_duplicate(values: Iterable[object]) -> object | None:
    seen: set[object] = set()
    for value in values:
        if value in seen:
            return value
        seen.add(value)
    return None


def _require_utc_datetime(field_name: str, value: datetime) -> datetime:
    offset = value.utcoffset()
    if value.tzinfo is None or offset is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if offset != timedelta(0):
        raise ValueError(f"{field_name} must use UTC offset")
    return value


class ScientificSource(ContractModel):
    """Traceable source metadata. This does not prove any question is validated."""

    id: ObjectId
    source_type: SourceType
    title: MediumText
    authors: list[ShortText] = Field(min_length=1)
    publication_year: int = Field(ge=1, le=2100)
    publication_or_publisher: MediumText
    identifier_type: IdentifierType
    identifier_value: ShortText | None = None
    citation_text: CitationText
    language: LanguageCode
    usage_permission_status: UsagePermissionStatus
    notes: LongText | None = None

    @field_validator("authors")
    @classmethod
    def reject_duplicate_authors(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate author {duplicate!r}")
        return value

    @model_validator(mode="after")
    def validate_identifier(self) -> ScientificSource:
        if self.identifier_type is IdentifierType.NONE and self.identifier_value is not None:
            raise ValueError("identifier_value is not allowed when identifier_type is NONE")
        if self.identifier_type is not IdentifierType.NONE and self.identifier_value is None:
            raise ValueError("identifier_value is required when identifier_type is not NONE")
        return self


class ConstructDefinition(ContractModel):
    """Scientific or architectural construct; not a psychometric scale by itself."""

    id: ObjectId
    name: ShortText
    definition: LongText
    conversation_module: ConversationModule
    architectural_relevance: LongText
    expected_output_target_ids: list[ObjectId] = Field(min_length=1)
    scope_note: LongText | None = None

    @field_validator("expected_output_target_ids")
    @classmethod
    def reject_duplicate_output_targets(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate expected_output_target_id {duplicate!r}")
        return value


class QuestionContentRevision(ContractModel):
    """Versioned question content. Approved wording changes require a new revision."""

    id: ObjectId
    question_id: ObjectId
    locale: LocaleCode
    revision: int = Field(ge=1)
    content_key: NonEmptyString
    wording: LongText
    respondent_instruction: LongText | None = None
    status: ContentRevisionStatus
    created_at: datetime
    supersedes_revision_id: ObjectId | None = None

    @field_validator("created_at")
    @classmethod
    def require_utc_created_at(cls, value: datetime) -> datetime:
        return _require_utc_datetime("created_at", value)

    @model_validator(mode="after")
    def validate_revision_chain_fields(self) -> QuestionContentRevision:
        if self.supersedes_revision_id == self.id:
            raise ValueError("supersedes_revision_id cannot reference the same revision")
        if self.revision == 1 and self.supersedes_revision_id is not None:
            raise ValueError("revision 1 cannot define supersedes_revision_id")
        if self.revision > 1 and self.supersedes_revision_id is None:
            raise ValueError("revision greater than 1 requires supersedes_revision_id")
        return self


class QuestionEvidenceLink(ContractModel):
    id: ObjectId
    question_content_revision_id: ObjectId
    construct_ids: list[ObjectId] = Field(min_length=1)
    source_ids: list[ObjectId] = Field(min_length=1)
    evidence_relation: EvidenceRelation
    claim_scope: ClaimScope
    rationale: LongText
    source_locator: SourceLocator
    adaptation_type: AdaptationType
    adaptation_note: LongText | None = None
    target_locale: LocaleCode

    @field_validator("construct_ids", "source_ids")
    @classmethod
    def reject_duplicate_references(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate reference id {duplicate!r}")
        return value

    @model_validator(mode="after")
    def validate_adaptation_claims(self) -> QuestionEvidenceLink:
        note_required_types = {
            AdaptationType.DIRECT_TRANSLATION,
            AdaptationType.FORWARD_BACK_TRANSLATION,
            AdaptationType.CULTURAL_ADAPTATION,
            AdaptationType.CONCEPTUAL_DERIVATION,
        }
        if self.claim_scope is ClaimScope.ITEM_ADAPTED and self.adaptation_note is None:
            raise ValueError("ITEM_ADAPTED evidence requires adaptation_note")
        if self.adaptation_type in note_required_types and self.adaptation_note is None:
            raise ValueError(f"{self.adaptation_type.value} evidence requires adaptation_note")
        if (
            self.claim_scope is ClaimScope.EXPERT_AUTHORED
            and self.adaptation_type is not AdaptationType.EXPERT_AUTHORED
        ):
            raise ValueError("EXPERT_AUTHORED claim requires EXPERT_AUTHORED adaptation_type")
        if (
            self.adaptation_type is AdaptationType.EXPERT_AUTHORED
            and self.claim_scope is not ClaimScope.EXPERT_AUTHORED
        ):
            raise ValueError("EXPERT_AUTHORED adaptation_type requires EXPERT_AUTHORED claim")
        return self


class ExpertReviewRecord(ContractModel):
    """Expert review applies only to the referenced question content revision."""

    id: ObjectId
    question_content_revision_id: ObjectId
    evidence_link_ids: list[ObjectId]
    reviewer_reference: ShortText
    reviewer_role: ShortText
    review_area: ReviewArea
    decision: ReviewDecision
    reviewed_at: datetime
    rationale: LongText | None = None
    required_changes: LongText | None = None

    @field_validator("reviewed_at")
    @classmethod
    def require_utc_reviewed_at(cls, value: datetime) -> datetime:
        return _require_utc_datetime("reviewed_at", value)

    @field_validator("evidence_link_ids")
    @classmethod
    def reject_duplicate_evidence_links(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate evidence_link_id {duplicate!r}")
        return value

    @model_validator(mode="after")
    def validate_review_decision(self) -> ExpertReviewRecord:
        if self.decision is ReviewDecision.CHANGES_REQUESTED and self.required_changes is None:
            raise ValueError("CHANGES_REQUESTED review requires required_changes")
        if self.decision is ReviewDecision.REJECTED and self.rationale is None:
            raise ValueError("REJECTED review requires rationale")
        return self


class ContentEvaluationRecord(ContractModel):
    """Content evaluation metadata; participant personal data is not stored."""

    id: ObjectId
    question_content_revision_id: ObjectId
    evaluation_type: EvaluationType
    locale: LocaleCode
    conducted_at: datetime
    participant_count: int | None = Field(default=None, ge=1)
    result: EvaluationResult
    summary: LongText
    identified_issues: list[MediumText]
    revision_required: bool

    @field_validator("conducted_at")
    @classmethod
    def require_utc_conducted_at(cls, value: datetime) -> datetime:
        return _require_utc_datetime("conducted_at", value)

    @field_validator("identified_issues")
    @classmethod
    def reject_duplicate_identified_issues(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate identified issue {duplicate!r}")
        return value

    @model_validator(mode="after")
    def validate_evaluation_result(self) -> ContentEvaluationRecord:
        participant_evaluation_types = {
            EvaluationType.COGNITIVE_INTERVIEW,
            EvaluationType.PILOT_INTERVIEW,
            EvaluationType.EXPERT_PANEL,
            EvaluationType.USABILITY_TEST,
            EvaluationType.PSYCHOMETRIC_STUDY,
        }
        if self.evaluation_type in participant_evaluation_types and self.participant_count is None:
            raise ValueError(f"{self.evaluation_type.value} requires participant_count")
        if self.result is EvaluationResult.REVISION_REQUIRED and not self.revision_required:
            raise ValueError("REVISION_REQUIRED result requires revision_required true")
        if self.revision_required and self.result is not EvaluationResult.REVISION_REQUIRED:
            raise ValueError("revision_required true requires REVISION_REQUIRED result")
        if (
            self.result
            in {
                EvaluationResult.PASSED_WITH_NOTES,
                EvaluationResult.REVISION_REQUIRED,
            }
            and not self.identified_issues
        ):
            raise ValueError(f"{self.result.value} requires identified_issues")
        return self


RegistryObject = (
    ScientificSource
    | ConstructDefinition
    | QuestionContentRevision
    | QuestionEvidenceLink
    | ExpertReviewRecord
    | ContentEvaluationRecord
)


class ScientificContentRegistry(ContractModel):
    id: ObjectId
    schema_version: NonEmptyString
    registry_version: int = Field(ge=1)
    question_catalog_id: ObjectId
    question_catalog_version: int = Field(ge=1)
    content_bundle_version: int = Field(ge=1)
    created_at: datetime
    sources: list[ScientificSource]
    constructs: list[ConstructDefinition]
    question_content_revisions: list[QuestionContentRevision]
    evidence_links: list[QuestionEvidenceLink]
    expert_reviews: list[ExpertReviewRecord]
    evaluations: list[ContentEvaluationRecord]

    @field_validator("created_at")
    @classmethod
    def require_utc_created_at(cls, value: datetime) -> datetime:
        return _require_utc_datetime("created_at", value)

    @model_validator(mode="after")
    def validate_registry_integrity(self) -> ScientificContentRegistry:
        self._validate_unique_object_ids()

        sources_by_id = {source.id: source for source in self.sources}
        constructs_by_id = {construct.id: construct for construct in self.constructs}
        revisions_by_id = {revision.id: revision for revision in self.question_content_revisions}
        evidence_links_by_id = {link.id: link for link in self.evidence_links}

        self._validate_revision_chain(revisions_by_id)
        self._validate_unique_question_locale_revisions()
        self._validate_evidence_links(sources_by_id, constructs_by_id, revisions_by_id)
        self._validate_expert_reviews(revisions_by_id, evidence_links_by_id)
        self._validate_evaluations(revisions_by_id)
        return self

    def _validate_unique_object_ids(self) -> None:
        seen: dict[str, str] = {}
        collections: list[tuple[str, Iterable[RegistryObject]]] = [
            ("source", self.sources),
            ("construct", self.constructs),
            ("question_content_revision", self.question_content_revisions),
            ("evidence_link", self.evidence_links),
            ("expert_review", self.expert_reviews),
            ("evaluation", self.evaluations),
        ]

        for object_type, objects in collections:
            for item in objects:
                previous_type = seen.get(item.id)
                if previous_type is not None:
                    raise ValueError(
                        f"duplicate object id {item.id!r} used by "
                        f"{previous_type!r} and {object_type!r}"
                    )
                seen[item.id] = object_type

    def _validate_revision_chain(self, revisions_by_id: dict[str, QuestionContentRevision]) -> None:
        for revision in self.question_content_revisions:
            supersedes_revision_id = revision.supersedes_revision_id
            if supersedes_revision_id is None:
                continue

            superseded = revisions_by_id.get(supersedes_revision_id)
            if superseded is None:
                raise ValueError(
                    f"question content revision {revision.id!r} references unknown "
                    f"supersedes_revision_id {supersedes_revision_id!r}"
                )
            if superseded.question_id != revision.question_id:
                raise ValueError(
                    f"question content revision {revision.id!r} supersedes revision "
                    f"{superseded.id!r} for different question_id"
                )
            if superseded.locale != revision.locale:
                raise ValueError(
                    f"question content revision {revision.id!r} supersedes revision "
                    f"{superseded.id!r} for different locale"
                )
            if superseded.revision >= revision.revision:
                raise ValueError(
                    f"question content revision {revision.id!r} must supersede a lower "
                    "revision number"
                )

    def _validate_unique_question_locale_revisions(self) -> None:
        revision_keys: dict[tuple[str, str, int], str] = {}
        approved_keys: dict[tuple[str, str], str] = {}

        for revision in self.question_content_revisions:
            revision_key = (revision.question_id, revision.locale, revision.revision)
            previous_revision_id = revision_keys.get(revision_key)
            if previous_revision_id is not None:
                raise ValueError(
                    f"question_id {revision.question_id!r}, locale {revision.locale!r}, "
                    f"revision {revision.revision!r} is used by {previous_revision_id!r} "
                    f"and {revision.id!r}"
                )
            revision_keys[revision_key] = revision.id

            if revision.status is not ContentRevisionStatus.APPROVED:
                continue
            approved_key = (revision.question_id, revision.locale)
            previous_approved_id = approved_keys.get(approved_key)
            if previous_approved_id is not None:
                raise ValueError(
                    f"question_id {revision.question_id!r} and locale {revision.locale!r} "
                    f"have multiple APPROVED revisions {previous_approved_id!r} "
                    f"and {revision.id!r}"
                )
            approved_keys[approved_key] = revision.id

    def _validate_evidence_links(
        self,
        sources_by_id: dict[str, ScientificSource],
        constructs_by_id: dict[str, ConstructDefinition],
        revisions_by_id: dict[str, QuestionContentRevision],
    ) -> None:
        for link in self.evidence_links:
            revision = revisions_by_id.get(link.question_content_revision_id)
            if revision is None:
                raise ValueError(
                    f"evidence link {link.id!r} references unknown "
                    f"question_content_revision_id {link.question_content_revision_id!r}"
                )

            for construct_id in link.construct_ids:
                if construct_id not in constructs_by_id:
                    raise ValueError(
                        f"evidence link {link.id!r} references unknown construct_id "
                        f"{construct_id!r}"
                    )

            referenced_sources = []
            for source_id in link.source_ids:
                source = sources_by_id.get(source_id)
                if source is None:
                    raise ValueError(
                        f"evidence link {link.id!r} references unknown source_id {source_id!r}"
                    )
                referenced_sources.append(source)

            if link.target_locale != revision.locale:
                raise ValueError(
                    f"evidence link {link.id!r} target_locale {link.target_locale!r} "
                    f"does not match revision locale {revision.locale!r}"
                )

            if link.claim_scope is ClaimScope.VALIDATED_ITEM and not any(
                source.source_type is SourceType.VALIDATED_INSTRUMENT
                for source in referenced_sources
            ):
                raise ValueError(
                    f"evidence link {link.id!r} claims VALIDATED_ITEM without a "
                    "VALIDATED_INSTRUMENT source"
                )

    def _validate_expert_reviews(
        self,
        revisions_by_id: dict[str, QuestionContentRevision],
        evidence_links_by_id: dict[str, QuestionEvidenceLink],
    ) -> None:
        for review in self.expert_reviews:
            if review.question_content_revision_id not in revisions_by_id:
                raise ValueError(
                    f"expert review {review.id!r} references unknown "
                    f"question_content_revision_id {review.question_content_revision_id!r}"
                )

            for evidence_link_id in review.evidence_link_ids:
                evidence_link = evidence_links_by_id.get(evidence_link_id)
                if evidence_link is None:
                    raise ValueError(
                        f"expert review {review.id!r} references unknown evidence_link_id "
                        f"{evidence_link_id!r}"
                    )
                if (
                    evidence_link.question_content_revision_id
                    != review.question_content_revision_id
                ):
                    raise ValueError(
                        f"expert review {review.id!r} references evidence_link_id "
                        f"{evidence_link_id!r} for a different question_content_revision_id"
                    )

    def _validate_evaluations(
        self,
        revisions_by_id: dict[str, QuestionContentRevision],
    ) -> None:
        for evaluation in self.evaluations:
            revision = revisions_by_id.get(evaluation.question_content_revision_id)
            if revision is None:
                raise ValueError(
                    f"evaluation {evaluation.id!r} references unknown "
                    f"question_content_revision_id {evaluation.question_content_revision_id!r}"
                )
            if evaluation.locale != revision.locale:
                raise ValueError(
                    f"evaluation {evaluation.id!r} locale {evaluation.locale!r} "
                    f"does not match revision locale {revision.locale!r}"
                )
