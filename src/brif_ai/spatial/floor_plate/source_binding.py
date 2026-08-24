"""Deterministic source-binding grammar and validation for BRIF.AI floor plate."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from brif_ai.spatial.site.models import SitePoint

_POINT_CONTAINER_PATTERN = re.compile(r"\(([^()]*)\)")

# Dimension/area rejection patterns
_DIMENSION_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:x|×|metreye|metre\s*x|metre\s*×|m\s*x|m\s*×)\s*\d+(?:[.,]\d+)?\b",
    re.IGNORECASE,
)
_AREA_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*m²\b",
    re.IGNORECASE,
)


class FloorPlateSourceBindingError(ValueError):
    """Raised when floor plate geometry cannot be deterministically proven from user message."""


def _to_decimal(val: float | Decimal | int | str) -> Decimal:
    """Convert value to exact Decimal representation."""
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def extract_floor_plate_coordinates_from_text(
    user_message: str,
) -> list[tuple[Decimal, Decimal]]:
    """Deterministically extract ordered 2D Cartesian coordinate pairs from raw user message.

    Canonical syntax:
    - Semicolon separator: (0;0), (12;0), (12;18), (0;18) or (12,5 ; 18,5)
    - Comma separator: (0, 0), (12, 0), (12, 18), (0, 18) (only if dot is used for decimals)

    Rejects:
    - Ambiguous comma-separated decimal coords, e.g. (12,5, 18,5)
    - Dimension text like '12x18' or area '216 m²' (underconstrained placement)
    - Fewer than 3 points
    """
    clean_msg = user_message.strip()

    parenthesized_matches = list(_POINT_CONTAINER_PATTERN.finditer(clean_msg))

    if not parenthesized_matches:
        if _DIMENSION_PATTERN.search(clean_msg) or _AREA_PATTERN.search(clean_msg):
            raise FloorPlateSourceBindingError(
                "Boyut veya alan ifadeleri (örn: '12x18', '216 m²') doğrudan köşe koordinatı "
                "olarak kabul edilmez. Taban oturumunun konumu belirsiz olduğu için açık köşe "
                "koordinatları belirtilmelidir."
            )
        raise FloorPlateSourceBindingError(
            "Kullanıcı mesajında açık köşe koordinatı listesi ((x;y)) bulunamadı."
        )

    if len(parenthesized_matches) < 3:
        raise FloorPlateSourceBindingError(
            f"Taban oturumu geometrisi en az 3 köşe gerektirir, "
            f"bulunan: {len(parenthesized_matches)}."
        )

    points: list[tuple[Decimal, Decimal]] = []
    for idx, match in enumerate(parenthesized_matches):
        raw_inner = match.group(1).strip()
        if not raw_inner:
            raise FloorPlateSourceBindingError(f"{idx + 1}. parantez içi boş koordinat içeriyor.")

        if ";" in raw_inner:
            parts = raw_inner.split(";")
            if len(parts) != 2:
                raise FloorPlateSourceBindingError(
                    f"{idx + 1}. koordinat ikilisi noktalı virgül ile 2 eleman içermelidir: "
                    f"{raw_inner!r}"
                )
            x_str = parts[0].strip().replace(",", ".")
            y_str = parts[1].strip().replace(",", ".")
        elif "," in raw_inner:
            parts = raw_inner.split(",")
            if len(parts) != 2:
                raise FloorPlateSourceBindingError(
                    f"{idx + 1}. koordinat ikilisinde virgül ayrımı belirsizdir: {raw_inner!r}"
                )
            x_str = parts[0].strip()
            y_str = parts[1].strip()
        else:
            raise FloorPlateSourceBindingError(
                f"{idx + 1}. koordinat geçerli ayraca (; veya ,) sahip değil: {raw_inner!r}"
            )

        try:
            x_dec = Decimal(x_str)
            y_dec = Decimal(y_str)
        except InvalidOperation as err:
            raise FloorPlateSourceBindingError(
                f"{idx + 1}. koordinat sayısal değere dönüştürülemedi: {raw_inner!r}"
            ) from err

        if not x_dec.is_finite() or not y_dec.is_finite():
            raise FloorPlateSourceBindingError(
                f"{idx + 1}. koordinat sonlu bir sayısal değer olmalıdır."
            )

        points.append((x_dec, y_dec))

    return points


def validate_floor_plate_source_binding(
    user_message: str,
    proposed_vertices: list[SitePoint],
) -> None:
    """Validate that proposed floor plate geometry is deterministically proven by the user message.

    Enforces:
    - User message non-empty.
    - Explicit coordinates present and matched exactly (1:1 vertex count, order, coordinate values).
    - Dimension-only language rejected because placement is underconstrained.
    """
    clean_msg = user_message.strip()
    if not clean_msg:
        raise FloorPlateSourceBindingError("Kullanıcı mesajı boş olamaz.")

    extracted_coords = extract_floor_plate_coordinates_from_text(clean_msg)

    if len(proposed_vertices) != len(extracted_coords):
        raise FloorPlateSourceBindingError(
            f"Önerilen köşe sayısı ({len(proposed_vertices)}) "
            f"kullanıcı mesajındaki köşe sayısı ({len(extracted_coords)}) ile eşleşmiyor."
        )

    for idx, (prop_pt, (ext_x, ext_y)) in enumerate(
        zip(proposed_vertices, extracted_coords, strict=True)
    ):
        prop_x_dec = _to_decimal(prop_pt.x_m)
        prop_y_dec = _to_decimal(prop_pt.y_m)
        if prop_x_dec != ext_x or prop_y_dec != ext_y:
            raise FloorPlateSourceBindingError(
                f"Köşe {idx} koordinatları eşleşmiyor: "
                f"önerilen ({prop_pt.x_m}, {prop_pt.y_m}), "
                f"kullanıcı mesajı ({ext_x}, {ext_y})."
            )
