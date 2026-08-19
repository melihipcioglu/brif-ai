"""Strict immutable contracts for BRIF.AI Schematic Layout Problem V0."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from brif_ai.brief.models.common import Priority
from brif_ai.core.models.common import NonEmptyString, ObjectId, SpaceFunction
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationship,
    SpatialRelationType,
    UnconstrainedPair,
)


class _LayoutContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LayoutSpace(_LayoutContract):
    """Deterministic space representation prepared for schematic layout solving.

    Preserves exact identity, source ProgramSpace traceability, stakeholder IDs,
    and evidence IDs. Contains zero geometric or dimensional assumptions.
    """

    id: ObjectId
    source_program_space_id: ObjectId
    display_name: NonEmptyString
    function: SpaceFunction
    instance_index: int = Field(ge=1)
    mandatory: bool
    stakeholder_ids: list[ObjectId] = Field(default_factory=list)
    evidence_ids: list[ObjectId] = Field(default_factory=list)


class LayoutConstraint(_LayoutContract):
    """Authoritative spatial relationship constraint for schematic layout problem.

    Derived strictly from USER_CONFIRMED spatial relationships.
    Preserves exact relationship priority (MUST/SHOULD/COULD) without prematurely
    converting priority into solver hard vs. soft mechanics.
    """

    id: ObjectId
    source_relationship_id: ObjectId
    source_space_id: ObjectId
    target_space_id: ObjectId
    relation_type: SpatialRelationType
    provenance: Literal[RelationshipProvenance.USER_CONFIRMED] = (
        RelationshipProvenance.USER_CONFIRMED
    )
    priority: Priority = Priority.MUST
    evidence_ids: list[ObjectId] = Field(default_factory=list)
    rationale: str | None = None
    bidirectional: bool = True

    @model_validator(mode="after")
    def validate_constraint_invariants(self) -> LayoutConstraint:
        if self.source_space_id == self.target_space_id:
            raise ValueError(f"self-constraint not allowed on space {self.source_space_id!r}")
        if self.id != self.source_relationship_id:
            raise ValueError(
                f"LayoutConstraint id {self.id!r} must match "
                f"source_relationship_id {self.source_relationship_id!r}"
            )
        return self


class SchematicLayoutProblem(_LayoutContract):
    """Immutable input problem boundary defining WHAT a schematic layout solver must solve.

    Contains zero geometric dimensions, areas, coordinates, or floor positions.
    Maintains strict epistemic segregation between authoritative constraints
    (USER_CONFIRMED) and informational relationships (USER_STATED / AI_INFERRED).
    """

    schema_version: Literal["schematic_layout_problem.v0"] = "schematic_layout_problem.v0"
    project_id: ObjectId
    source_brief_version: int = Field(ge=1)
    source_program_schema_version: Literal["spatial_program.v0"] = "spatial_program.v0"
    created_at: datetime
    spaces: list[LayoutSpace] = Field(min_length=1)
    authoritative_constraints: list[LayoutConstraint] = Field(default_factory=list)
    informational_relationships: list[SpatialRelationship] = Field(default_factory=list)
    unconstrained_pairs: list[UnconstrainedPair] = Field(default_factory=list)

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
    def validate_problem_integrity(self) -> SchematicLayoutProblem:
        # Validate unique space IDs
        space_ids: set[str] = set()
        for space in self.spaces:
            if space.id in space_ids:
                raise ValueError(f"duplicate layout space id {space.id!r}")
            space_ids.add(space.id)

        # Validate authoritative constraints
        constraint_ids: set[str] = set()
        for constraint in self.authoritative_constraints:
            if constraint.id in constraint_ids:
                raise ValueError(f"duplicate authoritative constraint id {constraint.id!r}")
            constraint_ids.add(constraint.id)
            if constraint.source_space_id not in space_ids:
                raise ValueError(
                    f"constraint {constraint.id!r} references unknown source_space_id "
                    f"{constraint.source_space_id!r}"
                )
            if constraint.target_space_id not in space_ids:
                raise ValueError(
                    f"constraint {constraint.id!r} references unknown target_space_id "
                    f"{constraint.target_space_id!r}"
                )

        # Validate informational relationships
        info_ids: set[str] = set()
        for rel in self.informational_relationships:
            if rel.id in info_ids:
                raise ValueError(f"duplicate informational relationship id {rel.id!r}")
            if rel.id in constraint_ids:
                raise ValueError(
                    f"relationship {rel.id!r} cannot be both authoritative and informational"
                )
            info_ids.add(rel.id)
            if rel.source_space_id not in space_ids:
                raise ValueError(
                    f"informational relationship {rel.id!r} references unknown "
                    f"source_space_id {rel.source_space_id!r}"
                )
            if rel.target_space_id not in space_ids:
                raise ValueError(
                    f"informational relationship {rel.id!r} references unknown "
                    f"target_space_id {rel.target_space_id!r}"
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

        return self
