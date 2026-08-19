"""Strict immutable contracts for BRIF.AI Site / Buildable Envelope V0."""

from __future__ import annotations

import hashlib
import math
import sys
from datetime import datetime, timedelta
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from brif_ai.core.models.common import ObjectId
from brif_ai.spatial.models import RelationshipProvenance
from brif_ai.spatial.site.geometry import (
    validate_envelope_inside_parcel,
    validate_polygon_geometry,
)

if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:  # pragma: no cover

    class StrEnum(str, Enum):  # noqa: UP042
        pass


class SiteGeometryRole(StrEnum):
    """Semantic role of a site polygon."""

    PARCEL_BOUNDARY = "PARCEL_BOUNDARY"
    BUILDABLE_ENVELOPE = "BUILDABLE_ENVELOPE"


def generate_site_geometry_id(
    project_id: str,
    role: SiteGeometryRole | str,
) -> str:
    """Generate deterministic geometry ID based on project and role (independent of coordinates)."""
    raw_role = role.value if isinstance(role, SiteGeometryRole) else str(role)
    seed = f"{project_id}:{raw_role}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"sgeom_{digest}"


class _SiteContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SitePoint(_SiteContract):
    """2D Cartesian point in project-local metres."""

    x_m: float
    y_m: float

    @field_validator("x_m", "y_m")
    @classmethod
    def require_finite_coordinates(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError(f"Coordinate value must be finite, got {v!r}")
        return v


class SitePolygonInput(_SiteContract):
    """Caller input contract for defining site geometry before builder assignment."""

    vertices: list[SitePoint] = Field(min_length=3)
    # Explicit authority model; NO DEFAULT
    provenance: RelationshipProvenance
    evidence_ids: list[ObjectId] = Field(default_factory=list)
    rationale: str | None = None

    @model_validator(mode="after")
    def validate_input_polygon(self) -> SitePolygonInput:
        validate_polygon_geometry(self.vertices)
        if self.provenance == RelationshipProvenance.USER_CONFIRMED and not self.evidence_ids:
            raise ValueError("USER_CONFIRMED site geometry requires at least one evidence ID.")
        return self


class SitePolygon(_SiteContract):
    """Materialized immutable site polygon with assigned semantic role and deterministic ID."""

    id: ObjectId
    role: SiteGeometryRole
    vertices: list[SitePoint] = Field(min_length=3)
    provenance: RelationshipProvenance
    evidence_ids: list[ObjectId] = Field(default_factory=list)
    rationale: str | None = None

    @model_validator(mode="after")
    def validate_materialized_polygon(self) -> SitePolygon:
        validate_polygon_geometry(self.vertices)
        if self.provenance == RelationshipProvenance.USER_CONFIRMED and not self.evidence_ids:
            raise ValueError(
                f"USER_CONFIRMED site polygon {self.id!r} requires at least one evidence ID."
            )
        return self


class SiteBuildableEnvelope(_SiteContract):
    """Authoritative project-level site geometry contract defining allowable placement bounds."""

    schema_version: Literal["site_buildable_envelope.v0"] = "site_buildable_envelope.v0"
    project_id: ObjectId
    source_brief_version: int = Field(ge=1)
    source_program_schema_version: Literal["spatial_program.v0"] = "spatial_program.v0"
    created_at: datetime
    coordinate_system: Literal["LOCAL_CARTESIAN_METRES"] = "LOCAL_CARTESIAN_METRES"
    parcel_boundary: SitePolygon | None = None
    buildable_envelope: SitePolygon | None = None
    authoritative_geometry_ids: list[ObjectId] = Field(default_factory=list)

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
    def validate_envelope_integrity(self) -> SiteBuildableEnvelope:
        if self.buildable_envelope is not None and self.parcel_boundary is None:
            raise ValueError("Buildable envelope cannot be defined without a parcel boundary.")

        if (
            self.parcel_boundary is not None
            and self.parcel_boundary.role != SiteGeometryRole.PARCEL_BOUNDARY
        ):
            raise ValueError(
                f"parcel_boundary must have role PARCEL_BOUNDARY, "
                f"got {self.parcel_boundary.role.value!r}"
            )

        if (
            self.buildable_envelope is not None
            and self.buildable_envelope.role != SiteGeometryRole.BUILDABLE_ENVELOPE
        ):
            raise ValueError(
                f"buildable_envelope must have role BUILDABLE_ENVELOPE, "
                f"got {self.buildable_envelope.role.value!r}"
            )

        if self.parcel_boundary is not None and self.buildable_envelope is not None:
            validate_envelope_inside_parcel(
                envelope_vertices=self.buildable_envelope.vertices,
                parcel_vertices=self.parcel_boundary.vertices,
            )

        # Validate authoritative_geometry_ids matches exactly USER_CONFIRMED polygons
        confirmed_ids: list[str] = []
        if (
            self.parcel_boundary is not None
            and self.parcel_boundary.provenance == RelationshipProvenance.USER_CONFIRMED
        ):
            confirmed_ids.append(self.parcel_boundary.id)
        if (
            self.buildable_envelope is not None
            and self.buildable_envelope.provenance == RelationshipProvenance.USER_CONFIRMED
        ):
            confirmed_ids.append(self.buildable_envelope.id)

        expected_authoritative = sorted(confirmed_ids)
        if self.authoritative_geometry_ids != expected_authoritative:
            raise ValueError(
                f"authoritative_geometry_ids mismatch: expected {expected_authoritative}, "
                f"got {self.authoritative_geometry_ids}"
            )

        return self
