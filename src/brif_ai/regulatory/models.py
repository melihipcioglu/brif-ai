"""BRIF.AI — Turkish Regulatory Foundation Models."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:  # pragma: no cover - compatibility for local Python 3.10 tooling

    class StrEnum(str, Enum):  # noqa: UP042
        pass


class StrictRegulatoryModel(BaseModel):
    """Base model enforcing strict validation and immutable behavior for regulatory contracts."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
    )


class SourceType(StrEnum):
    NATIONAL_REGULATION = "NATIONAL_REGULATION"
    MINISTRY_REGULATION = "MINISTRY_REGULATION"
    MUNICIPAL_REGULATION = "MUNICIPAL_REGULATION"
    IMPLEMENTATION_PLAN = "IMPLEMENTATION_PLAN"
    PLAN_NOTE = "PLAN_NOTE"
    STANDARD = "STANDARD"
    OTHER_OFFICIAL = "OTHER_OFFICIAL"


class SourceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    FUTURE = "FUTURE"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    PARTIAL = "PARTIAL"
    VERIFIED = "VERIFIED"


class RegulatoryUnit(StrEnum):
    METER = "METER"
    SQUARE_METER = "SQUARE_METER"
    RATIO = "RATIO"
    COUNT = "COUNT"
    PERCENT = "PERCENT"


class ComplianceStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class ConstraintType(StrEnum):
    MAX_VALUE = "MAX_VALUE"
    MIN_VALUE = "MIN_VALUE"
    RANGE = "RANGE"
    REQUIRED = "REQUIRED"
    PROHIBITED = "PROHIBITED"
    FORMULA_LIMIT = "FORMULA_LIMIT"


class RegulatorySource(StrictRegulatoryModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    jurisdiction: str = Field(default="TR")
    authority: str = Field(min_length=1)
    official_url: str | None = None
    source_type: SourceType
    publication_date: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    retrieved_at: datetime | None = None
    version_label: str | None = None
    content_sha256: str | None = None
    supersedes_source_id: str | None = None
    status: SourceStatus = SourceStatus.ACTIVE


# Typed Rule Parameters (Amendments 8 & 9)
class MaxValueParameters(StrictRegulatoryModel):
    type: Literal["MAX_VALUE"] = "MAX_VALUE"
    fact_key: str
    limit_value: Decimal
    unit: RegulatoryUnit


class MinValueParameters(StrictRegulatoryModel):
    type: Literal["MIN_VALUE"] = "MIN_VALUE"
    fact_key: str
    limit_value: Decimal
    unit: RegulatoryUnit


class RangeParameters(StrictRegulatoryModel):
    type: Literal["RANGE"] = "RANGE"
    fact_key: str
    min_value: Decimal
    max_value: Decimal
    unit: RegulatoryUnit


class RequiredParameters(StrictRegulatoryModel):
    type: Literal["REQUIRED"] = "REQUIRED"
    fact_key: str


class ProhibitedParameters(StrictRegulatoryModel):
    type: Literal["PROHIBITED"] = "PROHIBITED"
    fact_key: str


class FormulaLimitParameters(StrictRegulatoryModel):
    type: Literal["FORMULA_LIMIT"] = "FORMULA_LIMIT"
    formula_type: str
    target_fact_key: str
    parameters: dict[str, Decimal]


RuleParameters = (
    MaxValueParameters
    | MinValueParameters
    | RangeParameters
    | RequiredParameters
    | ProhibitedParameters
    | FormulaLimitParameters
)


class RegulatoryRule(StrictRegulatoryModel):
    rule_id: str = Field(min_length=1)
    ruleset_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    article_reference: str = Field(min_length=1)
    title: str = Field(min_length=1)
    scope: str = Field(default="general")
    constraint_type: ConstraintType
    parameters: RuleParameters
    severity: Severity = Severity.CRITICAL
    effective_from: date | None = None
    effective_to: date | None = None
    provenance_note: str | None = None


class RegulatoryRuleSet(StrictRegulatoryModel):
    ruleset_id: str = Field(min_length=1)
    country: str = Field(default="TR")
    jurisdiction: str = Field(default="TR-NATIONAL")
    effective_from: date | None = None
    effective_to: date | None = None
    source_ids: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    content_hash: str | None = None
    rules: list[RegulatoryRule] = Field(default_factory=list)

    def compute_canonical_hash(self) -> str:
        """Compute stable canonical content hash excluding volatile metadata."""
        data = {
            "ruleset_id": self.ruleset_id,
            "country": self.country,
            "jurisdiction": self.jurisdiction,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "source_ids": sorted(self.source_ids),
            "rules": [
                rule.model_dump(mode="json") for rule in sorted(self.rules, key=lambda r: r.rule_id)
            ],
        }
        canonical_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


class ZoningContext(StrictRegulatoryModel):
    """Typed parcel zoning inputs. Missing values are None (UNKNOWN), distinct from 0."""

    parcel_area_m2: Decimal | None = None
    land_use: str | None = None
    building_order: str | None = None
    taks: Decimal | None = None
    kaks_or_emsal: Decimal | None = None
    max_height_m: Decimal | None = None
    max_floors: int | None = None
    front_setback_m: Decimal | None = None
    side_setback_m: Decimal | None = None
    rear_setback_m: Decimal | None = None
    road_width_m: Decimal | None = None
    plan_note_references: list[str] = Field(default_factory=list)


class ProjectRegulatoryContext(StrictRegulatoryModel):
    project_id: str = Field(min_length=1)
    country: str = Field(default="TR")
    province: str = Field(min_length=1)
    district: str = Field(min_length=1)
    municipality: str | None = None
    as_of_date: date | None = None
    ruleset_id: str = Field(min_length=1)
    source_ids: list[str] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    zoning_context: ZoningContext | None = None


class DesignFacts(StrictRegulatoryModel):
    """Structured observed facts from architectural design/program. NO free-text parsing."""

    parcel_area_m2: Decimal | None = None
    proposed_footprint_m2: Decimal | None = None
    proposed_total_floor_area_m2: Decimal | None = None
    proposed_height_m: Decimal | None = None
    proposed_floor_count: int | None = None
    provided_parking_spaces: int | None = None
    front_setback_m: Decimal | None = None
    side_setback_m: Decimal | None = None
    rear_setback_m: Decimal | None = None
    taks: Decimal | None = None
    kaks_or_emsal: Decimal | None = None


class ComplianceFinding(StrictRegulatoryModel):
    finding_id: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    status: ComplianceStatus
    severity: Severity = Severity.CRITICAL
    observed_value: Any = None
    required_value: Any = None
    observed_unit: RegulatoryUnit | None = None
    required_unit: RegulatoryUnit | None = None
    message: str = Field(min_length=1)
    source_id: str | None = None
    article_reference: str | None = None
    provenance_note: str | None = None


class GenerationConstraintSet(StrictRegulatoryModel):
    """Exported spatial boundaries for future plan generator."""

    max_footprint_m2: Decimal | None = None
    max_total_floor_area_m2: Decimal | None = None
    max_height_m: Decimal | None = None
    max_floors: int | None = None
    min_front_setback_m: Decimal | None = None
    min_side_setback_m: Decimal | None = None
    min_rear_setback_m: Decimal | None = None
    required_parking_spaces: int | None = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
