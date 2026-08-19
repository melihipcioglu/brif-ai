"""Authoritative Room Geometry Solver V0 package for BRIF.AI."""

from __future__ import annotations

from brif_ai.spatial.room_solver.errors import (
    RoomGeometryEngineError,
    RoomGeometryGridAlignmentError,
    RoomGeometryInfeasibleError,
    RoomGeometryInputMismatchError,
    RoomGeometrySolverError,
    RoomGeometryUnderconstrainedSpaceError,
    RoomGeometryUnsupportedDirectiveError,
    RoomGeometryUnsupportedFloorPlateError,
    RoomGeometryUnsupportedMetricError,
    RoomGeometryUnsupportedOptionalSpaceError,
)
from brif_ai.spatial.room_solver.models import (
    RoomGeometrySolution,
    RoomGeometrySolverConfig,
    RoomRectangle,
)
from brif_ai.spatial.room_solver.solver import RoomGeometrySolver

__all__ = [
    "RoomGeometryEngineError",
    "RoomGeometryGridAlignmentError",
    "RoomGeometryInfeasibleError",
    "RoomGeometryInputMismatchError",
    "RoomGeometrySolution",
    "RoomGeometrySolver",
    "RoomGeometrySolverConfig",
    "RoomGeometrySolverError",
    "RoomGeometryUnderconstrainedSpaceError",
    "RoomGeometryUnsupportedDirectiveError",
    "RoomGeometryUnsupportedFloorPlateError",
    "RoomGeometryUnsupportedMetricError",
    "RoomGeometryUnsupportedOptionalSpaceError",
    "RoomRectangle",
]
