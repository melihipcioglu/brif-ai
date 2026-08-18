"""Deterministic validation engine and contradiction matrix for spatial relationships."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Collection, Sequence
from typing import Any

from brif_ai.spatial.errors import (
    InvalidEvidenceReferenceError,
    NonexistentSpaceError,
    SelfRelationshipError,
)
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialConflict,
    SpatialRelationship,
    SpatialRelationshipInput,
    SpatialRelationType,
    generate_relationship_id,
)

# Canonical mutually exclusive relationship pairs on the same space pair (A, B).
# Each entry is a frozenset of two SpatialRelationTypes that are logically guaranteed
# to contradict each other by their explicit semantic definitions.
MUTUALLY_EXCLUSIVE_PAIRS: frozenset[frozenset[SpatialRelationType]] = frozenset(
    {
        # Physical border adjacency directly contradicts deliberate physical separation/distance.
        frozenset({SpatialRelationType.ADJACENT_TO, SpatialRelationType.SEPARATED_FROM}),
        # Proximity/nearness directly contradicts deliberate physical separation/distance.
        frozenset({SpatialRelationType.NEAR, SpatialRelationType.SEPARATED_FROM}),
        # Direct access opening directly contradicts physical separation/distance.
        frozenset({SpatialRelationType.DIRECT_ACCESS, SpatialRelationType.SEPARATED_FROM}),
    }
)


_CONFLICT_REASONS: dict[frozenset[SpatialRelationType], str] = {
    frozenset({SpatialRelationType.ADJACENT_TO, SpatialRelationType.SEPARATED_FROM}): (
        "Fiziksel bitişiklik (ADJACENT_TO) ile mekânsal ayrışma (SEPARATED_FROM) "
        "aynı mekân çifti için birbiriyle çelişmektedir."
    ),
    frozenset({SpatialRelationType.NEAR, SpatialRelationType.SEPARATED_FROM}): (
        "Yakınlık tercihi (NEAR) ile mekânsal ayrışma (SEPARATED_FROM) "
        "aynı mekân çifti için birbiriyle çelişmektedir."
    ),
    frozenset({SpatialRelationType.DIRECT_ACCESS, SpatialRelationType.SEPARATED_FROM}): (
        "Doğrudan geçiş (DIRECT_ACCESS) ile mekânsal ayrışma (SEPARATED_FROM) "
        "aynı mekân çifti için birbiriyle çelişmektedir."
    ),
}

_DedupKey = tuple[tuple[str, str], SpatialRelationType, RelationshipProvenance, str, bool]


def _pair_key(space_a: str, space_b: str) -> tuple[str, str]:
    """Return deterministic canonical pair key."""
    return tuple(sorted([space_a, space_b]))  # type: ignore[return-value]


def validate_spatial_relationship_inputs(
    inputs: Sequence[SpatialRelationshipInput],
    valid_space_ids: Collection[str],
) -> None:
    """Validate structural constraints on relationship inputs before graph building.

    Raises:
        NonexistentSpaceError: If source or target space is not in valid_space_ids.
        SelfRelationshipError: If source == target.
    """
    valid_set = set(valid_space_ids)
    for idx, item in enumerate(inputs):
        if item.source_space_id not in valid_set:
            raise NonexistentSpaceError(
                f"Relationship at index {idx} references nonexistent source_space_id "
                f"{item.source_space_id!r}"
            )
        if item.target_space_id not in valid_set:
            raise NonexistentSpaceError(
                f"Relationship at index {idx} references nonexistent target_space_id "
                f"{item.target_space_id!r}"
            )
        if item.source_space_id == item.target_space_id:
            raise SelfRelationshipError(
                f"Self-relationship not allowed: space {item.source_space_id!r} "
                f"cannot relate to itself"
            )


def validate_evidence_references(
    inputs: Sequence[SpatialRelationshipInput],
    valid_evidence_ids: Collection[str],
) -> None:
    """Verify that every referenced evidence_id exists in the authoritative BriefSnapshot.

    USER_CONFIRMED relationships MUST have at least one valid evidence_id.

    Raises:
        InvalidEvidenceReferenceError: If a USER_CONFIRMED relationship lacks evidence_ids,
            or if any referenced evidence_id is not present in valid_evidence_ids.
    """
    valid_set = set(valid_evidence_ids)
    for idx, item in enumerate(inputs):
        if item.provenance == RelationshipProvenance.USER_CONFIRMED and not item.evidence_ids:
            raise InvalidEvidenceReferenceError(
                f"Relationship at index {idx} ({item.relation_type.value}) has provenance "
                "USER_CONFIRMED but does not reference any evidence_id"
            )
        for ev_id in item.evidence_ids:
            if ev_id not in valid_set:
                raise InvalidEvidenceReferenceError(
                    f"Relationship at index {idx} ({item.relation_type.value}) references "
                    f"nonexistent evidence_id {ev_id!r}"
                )


def deduplicate_and_materialize_relationships(
    project_id: str,
    inputs: Sequence[SpatialRelationshipInput],
) -> list[SpatialRelationship]:
    """Deduplicate identical structured relationships and materialize with stable IDs.

    Preserves exact original provenance (USER_STATED, AI_INFERRED, USER_CONFIRMED)
    without any automatic provenance promotion.
    """
    dedup_map: dict[_DedupKey, dict[str, Any]] = {}

    for item in inputs:
        pk = _pair_key(item.source_space_id, item.target_space_id)
        priority_val = (
            item.priority.value if hasattr(item.priority, "value") else str(item.priority)
        )
        key: _DedupKey = (
            pk,
            item.relation_type,
            item.provenance,
            priority_val,
            item.bidirectional,
        )

        if key in dedup_map:
            existing = dedup_map[key]
            # Merge evidence IDs deterministically
            merged_evidence = sorted(set(existing["evidence_ids"] + list(item.evidence_ids)))
            existing["evidence_ids"] = merged_evidence
            if item.rationale and not existing.get("rationale"):
                existing["rationale"] = item.rationale
        else:
            rel_id = generate_relationship_id(
                project_id,
                item.relation_type,
                item.source_space_id,
                item.target_space_id,
                bidirectional=item.bidirectional,
            )
            # Use canonical node order for bidirectional relations
            if item.bidirectional:
                src, tgt = pk[0], pk[1]
            else:
                src, tgt = item.source_space_id, item.target_space_id

            dedup_map[key] = {
                "id": rel_id,
                "source_space_id": src,
                "target_space_id": tgt,
                "relation_type": item.relation_type,
                "provenance": item.provenance,
                "priority": item.priority,
                "evidence_ids": sorted(set(item.evidence_ids)),
                "rationale": item.rationale,
                "bidirectional": item.bidirectional,
            }

    # Sort deterministically by ID
    materialized = [SpatialRelationship.model_validate(data) for data in dedup_map.values()]
    return sorted(materialized, key=lambda r: (r.id, r.source_space_id, r.target_space_id))


def detect_spatial_conflicts(
    relationships: Sequence[SpatialRelationship],
) -> list[SpatialConflict]:
    """Detect mutually exclusive relationship pairs and generate structured SpatialConflicts.

    Does not crash graph construction; returns structured conflicts so the caller / elicitation
    engine can inspect and resolve them.
    """
    pair_relationships: dict[tuple[str, str], list[SpatialRelationship]] = defaultdict(list)
    for rel in relationships:
        pk = _pair_key(rel.source_space_id, rel.target_space_id)
        pair_relationships[pk].append(rel)

    conflicts: list[SpatialConflict] = []

    for (space_a, space_b), rels in sorted(pair_relationships.items()):
        seen_conflict_pairs: set[frozenset[SpatialRelationType]] = set()

        for i in range(len(rels)):
            for j in range(i + 1, len(rels)):
                rel_1 = rels[i]
                rel_2 = rels[j]
                rel_types = frozenset({rel_1.relation_type, rel_2.relation_type})

                if rel_types in MUTUALLY_EXCLUSIVE_PAIRS and rel_types not in seen_conflict_pairs:
                    seen_conflict_pairs.add(rel_types)
                    reason = _CONFLICT_REASONS.get(
                        rel_types,
                        f"Çelişkili ilişkiler: {rel_1.relation_type.value}, "
                        f"{rel_2.relation_type.value}",
                    )
                    sorted_types = sorted(list(rel_types), key=lambda t: t.value)
                    type_str = "|".join(t.value for t in sorted_types)
                    conflict_id_raw = f"conf|{space_a}|{space_b}|{type_str}"
                    digest = hashlib.sha256(conflict_id_raw.encode()).hexdigest()[:16]
                    conflict_id = f"conf_{digest}"

                    conflicts.append(
                        SpatialConflict(
                            conflict_id=conflict_id,
                            space_a_id=space_a,
                            space_b_id=space_b,
                            conflicting_relationship_ids=sorted([rel_1.id, rel_2.id]),
                            conflicting_relation_types=sorted_types,
                            reason=reason,
                        )
                    )

    return sorted(conflicts, key=lambda c: (c.conflict_id, c.space_a_id, c.space_b_id))
