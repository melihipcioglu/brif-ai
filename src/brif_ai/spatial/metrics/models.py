"""Strict immutable contracts and units for BRIF.AI Metric Spatial Requirements V0."""

from __future__ import annotations

import hashlib
import math
import sys
from datetime import datetime, timedelta
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from brif_ai.brief.models.common import Priority
from brif_ai.core.models.common import NonEmptyString, ObjectId
from brif_ai.spatial.models import RelationshipProvenance

if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:  # pragma: no cover

    class StrEnum(str, Enum):  # noqa: UP042
        pass


class MetricRequirementType(StrEnum):
    """Canonical space-level metric requirement types for V0.

    Scope is strictly limited to clear semantic dimensional/area requirements
    without geometric or rectangular room shape assumptions.
    """

    MIN_AREA = "MIN_AREA"
    MAX_AREA = "MAX_AREA"
    TARGET_AREA = "TARGET_AREA"
    MIN_CLEAR_WIDTH = "MIN_CLEAR_WIDTH"


class MetricUnit(StrEnum):
    """Canonical SI metric units for architectural space requirements."""

    SQUARE_METRE = "SQUARE_METRE"
    METRE = "METRE"


def generate_metric_requirement_id(
    project_id: str,
    space_id: str,
    requirement_type: MetricRequirementType | str,
) -> str:
    """Generate deterministic requirement ID based on project, space, and type."""
    raw_type = (
        requirement_type.value
        if isinstance(requirement_type, MetricRequirementType)
        else str(requirement_type)
    )
    seed = f"{project_id}:{space_id}:{raw_type}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"mreq_{digest}"


def _validate_numeric_value(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(
            f"Metric requirement value must be finite and strictly positive (> 0), got {value!r}"
        )
    return value


def _validate_unit_compatibility(
    req_type: MetricRequirementType,
    unit: MetricUnit,
) -> None:
    if req_type in (
        MetricRequirementType.MIN_AREA,
        MetricRequirementType.MAX_AREA,
        MetricRequirementType.TARGET_AREA,
    ):
        if unit != MetricUnit.SQUARE_METRE:
            raise ValueError(
                f"Requirement {req_type.value!r} requires unit SQUARE_METRE, got {unit.value!r}"
            )
    elif req_type == MetricRequirementType.MIN_CLEAR_WIDTH and unit != MetricUnit.METRE:
        raise ValueError(f"Requirement {req_type.value!r} requires unit METRE, got {unit.value!r}")


class _MetricContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProposedMetricRequirement(_MetricContract):
    """Structured metric requirement proposed during conversation.

    Must not become authoritative until explicit user approval.
    """

    proposal_id: NonEmptyString
    space_id: ObjectId
    requirement_type: MetricRequirementType
    value: float
    unit: MetricUnit
    rationale: str | None = None
    requires_user_confirmation: Literal[True] = True

    @field_validator("value")
    @classmethod
    def require_finite_positive_value(cls, v: float) -> float:
        return _validate_numeric_value(v)

    @model_validator(mode="after")
    def validate_proposal_invariants(self) -> ProposedMetricRequirement:
        if self.requirement_type == MetricRequirementType.TARGET_AREA:
            raise ValueError("TARGET_AREA is not supported for conversational proposals in V0")
        _validate_unit_compatibility(self.requirement_type, self.unit)
        return self


class MetricRequirementInput(_MetricContract):
    """Caller input contract for defining a space-level metric requirement before ID generation.

    Evidence & Provenance Semantics:
    - Provenance is explicitly required on every input (no implicit default to USER_CONFIRMED).
    - When provenance == USER_CONFIRMED, at least one evidence_id is strictly required.
    - Evidence IDs are preserved for traceability; cross-domain existence validation against
      BriefSnapshot evidence catalog is deferred to a future integration boundary.
    """

    space_id: ObjectId
    requirement_type: MetricRequirementType
    value: float
    unit: MetricUnit
    provenance: RelationshipProvenance
    priority: Priority = Priority.MUST
    evidence_ids: list[ObjectId] = Field(default_factory=list)
    rationale: str | None = None

    @field_validator("value")
    @classmethod
    def require_finite_positive_value(cls, v: float) -> float:
        return _validate_numeric_value(v)

    @model_validator(mode="after")
    def validate_input_invariants(self) -> MetricRequirementInput:
        _validate_unit_compatibility(self.requirement_type, self.unit)
        if self.provenance == RelationshipProvenance.USER_CONFIRMED and not self.evidence_ids:
            raise ValueError(
                f"USER_CONFIRMED metric requirement on space {self.space_id!r} "
                f"requires at least one evidence ID."
            )
        return self


class MetricRequirement(_MetricContract):
    """Materialized, immutable metric spatial requirement bound to a specific space.

    Evidence & Provenance Semantics:
    - Provenance is explicit (no default).
    - When provenance == USER_CONFIRMED, at least one evidence_id is strictly required.
    - Evidence IDs are preserved for traceability.
    """

    id: ObjectId
    space_id: ObjectId
    requirement_type: MetricRequirementType
    value: float
    unit: MetricUnit
    provenance: RelationshipProvenance
    priority: Priority = Priority.MUST
    evidence_ids: list[ObjectId] = Field(default_factory=list)
    rationale: str | None = None

    @field_validator("value")
    @classmethod
    def require_finite_positive_value(cls, v: float) -> float:
        return _validate_numeric_value(v)

    @model_validator(mode="after")
    def validate_requirement_invariants(self) -> MetricRequirement:
        _validate_unit_compatibility(self.requirement_type, self.unit)
        if self.provenance == RelationshipProvenance.USER_CONFIRMED and not self.evidence_ids:
            raise ValueError(
                f"USER_CONFIRMED metric requirement {self.id!r} on space {self.space_id!r} "
                f"requires at least one evidence ID."
            )
        return self


class SpaceMetricRequirements(_MetricContract):
    """Collection of metric requirements for a discrete addressable space."""

    space_id: ObjectId
    requirements: list[MetricRequirement] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_space_metric_invariants(self) -> SpaceMetricRequirements:
        req_types: set[MetricRequirementType] = set()
        req_map: dict[MetricRequirementType, float] = {}

        for req in self.requirements:
            if req.space_id != self.space_id:
                raise ValueError(
                    f"Requirement {req.id!r} space_id {req.space_id!r} does not match "
                    f"container space_id {self.space_id!r}"
                )
            if req.requirement_type in req_types:
                raise ValueError(
                    f"Duplicate requirement_type {req.requirement_type.value!r} for space "
                    f"{self.space_id!r}"
                )
            req_types.add(req.requirement_type)
            req_map[req.requirement_type] = req.value

        # Area range invariant checks
        min_area = req_map.get(MetricRequirementType.MIN_AREA)
        max_area = req_map.get(MetricRequirementType.MAX_AREA)
        target_area = req_map.get(MetricRequirementType.TARGET_AREA)

        if min_area is not None and max_area is not None and min_area > max_area:
            raise ValueError(
                f"Space {self.space_id!r} MIN_AREA ({min_area}) cannot exceed MAX_AREA ({max_area})"
            )

        if target_area is not None:
            if min_area is not None and target_area < min_area:
                raise ValueError(
                    f"Space {self.space_id!r} TARGET_AREA ({target_area}) cannot be less than "
                    f"MIN_AREA ({min_area})"
                )
            if max_area is not None and target_area > max_area:
                raise ValueError(
                    f"Space {self.space_id!r} TARGET_AREA ({target_area}) cannot exceed "
                    f"MAX_AREA ({max_area})"
                )

        return self


class MetricSpatialRequirements(_MetricContract):
    """Authoritative, immutable metric requirements contract for a spatial project."""

    schema_version: Literal["metric_spatial_requirements.v0"] = "metric_spatial_requirements.v0"
    project_id: ObjectId
    source_brief_version: int = Field(ge=1)
    source_program_schema_version: Literal["spatial_program.v0"] = "spatial_program.v0"
    created_at: datetime
    space_requirements: list[SpaceMetricRequirements] = Field(default_factory=list)
    authoritative_requirement_ids: list[ObjectId] = Field(default_factory=list)

    @field_validator("created_at")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        offset = value.utcoffset()
        if value.tzinfo is None or offset is None:
            raise ValueError("created_at must be timezone-aware")
        if offset != timedelta(0):
            raise ValueError("created_at must use UTC offset")
        return value

    @model_validator(mode="after")
    def validate_requirements_set_integrity(self) -> MetricSpatialRequirements:
        space_ids: set[str] = set()
        all_req_ids: set[str] = set()
        confirmed_req_ids: list[str] = []

        for space_req in self.space_requirements:
            if space_req.space_id in space_ids:
                raise ValueError(f"duplicate space_id {space_req.space_id!r} in space_requirements")
            space_ids.add(space_req.space_id)

            for req in space_req.requirements:
                if req.id in all_req_ids:
                    raise ValueError(f"duplicate requirement id {req.id!r}")
                all_req_ids.add(req.id)
                if req.provenance == RelationshipProvenance.USER_CONFIRMED:
                    confirmed_req_ids.append(req.id)

        expected_authoritative_ids = sorted(confirmed_req_ids)
        if self.authoritative_requirement_ids != expected_authoritative_ids:
            raise ValueError(
                f"authoritative_requirement_ids mismatch: expected {expected_authoritative_ids}, "
                f"got {self.authoritative_requirement_ids}"
            )

        return self
