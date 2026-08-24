"""Tests for deterministic site geometry source-binding and grammar validator."""

from __future__ import annotations

from decimal import Decimal

import pytest

from brif_ai.spatial.site.models import SiteGeometryRole, SitePoint
from brif_ai.spatial.site.source_binding import (
    SiteSourceBindingError,
    detect_site_geometry_role,
    extract_site_coordinates_from_text,
    validate_site_geometry_source_binding,
)


class TestDetectSiteGeometryRole:
    """Tests for role detection in Turkish user messages."""

    def test_detect_parcel_boundary_cues(self) -> None:
        assert (
            detect_site_geometry_role("Parsel sınırı: (0;0), (20;0), (20;30), (0;30)")
            == SiteGeometryRole.PARCEL_BOUNDARY
        )
        assert (
            detect_site_geometry_role("parsel koordinatları (0;0), (10;0), (10;10)")
            == SiteGeometryRole.PARCEL_BOUNDARY
        )
        assert (
            detect_site_geometry_role("arsa sınırı şöyle: (0;0), (20;0), (20;20)")
            == SiteGeometryRole.PARCEL_BOUNDARY
        )
        assert (
            detect_site_geometry_role("Parsel siniri: (0;0), (20;0), (20;30)")
            == SiteGeometryRole.PARCEL_BOUNDARY
        )

    def test_detect_buildable_envelope_cues(self) -> None:
        assert (
            detect_site_geometry_role("Yapılaşma zarfı: (2;2), (18;2), (18;28), (2;28)")
            == SiteGeometryRole.BUILDABLE_ENVELOPE
        )
        assert (
            detect_site_geometry_role("yapilasma zarfi koordinatları (2;2), (18;2), (18;28)")
            == SiteGeometryRole.BUILDABLE_ENVELOPE
        )
        assert (
            detect_site_geometry_role("yapılaşabilir alan (2;2), (18;2), (18;28)")
            == SiteGeometryRole.BUILDABLE_ENVELOPE
        )
        assert (
            detect_site_geometry_role("yapılaşma alanı sınırları (2;2), (18;2), (18;28)")
            == SiteGeometryRole.BUILDABLE_ENVELOPE
        )

    def test_ambiguous_both_cues_rejected(self) -> None:
        msg = "Parsel sınırı içinde yapılaşma zarfı: (0;0), (20;0), (20;20)"
        with pytest.raises(SiteSourceBindingError, match="rol belirsiz"):
            detect_site_geometry_role(msg)

    def test_missing_cue_rejected(self) -> None:
        msg = "Koordinatlar: (0;0), (20;0), (20;30), (0;30)"
        with pytest.raises(SiteSourceBindingError, match="açık bir parsel sınırı"):
            detect_site_geometry_role(msg)


class TestExtractSiteCoordinates:
    """Tests for deterministic coordinate extraction."""

    def test_extract_semicolon_separated_integer_points(self) -> None:
        msg = "Parsel: (0;0), (20;0), (20;30), (0;30)"
        points = extract_site_coordinates_from_text(msg)
        assert points == [
            (Decimal("0"), Decimal("0")),
            (Decimal("20"), Decimal("0")),
            (Decimal("20"), Decimal("30")),
            (Decimal("0"), Decimal("30")),
        ]

    def test_extract_semicolon_with_decimal_comma(self) -> None:
        msg = "Parsel: (0,5; 0,5), (20,5; 0,5), (20,5; 30,5), (0,5; 30,5)"
        points = extract_site_coordinates_from_text(msg)
        assert points == [
            (Decimal("0.5"), Decimal("0.5")),
            (Decimal("20.5"), Decimal("0.5")),
            (Decimal("20.5"), Decimal("30.5")),
            (Decimal("0.5"), Decimal("30.5")),
        ]

    def test_extract_comma_separated_with_decimal_dot(self) -> None:
        msg = "Zarf: (2.5, 2.5), (18.5, 2.5), (18.5, 28.5), (2.5, 28.5)"
        points = extract_site_coordinates_from_text(msg)
        assert points == [
            (Decimal("2.5"), Decimal("2.5")),
            (Decimal("18.5"), Decimal("2.5")),
            (Decimal("18.5"), Decimal("28.5")),
            (Decimal("2.5"), Decimal("28.5")),
        ]

    def test_reject_ambiguous_comma_separated_decimal_commas(self) -> None:
        msg = "Parsel: (0,5, 0,5), (20,5, 0,5), (20,5, 30,5)"
        with pytest.raises(SiteSourceBindingError, match="tam 2 koordinat"):
            extract_site_coordinates_from_text(msg)

    def test_source_grammar_ambiguity_and_canonical_formats(self) -> None:
        # 1. Valid semicolon with decimal comma: (20,5 ; 30,0)
        msg1 = "Parsel: (0,0 ; 0,0), (20,5 ; 30,0), (0,0 ; 30,0)"
        pts1 = extract_site_coordinates_from_text(msg1)
        assert pts1[1] == (Decimal("20.5"), Decimal("30.0"))

        # 2. Valid canonical integer: (20;30)
        msg2 = "Parsel: (0;0), (20;30), (0;30)"
        pts2 = extract_site_coordinates_from_text(msg2)
        assert pts2[1] == (Decimal("20"), Decimal("30"))

        # 3. Valid comma-delimited pair with decimal dot: (20.5, 30.0)
        msg3 = "Parsel: (0.0, 0.0), (20.5, 30.0), (0.0, 30.0)"
        pts3 = extract_site_coordinates_from_text(msg3)
        assert pts3[1] == (Decimal("20.5"), Decimal("30.0"))

        # 4. Ambiguous (20,5,30,0) must be rejected
        msg4 = "Parsel: (0,0,0,0), (20,5,30,0), (0,0,30,0)"
        with pytest.raises(SiteSourceBindingError, match="tam 2 koordinat"):
            extract_site_coordinates_from_text(msg4)

    def test_reject_dimension_synthesis_attempts(self) -> None:
        messages = [
            "Arsam 20x30",
            "Parsel 20×30 metre",
            "Arsam 20 metreye 30 metre",
            "Parsel yaklaşık 600 m²",
            "Ön çekme 5 metre, yan çekme 3 metre",
        ]
        for msg in messages:
            with pytest.raises(SiteSourceBindingError, match="otomatik geometri üretilemez"):
                extract_site_coordinates_from_text(msg)

    def test_reject_empty_and_insufficient_points(self) -> None:
        with pytest.raises(SiteSourceBindingError, match="koordinat noktası bulunamadı"):
            extract_site_coordinates_from_text("Parsel sınırı belirlemek istiyorum.")

        with pytest.raises(SiteSourceBindingError, match="Boş koordinat noktası"):
            extract_site_coordinates_from_text("Parsel () (10;0) (10;10)")

        with pytest.raises(SiteSourceBindingError, match="en az 3 koordinat noktası gereklidir"):
            extract_site_coordinates_from_text("Parsel: (0;0), (20;0)")


class TestValidateSiteGeometrySourceBinding:
    """Tests for end-to-end source-binding and exact numeric equivalence."""

    def test_exact_match_passes(self) -> None:
        msg = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"
        vertices = [
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=30.0),
            SitePoint(x_m=0.0, y_m=30.0),
        ]
        # Should not raise
        validate_site_geometry_source_binding(
            user_message=msg,
            proposed_role=SiteGeometryRole.PARCEL_BOUNDARY,
            proposed_vertices=vertices,
        )

    def test_role_mismatch_rejected(self) -> None:
        msg = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"
        vertices = [
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=30.0),
            SitePoint(x_m=0.0, y_m=30.0),
        ]
        with pytest.raises(SiteSourceBindingError, match="eşleşmiyor"):
            validate_site_geometry_source_binding(
                user_message=msg,
                proposed_role=SiteGeometryRole.BUILDABLE_ENVELOPE,
                proposed_vertices=vertices,
            )

    def test_vertex_count_mismatch_rejected(self) -> None:
        msg = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"
        vertices = [
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=30.0),
        ]
        with pytest.raises(SiteSourceBindingError, match="köşe sayısı"):
            validate_site_geometry_source_binding(
                user_message=msg,
                proposed_role=SiteGeometryRole.PARCEL_BOUNDARY,
                proposed_vertices=vertices,
            )

    def test_vertex_reordering_rejected(self) -> None:
        msg = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"
        # Reordered vertices (shifted by 1)
        vertices = [
            SitePoint(x_m=20.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=30.0),
            SitePoint(x_m=0.0, y_m=30.0),
            SitePoint(x_m=0.0, y_m=0.0),
        ]
        with pytest.raises(SiteSourceBindingError, match="Köşe 0 koordinatları eşleşmiyor"):
            validate_site_geometry_source_binding(
                user_message=msg,
                proposed_role=SiteGeometryRole.PARCEL_BOUNDARY,
                proposed_vertices=vertices,
            )

    def test_numeric_tolerance_zero_enforced(self) -> None:
        msg = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"
        # Slight hallucination (20.00001 instead of 20)
        vertices = [
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=20.00001, y_m=0.0),
            SitePoint(x_m=20.0, y_m=30.0),
            SitePoint(x_m=0.0, y_m=30.0),
        ]
        with pytest.raises(SiteSourceBindingError, match="Köşe 1 koordinatları eşleşmiyor"):
            validate_site_geometry_source_binding(
                user_message=msg,
                proposed_role=SiteGeometryRole.PARCEL_BOUNDARY,
                proposed_vertices=vertices,
            )
