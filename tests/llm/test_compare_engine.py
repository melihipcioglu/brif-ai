from __future__ import annotations

import pytest

from brif_ai.llm.compare_engine import (
    CompareFailureCategory,
    ComparePlanValidationError,
    analyze_compare_request,
    build_compare_plan_schema,
    extract_explicit_axes,
    render_compare_plan,
    semantic_match,
    validate_compare_plan,
    validate_rendered_compare,
)
from brif_ai.llm.contracts import (
    ActiveContextSnapshot,
    CompareApproach,
    CompareDecisionPlan,
    CompareMode,
    CompareOutcome,
    ConversationRequest,
    VisibleEntity,
)


def compare_request(message: str, names: list[str]) -> ConversationRequest:
    return ConversationRequest(
        message=message,
        active_context=ActiveContextSnapshot(
            project_id="project_compare",
            building_id="building_main",
            level_id="level_ground",
            zone_id="zone_shared",
            entity_id=None,
            context_fingerprint="compare|main|ground|shared",
            generation_id=1,
        ),
        visible_entities=[
            VisibleEntity(
                entity_id=f"space_dynamic_{index}",
                entity_type="space",
                name=name,
                project_id="project_compare",
                building_id="building_main",
                level_id="level_ground",
                zone_id="zone_shared",
            )
            for index, name in enumerate(names)
        ],
    )


def open_plan() -> CompareDecisionPlan:
    return CompareDecisionPlan(
        mode=CompareMode.OPEN_ALTERNATIVES,
        approach_1=CompareApproach.INTEGRATED_FLOW,
        outcome_1=CompareOutcome.CONTINUOUS_INTERACTION,
        approach_2=CompareApproach.PARALLEL_RHYTHMS,
        outcome_2=CompareOutcome.INDEPENDENT_SIMULTANEOUS_USE,
        confidence=0.91,
    )


def explicit_plan(
    outcome_1: CompareOutcome = CompareOutcome.CONTROLLED_PERSONAL_USE,
    outcome_2: CompareOutcome = CompareOutcome.EASY_DAILY_USE,
) -> CompareDecisionPlan:
    return CompareDecisionPlan(
        mode=CompareMode.EXPLICIT_AXES,
        approach_1=CompareApproach.AXIS_1,
        outcome_1=outcome_1,
        approach_2=CompareApproach.AXIS_2,
        outcome_2=outcome_2,
        confidence=0.92,
    )


def entity_choice_plan() -> CompareDecisionPlan:
    return CompareDecisionPlan(
        mode=CompareMode.ENTITY_CHOICE,
        approach_1=CompareApproach.CHOICE_1,
        outcome_1=CompareOutcome.INDOOR_CONTINUITY,
        approach_2=CompareApproach.CHOICE_2,
        outcome_2=CompareOutcome.OUTDOOR_EXPERIENCE,
        confidence=0.9,
    )


def test_open_alternatives_analysis_keeps_all_subjects_in_one_problem() -> None:
    request = compare_request(
        (
            "Salon ile mutfak arasındaki ilişkiyi güçlendirmek istiyorum. "
            "Teras da günlük oturma ve sohbet alanıyla ilişkili olsun. "
            "Bana iki farklı düzenleme alternatifi öner."
        ),
        ["Salon", "Mutfak", "Teras"],
    )

    analysis = analyze_compare_request(request)

    assert analysis.mode is CompareMode.OPEN_ALTERNATIVES
    assert analysis.subject_labels == ("Salon", "Mutfak", "Teras")
    assert analysis.axes is None
    assert analysis.choice_labels is None


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "Birinde mahremiyet, diğerinde kullanım kolaylığı daha baskın olsun.",
            ("mahremiyet", "kullanım kolaylığı"),
        ),
        (
            "Birinde sessizlik ve odaklanma, diğerinde aileyle etkileşim daha önemli olsun.",
            ("sessizlik ve odaklanma", "aileyle etkileşim"),
        ),
        (
            "Birinde düzen ve kontrol, diğerinde esneklik ve serbest kullanım ön planda olsun.",
            ("düzen ve kontrol", "esneklik ve serbest kullanım"),
        ),
        ("Biri gösteriş, diğeri sadelik.", ("gösteriş", "sadelik")),
        (
            "Birincide bireysel çalışma, ikincide birlikte çalışma.",
            ("bireysel çalışma", "birlikte çalışma"),
        ),
    ],
)
def test_explicit_axis_extraction(message: str, expected: tuple[str, str]) -> None:
    assert extract_explicit_axes(message) == expected


@pytest.mark.parametrize(
    "message",
    [
        "Mahremiyet ve kolaylık önemli.",
        "İki farklı yaklaşım öner.",
        "Bir seçenek düzenli olabilir.",
    ],
)
def test_uncertain_axis_language_falls_back_to_open(message: str) -> None:
    request = compare_request(message, ["Meditasyon Odası", "Çalışma Odası"])
    assert analyze_compare_request(request).mode is CompareMode.OPEN_ALTERNATIVES


@pytest.mark.parametrize(
    "names",
    [
        ["Salon", "Mutfak"],
        ["Atölye", "Sergi Alanı"],
        ["Laboratuvar", "Hazırlık Alanı"],
        ["Kütüphane", "Okuma Salonu"],
        ["Meditasyon Odası", "Müzik Odası"],
    ],
)
def test_subject_names_do_not_change_open_mode(names: list[str]) -> None:
    request = compare_request(
        f"{names[0]} ile {names[1]} için iki farklı kullanım yaklaşımı öner.",
        names,
    )
    analysis = analyze_compare_request(request)
    assert analysis.mode is CompareMode.OPEN_ALTERNATIVES
    assert analysis.subject_labels == tuple(names)


@pytest.mark.parametrize(
    ("focus", "expected"),
    [
        (
            "Hasta mahremiyeti önemli.",
            (CompareApproach.PRIVACY_BALANCE, CompareApproach.INTEGRATED_FLOW),
        ),
        (
            "Değişen etkinlikler için esnek kullanım önemli.",
            (CompareApproach.ADAPTABLE_USE, CompareApproach.ORDERED_USE),
        ),
        (
            "Hem odaklanma hem birlikte çalışma önemli.",
            (CompareApproach.INDIVIDUAL_BALANCE, CompareApproach.SHARED_ACTIVITY),
        ),
    ],
)
def test_open_requirement_semantics_select_diverse_safe_families(
    focus: str,
    expected: tuple[CompareApproach, CompareApproach],
) -> None:
    request = compare_request(
        f"Laboratuvar ile Hazırlık Alanı için iki alternatif öner. {focus}",
        ["Laboratuvar", "Hazırlık Alanı"],
    )
    assert analyze_compare_request(request).open_approaches == expected


@pytest.mark.parametrize(
    "message",
    [
        "Salon kullanımını mı teras kullanımını mı öne çıkarmalıyım?",
        "Açık mutfak mı kapalı mutfak mı bizim için uygun?",
        "Bu iki mevcut seçenekten hangisini seçmeliyim?",
    ],
)
def test_selection_evidence_enables_entity_choice(message: str) -> None:
    names = ["Salon", "Teras"]
    if "mutfak" in message.casefold():
        names = ["Açık Mutfak", "Kapalı Mutfak"]
    request = compare_request(message, names)
    analysis = analyze_compare_request(request)
    assert analysis.mode is CompareMode.ENTITY_CHOICE
    assert analysis.choice_labels == tuple(names)


def test_open_plan_renders_subjects_in_both_alternatives_but_not_titles() -> None:
    request = compare_request(
        "Atölye ile sergi alanı için iki farklı organizasyon yaklaşımı öner.",
        ["Atölye", "Sergi Alanı"],
    )
    analysis = analyze_compare_request(request)
    plan = open_plan()

    validate_compare_plan(plan, request, analysis)
    result = render_compare_plan(plan, request, analysis)
    validate_rendered_compare(result, request)

    first_heading, second_heading = result.assistant_message.split("\n\n")[:2]
    assert "Atölye" not in first_heading.split(":", maxsplit=1)[0]
    assert "Sergi Alanı" not in second_heading.split(":", maxsplit=1)[0]
    assert result.assistant_message.count("Atölye") == 2
    assert result.assistant_message.count("Sergi Alanı") == 2


@pytest.mark.parametrize(
    ("updates", "category"),
    [
        (
            {"approach_2": CompareApproach.INTEGRATED_FLOW},
            CompareFailureCategory.ALTERNATIVES_TOO_SIMILAR,
        ),
        (
            {"approach_1": CompareApproach.AXIS_1},
            CompareFailureCategory.MODE_MISMATCH,
        ),
        (
            {"outcome_1": CompareOutcome.PREDICTABLE_ROUTINE},
            CompareFailureCategory.KEY_DIFFERENCE_INVALID,
        ),
    ],
)
def test_open_plan_rejects_invalid_semantic_enum_combinations(
    updates: dict[str, object],
    category: CompareFailureCategory,
) -> None:
    request = compare_request(
        "Salon ile mutfak için iki farklı yaklaşım öner.",
        ["Salon", "Mutfak"],
    )
    plan = open_plan().model_copy(update=updates)
    with pytest.raises(ComparePlanValidationError) as captured:
        validate_compare_plan(plan, request, analyze_compare_request(request))
    assert captured.value.category is category


@pytest.mark.parametrize(
    ("axes", "outcomes"),
    [
        (
            "Birinde mahremiyet, diğerinde kullanım kolaylığı daha baskın olsun.",
            (CompareOutcome.CONTROLLED_PERSONAL_USE, CompareOutcome.EASY_DAILY_USE),
        ),
        (
            "Birinde sessizlik ve odaklanma, diğerinde aileyle etkileşim daha önemli olsun.",
            (CompareOutcome.FOCUSED_ACTIVITY, CompareOutcome.SHARED_INTERACTION),
        ),
        (
            "Birinde düzen ve kontrol, diğerinde esneklik ve serbest kullanım ön planda olsun.",
            (CompareOutcome.ORDER_AND_OVERSIGHT, CompareOutcome.FLEXIBLE_SELF_DIRECTED_USE),
        ),
        (
            "Biri gösteriş, diğeri sadelik.",
            (CompareOutcome.EXPRESSIVE_CHARACTER, CompareOutcome.CALM_SIMPLICITY),
        ),
    ],
)
def test_explicit_axes_drive_ordered_plan_and_natural_renderer(
    axes: str,
    outcomes: tuple[CompareOutcome, CompareOutcome],
) -> None:
    request = compare_request(
        f"Çalışma Alanı ile Aile Yaşam Alanı için iki yaklaşım öner. {axes}",
        ["Çalışma Alanı", "Aile Yaşam Alanı"],
    )
    analysis = analyze_compare_request(request)
    plan = explicit_plan(*outcomes)
    validate_compare_plan(plan, request, analysis)
    result = render_compare_plan(plan, request, analysis)
    validate_rendered_compare(result, request)
    assert analysis.axes is not None
    assert analysis.axes[0] in result.assistant_message.casefold()
    assert analysis.axes[1] in result.assistant_message.casefold()
    assert result.assistant_message.count("Çalışma Alanı") == 2
    assert result.assistant_message.count("Aile Yaşam Alanı") == 2


def test_explicit_axes_rejects_swapped_approaches() -> None:
    request = compare_request(
        (
            "Ebeveyn Yatak Odası ile Giyinme Alanı için iki yaklaşım öner. "
            "Birinde mahremiyet, diğerinde kullanım kolaylığı daha baskın olsun."
        ),
        ["Ebeveyn Yatak Odası", "Giyinme Alanı"],
    )
    plan = explicit_plan().model_copy(
        update={
            "approach_1": CompareApproach.AXIS_2,
            "approach_2": CompareApproach.AXIS_1,
        }
    )
    with pytest.raises(ComparePlanValidationError) as captured:
        validate_compare_plan(plan, request, analyze_compare_request(request))
    assert captured.value.category is CompareFailureCategory.AXIS_MISMATCH


def test_entity_choice_uses_choice_names_only_when_selection_is_explicit() -> None:
    request = compare_request(
        "Salon kullanımını mı teras kullanımını mı öne çıkarmalıyım? İkisini karşılaştır.",
        ["Salon", "Teras"],
    )
    analysis = analyze_compare_request(request)
    plan = entity_choice_plan()
    validate_compare_plan(plan, request, analysis)
    result = render_compare_plan(plan, request, analysis)
    validate_rendered_compare(result, request)
    assert "Alternatif 1 - Salon:" in result.assistant_message
    assert "Alternatif 2 - Teras:" in result.assistant_message


def test_entity_choice_requires_distinct_outcomes() -> None:
    request = compare_request("Salon mu teras mı?", ["Salon", "Teras"])
    plan = entity_choice_plan().model_copy(update={"outcome_2": CompareOutcome.INDOOR_CONTINUITY})
    with pytest.raises(ComparePlanValidationError) as captured:
        validate_compare_plan(plan, request, analyze_compare_request(request))
    assert captured.value.category is CompareFailureCategory.ENTITY_CHOICE_MISMATCH


def test_dynamic_schema_makes_explicit_axis_order_unrepresentable() -> None:
    request = compare_request(
        (
            "Çalışma Alanı için iki kullanım yaklaşımı öner. Birinde bireysel çalışma, "
            "diğerinde iki kişinin birlikte çalışması önemli."
        ),
        ["Çalışma Alanı"],
    )
    analysis = analyze_compare_request(request)
    schema = build_compare_plan_schema(analysis)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    assert properties["approach_1"]["enum"] == ["axis_1"]
    assert properties["approach_2"]["enum"] == ["axis_2"]
    assert properties["outcome_1"]["enum"] == ["individual_productivity"]
    assert properties["outcome_2"]["enum"] == ["collaborative_productivity"]


@pytest.mark.parametrize(
    ("message", "names", "expected_outcomes"),
    [
        (
            "Açık mutfak mı kapalı mutfak mı?",
            ["Açık Mutfak", "Kapalı Mutfak"],
            (["open_shared_use"], ["separated_controlled_use"]),
        ),
        (
            "Salon mu teras mı?",
            ["Salon", "Teras"],
            (
                [
                    "indoor_continuity",
                    "outdoor_experience",
                    "open_shared_use",
                    "separated_controlled_use",
                    "focused_activity",
                    "shared_interaction",
                    "adaptable_daily_use",
                    "controlled_personal_use",
                ],
                [
                    "indoor_continuity",
                    "outdoor_experience",
                    "open_shared_use",
                    "separated_controlled_use",
                    "focused_activity",
                    "shared_interaction",
                    "adaptable_daily_use",
                    "controlled_personal_use",
                ],
            ),
        ),
    ],
)
def test_dynamic_schema_constrains_entity_choice_without_public_text(
    message: str,
    names: list[str],
    expected_outcomes: tuple[list[str], list[str]],
) -> None:
    schema = build_compare_plan_schema(analyze_compare_request(compare_request(message, names)))
    properties = schema["properties"]
    assert isinstance(properties, dict)
    assert properties["approach_1"]["enum"] == ["choice_1"]
    assert properties["approach_2"]["enum"] == ["choice_2"]
    assert properties["outcome_1"]["enum"] == expected_outcomes[0]
    assert properties["outcome_2"]["enum"] == expected_outcomes[1]


def test_trusted_immediate_neighbor_relation_is_preserved_without_new_geometry() -> None:
    request = compare_request(
        "Teras salonun hemen yanında olsun. Bu ilişkiyi koruyan iki yaklaşım öner.",
        ["Teras", "Salon"],
    )
    analysis = analyze_compare_request(request)
    plan = open_plan()
    validate_compare_plan(plan, request, analysis)
    result = render_compare_plan(plan, request, analysis)
    validate_rendered_compare(result, request)
    assert result.assistant_message.count("hemen yanında") == 2


def test_rendered_compare_keeps_public_contract_invariants() -> None:
    request = compare_request(
        "Kütüphane ile Okuma Salonu için iki alternatif öner.",
        ["Kütüphane", "Okuma Salonu"],
    )
    analysis = analyze_compare_request(request)
    result = render_compare_plan(open_plan(), request, analysis)
    assert result.intent.value == "compare_alternatives"
    assert result.target.model_dump() == {
        "project_id": None,
        "building_id": None,
        "level_id": None,
        "zone_id": None,
        "entity_id": None,
    }
    assert result.user_requirements == []
    assert result.proposed_actions == []
    assert result.needs_user_confirmation is False
    assert result.needs_follow_up is False
    assert result.follow_up_question is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Akıcı günlük kullanım", "kullanım kolaylığı"),
        ("Kişisel hazırlık daha kontrollü", "mahremiyet"),
        ("Yalın bir anlatım", "sadelik"),
        ("Fikir paylaşımı", "birlikte çalışma"),
    ],
)
def test_semantic_token_families_generalize_without_embeddings(text: str, expected: str) -> None:
    assert semantic_match(text, expected)
