"""Semantic geometric validation adapter for Authoritative FloorPlate V0."""

from __future__ import annotations

from collections.abc import Sequence

from brif_ai.spatial.floor_plate.errors import FloorPlateOutsideBuildableEnvelopeError
from brif_ai.spatial.site.errors import SiteEnvelopeOutsideParcelError
from brif_ai.spatial.site.geometry import validate_envelope_inside_parcel
from brif_ai.spatial.site.models import SitePoint


def validate_floor_plate_inside_buildable_envelope(
    floor_plate_vertices: Sequence[SitePoint],
    envelope_vertices: Sequence[SitePoint],
) -> None:
    """Validate that the floor plate polygon lies fully inside or on the site buildable envelope.

    Delegates to the interval-partitioned 2D concave containment validator from
    `brif_ai.spatial.site.geometry` and translates site-level errors to FloorPlate domain errors.
    """
    try:
        validate_envelope_inside_parcel(
            envelope_vertices=floor_plate_vertices,
            parcel_vertices=envelope_vertices,
        )
    except SiteEnvelopeOutsideParcelError as exc:
        raise FloorPlateOutsideBuildableEnvelopeError(
            f"FloorPlate polygon passes or lies outside the site buildable envelope: {exc}"
        ) from exc
