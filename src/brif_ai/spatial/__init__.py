"""BRIF.AI Spatial Relationship Graph Domain Package."""

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
    ProposedSpatialRelationship,
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
    project_space_requests_to_spatial_nodes,
)
from brif_ai.spatial.persistence import (
    JSONSpatialRelationshipRepository,
    SpatialGraphNotFoundError,
    SpatialGraphPersistenceError,
    SpatialGraphVersionConflictError,
    SpatialRelationshipRepository,
)
from brif_ai.spatial.service import PersistentSpatialService
from brif_ai.spatial.validator import (
    MUTUALLY_EXCLUSIVE_PAIRS,
    deduplicate_and_materialize_relationships,
    detect_spatial_conflicts,
    validate_evidence_references,
    validate_spatial_relationship_inputs,
)

__all__ = [
    "JSONSpatialRelationshipRepository",
    "MUTUALLY_EXCLUSIVE_PAIRS",
    "DuplicateRelationshipError",
    "InvalidEvidenceReferenceError",
    "InvalidProvenanceError",
    "NonexistentSpaceError",
    "PersistentSpatialService",
    "ProposedSpatialRelationship",
    "RelationshipProvenance",
    "SelfRelationshipError",
    "SpatialConflict",
    "SpatialGraphError",
    "SpatialGraphNotFoundError",
    "SpatialGraphPersistenceError",
    "SpatialGraphVersionConflictError",
    "SpatialNode",
    "SpatialRelationship",
    "SpatialRelationshipGraph",
    "SpatialRelationshipGraphBuilder",
    "SpatialRelationshipInput",
    "SpatialRelationshipRepository",
    "SpatialRelationType",
    "UnconstrainedPair",
    "deduplicate_and_materialize_relationships",
    "detect_spatial_conflicts",
    "generate_relationship_id",
    "generate_spatial_node_id",
    "project_space_requests_to_spatial_nodes",
    "validate_evidence_references",
    "validate_spatial_relationship_inputs",
]
