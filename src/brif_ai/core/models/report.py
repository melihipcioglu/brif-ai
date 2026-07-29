"""Validation report contracts for BRIF.AI core v0."""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import Field, computed_field, field_validator

from brif_ai.core.models.common import (
    ContractModel,
    IssueSeverity,
    NonEmptyString,
    ObjectId,
    ObjectType,
    ValidationStatus,
)


class RuleMetadata(ContractModel):
    rulepack_id: NonEmptyString
    rulepack_version: NonEmptyString
    rule_id: NonEmptyString
    rule_version: NonEmptyString


class ObjectReference(ContractModel):
    object_type: ObjectType
    object_id: ObjectId


class ValidationIssue(ContractModel):
    severity: IssueSeverity
    message: NonEmptyString
    rule: RuleMetadata
    object_references: list[ObjectReference] = Field(min_length=1)


class ValidationReport(ContractModel):
    project_id: ObjectId
    schema_version: NonEmptyString
    rulepack_id: NonEmptyString
    rulepack_version: NonEmptyString
    validator_version: NonEmptyString
    validated_at: datetime
    issues: list[ValidationIssue]

    @field_validator("validated_at")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        offset = value.utcoffset()
        if value.tzinfo is None or offset is None:
            raise ValueError("validated_at must be timezone-aware")
        if offset != timedelta(0):
            raise ValueError("validated_at must use UTC offset")
        return value

    @computed_field(return_type=int)  # type: ignore[prop-decorator]
    @property
    def critical_count(self) -> int:
        return sum(issue.severity is IssueSeverity.CRITICAL for issue in self.issues)

    @computed_field(return_type=ValidationStatus)  # type: ignore[prop-decorator]
    @property
    def status(self) -> ValidationStatus:
        if self.critical_count > 0:
            return ValidationStatus.BLOCKED
        if self.issues:
            return ValidationStatus.REVISION_REQUIRED
        return ValidationStatus.PASS

    @computed_field(return_type=bool)  # type: ignore[prop-decorator]
    @property
    def is_showable(self) -> bool:
        return self.status is not ValidationStatus.BLOCKED
