"""Deterministic source-binding grammar and validation for BRIF.AI site geometry."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from brif_ai.spatial.site.models import SiteGeometryRole, SitePoint

_TURKISH_WORD_BOUND_PRE = r"(?<![\wıişğüçÖÇŞİĞÜ])"
_TURKISH_WORD_BOUND_POST = r"(?=[^\wıişğüçÖÇŞİĞÜ]|$)"

# Role matcher patterns (casefolded)
_PARCEL_PATTERN = re.compile(
    _TURKISH_WORD_BOUND_PRE
    + r"(?:parsel(?:\s+sınırı|\s+siniri)?|arsa\s+sınırı|arsa\s+siniri)"
    + _TURKISH_WORD_BOUND_POST,
    re.IGNORECASE,
)
_ENVELOPE_PATTERN = re.compile(
    _TURKISH_WORD_BOUND_PRE
    + r"(?:yapılaşma\s+zarfı|yapilasma\s+zarfi|"
    + r"yapılaşabilir\s+alan|yapilasabilir\s+alan|"
    + r"yapılaşma\s+alanı|yapilasma\s+alani)"
    + _TURKISH_WORD_BOUND_POST,
    re.IGNORECASE,
)

# Dimension/area/setback rejection patterns
_DIMENSION_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:x|×|metreye|metre\s*x|metre\s*×)\s*\d+(?:[.,]\d+)?\b",
    re.IGNORECASE,
)
_AREA_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*m²\b",
    re.IGNORECASE,
)
_SETBACK_PATTERN = re.compile(
    r"\b(?:ön|arka|yan)\s+çekme\b",
    re.IGNORECASE,
)

_POINT_CONTAINER_PATTERN = re.compile(r"\(([^()]*)\)")


class SiteSourceBindingError(ValueError):
    """Raised when proposed site geometry cannot be deterministically proven from user message."""


def detect_site_geometry_role(user_message: str) -> SiteGeometryRole:
    """Deterministically detect explicit site geometry role from raw user message.

    Rules:
    - Matches PARCEL_BOUNDARY or BUILDABLE_ENVELOPE cues.
    - If neither is matched, raises SiteSourceBindingError.
    - If both role families are present, raises SiteSourceBindingError (ambiguous).
    """
    has_parcel = bool(_PARCEL_PATTERN.search(user_message))
    has_envelope = bool(_ENVELOPE_PATTERN.search(user_message))

    if has_parcel and has_envelope:
        raise SiteSourceBindingError(
            "Mesaj hem parsel hem de yapılaşma zarfı ifadeleri içerdiği için rol belirsizdir."
        )

    if has_parcel:
        return SiteGeometryRole.PARCEL_BOUNDARY

    if has_envelope:
        return SiteGeometryRole.BUILDABLE_ENVELOPE

    raise SiteSourceBindingError(
        "Mesajda açık bir parsel sınırı veya yapılaşma zarfı rolü belirtilmemiş."
    )


def extract_site_coordinates_from_text(user_message: str) -> list[tuple[Decimal, Decimal]]:
    """Deterministically extract ordered 2D Cartesian coordinate pairs from raw user message.

    Canonical syntax:
    - Semicolon separator: (0;0), (20;0), (20;30), (0;30) or (20,5 ; 30,5)
    - Comma separator: (0, 0), (20, 0), (20, 30), (0, 30) (only if dot is used for decimals)

    Rejects:
    - Ambiguous comma-separated decimal coords, e.g. (20,5, 30,5)
    - Dimension text like '20x30' or area '600 m²' or setbacks 'ön çekme 5'
    - Fewer than 3 points
    """
    clean_msg = user_message.strip()

    # Find all parenthesized segments
    parenthesized_matches = list(_POINT_CONTAINER_PATTERN.finditer(clean_msg))

    if not parenthesized_matches:
        # Check if user supplied dimension/setback/area text
        if (
            _DIMENSION_PATTERN.search(clean_msg)
            or _AREA_PATTERN.search(clean_msg)
            or _SETBACK_PATTERN.search(clean_msg)
        ):
            raise SiteSourceBindingError(
                "Boyut, alan veya çekme mesafesi ifadelerinden otomatik geometri üretilemez. "
                "Açık koordinat listesi gereklidir."
            )
        raise SiteSourceBindingError("Mesajda parantez içinde koordinat noktası bulunamadı.")

    points: list[tuple[Decimal, Decimal]] = []

    for match in parenthesized_matches:
        raw_inner = match.group(1).strip()
        if not raw_inner:
            raise SiteSourceBindingError("Boş koordinat noktası '()' geçersizdir.")

        if ";" in raw_inner:
            parts = raw_inner.split(";")
            if len(parts) != 2:
                raise SiteSourceBindingError(
                    "Noktalı virgül ile ayrılmış noktada tam 2 koordinat (x;y) olmalıdır: "
                    f"{raw_inner!r}"
                )
            x_str = parts[0].strip().replace(",", ".")
            y_str = parts[1].strip().replace(",", ".")
        elif "," in raw_inner:
            parts = raw_inner.split(",")
            if len(parts) != 2:
                raise SiteSourceBindingError(
                    f"Virgül ile ayrılmış noktada tam 2 koordinat (x,y) olmalıdır: {raw_inner!r}"
                )
            # When comma is coordinate separator, coordinate numbers cannot have another comma
            x_str = parts[0].strip()
            y_str = parts[1].strip()
        else:
            raise SiteSourceBindingError(
                f"Koordinat ayırıcı ';' veya ',' bulunamadı: {raw_inner!r}"
            )

        try:
            x_dec = Decimal(x_str)
            y_dec = Decimal(y_str)
        except InvalidOperation as err:
            raise SiteSourceBindingError(
                f"Geçersiz sayısal koordinat değeri {raw_inner!r}: {err}"
            ) from err

        if not x_dec.is_finite() or not y_dec.is_finite():
            raise SiteSourceBindingError(f"Koordinat değerleri sonlu sayı olmalıdır: {raw_inner!r}")

        points.append((x_dec, y_dec))

    if len(points) < 3:
        raise SiteSourceBindingError(
            f"Geçerli bir poligon için en az 3 koordinat noktası gereklidir, bulunan: {len(points)}"
        )

    return points


def _to_decimal(val: float | Decimal | int | str) -> Decimal:
    """Convert value to exact Decimal representation."""
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (int, str)):
        return Decimal(str(val))
    return Decimal(str(val))


def validate_site_geometry_source_binding(
    user_message: str,
    proposed_role: SiteGeometryRole,
    proposed_vertices: list[SitePoint],
) -> None:
    """Validate that proposed site geometry matches user message role and coordinates 1:1.

    Enforces:
    - Role matched explicitly in user message.
    - Exact vertex count.
    - Exact vertex order.
    - Exact numeric equality via Decimal (zero geometric tolerance).
    """
    detected_role = detect_site_geometry_role(user_message)
    if detected_role != proposed_role:
        raise SiteSourceBindingError(
            f"Kullanıcı mesajındaki rol '{detected_role.value}' "
            f"ile önerilen rol '{proposed_role.value}' eşleşmiyor."
        )

    extracted_points = extract_site_coordinates_from_text(user_message)

    if len(proposed_vertices) != len(extracted_points):
        raise SiteSourceBindingError(
            f"Önerilen köşe sayısı ({len(proposed_vertices)}) "
            f"kullanıcı mesajındaki köşe sayısı ({len(extracted_points)}) ile eşleşmiyor."
        )

    for idx, (prop_pt, (ext_x, ext_y)) in enumerate(
        zip(proposed_vertices, extracted_points, strict=True)
    ):
        prop_x_dec = _to_decimal(prop_pt.x_m)
        prop_y_dec = _to_decimal(prop_pt.y_m)

        if prop_x_dec != ext_x or prop_y_dec != ext_y:
            raise SiteSourceBindingError(
                f"Köşe {idx} koordinatları eşleşmiyor: "
                f"önerilen ({prop_pt.x_m}, {prop_pt.y_m}), "
                f"kullanıcı mesajı ({ext_x}, {ext_y})."
            )
