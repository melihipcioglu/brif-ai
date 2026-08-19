"""Deterministic CP-SAT Room Geometry Solver V0 for BRIF.AI."""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import TYPE_CHECKING

from ortools.sat.python import cp_model

from brif_ai.brief.models.common import Priority
from brif_ai.spatial.floor_plate.geometry import (
    validate_floor_plate_inside_buildable_envelope,
)
from brif_ai.spatial.metrics.models import MetricRequirementType
from brif_ai.spatial.room_solver.errors import (
    RoomGeometryEngineError,
    RoomGeometryGridAlignmentError,
    RoomGeometryInfeasibleError,
    RoomGeometryInputMismatchError,
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
from brif_ai.spatial.solver_policy.models import (
    ConstraintEnforcement,
    SolverRelationOperator,
)

if TYPE_CHECKING:
    from brif_ai.spatial.floor_plate.models import FloorPlate
    from brif_ai.spatial.solver_input.models import LayoutSolverInputSet

_FLOAT_TOLERANCE: float = 1e-6


class RoomGeometrySolver:
    """Deterministic geometric solver placing rectangular rooms inside FloorPlate V0.

    ARCHITECTURAL & MATHEMATICAL INVARIANTS:
    1. Axis-Aligned Rectangular FloorPlate: V0 supports strictly axis-aligned rectangular
       FloorPlate geometries. Arbitrary vertex ordering (CW/CCW) and origins are supported.
    2. Mandatory Spaces Only: Optional spaces (mandatory=False) are rejected in V0.
    3. Conservative Metric Quantization:
       - MIN_AREA: ceil(value_m2 / grid_step_m^2)
       - MAX_AREA: floor(value_m2 / grid_step_m^2)
       - MIN_CLEAR_WIDTH: ceil(value_m / grid_step_m) applied to both width and depth.
       - Discretization never weakens confirmed requirements.
       - Missing MIN_AREA triggers RoomGeometryUnderconstrainedSpaceError.
    4. Required Adjacency: Two rooms must share a boundary segment of positive length
       (at least 1 grid unit). Corner-only touching does not satisfy adjacency.
    5. Universal Room Non-Overlap: AddNoOverlap2D is enforced across all rooms.
    6. Pure Feasibility: Zero architectural optimization objectives or penalty heuristics.
    7. Determinism: Single worker (num_search_workers=1) and fixed random_seed=0.
    """

    @classmethod
    def solve(
        cls,
        solver_input: LayoutSolverInputSet,
        floor_plate: FloorPlate,
        config: RoomGeometrySolverConfig,
    ) -> RoomGeometrySolution:
        """Solve and materialize a valid RoomGeometrySolution."""
        if solver_input is None or floor_plate is None or config is None:
            raise RoomGeometryInputMismatchError(
                "solver_input, floor_plate, and config are required."
            )

        # 1. Cross-contract schema and metadata consistency
        if solver_input.schema_version != "layout_solver_input_set.v0":
            raise RoomGeometryInputMismatchError(
                f"Unsupported solver_input schema_version: {solver_input.schema_version!r}"
            )
        if floor_plate.schema_version != "floor_plate.v0":
            raise RoomGeometryInputMismatchError(
                f"Unsupported floor_plate schema_version: {floor_plate.schema_version!r}"
            )
        if floor_plate.source_solver_input_schema_version != "layout_solver_input_set.v0":
            raise RoomGeometryInputMismatchError(
                f"Unsupported floor_plate source_solver_input_schema_version: "
                f"{floor_plate.source_solver_input_schema_version!r}"
            )
        if solver_input.project_id != floor_plate.project_id:
            raise RoomGeometryInputMismatchError(
                f"project_id mismatch: solver_input has {solver_input.project_id!r}, "
                f"floor_plate has {floor_plate.project_id!r}"
            )
        if solver_input.source_brief_version != floor_plate.source_brief_version:
            raise RoomGeometryInputMismatchError(
                f"source_brief_version mismatch: solver_input has "
                f"{solver_input.source_brief_version}, "
                f"floor_plate has {floor_plate.source_brief_version}"
            )
        if solver_input.coordinate_system != floor_plate.coordinate_system:
            raise RoomGeometryInputMismatchError(
                f"coordinate_system mismatch: solver_input has {solver_input.coordinate_system!r}, "
                f"floor_plate has {floor_plate.coordinate_system!r}"
            )

        # 2. Re-validate FloorPlate containment in site buildable envelope
        validate_floor_plate_inside_buildable_envelope(
            floor_plate_vertices=floor_plate.vertices,
            envelope_vertices=solver_input.buildable_envelope.vertices,
        )

        # 3. FloorPlate rectangularity capability gate
        if len(floor_plate.vertices) != 4:
            raise RoomGeometryUnsupportedFloorPlateError(
                f"RoomGeometrySolver V0 requires exactly 4 vertices for FloorPlate, "
                f"got {len(floor_plate.vertices)}."
            )

        xs = {round(v.x_m, 9) for v in floor_plate.vertices}
        ys = {round(v.y_m, 9) for v in floor_plate.vertices}
        if len(xs) != 2 or len(ys) != 2:
            raise RoomGeometryUnsupportedFloorPlateError(
                "RoomGeometrySolver V0 supports only axis-aligned rectangular FloorPlates. "
                f"Encountered non-rectangular coordinate distribution: xs={xs}, ys={ys}."
            )

        x_min = min(v.x_m for v in floor_plate.vertices)
        x_max = max(v.x_m for v in floor_plate.vertices)
        y_min = min(v.y_m for v in floor_plate.vertices)
        y_max = max(v.y_m for v in floor_plate.vertices)

        # Check all 4 corners are present
        expected_corners = {
            (round(x_min, 9), round(y_min, 9)),
            (round(x_max, 9), round(y_min, 9)),
            (round(x_max, 9), round(y_max, 9)),
            (round(x_min, 9), round(y_max, 9)),
        }
        actual_corners = {(round(v.x_m, 9), round(v.y_m, 9)) for v in floor_plate.vertices}
        if expected_corners != actual_corners:
            raise RoomGeometryUnsupportedFloorPlateError(
                "FloorPlate vertices do not form an axis-aligned rectangular bounding box."
            )

        fp_width = x_max - x_min
        fp_depth = y_max - y_min
        if fp_width <= _FLOAT_TOLERANCE or fp_depth <= _FLOAT_TOLERANCE:
            raise RoomGeometryUnsupportedFloorPlateError("FloorPlate dimensions must be positive.")

        # 4. Strict Decimal-based grid alignment check
        dec_w = Decimal(str(round(fp_width, 9)))
        dec_d = Decimal(str(round(fp_depth, 9)))
        dec_step = Decimal(str(round(config.grid_step_m, 9)))

        w_cells_dec = dec_w / dec_step
        d_cells_dec = dec_d / dec_step

        if (
            w_cells_dec != w_cells_dec.to_integral_value()
            or d_cells_dec != d_cells_dec.to_integral_value()
        ):
            raise RoomGeometryGridAlignmentError(
                f"FloorPlate dimensions ({dec_w}m x {dec_d}m) are not exact integer multiples "
                f"of grid_step_m ({dec_step}m)."
            )

        floor_w_units = int(w_cells_dec)
        floor_d_units = int(d_cells_dec)

        # 5. Space validation (mandatory spaces only)
        for space in solver_input.spaces:
            if not space.mandatory:
                raise RoomGeometryUnsupportedOptionalSpaceError(
                    f"Space {space.id!r} is optional (mandatory=False), which is unsupported in V0."
                )

        # 6. Metric requirements validation & quantization
        metrics_by_space = {
            smr.space_id: smr.requirements for smr in solver_input.space_metric_requirements
        }
        quantized_min_area: dict[str, int] = {}
        quantized_max_area: dict[str, int | None] = {}
        quantized_min_width: dict[str, int] = {}

        dec_step_sq = dec_step * dec_step

        for space in solver_input.spaces:
            reqs = metrics_by_space.get(space.id, [])
            min_area_val: float | None = None
            max_area_val: float | None = None
            min_width_val: float | None = None

            for req in reqs:
                if req.priority != Priority.MUST:
                    raise RoomGeometryUnsupportedMetricError(
                        f"Requirement {req.id!r} on space {space.id!r} has priority "
                        f"{req.priority.value!r}; only MUST is supported in V0."
                    )
                if req.requirement_type == MetricRequirementType.TARGET_AREA:
                    raise RoomGeometryUnsupportedMetricError(
                        f"TARGET_AREA metric requirement {req.id!r} on space {space.id!r} "
                        f"is unsupported in V0."
                    )
                if req.requirement_type == MetricRequirementType.MIN_AREA:
                    min_area_val = req.value
                elif req.requirement_type == MetricRequirementType.MAX_AREA:
                    max_area_val = req.value
                elif req.requirement_type == MetricRequirementType.MIN_CLEAR_WIDTH:
                    min_width_val = req.value
                else:
                    raise RoomGeometryUnsupportedMetricError(
                        f"Unsupported metric requirement type {req.requirement_type.value!r} "
                        f"on space {space.id!r}."
                    )

            if min_area_val is None:
                raise RoomGeometryUnderconstrainedSpaceError(
                    f"Space {space.id!r} lacks a mandatory hard MIN_AREA requirement."
                )

            # Quantize MIN_AREA: ceil(value / step^2)
            dec_min_a = Decimal(str(min_area_val))
            cells_min_a = int((dec_min_a / dec_step_sq).to_integral_value(rounding=ROUND_CEILING))
            quantized_min_area[space.id] = max(1, cells_min_a)

            # Quantize MAX_AREA: floor(value / step^2)
            if max_area_val is not None:
                dec_max_a = Decimal(str(max_area_val))
                cells_max_a = int((dec_max_a / dec_step_sq).to_integral_value(rounding=ROUND_FLOOR))
                quantized_max_area[space.id] = cells_max_a
            else:
                quantized_max_area[space.id] = None

            # Quantize MIN_CLEAR_WIDTH: ceil(value / step)
            if min_width_val is not None:
                dec_min_w = Decimal(str(min_width_val))
                cells_min_w = int((dec_min_w / dec_step).to_integral_value(rounding=ROUND_CEILING))
                quantized_min_width[space.id] = max(1, cells_min_w)
            else:
                quantized_min_width[space.id] = 1

        # 7. Directive validation (REQUIRED ADJACENCY only)
        for directive in solver_input.directives:
            if directive.enforcement != ConstraintEnforcement.REQUIRED:
                raise RoomGeometryUnsupportedDirectiveError(
                    f"Directive {directive.id!r} has enforcement {directive.enforcement.value!r}; "
                    f"only REQUIRED is supported in V0."
                )
            if directive.operator != SolverRelationOperator.ADJACENCY:
                raise RoomGeometryUnsupportedDirectiveError(
                    f"Directive {directive.id!r} has operator {directive.operator.value!r}; "
                    f"only ADJACENCY is supported in V0."
                )

        # 8. Build CP-SAT Model
        model = cp_model.CpModel()

        # Sort spaces deterministically
        sorted_spaces = sorted(solver_input.spaces, key=lambda s: s.id)

        # Create room integer and interval variables
        x_vars: dict[str, cp_model.IntVar] = {}
        y_vars: dict[str, cp_model.IntVar] = {}
        w_vars: dict[str, cp_model.IntVar] = {}
        d_vars: dict[str, cp_model.IntVar] = {}
        x_end_vars: dict[str, cp_model.IntVar] = {}
        y_end_vars: dict[str, cp_model.IntVar] = {}
        area_vars: dict[str, cp_model.IntVar] = {}
        x_intervals: list[cp_model.IntervalVar] = []
        y_intervals: list[cp_model.IntervalVar] = []

        total_floor_cells = floor_w_units * floor_d_units

        for space in sorted_spaces:
            sid = space.id
            min_w = quantized_min_width[sid]
            min_a = quantized_min_area[sid]
            max_a = quantized_max_area[sid]

            x = model.new_int_var(0, floor_w_units - 1, f"x_{sid}")
            y = model.new_int_var(0, floor_d_units - 1, f"y_{sid}")
            width = model.new_int_var(min_w, floor_w_units, f"w_{sid}")
            depth = model.new_int_var(min_w, floor_d_units, f"d_{sid}")
            x_end = model.new_int_var(1, floor_w_units, f"x_end_{sid}")
            y_end = model.new_int_var(1, floor_d_units, f"y_end_{sid}")

            model.add(x_end == x + width)
            model.add(y_end == y + depth)

            area = model.new_int_var(1, total_floor_cells, f"area_{sid}")
            model.add_multiplication_equality(area, [width, depth])
            model.add(area >= min_a)
            if max_a is not None:
                model.add(area <= max_a)

            x_int = model.new_interval_var(x, width, x_end, f"x_int_{sid}")
            y_int = model.new_interval_var(y, depth, y_end, f"y_int_{sid}")

            x_vars[sid] = x
            y_vars[sid] = y
            w_vars[sid] = width
            d_vars[sid] = depth
            x_end_vars[sid] = x_end
            y_end_vars[sid] = y_end
            area_vars[sid] = area
            x_intervals.append(x_int)
            y_intervals.append(y_int)

        # Enforce universal room non-overlap
        model.add_no_overlap_2d(x_intervals, y_intervals)

        # Enforce REQUIRED ADJACENCY directives
        sorted_directives = sorted(solver_input.directives, key=lambda d: d.id)
        for d in sorted_directives:
            a_id = d.source_space_id
            b_id = d.target_space_id

            ax, ay, ax_end, ay_end = x_vars[a_id], y_vars[a_id], x_end_vars[a_id], y_end_vars[a_id]
            bx, by, bx_end, by_end = x_vars[b_id], y_vars[b_id], x_end_vars[b_id], y_end_vars[b_id]

            # 4 possible shared-side orientations with positive segment overlap (>= 1 grid cell)
            # Case 1: A is to the left of B (A.right == B.left) with Y-overlap
            b_v1 = model.new_bool_var(f"adj_v1_{d.id}")
            model.add(ax_end == bx).only_enforce_if(b_v1)
            model.add(ay <= by_end - 1).only_enforce_if(b_v1)
            model.add(by <= ay_end - 1).only_enforce_if(b_v1)

            # Case 2: B is to the left of A (B.right == A.left) with Y-overlap
            b_v2 = model.new_bool_var(f"adj_v2_{d.id}")
            model.add(bx_end == ax).only_enforce_if(b_v2)
            model.add(ay <= by_end - 1).only_enforce_if(b_v2)
            model.add(by <= ay_end - 1).only_enforce_if(b_v2)

            # Case 3: A is below B (A.top == B.bottom) with X-overlap
            b_h1 = model.new_bool_var(f"adj_h1_{d.id}")
            model.add(ay_end == by).only_enforce_if(b_h1)
            model.add(ax <= bx_end - 1).only_enforce_if(b_h1)
            model.add(bx <= ax_end - 1).only_enforce_if(b_h1)

            # Case 4: B is below A (B.top == A.bottom) with X-overlap
            b_h2 = model.new_bool_var(f"adj_h2_{d.id}")
            model.add(by_end == ay).only_enforce_if(b_h2)
            model.add(ax <= bx_end - 1).only_enforce_if(b_h2)
            model.add(bx <= ax_end - 1).only_enforce_if(b_h2)

            model.add_bool_or([b_v1, b_v2, b_h1, b_h2])

        # 9. Solve CP-SAT Model
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = 0
        solver.parameters.max_time_in_seconds = config.max_time_seconds

        status = solver.solve(model)

        if status == cp_model.INFEASIBLE:
            raise RoomGeometryInfeasibleError(
                "Spatial constraints and room metric requirements are mathematically "
                "INFEASIBLE inside the specified FloorPlate."
            )
        if status == cp_model.MODEL_INVALID:
            raise RoomGeometryEngineError(f"CP-SAT model is invalid: {solver.response_stats()}")
        if status == cp_model.UNKNOWN:
            raise RoomGeometryEngineError(
                f"CP-SAT search ended with UNKNOWN status after {config.max_time_seconds}s "
                f"(neither feasible nor infeasible)."
            )
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RoomGeometryEngineError(f"Unexpected solver status: {status}")

        # 10. Reconstruct 2D Metric Coordinates & Invariant Validation
        step = config.grid_step_m
        rooms: list[RoomRectangle] = []

        for space in sorted_spaces:
            sid = space.id
            x_u = solver.value(x_vars[sid])
            y_u = solver.value(y_vars[sid])
            w_u = solver.value(w_vars[sid])
            d_u = solver.value(d_vars[sid])

            x_m = round(x_min + x_u * step, 9)
            y_m = round(y_min + y_u * step, 9)
            width_m = round(w_u * step, 9)
            depth_m = round(d_u * step, 9)
            area_m2 = round(width_m * depth_m, 9)

            # Bounding box containment check
            if (
                x_m < x_min - _FLOAT_TOLERANCE
                or y_m < y_min - _FLOAT_TOLERANCE
                or (x_m + width_m) > x_max + _FLOAT_TOLERANCE
                or (y_m + depth_m) > y_max + _FLOAT_TOLERANCE
            ):
                raise RoomGeometryEngineError(
                    f"Solved room {sid!r} ({x_m}, {y_m}, {width_m}, {depth_m}) passes outside "
                    f"FloorPlate bounds [{x_min}, {x_max}] x [{y_min}, {y_max}]."
                )

            rooms.append(
                RoomRectangle(
                    space_id=sid,
                    x_m=x_m,
                    y_m=y_m,
                    width_m=width_m,
                    depth_m=depth_m,
                    area_m2=area_m2,
                )
            )

        # Sort rooms by space_id
        rooms.sort(key=lambda r: r.space_id)

        # Cross-validation: room space IDs match solver_input spaces exactly
        if {r.space_id for r in rooms} != {s.id for s in solver_input.spaces}:
            raise RoomGeometryEngineError("Solved rooms do not match solver input spaces set.")

        created_at = max(solver_input.created_at, floor_plate.created_at)

        return RoomGeometrySolution(
            schema_version="room_geometry_solution.v0",
            project_id=solver_input.project_id,
            source_brief_version=solver_input.source_brief_version,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            source_floor_plate_schema_version="floor_plate.v0",
            source_floor_plate_id=floor_plate.id,
            created_at=created_at,
            coordinate_system="LOCAL_CARTESIAN_METRES",
            grid_step_m=config.grid_step_m,
            status="FEASIBLE",
            rooms=rooms,
        )
