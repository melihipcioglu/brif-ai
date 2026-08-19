"""Domain exceptions for BRIF.AI Site / Buildable Envelope V0."""

from __future__ import annotations

from brif_ai.spatial.errors import SpatialGraphError


class SiteGeometryError(SpatialGraphError):
    """Base exception for all site geometry and buildable envelope errors."""


class SiteMissingInputError(SiteGeometryError):
    """Raised when required SpatialProgram or input collection is missing."""


class SiteSchemaVersionMismatchError(SiteGeometryError):
    """Raised when SpatialProgram schema_version is incompatible with site builder."""

    def __init__(self, expected_schema: str, actual_schema: str) -> None:
        super().__init__(
            f"Incompatible program schema version: expected {expected_schema!r}, "
            f"got {actual_schema!r}."
        )
        self.expected_schema = expected_schema
        self.actual_schema = actual_schema


class SiteEnvelopeWithoutParcelError(SiteGeometryError):
    """Raised when a buildable envelope is supplied without an enclosing parcel boundary."""


class SiteEnvelopeOutsideParcelError(SiteGeometryError):
    """Raised when a buildable envelope polygon extends outside the parcel boundary."""


class SitePolygonDegenerateError(SiteGeometryError):
    """Raised when a polygon has fewer than 3 unique vertices or zero area."""


class SitePolygonSelfIntersectionError(SiteGeometryError):
    """Raised when a polygon self-intersects, self-touches, or has collinear edge overlap."""


class SiteInvalidCoordinateError(SiteGeometryError):
    """Raised when polygon coordinates are non-finite (NaN or infinite)."""


class SiteInvalidEvidenceError(SiteGeometryError):
    """Raised when a USER_CONFIRMED geometry lacks traceable evidence IDs."""
