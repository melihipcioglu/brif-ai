"""Deterministic SVG Plan View Renderer V0 for BRIF.AI."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils
from typing import TYPE_CHECKING

from brif_ai.spatial.site.errors import SiteEnvelopeOutsideParcelError
from brif_ai.spatial.site.geometry import validate_envelope_inside_parcel
from brif_ai.spatial.site.models import SitePoint
from brif_ai.spatial.svg_plan.errors import (
    SvgPlanInputMismatchError,
    SvgPlanInvalidGeometryError,
    SvgPlanRenderError,
    SvgPlanUnknownSpaceError,
)
from brif_ai.spatial.svg_plan.models import SvgPlanDocument, SvgPlanRenderConfig

if TYPE_CHECKING:
    from brif_ai.spatial.floor_plate.models import FloorPlate
    from brif_ai.spatial.room_solver.models import RoomGeometrySolution
    from brif_ai.spatial.solver_input.models import LayoutSolverInputSet


def _fmt(val: float, precision: int = 2) -> str:
    """Format floating point numbers deterministically without scientific notation."""
    if not math.isfinite(val):
        raise ValueError(f"Non-finite pixel value: {val!r}")
    if abs(val) < 1e-12:
        val = 0.0
    rounded = round(val, precision)
    if abs(rounded) < 1e-12:
        rounded = 0.0
    s = f"{rounded:.{precision}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


class SvgPlanRenderer:
    """Deterministic presentation renderer translating solved room geometry into 2D SVG plans.

    ARCHITECTURAL PRINCIPLES:
    1. Presentation Only: Never alters, moves, snaps, or optimizes room or floor geometry.
    2. Y-Axis Inversion: Translates Cartesian coordinates (+Y up) into SVG screen space (+Y down).
    3. Strict XML Safety: Escapes text elements and quotes XML attributes using Python stdlib.
    4. Determinism: Stable sorted order by space_id, deterministic numeric formatting,
       no timestamps or random IDs in the SVG markup.
    """

    @classmethod
    def render(
        cls,
        solver_input: LayoutSolverInputSet,
        floor_plate: FloorPlate,
        solution: RoomGeometrySolution,
        config: SvgPlanRenderConfig | None = None,
    ) -> SvgPlanDocument:
        """Render a deterministic SvgPlanDocument from confirmed solver inputs and solution."""
        cfg = config or SvgPlanRenderConfig()

        if solver_input is None or floor_plate is None or solution is None:
            raise SvgPlanInputMismatchError("solver_input, floor_plate, and solution are required.")

        # 1. Cross-contract schema and metadata consistency
        if solver_input.schema_version != "layout_solver_input_set.v0":
            raise SvgPlanInputMismatchError(
                f"Unsupported solver_input schema_version: {solver_input.schema_version!r}"
            )
        if floor_plate.schema_version != "floor_plate.v0":
            raise SvgPlanInputMismatchError(
                f"Unsupported floor_plate schema_version: {floor_plate.schema_version!r}"
            )
        if solution.schema_version != "room_geometry_solution.v0":
            raise SvgPlanInputMismatchError(
                f"Unsupported solution schema_version: {solution.schema_version!r}"
            )

        if not (solver_input.project_id == floor_plate.project_id == solution.project_id):
            raise SvgPlanInputMismatchError(
                f"project_id mismatch: solver_input={solver_input.project_id!r}, "
                f"floor_plate={floor_plate.project_id!r}, solution={solution.project_id!r}"
            )
        if not (
            solver_input.source_brief_version
            == floor_plate.source_brief_version
            == solution.source_brief_version
        ):
            raise SvgPlanInputMismatchError(
                f"source_brief_version mismatch: solver_input={solver_input.source_brief_version}, "
                f"floor_plate={floor_plate.source_brief_version}, "
                f"solution={solution.source_brief_version}"
            )
        if not (
            solver_input.coordinate_system
            == floor_plate.coordinate_system
            == solution.coordinate_system
        ):
            raise SvgPlanInputMismatchError(
                f"coordinate_system mismatch: solver_input={solver_input.coordinate_system!r}, "
                f"floor_plate={floor_plate.coordinate_system!r}, "
                f"solution={solution.coordinate_system!r}"
            )
        if solution.source_floor_plate_id != floor_plate.id:
            raise SvgPlanInputMismatchError(
                f"source_floor_plate_id mismatch: solution references "
                f"{solution.source_floor_plate_id!r}, floor_plate is {floor_plate.id!r}"
            )
        if solution.source_floor_plate_schema_version != floor_plate.schema_version:
            raise SvgPlanInputMismatchError(
                f"source_floor_plate_schema_version mismatch: solution has "
                f"{solution.source_floor_plate_schema_version!r}, "
                f"floor_plate has {floor_plate.schema_version!r}"
            )
        if solution.source_solver_input_schema_version != solver_input.schema_version:
            raise SvgPlanInputMismatchError(
                f"source_solver_input_schema_version mismatch: solution has "
                f"{solution.source_solver_input_schema_version!r}, "
                f"solver_input has {solver_input.schema_version!r}"
            )

        # 2. Space lookup and complete bidirectional set matching
        spaces_by_id = {s.id: s for s in solver_input.spaces}
        solution_space_ids = {r.space_id for r in solution.rooms}
        input_space_ids = set(spaces_by_id.keys())

        if solution_space_ids != input_space_ids:
            missing = input_space_ids - solution_space_ids
            extra = solution_space_ids - input_space_ids
            raise SvgPlanUnknownSpaceError(
                f"Solution room space IDs do not match solver input spaces. "
                f"Missing in solution: {missing}, Extra in solution: {extra}"
            )

        # 3. Cross-object geometric containment validation
        for room in solution.rooms:
            room_vertices = [
                SitePoint(x_m=room.x_m, y_m=room.y_m),
                SitePoint(x_m=room.x_m + room.width_m, y_m=room.y_m),
                SitePoint(x_m=room.x_m + room.width_m, y_m=room.y_m + room.depth_m),
                SitePoint(x_m=room.x_m, y_m=room.y_m + room.depth_m),
            ]
            try:
                validate_envelope_inside_parcel(
                    envelope_vertices=room_vertices,
                    parcel_vertices=floor_plate.vertices,
                )
            except SiteEnvelopeOutsideParcelError as e:
                raise SvgPlanInvalidGeometryError(
                    f"Room {room.space_id!r} extends outside FloorPlate boundaries: {e}"
                ) from e

        # 4. Canvas dimensioning & coordinate transformation setup
        floor_min_x = min(v.x_m for v in floor_plate.vertices)
        floor_max_x = max(v.x_m for v in floor_plate.vertices)
        floor_min_y = min(v.y_m for v in floor_plate.vertices)
        floor_max_y = max(v.y_m for v in floor_plate.vertices)

        plan_w_m = floor_max_x - floor_min_x
        plan_h_m = floor_max_y - floor_min_y

        if plan_w_m <= 0 or plan_h_m <= 0:
            raise SvgPlanInvalidGeometryError(
                f"FloorPlate must have strictly positive extents, got {plan_w_m}m x {plan_h_m}m."
            )

        scale = cfg.scale_px_per_m
        margin = cfg.margin_px

        width_px = plan_w_m * scale + 2 * margin
        height_px = plan_h_m * scale + 2 * margin

        # 5. Transform FloorPlate polygon points (preserving original vertex order)
        fp_points: list[str] = []
        for v in floor_plate.vertices:
            px = margin + (v.x_m - floor_min_x) * scale
            py = margin + (floor_max_y - v.y_m) * scale
            fp_points.append(f"{_fmt(px)},{_fmt(py)}")
        points_attr = " ".join(fp_points)

        # 6. Build room groups in deterministic space_id order
        sorted_rooms = sorted(solution.rooms, key=lambda r: r.space_id)
        room_elements: list[str] = []

        for room in sorted_rooms:
            rx = margin + (room.x_m - floor_min_x) * scale
            ry = margin + (floor_max_y - (room.y_m + room.depth_m)) * scale
            rw = room.width_m * scale
            rh = room.depth_m * scale
            cx = rx + rw / 2.0
            cy = ry + rh / 2.0

            space = spaces_by_id[room.space_id]
            display_name = space.display_name
            escaped_name = saxutils.escape(display_name)
            quoted_space_id = saxutils.quoteattr(space.id)
            escaped_space_id_text = saxutils.escape(space.id)
            area_text = saxutils.escape(f"{_fmt(room.area_m2, 2)} m²")

            # Determine label line offsets
            if cfg.show_area_labels and cfg.show_space_ids:
                name_y = cy - 12.0
                area_y = cy + 2.0
                id_y = cy + 14.0
            elif cfg.show_area_labels and not cfg.show_space_ids:
                name_y = cy - 8.0
                area_y = cy + 8.0
                id_y = None
            elif not cfg.show_area_labels and cfg.show_space_ids:
                name_y = cy - 7.0
                area_y = None
                id_y = cy + 7.0
            else:
                name_y = cy
                area_y = None
                id_y = None

            group_lines = [
                f"    <g data-space-id={quoted_space_id}>",
                f"      <title>{escaped_name}</title>",
                f'      <rect class="room-rect" x="{_fmt(rx)}" y="{_fmt(ry)}" '
                f'width="{_fmt(rw)}" height="{_fmt(rh)}" />',
                f'      <text class="room-label" x="{_fmt(cx)}" y="{_fmt(name_y)}">'
                f"{escaped_name}</text>",
            ]
            if area_y is not None:
                group_lines.append(
                    f'      <text class="room-area" x="{_fmt(cx)}" y="{_fmt(area_y)}">'
                    f"{area_text}</text>"
                )
            if id_y is not None:
                group_lines.append(
                    f'      <text class="room-id" x="{_fmt(cx)}" y="{_fmt(id_y)}">'
                    f"{escaped_space_id_text}</text>"
                )
            group_lines.append("    </g>")
            room_elements.append("\n".join(group_lines))

        # 7. Assemble SVG document
        style_lines = [
            "    .plan-background { fill: #ffffff; }",
            "    .floor-plate { fill: #f8f9fa; stroke: #1a1a1a; stroke-width: 2px; "
            "stroke-linejoin: round; }",
            "    .room-rect { fill: #ffffff; stroke: #2b2b2b; stroke-width: 1.5px; }",
            f"    .room-label {{ font-family: sans-serif; font-size: "
            f"{_fmt(cfg.room_label_font_px)}px; font-weight: 600; fill: #111111; "
            f"text-anchor: middle; dominant-baseline: central; }}",
            f"    .room-area {{ font-family: sans-serif; font-size: "
            f"{_fmt(cfg.area_label_font_px)}px; fill: #555555; "
            f"text-anchor: middle; dominant-baseline: central; }}",
            "    .room-id { font-family: monospace; font-size: 9px; fill: #888888; "
            "text-anchor: middle; dominant-baseline: central; }",
        ]
        style_block = "\n".join(style_lines)

        w_str = _fmt(width_px)
        h_str = _fmt(height_px)
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_str} {h_str}" '
            f'width="{w_str}" height="{h_str}">',
            "  <style>",
            style_block,
            "  </style>",
            f'  <rect class="plan-background" width="{w_str}" height="{h_str}" />',
            f'  <polygon class="floor-plate" points="{points_attr}" />',
            "\n".join(room_elements),
            "</svg>",
        ]

        svg_content = "\n".join(svg_parts)

        # 8. Post-assembly XML validation
        try:
            ET.fromstring(svg_content)
        except ET.ParseError as e:
            raise SvgPlanRenderError(f"Generated SVG failed XML validation: {e}") from e

        return SvgPlanDocument(
            schema_version="svg_plan_document.v0",
            project_id=solver_input.project_id,
            source_brief_version=solver_input.source_brief_version,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            source_floor_plate_schema_version="floor_plate.v0",
            source_floor_plate_id=floor_plate.id,
            source_room_solution_schema_version="room_geometry_solution.v0",
            coordinate_system="LOCAL_CARTESIAN_METRES",
            width_px=width_px,
            height_px=height_px,
            svg=svg_content,
        )
