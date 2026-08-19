"""Strict immutable contracts for BRIF.AI Spatial Program V0."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from brif_ai.core.models.common import NonEmptyString, ObjectId, SpaceFunction
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationship,
    UnconstrainedPair,
)


class _SpatialProgramContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProgramSpace(_SpatialProgramContract):
    """Deterministic, discrete addressable space instance within a SpatialProgram.

    Preserves exact traceability to source SpaceRequest, requesting stakeholders,
    grounded evidence, space function, instance index, and mandatory status.
    """

    id: ObjectId
    source_space_request_id: ObjectId
    display_name: NonEmptyString
    function: SpaceFunction
    instance_index: int = Field(ge=1)
    mandatory: bool
    stakeholder_ids: list[ObjectId] = Field(default_factory=list)
    evidence_ids: list[ObjectId] = Field(default_factory=list)


class SpatialProgram(_SpatialProgramContract):
    """Authoritative, immutable spatial program contract.

    Acts as the strict deterministic machine-readable input boundary for future
    schematic plan generation.
    """

    schema_version: Literal["spatial_program.v0"] = "spatial_program.v0"
    project_id: ObjectId
    source_brief_version: int = Field(ge=1)
    created_at: datetime
    spaces: list[ProgramSpace] = Field(min_length=1)
    relationships: list[SpatialRelationship] = Field(default_factory=list)
    unconstrained_pairs: list[UnconstrainedPair] = Field(default_factory=list)
    authoritative_relationship_ids: list[ObjectId] = Field(default_factory=list)

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
    def validate_spatial_program_integrity(self) -> SpatialProgram:
        # Validate unique space IDs
        space_ids: set[str] = set()
        for space in self.spaces:
            if space.id in space_ids:
                raise ValueError(f"duplicate program space id {space.id!r}")
            space_ids.add(space.id)

        # Validate relationships and their endpoints
        rel_map: dict[str, SpatialRelationship] = {}
        for rel in self.relationships:
            if rel.id in rel_map:
                raise ValueError(f"duplicate relationship id {rel.id!r}")
            rel_map[rel.id] = rel
            if rel.source_space_id not in space_ids:
                raise ValueError(
                    f"relationship {rel.id!r} references unknown source_space_id "
                    f"{rel.source_space_id!r}"
                )
            if rel.target_space_id not in space_ids:
                raise ValueError(
                    f"relationship {rel.id!r} references unknown target_space_id "
                    f"{rel.target_space_id!r}"
                )

        # Validate unconstrained pairs
        for pair in self.unconstrained_pairs:
            if pair.space_a_id not in space_ids:
                raise ValueError(
                    f"unconstrained pair references unknown space_a_id {pair.space_a_id!r}"
                )
            if pair.space_b_id not in space_ids:
                raise ValueError(
                    f"unconstrained pair references unknown space_b_id {pair.space_b_id!r}"
                )

        # Validate authoritative_relationship_ids boundary:
        # Must match EXACTLY all relationships with USER_CONFIRMED provenance
        expected_authoritative_ids = sorted(
            r.id
            for r in self.relationships
            if r.provenance is RelationshipProvenance.USER_CONFIRMED
        )
        if self.authoritative_relationship_ids != expected_authoritative_ids:
            raise ValueError(
                f"authoritative_relationship_ids mismatch: expected {expected_authoritative_ids}, "
                f"got {self.authoritative_relationship_ids}"
            )

        return self
