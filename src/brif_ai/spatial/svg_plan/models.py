"""Strict immutable contracts for BRIF.AI SVG Plan View V0."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from brif_ai.core.models.common import ObjectId

_SVG_NAMESPACE: str = "http://www.w3.org/2000/svg"


class _SvgPlanContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SvgPlanRenderConfig(_SvgPlanContract):
    """Presentational configuration for rendering SVG plan drawings.

    These values are strictly presentation-only; altering them never affects
    underlying architectural geometry or coordinates.
    """

    scale_px_per_m: float = Field(default=80.0, gt=0)
    margin_px: float = Field(default=40.0, ge=0)
    room_label_font_px: float = Field(default=14.0, gt=0)
    area_label_font_px: float = Field(default=11.0, gt=0)
    show_area_labels: bool = True
    show_space_ids: bool = False

    @field_validator("scale_px_per_m", "room_label_font_px", "area_label_font_px")
    @classmethod
    def require_positive_finite(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"Value must be finite and strictly positive, got {value!r}")
        return value

    @field_validator("margin_px")
    @classmethod
    def require_non_negative_finite(cls, value: float) -> float:
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"margin_px must be finite and >= 0, got {value!r}")
        return value


class SvgPlanDocument(_SvgPlanContract):
    """Immutable SVG plan document representing a solved room layout."""

    schema_version: Literal["svg_plan_document.v0"] = "svg_plan_document.v0"
    project_id: ObjectId
    source_brief_version: int = Field(ge=1)
    source_solver_input_schema_version: Literal["layout_solver_input_set.v0"] = (
        "layout_solver_input_set.v0"
    )
    source_floor_plate_schema_version: Literal["floor_plate.v0"] = "floor_plate.v0"
    source_floor_plate_id: ObjectId
    source_room_solution_schema_version: Literal["room_geometry_solution.v0"] = (
        "room_geometry_solution.v0"
    )
    coordinate_system: Literal["LOCAL_CARTESIAN_METRES"] = "LOCAL_CARTESIAN_METRES"
    width_px: float = Field(gt=0)
    height_px: float = Field(gt=0)
    svg: str = Field(min_length=1)

    @field_validator("width_px", "height_px")
    @classmethod
    def require_positive_finite_dims(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"Dimension must be finite and strictly positive, got {value!r}")
        return value

    @model_validator(mode="after")
    def validate_svg_markup(self) -> SvgPlanDocument:
        if not self.svg or not self.svg.strip():
            raise ValueError("svg markup must not be empty.")

        try:
            root = ET.fromstring(self.svg)
        except ET.ParseError as e:
            raise ValueError(f"Malformed SVG XML: {e}") from e

        # Validate root tag and namespace
        expected_namespaced_tag = f"{{{_SVG_NAMESPACE}}}svg"
        if root.tag != expected_namespaced_tag and root.tag != "svg":
            raise ValueError(f"Expected root <svg> element, got <{root.tag}>.")

        return self
