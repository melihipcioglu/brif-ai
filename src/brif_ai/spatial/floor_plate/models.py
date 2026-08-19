"""Strict immutable contracts for BRIF.AI Authoritative FloorPlate V0.

Scope & Architectural Notes (V0):
- FloorPlate V0 is the schematic room-layout containment boundary for the current
  SITE-BASED NEW-BUILD SCHEMATIC WORKFLOW.
- This is the first contract in the pipeline that downstream room solvers are allowed
  to interpret as: "all generated room geometry must lie inside or on this polygon."
- Because wall thickness and structural slab geometry are not modeled yet, it must NOT
  be claimed to represent a construction-ready structural slab or finished exterior
  wall boundary. That interpretation belongs to later architectural-detail geometry.
- Single-floor, single-polygon (no holes, no multipolygons).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from brif_ai.core.models.common import ObjectId
from brif_ai.spatial.models import RelationshipProvenance
from brif_ai.spatial.site.geometry import validate_polygon_geometry
from brif_ai.spatial.site.models import SitePoint


def generate_floor_plate_id(project_id: str) -> str:
    """Generate deterministic FloorPlate ID based on project context (independent of coords)."""
    seed = f"{project_id}:PRIMARY_FLOOR_PLATE"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"fplate_{digest}"


class _FloorPlateContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FloorPlateInput(_FloorPlateContract):
    """Caller-facing input contract representing a floor-plate polygon submission."""

    vertices: list[SitePoint] = Field(min_length=3)
    provenance: RelationshipProvenance
    evidence_ids: list[ObjectId] = Field(default_factory=list)
    rationale: str | None = None

    @model_validator(mode="after")
    def validate_floor_plate_input_invariants(self) -> FloorPlateInput:
        if self.provenance == RelationshipProvenance.USER_CONFIRMED and not self.evidence_ids:
            raise ValueError("USER_CONFIRMED floor plate input requires at least one evidence ID.")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Duplicate evidence IDs are not permitted in FloorPlateInput.")
        return self


class FloorPlate(_FloorPlateContract):
    """Authoritative building-level polygon container for schematic room placement.

    Downstream layout engines use this contract as the hard bounding boundary within which
    all 2D room layouts must reside.
    """

    schema_version: Literal["floor_plate.v0"] = "floor_plate.v0"
    id: ObjectId
    project_id: ObjectId
    source_brief_version: int = Field(ge=1)
    source_solver_input_schema_version: Literal["layout_solver_input_set.v0"] = (
        "layout_solver_input_set.v0"
    )
    created_at: datetime
    coordinate_system: Literal["LOCAL_CARTESIAN_METRES"] = "LOCAL_CARTESIAN_METRES"
    vertices: list[SitePoint] = Field(min_length=3)
    provenance: Literal[RelationshipProvenance.USER_CONFIRMED]
    evidence_ids: list[ObjectId] = Field(min_length=1)
    rationale: str | None = None

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
    def validate_floor_plate_invariants(self) -> FloorPlate:
        # 1. Deterministic identity enforcement
        expected_id = generate_floor_plate_id(self.project_id)
        if self.id != expected_id:
            raise ValueError(
                f"FloorPlate id {self.id!r} does not match expected deterministic "
                f"id {expected_id!r}"
            )

        # 2. Duplicate evidence IDs check
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Duplicate evidence IDs are not permitted in FloorPlate.")

        # 3. Polygon geometric validity
        validate_polygon_geometry(self.vertices)

        return self
