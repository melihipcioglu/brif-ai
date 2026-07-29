"""User brief snapshot contracts for BRIF.AI v0.

Brief snapshots store user-confirmable brief data. Only CONFIRMED records are
intended to feed later architectural program generation; this module does not
perform that conversion.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator, model_validator

from brif_ai.brief.models.common import (
    BriefItemKind,
    ConfirmationStatus,
    ContradictionStatus,
    EvidenceSource,
    OpenQuestionStatus,
    Priority,
)
from brif_ai.core.models.common import ContractModel, NonEmptyString, ObjectId, SpaceFunction

DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
StakeholderRole = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
]
SourceReference = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=250)
]
EvidenceExcerpt = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]
NormalizedStatement = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]


def _first_duplicate(values: Iterable[str]) -> str | None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            return value
        seen.add(value)
    return None


class Stakeholder(ContractModel):
    id: ObjectId
    display_name: DisplayName
    role: StakeholderRole
    active: bool


class Evidence(ContractModel):
    id: ObjectId
    source_type: EvidenceSource
    source_reference: SourceReference
    excerpt: EvidenceExcerpt
    stimulus_id: ObjectId | None = None

    @model_validator(mode="after")
    def validate_stimulus_reference(self) -> Evidence:
        if self.source_type is EvidenceSource.VISUAL_STIMULUS and self.stimulus_id is None:
            raise ValueError("visual stimulus evidence requires stimulus_id")
        if self.source_type is not EvidenceSource.VISUAL_STIMULUS and self.stimulus_id is not None:
            raise ValueError("stimulus_id is only allowed for visual stimulus evidence")
        return self


class BriefItem(ContractModel):
    id: ObjectId
    kind: BriefItemKind
    normalized_statement: NormalizedStatement
    priority: Priority
    stakeholder_ids: list[ObjectId]
    evidence_ids: list[ObjectId] = Field(min_length=1)
    confirmation_status: ConfirmationStatus

    @field_validator("stakeholder_ids", "evidence_ids")
    @classmethod
    def reject_duplicate_references(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate reference id {duplicate!r}")
        return value


class SpaceRequest(ContractModel):
    id: ObjectId
    display_name: DisplayName
    space_function: SpaceFunction
    minimum_quantity: int = Field(ge=1)
    maximum_quantity: int | None = Field(default=None, ge=1)
    mandatory: bool
    stakeholder_ids: list[ObjectId]
    evidence_ids: list[ObjectId] = Field(min_length=1)
    confirmation_status: ConfirmationStatus

    @field_validator("stakeholder_ids", "evidence_ids")
    @classmethod
    def reject_duplicate_references(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate reference id {duplicate!r}")
        return value

    @model_validator(mode="after")
    def validate_quantity_range(self) -> SpaceRequest:
        if self.maximum_quantity is not None and self.maximum_quantity < self.minimum_quantity:
            raise ValueError("maximum_quantity cannot be less than minimum_quantity")
        return self


class UsageScenario(ContractModel):
    id: ObjectId
    title: NonEmptyString
    description: NonEmptyString
    stakeholder_ids: list[ObjectId] = Field(min_length=1)
    evidence_ids: list[ObjectId] = Field(min_length=1)
    confirmation_status: ConfirmationStatus

    @field_validator("stakeholder_ids", "evidence_ids")
    @classmethod
    def reject_duplicate_references(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate reference id {duplicate!r}")
        return value


class Contradiction(ContractModel):
    id: ObjectId
    brief_item_ids: list[ObjectId] = Field(min_length=2)
    description: NonEmptyString
    status: ContradictionStatus
    resolution_note: NonEmptyString | None = None

    @field_validator("brief_item_ids")
    @classmethod
    def reject_duplicate_brief_item_references(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate brief_item_id {duplicate!r}")
        return value

    @model_validator(mode="after")
    def require_resolution_note_when_resolved(self) -> Contradiction:
        if self.status is ContradictionStatus.RESOLVED and self.resolution_note is None:
            raise ValueError("resolved contradiction requires resolution_note")
        return self


class OpenQuestion(ContractModel):
    id: ObjectId
    question: NonEmptyString
    reason: NonEmptyString
    related_brief_item_ids: list[ObjectId]
    status: OpenQuestionStatus
    resolution_note: NonEmptyString | None = None

    @field_validator("related_brief_item_ids")
    @classmethod
    def reject_duplicate_brief_item_references(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate related_brief_item_id {duplicate!r}")
        return value

    @model_validator(mode="after")
    def require_resolution_note_when_closed(self) -> OpenQuestion:
        if (
            self.status
            in {
                OpenQuestionStatus.ANSWERED,
                OpenQuestionStatus.DISMISSED,
            }
            and self.resolution_note is None
        ):
            raise ValueError("answered or dismissed open question requires resolution_note")
        return self


BriefObject = (
    Stakeholder | Evidence | BriefItem | SpaceRequest | UsageScenario | Contradiction | OpenQuestion
)


class BriefSnapshot(ContractModel):
    project_id: ObjectId
    schema_version: NonEmptyString
    brief_version: int = Field(ge=1)
    created_at: datetime
    stakeholders: list[Stakeholder] = Field(min_length=1)
    evidence: list[Evidence]
    brief_items: list[BriefItem]
    space_requests: list[SpaceRequest]
    usage_scenarios: list[UsageScenario]
    contradictions: list[Contradiction]
    open_questions: list[OpenQuestion]

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
    def validate_snapshot_integrity(self) -> BriefSnapshot:
        self._validate_unique_object_ids()

        stakeholder_ids = {stakeholder.id for stakeholder in self.stakeholders}
        evidence_ids = {evidence.id for evidence in self.evidence}
        brief_item_ids = {brief_item.id for brief_item in self.brief_items}

        for brief_item in self.brief_items:
            self._validate_stakeholder_references(
                "brief item", brief_item.id, brief_item.stakeholder_ids, stakeholder_ids
            )
            self._validate_evidence_references(
                "brief item", brief_item.id, brief_item.evidence_ids, evidence_ids
            )

        for space_request in self.space_requests:
            self._validate_stakeholder_references(
                "space request",
                space_request.id,
                space_request.stakeholder_ids,
                stakeholder_ids,
            )
            self._validate_evidence_references(
                "space request",
                space_request.id,
                space_request.evidence_ids,
                evidence_ids,
            )

        for usage_scenario in self.usage_scenarios:
            self._validate_stakeholder_references(
                "usage scenario",
                usage_scenario.id,
                usage_scenario.stakeholder_ids,
                stakeholder_ids,
            )
            self._validate_evidence_references(
                "usage scenario",
                usage_scenario.id,
                usage_scenario.evidence_ids,
                evidence_ids,
            )

        for contradiction in self.contradictions:
            self._validate_brief_item_references(
                "contradiction",
                contradiction.id,
                contradiction.brief_item_ids,
                brief_item_ids,
            )

        for open_question in self.open_questions:
            self._validate_brief_item_references(
                "open question",
                open_question.id,
                open_question.related_brief_item_ids,
                brief_item_ids,
            )

        return self

    def _validate_unique_object_ids(self) -> None:
        seen: dict[str, str] = {}
        collections: list[tuple[str, Iterable[BriefObject]]] = [
            ("stakeholder", self.stakeholders),
            ("evidence", self.evidence),
            ("brief_item", self.brief_items),
            ("space_request", self.space_requests),
            ("usage_scenario", self.usage_scenarios),
            ("contradiction", self.contradictions),
            ("open_question", self.open_questions),
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

    @staticmethod
    def _validate_stakeholder_references(
        owner_type: str,
        owner_id: str,
        reference_ids: Iterable[str],
        valid_ids: set[str],
    ) -> None:
        for reference_id in reference_ids:
            if reference_id not in valid_ids:
                raise ValueError(
                    f"{owner_type} {owner_id!r} references unknown stakeholder_id {reference_id!r}"
                )

    @staticmethod
    def _validate_evidence_references(
        owner_type: str,
        owner_id: str,
        reference_ids: Iterable[str],
        valid_ids: set[str],
    ) -> None:
        for reference_id in reference_ids:
            if reference_id not in valid_ids:
                raise ValueError(
                    f"{owner_type} {owner_id!r} references unknown evidence_id {reference_id!r}"
                )

    @staticmethod
    def _validate_brief_item_references(
        owner_type: str,
        owner_id: str,
        reference_ids: Iterable[str],
        valid_ids: set[str],
    ) -> None:
        for reference_id in reference_ids:
            if reference_id not in valid_ids:
                raise ValueError(
                    f"{owner_type} {owner_id!r} references unknown brief_item_id {reference_id!r}"
                )
