"""Strict immutable contracts for BRIF.AI Spatial Relationship Graph V0."""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Iterable
from datetime import datetime, timedelta
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from brif_ai.brief.models.common import Priority
from brif_ai.core.models.common import NonEmptyString, ObjectId, SpaceFunction

if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:  # pragma: no cover

    class StrEnum(str, Enum):  # noqa: UP042
        pass


def _first_duplicate(values: Iterable[object]) -> object | None:
    seen: set[object] = set()
    for value in values:
        if value in seen:
            return value
        seen.add(value)
    return None


class SpatialRelationType(StrEnum):
    """Canonical spatial relation types between discrete space entities.

    SEMANTIC DEFINITIONS:
    - ADJACENT_TO:
        Spaces share an immediate physical boundary (wall, partition, floor/ceiling edge)
        or are directly contiguous in layout.
    - NEAR:
        Spaces are located in close physical or functional proximity within the building
        (e.g., in the same zone or short walking distance), without necessarily
        sharing a common wall.
    - SEPARATED_FROM:
        Spaces are intentionally placed distant from each other, in distinct zones, or separated
        by buffer spaces to prevent direct proximity or interaction.
    - DIRECT_ACCESS:
        Direct physical circulation exists between the two spaces without traversing intermediate
        rooms or corridors (e.g., a direct doorway or open threshold).
    - INDIRECT_ACCESS:
        Physical passage between the spaces exists via intermediate circulation spaces
        (e.g., corridor, foyer, staircase) rather than a direct room-to-room opening.
    - VISUAL_CONNECTION:
        A direct sightline, glazed partition, or visual opening allows occupants in one space
        to clearly see into the other space.
    - ACOUSTIC_SEPARATION:
        Acoustic attenuation or sound insulation is required between the two spaces to prevent
        sound transmission (e.g., sound-insulated walls or acoustic door seals). Can coexist
        with ADJACENT_TO or DIRECT_ACCESS if acoustically rated assemblies are used.
    - PRIVACY_SEPARATION:
        Spatial, visual, or acoustic buffering is required to maintain privacy between spaces
        (e.g., private bedroom retreat vs public entertaining area). Can coexist with
        VISUAL_CONNECTION when switchable, translucent, or high-level glazing is used.
    """

    ADJACENT_TO = "ADJACENT_TO"
    NEAR = "NEAR"
    SEPARATED_FROM = "SEPARATED_FROM"
    VISUAL_CONNECTION = "VISUAL_CONNECTION"
    DIRECT_ACCESS = "DIRECT_ACCESS"
    INDIRECT_ACCESS = "INDIRECT_ACCESS"
    ACOUSTIC_SEPARATION = "ACOUSTIC_SEPARATION"
    PRIVACY_SEPARATION = "PRIVACY_SEPARATION"


class RelationshipProvenance(StrEnum):
    """Epistemic status and origin of a spatial relationship requirement."""

    USER_STATED = "USER_STATED"
    AI_INFERRED = "AI_INFERRED"
    USER_CONFIRMED = "USER_CONFIRMED"


class _SpatialContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def generate_spatial_node_id(source_space_request_id: str, instance_index: int) -> str:
    """Generate a deterministic discrete node ID from a SpaceRequest ID and instance index."""
    cleaned = source_space_request_id.removeprefix("sr_")
    base = f"sn_{cleaned}"
    suffix = f"_{instance_index:02d}"
    if len(base) + len(suffix) > 64:
        base = base[: 64 - len(suffix)]
    return f"{base}{suffix}"


class SpatialNode(_SpatialContract):
    """Discrete addressable space instance in the spatial relationship graph.

    A SpaceRequest representing multiple requested spaces (e.g. minimum_quantity=2)
    deterministically expands into distinct SpatialNode instances (instance_index=1, 2, ...).
    """

    id: ObjectId
    display_name: NonEmptyString
    function: SpaceFunction
    source_space_request_id: ObjectId
    instance_index: int = Field(default=1, ge=1)
    mandatory: bool = True


class SpatialRelationshipInput(_SpatialContract):
    """Explicit structured relationship input from an authoritative caller.

    Zero free-text parsing. All fields must be explicitly populated.
    """

    source_space_id: ObjectId
    target_space_id: ObjectId
    relation_type: SpatialRelationType
    provenance: RelationshipProvenance
    priority: Priority = Priority.MUST
    evidence_ids: list[ObjectId] = Field(default_factory=list)
    rationale: str | None = None
    bidirectional: bool = True

    @field_validator("evidence_ids")
    @classmethod
    def reject_duplicate_evidence(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate evidence id {duplicate!r}")
        return value

    @model_validator(mode="after")
    def validate_endpoints_and_provenance(self) -> SpatialRelationshipInput:
        if self.source_space_id == self.target_space_id:
            raise ValueError(f"self-relationship not allowed on space {self.source_space_id!r}")
        if self.provenance == RelationshipProvenance.USER_CONFIRMED and not self.evidence_ids:
            raise ValueError("USER_CONFIRMED relationship requires at least one evidence_id")
        return self


def generate_relationship_id(
    project_id: str,
    relation_type: SpatialRelationType,
    source_id: str,
    target_id: str,
    *,
    bidirectional: bool = True,
) -> str:
    """Generate deterministic, stable relationship ID."""
    if bidirectional:
        first, second = sorted([source_id, target_id])
    else:
        first, second = source_id, target_id
    raw = f"{project_id}|{relation_type.value}|{first}|{second}".encode()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return f"srel_{digest}"


class SpatialRelationship(_SpatialContract):
    """Validated, immutable spatial relationship edge in the graph."""

    id: ObjectId
    source_space_id: ObjectId
    target_space_id: ObjectId
    relation_type: SpatialRelationType
    provenance: RelationshipProvenance
    priority: Priority = Priority.MUST
    evidence_ids: list[ObjectId] = Field(default_factory=list)
    rationale: str | None = None
    bidirectional: bool = True

    @field_validator("evidence_ids")
    @classmethod
    def reject_duplicate_evidence(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate evidence id {duplicate!r}")
        return value

    @model_validator(mode="after")
    def validate_non_self_relation(self) -> SpatialRelationship:
        if self.source_space_id == self.target_space_id:
            raise ValueError(f"self-relationship not allowed on space {self.source_space_id!r}")
        if self.provenance == RelationshipProvenance.USER_CONFIRMED and not self.evidence_ids:
            raise ValueError("USER_CONFIRMED relationship requires at least one evidence_id")
        return self


class SpatialConflict(_SpatialContract):
    """Structured conflict representation for mutually exclusive relationship assertions."""

    conflict_id: ObjectId
    space_a_id: ObjectId
    space_b_id: ObjectId
    conflicting_relationship_ids: list[ObjectId] = Field(min_length=2)
    conflicting_relation_types: list[SpatialRelationType] = Field(min_length=2)
    reason: NonEmptyString


class UnconstrainedPair(_SpatialContract):
    """Explicit deterministic representation of a space pair without any stated relation.

    Prevents hallucinating or assuming default relationships for unstated pairs.
    """

    space_a_id: ObjectId
    space_b_id: ObjectId

    @model_validator(mode="after")
    def validate_canonical_ordering(self) -> UnconstrainedPair:
        if self.space_a_id == self.space_b_id:
            raise ValueError("unconstrained pair must connect two distinct spaces")
        if self.space_a_id > self.space_b_id:
            raise ValueError(
                f"unconstrained pair must have space_a_id <= space_b_id: "
                f"{self.space_a_id!r} > {self.space_b_id!r}"
            )
        return self


class SpatialRelationshipGraph(_SpatialContract):
    """Authoritative, immutable spatial relationship graph for an architectural project."""

    schema_version: Literal["spatial_graph.v0"] = "spatial_graph.v0"
    project_id: ObjectId
    source_brief_version: int = Field(ge=1)
    created_at: datetime
    nodes: list[SpatialNode] = Field(min_length=1)
    relationships: list[SpatialRelationship] = Field(default_factory=list)
    unconstrained_pairs: list[UnconstrainedPair] = Field(default_factory=list)
    conflicts: list[SpatialConflict] = Field(default_factory=list)

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
    def validate_graph_integrity(self) -> SpatialRelationshipGraph:
        # Validate unique node IDs
        node_ids = set()
        for node in self.nodes:
            if node.id in node_ids:
                raise ValueError(f"duplicate spatial node id {node.id!r}")
            node_ids.add(node.id)

        # Validate unique relationship IDs
        rel_ids = set()
        for rel in self.relationships:
            if rel.id in rel_ids:
                raise ValueError(f"duplicate spatial relationship id {rel.id!r}")
            rel_ids.add(rel.id)
            if rel.source_space_id not in node_ids:
                raise ValueError(
                    f"relationship {rel.id!r} references unknown source_space_id "
                    f"{rel.source_space_id!r}"
                )
            if rel.target_space_id not in node_ids:
                raise ValueError(
                    f"relationship {rel.id!r} references unknown target_space_id "
                    f"{rel.target_space_id!r}"
                )

        # Validate unconstrained pairs references
        for pair in self.unconstrained_pairs:
            if pair.space_a_id not in node_ids:
                raise ValueError(
                    f"unconstrained pair references unknown space_a_id {pair.space_a_id!r}"
                )
            if pair.space_b_id not in node_ids:
                raise ValueError(
                    f"unconstrained pair references unknown space_b_id {pair.space_b_id!r}"
                )

        return self
