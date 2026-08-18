"""Domain exceptions for BRIF.AI spatial relationships and graph validation."""

from __future__ import annotations


class SpatialGraphError(Exception):
    """Base exception for all spatial relationship domain errors."""


class NonexistentSpaceError(SpatialGraphError):
    """Raised when a spatial relationship references a space ID not found in the graph."""


class SelfRelationshipError(SpatialGraphError):
    """Raised when a spatial relationship specifies identical source and target spaces."""


class DuplicateRelationshipError(SpatialGraphError):
    """Raised when an illegal duplicate relationship is detected."""


class InvalidProvenanceError(SpatialGraphError):
    """Raised when relationship provenance or evidence metadata violates invariants."""


class InvalidEvidenceReferenceError(SpatialGraphError):
    """Raised when a spatial relationship references an evidence ID not present in BriefSnapshot."""
