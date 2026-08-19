"""Strict immutable contracts for BRIF.AI Room Geometry Solver V0."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from brif_ai.core.models.common import ObjectId

_FLOAT_TOLERANCE: float = 1e-6


class _RoomSolverContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RoomGeometrySolverConfig(_RoomSolverContract):
    """Configuration options for CP-SAT room layout solving."""

    grid_step_m: float = Field(gt=0)
    max_time_seconds: float = Field(default=10.0, gt=0)

    @field_validator("grid_step_m", "max_time_seconds")
    @classmethod
    def require_positive_finite(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"Value must be finite and strictly positive, got {value!r}")
        return value


class RoomRectangle(_RoomSolverContract):
    """Real 2D axis-aligned geometric room rectangle placed inside FloorPlate."""

    space_id: ObjectId
    x_m: float
    y_m: float
    width_m: float = Field(gt=0)
    depth_m: float = Field(gt=0)
    area_m2: float = Field(gt=0)

    @field_validator("x_m", "y_m", "width_m", "depth_m", "area_m2")
    @classmethod
    def require_finite_coordinates(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError(f"Coordinate must be a finite number, got {value!r}")
        return value

    @model_validator(mode="after")
    def validate_rectangle_invariants(self) -> RoomRectangle:
        if self.width_m <= 0 or self.depth_m <= 0 or self.area_m2 <= 0:
            raise ValueError("width_m, depth_m, and area_m2 must be strictly positive.")

        expected_area = round(self.width_m * self.depth_m, 9)
        if abs(self.area_m2 - expected_area) > _FLOAT_TOLERANCE:
            raise ValueError(
                f"area_m2 {self.area_m2!r} does not match width_m * depth_m {expected_area!r}"
            )
        return self


class RoomGeometrySolution(_RoomSolverContract):
    """Authoritative geometric layout solution materializing 2D room rectangles."""

    schema_version: Literal["room_geometry_solution.v0"] = "room_geometry_solution.v0"
    project_id: ObjectId
    source_brief_version: int = Field(ge=1)
    source_solver_input_schema_version: Literal["layout_solver_input_set.v0"] = (
        "layout_solver_input_set.v0"
    )
    source_floor_plate_schema_version: Literal["floor_plate.v0"] = "floor_plate.v0"
    source_floor_plate_id: ObjectId
    created_at: datetime
    coordinate_system: Literal["LOCAL_CARTESIAN_METRES"] = "LOCAL_CARTESIAN_METRES"
    grid_step_m: float = Field(gt=0)
    status: Literal["FEASIBLE"] = "FEASIBLE"
    rooms: list[RoomRectangle] = Field(min_length=1)

    @field_validator("grid_step_m")
    @classmethod
    def require_finite_grid_step(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"grid_step_m must be finite and positive, got {value!r}")
        return value

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
    def validate_solution_invariants(self) -> RoomGeometrySolution:
        # 1. Unique space IDs
        space_ids: list[str] = [room.space_id for room in self.rooms]
        if len(space_ids) != len(set(space_ids)):
            raise ValueError("Duplicate space_id found among solved rooms.")

        # 2. Deterministic sorted room ordering
        expected_order = sorted(self.rooms, key=lambda r: r.space_id)
        if self.rooms != expected_order:
            raise ValueError("Rooms must be sorted deterministically in ascending space_id order.")

        # 3. Universal non-overlapping room rectangles
        n = len(self.rooms)
        for i in range(n):
            r1 = self.rooms[i]
            for j in range(i + 1, n):
                r2 = self.rooms[j]
                # Non-overlap check: rectangles are disjoint if separated along X or Y
                disjoint_x = (r1.x_m + r1.width_m <= r2.x_m + _FLOAT_TOLERANCE) or (
                    r2.x_m + r2.width_m <= r1.x_m + _FLOAT_TOLERANCE
                )
                disjoint_y = (r1.y_m + r1.depth_m <= r2.y_m + _FLOAT_TOLERANCE) or (
                    r2.y_m + r2.depth_m <= r1.y_m + _FLOAT_TOLERANCE
                )
                if not (disjoint_x or disjoint_y):
                    raise ValueError(
                        f"Room rectangles for space {r1.space_id!r} and {r2.space_id!r} "
                        f"overlap geometrically."
                    )

        return self
