"""BRIF.AI Site / Buildable Envelope V0 Package."""

from __future__ import annotations

from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.errors import (
    SiteEnvelopeOutsideParcelError,
    SiteEnvelopeWithoutParcelError,
    SiteGeometryError,
    SiteInvalidCoordinateError,
    SiteInvalidEvidenceError,
    SiteMissingInputError,
    SitePolygonDegenerateError,
    SitePolygonSelfIntersectionError,
    SiteSchemaVersionMismatchError,
)
from brif_ai.spatial.site.geometry import (
    calculate_polygon_area,
    cross_product_2d,
    is_point_in_or_on_polygon,
    is_point_on_segment,
    orientation_2d,
    segments_intersect,
    segments_properly_intersect,
    validate_envelope_inside_parcel,
    validate_polygon_geometry,
)
from brif_ai.spatial.site.models import (
    SiteBuildableEnvelope,
    SiteGeometryRole,
    SitePoint,
    SitePolygon,
    SitePolygonInput,
    generate_site_geometry_id,
)

__all__ = [
    "SiteBuildableEnvelope",
    "SiteBuildableEnvelopeBuilder",
    "SiteEnvelopeOutsideParcelError",
    "SiteEnvelopeWithoutParcelError",
    "SiteGeometryError",
    "SiteGeometryRole",
    "SiteInvalidCoordinateError",
    "SiteInvalidEvidenceError",
    "SiteMissingInputError",
    "SitePoint",
    "SitePolygon",
    "SitePolygonDegenerateError",
    "SitePolygonInput",
    "SitePolygonSelfIntersectionError",
    "SiteSchemaVersionMismatchError",
    "calculate_polygon_area",
    "cross_product_2d",
    "generate_site_geometry_id",
    "is_point_in_or_on_polygon",
    "is_point_on_segment",
    "orientation_2d",
    "segments_intersect",
    "segments_properly_intersect",
    "validate_envelope_inside_parcel",
    "validate_polygon_geometry",
]
