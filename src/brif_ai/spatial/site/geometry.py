"""Pure Python 2D computational geometry predicates for Site / Buildable Envelope V0."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

from brif_ai.spatial.site.errors import (
    SiteEnvelopeOutsideParcelError,
    SiteInvalidCoordinateError,
    SitePolygonDegenerateError,
    SitePolygonSelfIntersectionError,
)

if TYPE_CHECKING:
    from brif_ai.spatial.site.models import SitePoint

_GEOMETRY_EPSILON: float = 1e-9


def cross_product_2d(p: SitePoint, q: SitePoint, r: SitePoint) -> float:
    """Compute 2D cross product of vectors (q - p) and (r - p)."""
    return (q.x_m - p.x_m) * (r.y_m - p.y_m) - (q.y_m - p.y_m) * (r.x_m - p.x_m)


def orientation_2d(p: SitePoint, q: SitePoint, r: SitePoint) -> int:
    """Determine orientation of triplet (p, q, r).

    Returns:
         0 if collinear (within _GEOMETRY_EPSILON)
         1 if counter-clockwise
        -1 if clockwise
    """
    cp = cross_product_2d(p, q, r)
    if abs(cp) <= _GEOMETRY_EPSILON:
        return 0
    return 1 if cp > 0 else -1


def is_point_on_segment(pt: SitePoint, p1: SitePoint, p2: SitePoint) -> bool:
    """Check if point pt lies on closed segment (p1, p2)."""
    if abs(cross_product_2d(p1, p2, pt)) > _GEOMETRY_EPSILON:
        return False
    min_x, max_x = min(p1.x_m, p2.x_m), max(p1.x_m, p2.x_m)
    min_y, max_y = min(p1.y_m, p2.y_m), max(p1.y_m, p2.y_m)
    return (
        min_x - _GEOMETRY_EPSILON <= pt.x_m <= max_x + _GEOMETRY_EPSILON
        and min_y - _GEOMETRY_EPSILON <= pt.y_m <= max_y + _GEOMETRY_EPSILON
    )


def segments_properly_intersect(
    p1: SitePoint,
    p2: SitePoint,
    q1: SitePoint,
    q2: SitePoint,
) -> bool:
    """Check if segments (p1, p2) and (q1, q2) cross strictly in their interiors."""
    o1 = orientation_2d(p1, p2, q1)
    o2 = orientation_2d(p1, p2, q2)
    o3 = orientation_2d(q1, q2, p1)
    o4 = orientation_2d(q1, q2, p2)

    return o1 != 0 and o2 != 0 and o1 != o2 and o3 != 0 and o4 != 0 and o3 != o4


def segments_intersect(
    p1: SitePoint,
    p2: SitePoint,
    q1: SitePoint,
    q2: SitePoint,
) -> bool:
    """Check if segments (p1, p2) and (q1, q2) intersect (crossing, touching, overlap)."""
    if segments_properly_intersect(p1, p2, q1, q2):
        return True

    return (
        is_point_on_segment(q1, p1, p2)
        or is_point_on_segment(q2, p1, p2)
        or is_point_on_segment(p1, q1, q2)
        or is_point_on_segment(p2, q1, q2)
    )


def calculate_polygon_area(vertices: Sequence[SitePoint]) -> float:
    """Compute absolute unsigned area using the 2D Shoelace formula."""
    n = len(vertices)
    if n < 3:
        return 0.0
    accum = 0.0
    for i in range(n):
        j = (i + 1) % n
        accum += vertices[i].x_m * vertices[j].y_m - vertices[j].x_m * vertices[i].y_m
    return 0.5 * abs(accum)


def is_point_in_or_on_polygon(pt: SitePoint, vertices: Sequence[SitePoint]) -> bool:
    """Test if point pt lies inside or on the boundary of polygon using ray casting."""
    n = len(vertices)
    if n < 3:
        return False

    # Check if point is on any edge
    for i in range(n):
        j = (i + 1) % n
        if is_point_on_segment(pt, vertices[i], vertices[j]):
            return True

    # Ray casting to (+inf, y)
    inside = False
    for i in range(n):
        j = (i + 1) % n
        vi = vertices[i]
        vj = vertices[j]

        # Check edge intersects horizontal ray
        if (vi.y_m > pt.y_m) != (vj.y_m > pt.y_m) and abs(vj.y_m - vi.y_m) > _GEOMETRY_EPSILON:
            x_cross = vi.x_m + (pt.y_m - vi.y_m) * (vj.x_m - vi.x_m) / (vj.y_m - vi.y_m)
            if x_cross > pt.x_m:
                inside = not inside

    return inside


def validate_polygon_geometry(vertices: Sequence[SitePoint]) -> None:
    """Validate that vertices form a valid simple polygon.

    Invariants enforced:
    1. At least 3 vertices.
    2. Finite coordinates on all points.
    3. Caller must not repeat first vertex at the end.
    4. All supplied vertices must be unique (no duplicate coordinates).
    5. Non-zero area.
    6. Non-self-intersecting (no non-adjacent edge crossing, touching, or collinear overlap).
    """
    n = len(vertices)
    if n < 3:
        raise SitePolygonDegenerateError(f"Polygon must have at least 3 vertices, got {n}.")

    for idx, v in enumerate(vertices):
        if not math.isfinite(v.x_m) or not math.isfinite(v.y_m):
            raise SiteInvalidCoordinateError(
                f"Vertex {idx} has non-finite coordinates: x={v.x_m!r}, y={v.y_m!r}."
            )

    # Check closing vertex repeat
    if (
        abs(vertices[0].x_m - vertices[-1].x_m) <= _GEOMETRY_EPSILON
        and abs(vertices[0].y_m - vertices[-1].y_m) <= _GEOMETRY_EPSILON
    ):
        raise SitePolygonDegenerateError(
            "Caller must not repeat the first vertex at the end of the polygon."
        )

    # Check all vertices are distinct
    for i in range(n):
        for j in range(i + 1, n):
            if (
                abs(vertices[i].x_m - vertices[j].x_m) <= _GEOMETRY_EPSILON
                and abs(vertices[i].y_m - vertices[j].y_m) <= _GEOMETRY_EPSILON
            ):
                raise SitePolygonDegenerateError(
                    f"Duplicate vertex found at indices {i} and {j}: "
                    f"({vertices[i].x_m}, {vertices[i].y_m}). All vertices must be unique."
                )

    # Check non-zero area
    area = calculate_polygon_area(vertices)
    if area <= _GEOMETRY_EPSILON:
        raise SitePolygonDegenerateError(
            f"Polygon area must be strictly positive, calculated area is {area}."
        )

    # Check self-intersection between edges
    for i in range(n):
        p1 = vertices[i]
        p2 = vertices[(i + 1) % n]

        for j in range(i + 1, n):
            q1 = vertices[j]
            q2 = vertices[(j + 1) % n]

            # Same edge
            if i == j:
                continue

            # Adjacent edges share a common vertex
            is_adjacent = (j == i + 1) or (i == 0 and j == n - 1)

            if is_adjacent:
                # Check for degenerate overlap between adjacent edges
                # For adjacent edges, the only intersection point must be the shared vertex
                shared = p2 if j == i + 1 else p1
                other_p = p1 if j == i + 1 else p2
                other_q = q2 if j == i + 1 else q1

                if is_point_on_segment(other_p, q1, q2) and other_p != shared:
                    raise SitePolygonSelfIntersectionError(
                        f"Adjacent edges ({i}, {j}) have collinear overlap or degenerate touching."
                    )
                if is_point_on_segment(other_q, p1, p2) and other_q != shared:
                    raise SitePolygonSelfIntersectionError(
                        f"Adjacent edges ({i}, {j}) have collinear overlap or degenerate touching."
                    )
            else:
                # Non-adjacent edges must not intersect at all
                if segments_intersect(p1, p2, q1, q2):
                    raise SitePolygonSelfIntersectionError(
                        f"Non-adjacent edges ({i}, {j}) intersect, touch, or overlap."
                    )


def _find_segment_intersection_parameters(
    p1: SitePoint,
    p2: SitePoint,
    q1: SitePoint,
    q2: SitePoint,
) -> list[float]:
    """Find all intersection/touch parameters t in [0, 1] along (p1, p2) with (q1, q2)."""
    px = p2.x_m - p1.x_m
    py = p2.y_m - p1.y_m
    qx = q2.x_m - q1.x_m
    qy = q2.y_m - q1.y_m

    cross_pq = px * qy - py * qx
    qpx = q1.x_m - p1.x_m
    qpy = q1.y_m - p1.y_m

    p_len_sq = px * px + py * py
    if p_len_sq <= _GEOMETRY_EPSILON * _GEOMETRY_EPSILON:
        return []

    if abs(cross_pq) > _GEOMETRY_EPSILON:
        t = (qpx * qy - qpy * qx) / cross_pq
        u = (qpx * py - qpy * px) / cross_pq

        if (
            -_GEOMETRY_EPSILON <= t <= 1.0 + _GEOMETRY_EPSILON
            and -_GEOMETRY_EPSILON <= u <= 1.0 + _GEOMETRY_EPSILON
        ):
            return [max(0.0, min(1.0, float(t)))]
        return []

    # Parallel or collinear: check if collinear
    cross_qp_p = qpx * py - qpy * px
    if abs(cross_qp_p) <= _GEOMETRY_EPSILON:
        params: list[float] = []
        for q in (q1, q2):
            t_val = ((q.x_m - p1.x_m) * px + (q.y_m - p1.y_m) * py) / p_len_sq
            if -_GEOMETRY_EPSILON <= t_val <= 1.0 + _GEOMETRY_EPSILON:
                params.append(max(0.0, min(1.0, float(t_val))))
        if is_point_on_segment(p1, q1, q2):
            params.append(0.0)
        if is_point_on_segment(p2, q1, q2):
            params.append(1.0)
        return params

    return []


def validate_envelope_inside_parcel(
    envelope_vertices: Sequence[SitePoint],
    parcel_vertices: Sequence[SitePoint],
) -> None:
    """Validate that buildable envelope lies completely inside or on the parcel boundary.

    ALGORITHM:
    1. Every envelope vertex must lie inside or on the parcel boundary.
    2. For every envelope edge (p1, p2):
       a. Collect all intersection / touch parameters t in [0, 1] with every parcel edge.
       b. Include t=0.0 and t=1.0.
       c. Sort and deduplicate parameters within _GEOMETRY_EPSILON.
       d. Partition into intervals [t_k, t_{k+1}].
       e. For every interval, test sample midpoint: P_mid = p1 + t_mid * (p2 - p1).
       f. P_mid must lie inside or on the parcel boundary.
    """
    from brif_ai.spatial.site.models import SitePoint

    # 1. Every envelope vertex must be in or on the parcel
    for idx, ev in enumerate(envelope_vertices):
        if not is_point_in_or_on_polygon(ev, parcel_vertices):
            raise SiteEnvelopeOutsideParcelError(
                f"Buildable envelope vertex {idx} ({ev.x_m}, {ev.y_m}) lies outside "
                f"the parcel boundary."
            )

    n_env = len(envelope_vertices)
    n_par = len(parcel_vertices)

    for i in range(n_env):
        ep1 = envelope_vertices[i]
        ep2 = envelope_vertices[(i + 1) % n_env]

        t_params: list[float] = [0.0, 1.0]

        for j in range(n_par):
            pp1 = parcel_vertices[j]
            pp2 = parcel_vertices[(j + 1) % n_par]
            found_t = _find_segment_intersection_parameters(ep1, ep2, pp1, pp2)
            t_params.extend(found_t)

        # Sort and deduplicate t_params within _GEOMETRY_EPSILON
        t_sorted = sorted(t_params)
        t_dedup: list[float] = []
        for t in t_sorted:
            if not t_dedup or abs(t - t_dedup[-1]) > _GEOMETRY_EPSILON:
                t_dedup.append(t)

        # Test midpoint of each partitioned interval
        for k in range(len(t_dedup) - 1):
            t_start = t_dedup[k]
            t_end = t_dedup[k + 1]
            if (t_end - t_start) <= _GEOMETRY_EPSILON:
                continue

            t_mid = (t_start + t_end) / 2.0
            mid_x = ep1.x_m + t_mid * (ep2.x_m - ep1.x_m)
            mid_y = ep1.y_m + t_mid * (ep2.y_m - ep1.y_m)
            mid_pt = SitePoint(x_m=mid_x, y_m=mid_y)

            if not is_point_in_or_on_polygon(mid_pt, parcel_vertices):
                raise SiteEnvelopeOutsideParcelError(
                    f"Buildable envelope edge {i} passes outside the parcel boundary "
                    f"in interval [{t_start:.4f}, {t_end:.4f}] "
                    f"(sample point ({mid_x}, {mid_y}) is outside)."
                )
