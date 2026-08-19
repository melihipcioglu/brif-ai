"""Strict immutable contracts and total mappings for BRIF.AI Layout Solver Policy V0."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from brif_ai.brief.models.common import Priority
from brif_ai.core.models.common import ObjectId
from brif_ai.spatial.layout.models import LayoutSpace
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationType,
    UnconstrainedPair,
)

if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:  # pragma: no cover

    class StrEnum(str, Enum):  # noqa: UP042
        pass


class ConstraintEnforcement(StrEnum):
    """Enforcement level indicating HOW a future layout solver must treat a directive.

    Mapped deterministically from design Priority:
    - MUST -> REQUIRED
    - SHOULD -> PREFERRED
    - COULD -> OPTIONAL
    - UNSPECIFIED -> UNSPECIFIED
    """

    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"
    OPTIONAL = "OPTIONAL"
    UNSPECIFIED = "UNSPECIFIED"


class SolverRelationOperator(StrEnum):
    """Abstract, solver-neutral geometric/topological relation operators.

    Mapped deterministically from canonical SpatialRelationType without
    inventing geometric thresholds or numerical distance metrics.
    """

    ADJACENCY = "ADJACENCY"
    PROXIMITY = "PROXIMITY"
    SEPARATION = "SEPARATION"
    VISUAL_CONNECTIVITY = "VISUAL_CONNECTIVITY"
    DIRECT_CONNECTIVITY = "DIRECT_CONNECTIVITY"
    INDIRECT_CONNECTIVITY = "INDIRECT_CONNECTIVITY"
    ACOUSTIC_BUFFERING = "ACOUSTIC_BUFFERING"
    PRIVACY_BUFFERING = "PRIVACY_BUFFERING"


def map_priority_to_enforcement(priority: Priority) -> ConstraintEnforcement:
    """Total immutable mapping from design Priority to solver ConstraintEnforcement."""
    match priority:
        case Priority.MUST:
            return ConstraintEnforcement.REQUIRED
        case Priority.SHOULD:
            return ConstraintEnforcement.PREFERRED
        case Priority.COULD:
            return ConstraintEnforcement.OPTIONAL
        case Priority.UNSPECIFIED:
            return ConstraintEnforcement.UNSPECIFIED


def map_relation_type_to_operator(
    relation_type: SpatialRelationType,
) -> SolverRelationOperator:
    """Total immutable mapping from SpatialRelationType to abstract SolverRelationOperator."""
    match relation_type:
        case SpatialRelationType.ADJACENT_TO:
            return SolverRelationOperator.ADJACENCY
        case SpatialRelationType.NEAR:
            return SolverRelationOperator.PROXIMITY
        case SpatialRelationType.SEPARATED_FROM:
            return SolverRelationOperator.SEPARATION
        case SpatialRelationType.VISUAL_CONNECTION:
            return SolverRelationOperator.VISUAL_CONNECTIVITY
        case SpatialRelationType.DIRECT_ACCESS:
            return SolverRelationOperator.DIRECT_CONNECTIVITY
        case SpatialRelationType.INDIRECT_ACCESS:
            return SolverRelationOperator.INDIRECT_CONNECTIVITY
        case SpatialRelationType.ACOUSTIC_SEPARATION:
            return SolverRelationOperator.ACOUSTIC_BUFFERING
        case SpatialRelationType.PRIVACY_SEPARATION:
            return SolverRelationOperator.PRIVACY_BUFFERING


class _SolverPolicyContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SolverDirective(_SolverPolicyContract):
    """Authoritative instruction for downstream layout solver engine.

    Derived exclusively from authoritative constraints (USER_CONFIRMED).
    Combines abstract relational operator with explicit enforcement level.
    """

    id: ObjectId
    source_constraint_id: ObjectId
    source_space_id: ObjectId
    target_space_id: ObjectId
    source_relation_type: SpatialRelationType
    operator: SolverRelationOperator
    enforcement: ConstraintEnforcement
    priority: Priority
    provenance: Literal[RelationshipProvenance.USER_CONFIRMED] = (
        RelationshipProvenance.USER_CONFIRMED
    )
    evidence_ids: list[ObjectId] = Field(default_factory=list)
    rationale: str | None = None
    bidirectional: bool = True

    @model_validator(mode="after")
    def validate_directive_invariants(self) -> SolverDirective:
        if self.source_space_id == self.target_space_id:
            raise ValueError(f"self-directive not allowed on space {self.source_space_id!r}")
        if self.id != self.source_constraint_id:
            raise ValueError(
                f"SolverDirective id {self.id!r} must match "
                f"source_constraint_id {self.source_constraint_id!r}"
            )
        # Verify mapped consistency
        expected_enforcement = map_priority_to_enforcement(self.priority)
        if self.enforcement != expected_enforcement:
            raise ValueError(
                f"enforcement {self.enforcement!r} does not match priority {self.priority!r} "
                f"(expected {expected_enforcement!r})"
            )
        expected_operator = map_relation_type_to_operator(self.source_relation_type)
        if self.operator != expected_operator:
            raise ValueError(
                f"operator {self.operator!r} does not match relation_type "
                f"{self.source_relation_type!r} (expected {expected_operator!r})"
            )
        return self


class SolverDirectiveSet(_SolverPolicyContract):
    """Authoritative, solver-facing input contract prepared for layout generation.

    Contains exclusively authoritative solver directives, discrete spaces,
    and unconstrained pairs. Informational relationships are deliberately excluded
    to prevent accidental solver consumption.
    """

    schema_version: Literal["solver_directive_set.v0"] = "solver_directive_set.v0"
    project_id: ObjectId
    source_brief_version: int = Field(ge=1)
    source_layout_problem_schema_version: Literal["schematic_layout_problem.v0"] = (
        "schematic_layout_problem.v0"
    )
    created_at: datetime
    spaces: list[LayoutSpace] = Field(min_length=1)
    directives: list[SolverDirective] = Field(default_factory=list)
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
    def validate_directive_set_integrity(self) -> SolverDirectiveSet:
        # Validate unique space IDs
        space_ids: set[str] = set()
        for space in self.spaces:
            if space.id in space_ids:
                raise ValueError(f"duplicate space id {space.id!r}")
            space_ids.add(space.id)

        # Validate directives
        directive_ids: set[str] = set()
        for directive in self.directives:
            if directive.id in directive_ids:
                raise ValueError(f"duplicate directive id {directive.id!r}")
            directive_ids.add(directive.id)
            if directive.source_space_id not in space_ids:
                raise ValueError(
                    f"directive {directive.id!r} references unknown source_space_id "
                    f"{directive.source_space_id!r}"
                )
            if directive.target_space_id not in space_ids:
                raise ValueError(
                    f"directive {directive.id!r} references unknown target_space_id "
                    f"{directive.target_space_id!r}"
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
