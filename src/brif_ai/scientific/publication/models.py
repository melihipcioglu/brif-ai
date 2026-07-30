"""Scientific publication validation data contracts for BRIF.AI v0.

Scientific Decision Boundary:
-----------------------------
These models do not decide whether a question is scientifically validated by themselves.
- `PublicationValidationRequest` only carries validation input.
- `PublicationIssue` only carries validator findings.
- `PublicationValidationReport` only derives publication readiness from issue
  and question result records.
- Permission, expert review, evidence, and psychometric policies will be applied
  in the subsequent validator service.
- AI confidence or evidence scores will NOT be used.

Deterministic Issue ID Boundary:
--------------------------------
Later validator services must observe the following issue ID assignment rule:
- Issue drafts will first be sorted by fixed ordering.
- Then deterministic `ObjectId` values such as `publication_issue_0001`,
  `publication_issue_0002` will be assigned.
- Random UUID or time-based issue IDs will not be used.
- The same validation input must produce the exact same issue order and issue ID values.
(Note: Issue ID generation functions are not implemented in this model layer.)
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Annotated

from pydantic import Field, StringConstraints, computed_field, field_validator, model_validator

from brif_ai.conversation.models.catalog import QuestionCatalog
from brif_ai.core.models.common import ContractModel, NonEmptyString, ObjectId
from brif_ai.scientific.models.common import LocaleCode
from brif_ai.scientific.models.registry import ScientificContentRegistry
from brif_ai.scientific.publication.common import (
    PublicationIssueCode,
    PublicationIssueSeverity,
    PublicationObjectType,
)

LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


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


class PublicationValidationRequest(ContractModel):
    """Validation request carrying catalog, registry, and target locale.

    Does not validate catalog/registry id or version mismatch because any mismatch
    will be reported as a CRITICAL issue by the validator service.
    """

    catalog: QuestionCatalog
    registry: ScientificContentRegistry
    target_locale: LocaleCode
    checked_at: datetime
    validator_version: NonEmptyString

    @field_validator("checked_at")
    @classmethod
    def require_utc_checked_at(cls, value: datetime) -> datetime:
        return _require_utc_datetime("checked_at", value)


class PublicationIssue(ContractModel):
    """Describes a scientific deficiency or structural issue identified during validation."""

    id: ObjectId
    code: PublicationIssueCode
    severity: PublicationIssueSeverity
    object_type: PublicationObjectType
    object_id: ObjectId
    question_id: ObjectId | None = None
    question_content_revision_id: ObjectId | None = None
    message: LongText
    related_object_ids: list[ObjectId] = Field(default_factory=list)

    @field_validator("related_object_ids")
    @classmethod
    def reject_duplicate_related_object_ids(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate related_object_id {duplicate!r}")
        return value

    @computed_field(return_type=bool)  # type: ignore[prop-decorator]
    @property
    def blocking(self) -> bool:
        return self.severity.is_blocking


class QuestionPublicationResult(ContractModel):
    """Publication validation result for a single question."""

    question_id: ObjectId
    target_locale: LocaleCode
    selected_content_revision_id: ObjectId | None = None
    issue_ids: list[ObjectId] = Field(default_factory=list)
    blocking_issue_ids: list[ObjectId] = Field(default_factory=list)

    @field_validator("issue_ids")
    @classmethod
    def reject_duplicate_issue_ids(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate issue_id {duplicate!r}")
        return value

    @field_validator("blocking_issue_ids")
    @classmethod
    def reject_duplicate_blocking_issue_ids(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate blocking_issue_id {duplicate!r}")
        return value

    @model_validator(mode="after")
    def validate_blocking_issue_ids_subset(self) -> QuestionPublicationResult:
        if not set(self.blocking_issue_ids).issubset(set(self.issue_ids)):
            raise ValueError("blocking_issue_ids must be a subset of issue_ids")
        return self

    @computed_field(return_type=bool)  # type: ignore[prop-decorator]
    @property
    def ready_for_publication(self) -> bool:
        return self.selected_content_revision_id is not None and len(self.blocking_issue_ids) == 0


class PublicationValidationReport(ContractModel):
    """Overall publication validation report aggregating issues and question publication results."""

    catalog_id: ObjectId
    catalog_version: int = Field(ge=1)
    registry_id: ObjectId
    registry_version: int = Field(ge=1)
    target_locale: LocaleCode
    checked_at: datetime
    validator_version: NonEmptyString
    question_results: list[QuestionPublicationResult] = Field(default_factory=list)
    issues: list[PublicationIssue] = Field(default_factory=list)

    @field_validator("checked_at")
    @classmethod
    def require_utc_checked_at(cls, value: datetime) -> datetime:
        return _require_utc_datetime("checked_at", value)

    @model_validator(mode="after")
    def validate_report_integrity(self) -> PublicationValidationReport:
        issues_by_id: dict[str, PublicationIssue] = {}
        for issue in self.issues:
            if issue.id in issues_by_id:
                raise ValueError(f"duplicate issue id {issue.id!r} in report")
            issues_by_id[issue.id] = issue

        seen_question_ids: set[str] = set()
        for result in self.question_results:
            if result.question_id in seen_question_ids:
                raise ValueError(
                    f"duplicate question_id {result.question_id!r} in question_results"
                )
            seen_question_ids.add(result.question_id)

            if result.target_locale != self.target_locale:
                raise ValueError(
                    f"question result target_locale {result.target_locale!r} "
                    f"does not match report target_locale {self.target_locale!r}"
                )

            expected_blocking_issue_ids: list[str] = []
            for issue_id in result.issue_ids:
                issue_obj = issues_by_id.get(issue_id)
                if issue_obj is None:
                    raise ValueError(
                        f"question result for {result.question_id!r} references unknown "
                        f"issue_id {issue_id!r}"
                    )
                if issue_obj.question_id is None:
                    raise ValueError(
                        f"report-level issue {issue_id!r} (question_id=None) cannot be "
                        f"linked to question result for {result.question_id!r}"
                    )
                if issue_obj.question_id != result.question_id:
                    raise ValueError(
                        f"question result for {result.question_id!r} references issue {issue_id!r} "
                        f"which belongs to question_id {issue_obj.question_id!r}"
                    )
                if issue_obj.blocking:
                    expected_blocking_issue_ids.append(issue_id)

            if set(result.blocking_issue_ids) != set(expected_blocking_issue_ids):
                raise ValueError(
                    f"question result for {result.question_id!r} blocking_issue_ids "
                    f"{result.blocking_issue_ids!r} does not match expected blocking issues "
                    f"{expected_blocking_issue_ids!r}"
                )

        return self

    @computed_field(return_type=bool)  # type: ignore[prop-decorator]
    @property
    def ready_for_publication(self) -> bool:
        if not self.question_results:
            return False
        if any(issue.blocking for issue in self.issues):
            return False
        return all(res.ready_for_publication for res in self.question_results)
