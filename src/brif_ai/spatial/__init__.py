"""BRIF.AI — Spatial Relationship Domain Package (V0.2).

Provides strict immutable contracts and deterministic builder for spatial
relationship graphs derived from approved briefs and structured relationship inputs.
"""

from __future__ import annotations

from brif_ai.spatial.builder import SpatialRelationshipGraphBuilder
from brif_ai.spatial.errors import (
    DuplicateRelationshipError,
    InvalidEvidenceReferenceError,
    InvalidProvenanceError,
    NonexistentSpaceError,
    SelfRelationshipError,
    SpatialGraphError,
)
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialConflict,
    SpatialNode,
    SpatialRelationship,
    SpatialRelationshipGraph,
    SpatialRelationshipInput,
    SpatialRelationType,
    UnconstrainedPair,
    generate_relationship_id,
    generate_spatial_node_id,
)
from brif_ai.spatial.validator import (
    MUTUALLY_EXCLUSIVE_PAIRS,
    deduplicate_and_materialize_relationships,
    detect_spatial_conflicts,
    validate_evidence_references,
    validate_spatial_relationship_inputs,
)

__all__ = [
    "MUTUALLY_EXCLUSIVE_PAIRS",
    "DuplicateRelationshipError",
    "InvalidEvidenceReferenceError",
    "InvalidProvenanceError",
    "NonexistentSpaceError",
    "RelationshipProvenance",
    "SelfRelationshipError",
    "SpatialConflict",
    "SpatialGraphError",
    "SpatialNode",
    "SpatialRelationship",
    "SpatialRelationshipGraph",
    "SpatialRelationshipGraphBuilder",
    "SpatialRelationshipInput",
    "SpatialRelationType",
    "UnconstrainedPair",
    "deduplicate_and_materialize_relationships",
    "detect_spatial_conflicts",
    "generate_relationship_id",
    "generate_spatial_node_id",
    "validate_evidence_references",
    "validate_spatial_relationship_inputs",
]
