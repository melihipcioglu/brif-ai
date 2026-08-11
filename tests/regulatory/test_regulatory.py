"""BRIF.AI — Comprehensive Tests for Turkish Regulatory Foundation V0."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from brif_ai.contentpacks.tr.regulatory.demo_ruleset import (
    DEMO_REGULATORY_SOURCE,
    build_demo_ruleset,
)
from brif_ai.regulatory.compliance import DeterministicComplianceEngine
from brif_ai.regulatory.models import (
    ComplianceStatus,
    DesignFacts,
    ProjectRegulatoryContext,
    RegulatoryRuleSet,
    RegulatorySource,
    SourceStatus,
    SourceType,
    VerificationStatus,
    ZoningContext,
)
from brif_ai.regulatory.registry import RegulatoryRegistry
from brif_ai.regulatory.update_detection import (
    RegulatoryChangeDetector,
    RegulatorySourceSnapshot,
)


def test_regulatory_source_validation_and_hierarchy() -> None:
    source = RegulatorySource(
        source_id="src_resmi_gazete_30113",
        title="Planlı Alanlar İmar Yönetmeliği",
        jurisdiction="TR",
        authority="Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
        official_url="https://www.resmigazete.gov.tr/eskiler/2017/07/20170703-1.htm",
        source_type=SourceType.NATIONAL_REGULATION,
        publication_date=date(2017, 7, 3),
        effective_from=date(2017, 10, 1),
        status=SourceStatus.ACTIVE,
    )
    assert source.source_id == "src_resmi_gazete_30113"
    assert source.source_type == SourceType.NATIONAL_REGULATION


def test_ruleset_hash_determinism_across_serialization_cycles() -> None:
    ruleset1 = build_demo_ruleset()
    hash1 = ruleset1.compute_canonical_hash()

    # Serialize to JSON and re-parse
    json_str = ruleset1.model_dump_json()
    ruleset2 = RegulatoryRuleSet.model_validate_json(json_str)
    hash2 = ruleset2.compute_canonical_hash()

    assert hash1 == hash2


def test_deterministic_compliance_engine_max_value_pass_and_fail() -> None:
    engine = DeterministicComplianceEngine()
    ruleset = build_demo_ruleset()
    sources = {DEMO_REGULATORY_SOURCE.source_id: DEMO_REGULATORY_SOURCE}

    context = ProjectRegulatoryContext(
        project_id="proj_house",
        country="TR",
        province="İstanbul",
        district="Kadıköy",
        ruleset_id=ruleset.ruleset_id,
        verification_status=VerificationStatus.VERIFIED,
    )

    # 1. PASS case: proposed_height_m = 10.5m (<= limit 12.5m)
    pass_facts = DesignFacts(proposed_height_m=Decimal("10.50"))
    findings_pass = engine.evaluate_ruleset(ruleset, context, pass_facts, sources)
    height_finding_pass = next(f for f in findings_pass if f.rule_id == "rule_height_max_01")
    assert height_finding_pass.status == ComplianceStatus.PASS
    assert height_finding_pass.source_id == DEMO_REGULATORY_SOURCE.source_id

    # 2. FAIL case: proposed_height_m = 15.0m (> limit 12.5m)
    fail_facts = DesignFacts(proposed_height_m=Decimal("15.00"))
    findings_fail = engine.evaluate_ruleset(ruleset, context, fail_facts, sources)
    height_finding_fail = next(f for f in findings_fail if f.rule_id == "rule_height_max_01")
    assert height_finding_fail.status == ComplianceStatus.FAIL


def test_none_fact_produces_unknown_and_preserves_zero() -> None:
    engine = DeterministicComplianceEngine()
    ruleset = build_demo_ruleset()

    context = ProjectRegulatoryContext(
        project_id="proj_house",
        country="TR",
        province="İstanbul",
        district="Kadıköy",
        ruleset_id=ruleset.ruleset_id,
        verification_status=VerificationStatus.VERIFIED,
    )

    # None fact -> UNKNOWN
    none_facts = DesignFacts(proposed_height_m=None)
    findings_none = engine.evaluate_ruleset(ruleset, context, none_facts)
    height_finding_none = next(f for f in findings_none if f.rule_id == "rule_height_max_01")
    assert height_finding_none.status == ComplianceStatus.UNKNOWN

    # Zero fact -> Preserved as Decimal(0) and evaluated against rule
    zero_facts = DesignFacts(proposed_height_m=Decimal("0.00"))
    findings_zero = engine.evaluate_ruleset(ruleset, context, zero_facts)
    height_finding_zero = next(f for f in findings_zero if f.rule_id == "rule_height_max_01")
    assert height_finding_zero.status == ComplianceStatus.PASS
    assert height_finding_zero.observed_value == Decimal("0.00")


def test_unverified_context_cannot_yield_verified_pass() -> None:
    engine = DeterministicComplianceEngine()
    ruleset = build_demo_ruleset()

    unverified_context = ProjectRegulatoryContext(
        project_id="proj_house",
        country="TR",
        province="İstanbul",
        district="Kadıköy",
        ruleset_id=ruleset.ruleset_id,
        verification_status=VerificationStatus.UNVERIFIED,
    )

    facts = DesignFacts(proposed_height_m=Decimal("10.00"))
    findings = engine.evaluate_ruleset(ruleset, unverified_context, facts)
    for finding in findings:
        assert finding.status == ComplianceStatus.UNKNOWN


def test_taks_formula_limit_compliance_evaluation() -> None:
    engine = DeterministicComplianceEngine()
    ruleset = build_demo_ruleset()

    context = ProjectRegulatoryContext(
        project_id="proj_house",
        country="TR",
        province="Ankara",
        district="Çankaya",
        ruleset_id=ruleset.ruleset_id,
        verification_status=VerificationStatus.VERIFIED,
        zoning_context=ZoningContext(
            parcel_area_m2=Decimal("500.00"),
            taks=Decimal("0.40"),  # max footprint = 500 * 0.40 = 200 m2
        ),
    )

    # 1. PASS: footprint = 180 m2
    pass_facts = DesignFacts(
        parcel_area_m2=Decimal("500.00"),
        taks=Decimal("0.40"),
        proposed_footprint_m2=Decimal("180.00"),
    )
    findings_pass = engine.evaluate_ruleset(ruleset, context, pass_facts)
    taks_finding_pass = next(f for f in findings_pass if f.rule_id == "rule_taks_max_01")
    assert taks_finding_pass.status == ComplianceStatus.PASS

    # 2. FAIL: footprint = 250 m2
    fail_facts = DesignFacts(
        parcel_area_m2=Decimal("500.00"),
        taks=Decimal("0.40"),
        proposed_footprint_m2=Decimal("250.00"),
    )
    findings_fail = engine.evaluate_ruleset(ruleset, context, fail_facts)
    taks_finding_fail = next(f for f in findings_fail if f.rule_id == "rule_taks_max_01")
    assert taks_finding_fail.status == ComplianceStatus.FAIL


def test_update_candidate_creation_and_non_activation_invariant() -> None:
    detector = RegulatoryChangeDetector()
    registry = RegulatoryRegistry()

    ruleset = build_demo_ruleset()
    registry.register_ruleset(ruleset)

    now = datetime.now(timezone.utc)  # noqa: UP017
    snap1 = RegulatorySourceSnapshot(
        source_id="src_tr_pa_imar_demo",
        url="https://resmigazete.gov.tr/demo/pa_imar",
        content_sha256="hash_v1_11111111",
        retrieved_at=now,
    )
    snap2 = RegulatorySourceSnapshot(
        source_id="src_tr_pa_imar_demo",
        url="https://resmigazete.gov.tr/demo/pa_imar",
        content_sha256="hash_v2_22222222",
        retrieved_at=now,
    )

    candidate = detector.compare_snapshots(
        source_id="src_tr_pa_imar_demo",
        official_url="https://resmigazete.gov.tr/demo/pa_imar",
        previous_snapshot=snap1,
        current_snapshot=snap2,
        detected_at=now,
    )

    assert candidate is not None
    assert candidate.verification_status == VerificationStatus.UNVERIFIED
    assert candidate.old_content_sha256 == "hash_v1_11111111"
    assert candidate.new_content_sha256 == "hash_v2_22222222"

    # Invariant check: Active ruleset in registry remains UNCHANGED by candidate creation
    active_ruleset = registry.get_ruleset(ruleset.ruleset_id)
    assert active_ruleset is not None
    assert active_ruleset.compute_canonical_hash() == ruleset.compute_canonical_hash()


def test_generation_constraint_boundary_export() -> None:
    engine = DeterministicComplianceEngine()
    context = ProjectRegulatoryContext(
        project_id="proj_house",
        country="TR",
        province="İzmir",
        district="Urla",
        ruleset_id="TR-REG-DEMO-2026",
        verification_status=VerificationStatus.VERIFIED,
        zoning_context=ZoningContext(
            parcel_area_m2=Decimal("600.00"),
            taks=Decimal("0.35"),  # max footprint = 210 m2
            kaks_or_emsal=Decimal("0.70"),  # max total floor = 420 m2
            max_height_m=Decimal("9.50"),
            max_floors=2,
            front_setback_m=Decimal("5.00"),
            side_setback_m=Decimal("3.00"),
            rear_setback_m=Decimal("3.00"),
        ),
    )

    constraints = engine.to_generation_constraints(context, [])
    assert constraints.max_footprint_m2 == Decimal("210.00")
    assert constraints.max_total_floor_area_m2 == Decimal("420.00")
    assert constraints.max_height_m == Decimal("9.50")
    assert constraints.min_front_setback_m == Decimal("5.00")
