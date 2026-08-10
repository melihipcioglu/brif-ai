from __future__ import annotations

import pytest

from brif_ai.llm.contracts import (
    ActiveContextSnapshot,
    ArchitecturalIntentResult,
    ConversationRequest,
    VisibleEntity,
)
from brif_ai.llm.policy_validator import (
    AlternativeQualityError,
    ArchitecturalIntentPolicyValidator,
    PolicyValidationError,
    UnsupportedSpatialClaimError,
    validate_spatial_direction_claims,
)

from .test_contracts import valid_result_data

INTERNAL_ID_PREFIXES = (
    "space_",
    "project_",
    "building_",
    "block_",
    "level_",
    "lvl_",
    "zone_",
    "entity_",
)


def conversation_request(*, entity_id: str | None = "space_study") -> ConversationRequest:
    return ConversationRequest(
        message="Bu odayı biraz büyüt.",
        active_context=ActiveContextSnapshot(
            project_id="proj_house_2story",
            building_id="bldg_main",
            level_id="lvl_ground",
            zone_id="zone_living",
            entity_id=entity_id,
            context_fingerprint="house|main|ground|living|study",
            generation_id=4,
        ),
        visible_entities=[
            VisibleEntity(
                entity_id="space_study",
                entity_type="space",
                name="Çalışma Odası",
                project_id="proj_house_2story",
                building_id="bldg_main",
                level_id="lvl_ground",
                zone_id="zone_living",
            )
        ],
    )


def request_with_master_bathroom() -> ConversationRequest:
    request = conversation_request()
    return request.model_copy(
        update={
            "visible_entities": [
                *request.visible_entities,
                VisibleEntity(
                    entity_id="space_master_bathroom",
                    entity_type="space",
                    name="Ebeveyn Banyosu",
                    project_id="proj_house_2story",
                    building_id="bldg_main",
                    level_id="lvl_ground",
                    zone_id="zone_living",
                ),
            ]
        }
    )


def public_texts(result: ArchitecturalIntentResult) -> list[str]:
    return [
        result.assistant_message,
        result.follow_up_question or "",
        *result.user_requirements,
        *result.interpreted_priorities,
        *result.constraints_to_check,
        *result.missing_information,
        *result.warnings,
        *(action.description for action in result.proposed_actions),
    ]


def assert_no_internal_ids(result: ArchitecturalIntentResult) -> None:
    combined = "\n".join(public_texts(result)).casefold()
    assert all(prefix not in combined for prefix in INTERNAL_ID_PREFIXES)


def result() -> ArchitecturalIntentResult:
    return ArchitecturalIntentResult.model_validate(valid_result_data())


def test_visible_entities_outside_entity_id_rejected() -> None:
    data = valid_result_data()
    target = data["target"]
    assert isinstance(target, dict)
    target["entity_id"] = "space_hallucinated"
    actions = data["proposed_actions"]
    assert isinstance(actions, list)
    actions[0]["target_entity_id"] = "space_hallucinated"

    with pytest.raises(PolicyValidationError, match="visible_entities"):
        ArchitecturalIntentPolicyValidator().validate(
            ArchitecturalIntentResult.model_validate(data), conversation_request()
        )


def test_foreign_scope_entity_is_not_made_visible_by_client_payload() -> None:
    data = valid_result_data()
    target = data["target"]
    assert isinstance(target, dict)
    target["entity_id"] = "space_foreign"
    actions = data["proposed_actions"]
    assert isinstance(actions, list)
    actions[0]["target_entity_id"] = "space_foreign"
    request = conversation_request().model_copy(
        update={
            "visible_entities": [
                VisibleEntity(
                    entity_id="space_foreign",
                    entity_type="space",
                    name="Foreign Space",
                    project_id="proj_tower_50floor",
                    building_id="tower_a",
                    level_id="lvl_32",
                    zone_id="zone_ops_32",
                )
            ]
        }
    )

    with pytest.raises(PolicyValidationError, match="visible_entities"):
        ArchitecturalIntentPolicyValidator().validate(
            ArchitecturalIntentResult.model_validate(data), request
        )


def test_other_project_id_rejected() -> None:
    data = valid_result_data()
    target = data["target"]
    assert isinstance(target, dict)
    target["project_id"] = "proj_tower_50floor"

    with pytest.raises(PolicyValidationError, match="project_id"):
        ArchitecturalIntentPolicyValidator().validate(
            ArchitecturalIntentResult.model_validate(data), conversation_request()
        )


def test_other_level_id_rejected() -> None:
    data = valid_result_data()
    target = data["target"]
    assert isinstance(target, dict)
    target["level_id"] = "lvl_32"

    with pytest.raises(PolicyValidationError, match="level_id"):
        ArchitecturalIntentPolicyValidator().validate(
            ArchitecturalIntentResult.model_validate(data), conversation_request()
        )


def test_ambiguous_modification_forces_follow_up() -> None:
    data = valid_result_data()
    data["target"] = {
        "project_id": "proj_house_2story",
        "building_id": "bldg_main",
        "level_id": "lvl_ground",
        "zone_id": "zone_living",
        "entity_id": None,
    }
    data["proposed_actions"] = []
    data["needs_user_confirmation"] = False
    safe_result = ArchitecturalIntentPolicyValidator().validate(
        ArchitecturalIntentResult.model_validate(data),
        conversation_request(entity_id=None),
    )

    assert safe_result.needs_follow_up is True
    assert safe_result.follow_up_question


def test_confidence_does_not_override_scope_policy() -> None:
    data = valid_result_data()
    data["confidence"] = 1.0
    target = data["target"]
    assert isinstance(target, dict)
    target["project_id"] = "invented_project"

    with pytest.raises(PolicyValidationError):
        ArchitecturalIntentPolicyValidator().validate(
            ArchitecturalIntentResult.model_validate(data), conversation_request()
        )


def test_relationship_request_is_normalized_from_full_sentence() -> None:
    data = valid_result_data()
    data["intent"] = "request_visual_preference"
    request = conversation_request().model_copy(
        update={"message": "Ebeveyn banyosu yataktan görünmesin ve kuzey tarafında olsun."}
    )

    safe_result = ArchitecturalIntentPolicyValidator().validate(
        ArchitecturalIntentResult.model_validate(data), request
    )

    assert safe_result.intent.value == "modify_relationship"


def test_material_and_color_request_remains_visual_preference() -> None:
    data = valid_result_data()
    data.update(
        {
            "assistant_message": "Açık meşe ve sıcak beyaz tonlarını değerlendirebilirim.",
            "intent": "request_visual_preference",
            "user_requirements": ["Açık meşe ve sıcak beyaz tonları."],
            "interpreted_priorities": ["sıcak atmosfer"],
            "constraints_to_check": [],
        }
    )
    request = conversation_request().model_copy(
        update={"message": "Çalışma odasında açık meşe ve sıcak beyaz tonları istiyorum."}
    )

    safe_result = ArchitecturalIntentPolicyValidator().validate(
        ArchitecturalIntentResult.model_validate(data), request
    )

    assert safe_result.intent.value == "request_visual_preference"


@pytest.mark.parametrize(
    "public_field",
    [
        "assistant_message",
        "follow_up_question",
        "warning",
        "action_description",
        "constraint",
        "missing_information",
    ],
)
def test_internal_id_is_removed_from_each_public_response_field(
    public_field: str,
) -> None:
    data = valid_result_data()
    leaked_text = "space_master_bedroom için değerlendirme yapalım."
    if public_field == "assistant_message":
        data["assistant_message"] = leaked_text
    elif public_field == "follow_up_question":
        data["needs_follow_up"] = True
        data["follow_up_question"] = leaked_text
    elif public_field == "warning":
        data["warnings"] = [leaked_text]
    elif public_field == "action_description":
        actions = data["proposed_actions"]
        assert isinstance(actions, list)
        actions[0]["description"] = leaked_text
    elif public_field == "constraint":
        data["constraints_to_check"] = [leaked_text]
    else:
        data["missing_information"] = [leaked_text]

    safe_result = ArchitecturalIntentPolicyValidator().validate(
        ArchitecturalIntentResult.model_validate(data), conversation_request()
    )

    assert_no_internal_ids(safe_result)


def test_follow_up_question_is_cleared_when_follow_up_is_not_needed() -> None:
    data = valid_result_data()
    data["needs_follow_up"] = False
    data["follow_up_question"] = "Bu soru kullanıcıya gösterilmemeli."

    safe_result = ArchitecturalIntentPolicyValidator().validate(
        ArchitecturalIntentResult.model_validate(data), conversation_request()
    )

    assert safe_result.needs_follow_up is False
    assert safe_result.follow_up_question is None


@pytest.mark.parametrize(
    "public_field",
    [
        "assistant_message",
        "follow_up_question",
        "user_requirement",
        "interpreted_priority",
        "constraint",
        "missing_information",
        "warning",
        "action_description",
    ],
)
def test_internal_technical_terms_are_localized_in_each_public_response_field(
    public_field: str,
) -> None:
    data = valid_result_data()
    leaked_text = (
        "pending_proposals içinde modify_space için contextFingerprint ve generationId "
        "takip ediliyor."
    )
    if public_field == "assistant_message":
        data["assistant_message"] = leaked_text
    elif public_field == "follow_up_question":
        data["needs_follow_up"] = True
        data["follow_up_question"] = leaked_text
    elif public_field == "user_requirement":
        data["user_requirements"] = [leaked_text]
    elif public_field == "interpreted_priority":
        data["interpreted_priorities"] = [leaked_text]
    elif public_field == "constraint":
        data["constraints_to_check"] = [leaked_text]
    elif public_field == "missing_information":
        data["missing_information"] = [leaked_text]
    elif public_field == "warning":
        data["warnings"] = [leaked_text]
    else:
        actions = data["proposed_actions"]
        assert isinstance(actions, list)
        actions[0]["description"] = leaked_text

    safe_result = ArchitecturalIntentPolicyValidator().validate(
        ArchitecturalIntentResult.model_validate(data), conversation_request()
    )

    combined = "\n".join(public_texts(safe_result))
    combined_casefolded = combined.casefold()
    assert "pending_proposals" not in combined_casefolded
    assert "modify_space" not in combined_casefolded
    assert "contextfingerprint" not in combined_casefolded
    assert "generationid" not in combined_casefolded
    assert "bekleyen öneriler" in combined_casefolded
    assert "mekân düzenleme önerisi" in combined_casefolded
    assert "bağlam bilgisi" in combined_casefolded
    assert "bağlam sürümü" in combined_casefolded


@pytest.mark.parametrize(
    ("internal_term", "natural_phrase"),
    [
        ("pendingProposals", "bekleyen öneriler"),
        ("proposed_actions", "önerilen adımlar"),
        ("modifyRelationship", "mekânsal ilişki düzenleme önerisi"),
        ("active_context", "aktif bağlam"),
        ("targetEntityId", "mekân bilgisi"),
        ("requires_user_confirmation", "kullanıcı onayı gerekiyor"),
        ("followUpQuestion", "takip sorusu"),
        ("request_visual_preference", "görsel tercih talebi"),
    ],
)
def test_related_internal_terms_are_localized(
    internal_term: str,
    natural_phrase: str,
) -> None:
    data = valid_result_data()
    data["assistant_message"] = f"{internal_term} kullanıcıya gösterilmemeli."

    safe_result = ArchitecturalIntentPolicyValidator().validate(
        ArchitecturalIntentResult.model_validate(data), conversation_request()
    )

    assert internal_term.casefold() not in safe_result.assistant_message.casefold()
    assert natural_phrase in safe_result.assistant_message.casefold()


def test_visible_entity_id_is_replaced_with_natural_name() -> None:
    data = valid_result_data()
    data["assistant_message"] = "space_master_bathroom için mahremiyet önerisi hazırlayabilirim."

    safe_result = ArchitecturalIntentPolicyValidator().validate(
        ArchitecturalIntentResult.model_validate(data),
        request_with_master_bathroom(),
    )

    assert "Ebeveyn Banyosu" in safe_result.assistant_message
    assert_no_internal_ids(safe_result)


def test_unmatched_internal_ids_use_safe_natural_fallbacks() -> None:
    data = valid_result_data()
    data["warnings"] = [
        (
            "space_unknown_room project_unknown building_unknown block_unknown "
            "level_unknown lvl_unknown zone_unknown entity_unknown"
        )
    ]

    safe_result = ArchitecturalIntentPolicyValidator().validate(
        ArchitecturalIntentResult.model_validate(data), conversation_request()
    )

    assert "mekân" in safe_result.warnings[0]
    assert_no_internal_ids(safe_result)


def test_machine_target_id_is_preserved_while_public_text_is_sanitized() -> None:
    data = valid_result_data()
    data["assistant_message"] = "space_study için öneri hazırlayabilirim."

    safe_result = ArchitecturalIntentPolicyValidator().validate(
        ArchitecturalIntentResult.model_validate(data), conversation_request()
    )

    assert safe_result.target.entity_id == "space_study"
    assert safe_result.proposed_actions[0].target_entity_id == "space_study"
    assert "Çalışma Odası" in safe_result.assistant_message
    assert_no_internal_ids(safe_result)


def test_conceptual_space_alternatives_regression() -> None:
    request_msg = (
        "Terası gün ışığı alan günlük oturma ve sohbet alanı olarak kullanmak istiyorum. "
        "Salon, mutfak, teras ve giriş için iki farklı düzenleme alternatifini "
        "ayrıntılı şekilde sun."
    )
    req = conversation_request().model_copy(update={"message": request_msg})

    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": (
                "Alternatif 1 — Açık Geçiş Planı: Girişten salon algılanır; mutfak "
                "salonun yanında kalır ve terasa bağlanarak sohbet alanına katılır.\n\n"
                "Alternatif 2 — Bağımsız Hol Kurgusu: Giriş sirkülasyon holüne açılır; "
                "mutfak terasa doğrudan bağlanır, salon sakin kalır.\n\n"
                "Temel fark: Alternatif 1 açık düzen sunarken Alternatif 2 bağımsız hol sağlar."
            ),
            "user_requirements": [
                "Terasın gün ışığı alan oturma ve sohbet alanı olarak kullanılması"
            ],
            "interpreted_priorities": [
                "Salon, mutfak, teras ve giriş ilişki alternatiflerinin sunulması"
            ],
            "constraints_to_check": ["Terasın oryantasyonu ve ışık alımı"],
            "missing_information": [],
            "proposed_actions": [],
            "needs_user_confirmation": False,
            "needs_follow_up": False,
            "follow_up_question": None,
            "warnings": [],
            "target": {
                "project_id": None,
                "building_id": None,
                "level_id": None,
                "zone_id": None,
                "entity_id": None,
            },
        }
    )

    validator = ArchitecturalIntentPolicyValidator()
    validator.validate_semantic_integrity(ArchitecturalIntentResult.model_validate(data), req)

    safe_result = validator.validate(ArchitecturalIntentResult.model_validate(data), req)

    assert safe_result.intent.value == "compare_alternatives"
    assert safe_result.needs_follow_up is False
    assert safe_result.follow_up_question is None
    assert safe_result.proposed_actions == []
    assert safe_result.target.entity_id is None
    assert "Alternatif 1" in safe_result.assistant_message
    assert "Alternatif 2" in safe_result.assistant_message
    for space in ("salon", "mutfak", "teras", "giriş"):
        assert space in safe_result.assistant_message.casefold()
    for forbidden in ("öğe bilgisi", "entity", "ilgili mekân", "visible_entities"):
        assert forbidden not in safe_result.assistant_message.casefold()


@pytest.mark.parametrize(
    "forbidden_word",
    [
        "entity",
        "entity_id",
        "target",
        "enum",
        "öğe bilgisi",
        "ilgili mekân",
        "visible_entities",
        "aktif kapsam kimliği",
    ],
)
def test_semantic_validation_rejects_forbidden_internal_words(
    forbidden_word: str,
) -> None:
    data = valid_result_data()
    data["assistant_message"] = f"Plan üzerinde {forbidden_word} incelemesi tamamlandı."

    validator = ArchitecturalIntentPolicyValidator()
    with pytest.raises(PolicyValidationError, match="İç sistem dili"):
        validator.validate_semantic_integrity(
            ArchitecturalIntentResult.model_validate(data), conversation_request()
        )


def test_semantic_validation_rejects_single_alternative_on_comparison_request() -> None:
    req = conversation_request().model_copy(
        update={"message": "Salon ve mutfak için iki farklı düzenleme alternatifi sun."}
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": "Yalnızca tek bir alternatif değerlendirildi.",
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )

    validator = ArchitecturalIntentPolicyValidator()
    with pytest.raises(PolicyValidationError, match="Alternatif 1|bölümlerini içermelidir"):
        validator.validate_semantic_integrity(ArchitecturalIntentResult.model_validate(data), req)


@pytest.mark.parametrize(
    "unsupported_word",
    ["doğusunda", "güneyinde", "kuzeye", "batı cephesinde"],
)
def test_unsupported_spatial_claim_rejected_when_absent_from_context(unsupported_word: str) -> None:
    req = conversation_request()
    data = valid_result_data()
    data["assistant_message"] = f"Teras {unsupported_word} konumlandırılmıştır."

    validator = ArchitecturalIntentPolicyValidator()
    with pytest.raises(UnsupportedSpatialClaimError, match="yön bilgisi"):
        validator.validate_semantic_integrity(ArchitecturalIntentResult.model_validate(data), req)


def test_dogrudan_connection_is_not_false_positive_for_dogu() -> None:
    req = conversation_request()
    data = valid_result_data()
    data["assistant_message"] = "Salon ve mutfak arasındaki ilişki doğrudan güçlendirilir."

    validate_spatial_direction_claims(ArchitecturalIntentResult.model_validate(data), req)


def test_direction_allowed_when_present_in_user_message() -> None:
    req = conversation_request().model_copy(update={"message": "Teras güneyde yer alsın."})
    data = valid_result_data()
    data["assistant_message"] = "Teras güney cephesinde düzenlenmiştir."

    validator = ArchitecturalIntentPolicyValidator()
    validator.validate_semantic_integrity(ArchitecturalIntentResult.model_validate(data), req)


def test_direction_allowed_when_present_in_conversation_summary() -> None:
    req = conversation_request().model_copy(
        update={"conversation_summary": "user: Kuzeye bakan bir teras istiyorum."}
    )
    data = valid_result_data()
    data["assistant_message"] = "Kuzey alanında açık teras kurgulandı."

    validator = ArchitecturalIntentPolicyValidator()
    validator.validate_semantic_integrity(ArchitecturalIntentResult.model_validate(data), req)


def test_direction_allowed_when_present_in_current_decisions() -> None:
    req = conversation_request().model_copy(
        update={"current_decisions": ["Terasın batıda olmasına karar verildi."]}
    )
    data = valid_result_data()
    data["assistant_message"] = "Batı tarafındaki teras alanı korundu."

    validator = ArchitecturalIntentPolicyValidator()
    validator.validate_semantic_integrity(ArchitecturalIntentResult.model_validate(data), req)


def test_direction_allowed_when_present_in_pending_proposals() -> None:
    req = conversation_request().model_copy(
        update={
            "pending_proposals": [
                {
                    "status": "pending_user_confirmation",
                    "context_fingerprint": "house|main|ground|living|study",
                    "generation_id": 4,
                    "action": {
                        "action_type": "suggest_relationship_change",
                        "target_entity_id": "space_study",
                        "description": "Çalışma odasını doğu kanadına al.",
                        "requires_user_confirmation": True,
                    },
                }
            ]
        }
    )
    data = valid_result_data()
    data["assistant_message"] = "Doğusunda yer alan alan onay bekliyor."

    validator = ArchitecturalIntentPolicyValidator()
    validator.validate_semantic_integrity(ArchitecturalIntentResult.model_validate(data), req)


def test_direction_allowed_when_present_in_visible_entity_name() -> None:
    req = conversation_request().model_copy(
        update={
            "visible_entities": [
                VisibleEntity(
                    entity_id="space_terrace",
                    entity_type="space",
                    name="Güney Terası",
                    project_id="proj_house_2story",
                    building_id="bldg_main",
                    level_id="lvl_ground",
                    zone_id="zone_living",
                )
            ]
        }
    )
    data = valid_result_data()
    data["assistant_message"] = "Güney alanındaki kullanım değerlendirildi."

    validator = ArchitecturalIntentPolicyValidator()
    validator.validate_semantic_integrity(ArchitecturalIntentResult.model_validate(data), req)


@pytest.mark.parametrize("field_name", ["warnings", "user_requirements", "missing_information"])
def test_unsupported_direction_detected_in_other_public_fields(field_name: str) -> None:
    req = conversation_request()
    data = valid_result_data()
    data[field_name] = ["Planın batı kısmında belirsizlik var."]

    validator = ArchitecturalIntentPolicyValidator()
    with pytest.raises(UnsupportedSpatialClaimError, match="yön bilgisi"):
        validator.validate_semantic_integrity(ArchitecturalIntentResult.model_validate(data), req)


def test_unsupported_direction_detected_in_proposed_action_description() -> None:
    req = conversation_request()
    data = valid_result_data()
    data["proposed_actions"] = [
        {
            "action_type": "suggest_relationship_change",
            "target_entity_id": "space_study",
            "description": "Terası kuzey tarafına taşı.",
            "requires_user_confirmation": True,
        }
    ]

    validator = ArchitecturalIntentPolicyValidator()
    with pytest.raises(UnsupportedSpatialClaimError, match="yön bilgisi"):
        validator.validate_semantic_integrity(ArchitecturalIntentResult.model_validate(data), req)


def test_sanitize_removes_target_from_assistant_message() -> None:
    req = conversation_request()
    data = valid_result_data()
    data["assistant_message"] = "Plan üzerinde target alanı düzenlenmiştir."
    result = ArchitecturalIntentResult.model_validate(data)

    sanitized = ArchitecturalIntentPolicyValidator().sanitize(result, req)
    assert "target" not in sanitized.assistant_message.casefold()
    assert "hedef" in sanitized.assistant_message.casefold()


def test_sanitize_removes_entity_id_from_warnings() -> None:
    req = conversation_request()
    data = valid_result_data()
    data["warnings"] = ["Aktif kapsamda entity_id bilgisi bulunamadı."]
    result = ArchitecturalIntentResult.model_validate(data)

    sanitized = ArchitecturalIntentPolicyValidator().sanitize(result, req)
    assert "entity_id" not in " ".join(sanitized.warnings).casefold()
    assert "mekân bilgisi" in " ".join(sanitized.warnings).casefold()


def test_sanitize_neutralizes_unsupported_salonun_dogusunda() -> None:
    req = conversation_request()
    data = valid_result_data()
    data["assistant_message"] = "Teras salonun doğusundadır."
    result = ArchitecturalIntentResult.model_validate(data)

    sanitized = ArchitecturalIntentPolicyValidator().sanitize(result, req)
    assert "doğusunda" not in sanitized.assistant_message.casefold()
    assert "doğu" not in sanitized.assistant_message.casefold()
    assert "ilişkili" in sanitized.assistant_message.casefold()


def test_sanitize_neutralizes_unsupported_ortak_alanin_guneyinde() -> None:
    req = conversation_request()
    data = valid_result_data()
    data["assistant_message"] = "Oturma köşesi ortak alanın güneyinde kalmaktadır."
    result = ArchitecturalIntentResult.model_validate(data)

    sanitized = ArchitecturalIntentPolicyValidator().sanitize(result, req)
    assert "güneyinde" not in sanitized.assistant_message.casefold()
    assert "güney" not in sanitized.assistant_message.casefold()
    assert "ilişkili" in sanitized.assistant_message.casefold()


def test_sanitize_preserves_dogrudan_baglanti() -> None:
    req = conversation_request()
    data = valid_result_data()
    data["assistant_message"] = "Salon ile mutfak arasında doğrudan bağlantı kurulmalıdır."
    result = ArchitecturalIntentResult.model_validate(data)

    sanitized = ArchitecturalIntentPolicyValidator().sanitize(result, req)
    assert "doğrudan bağlantı" in sanitized.assistant_message.casefold()


def test_sanitize_does_not_neutralize_direction_present_in_request_message() -> None:
    req = conversation_request().model_copy(update={"message": "Güney cephesinde teras istiyorum."})
    data = valid_result_data()
    data["assistant_message"] = "Güney cephesinde teras planlandı."
    result = ArchitecturalIntentResult.model_validate(data)

    sanitized = ArchitecturalIntentPolicyValidator().sanitize(result, req)
    assert "güney" in sanitized.assistant_message.casefold()


def test_sanitization_allows_semantic_validation_to_pass() -> None:
    req = conversation_request()
    data = valid_result_data()
    data["assistant_message"] = "Plan için target alanı ve teras salonun doğusundadır."
    result = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(result, req)
    validator.validate_semantic_integrity(sanitized, req)

    assert "target" not in sanitized.assistant_message.casefold()
    assert "doğusunda" not in sanitized.assistant_message.casefold()


def test_sanitization_preserves_structured_target_fields() -> None:
    req = conversation_request()
    data = valid_result_data()
    data["assistant_message"] = "target nesnesi incelendi."
    data["target"] = {
        "project_id": "proj_house_2story",
        "building_id": "bldg_main",
        "level_id": "lvl_ground",
        "zone_id": "zone_living",
        "entity_id": "space_living",
    }
    result = ArchitecturalIntentResult.model_validate(data)

    sanitized = ArchitecturalIntentPolicyValidator().sanitize(result, req)
    assert sanitized.target.entity_id == "space_living"
    assert sanitized.target.project_id == "proj_house_2story"
    assert "target nesnesi" not in sanitized.assistant_message


def test_compare_alternatives_quality_accepts_distinct_valid_alternatives() -> None:
    req = conversation_request().model_copy(
        update={"message": "Salon ve mutfak için iki farklı düzenleme alternatifi sun."}
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": (
                "Alternatif 1 — Açık Bölüntü Planı: Salon ve mutfak arasındaki "
                "seperatör kaldırılarak geniş bir adalı tezgah eklenir.\n\n"
                "Alternatif 2 — Şeffaf Geçiş Kurgusu: Salon ve mutfak arasına temperli "
                "cam kayar kapı eklenerek mahremiyet korunur.\n\n"
                "Temel fark: Alternatif 1 kesintisiz bütünsellik sağlarken "
                "Alternatif 2 esnek bölüntü olanağı sunar."
            ),
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    result = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(result, req)
    validator.validate_semantic_integrity(sanitized, req)


def test_compare_alternatives_rejects_identical_alternatives() -> None:
    req = conversation_request().model_copy(
        update={"message": "Salon ve mutfak için iki farklı düzenleme alternatifi sun."}
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": (
                "Alternatif 1 — Aynı Düzen: Salon ve mutfak arasında kapı kurgulanır.\n"
                "Alternatif 2 — Aynı Düzen: Salon ve mutfak arasında kapı kurgulanır.\n"
                "Temel fark: İki alternatif arasında fark yoktur."
            ),
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    result = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(result, req)
    with pytest.raises(AlternativeQualityError, match="yeterince farklı değil"):
        validator.validate_semantic_integrity(sanitized, req)


def test_compare_alternatives_rejects_minor_word_swap_repetitions() -> None:
    req = conversation_request().model_copy(
        update={"message": "Salon ve mutfak için iki farklı düzenleme alternatifi sun."}
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": (
                "Alternatif 1 — Bölüntü: Salon ve mutfak arasına şeffaf bölüntü konur.\n"
                "Alternatif 2 — Bölüntü: Salon ve mutfak arasına şeffaf bölüntü konacaktır.\n"
                "Temel fark: İki alternatif benzerdir."
            ),
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    result = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(result, req)
    with pytest.raises(AlternativeQualityError, match="yeterince farklı değil"):
        validator.validate_semantic_integrity(sanitized, req)


def test_compare_alternatives_rejects_missing_key_difference() -> None:
    req = conversation_request().model_copy(
        update={"message": "Salon ve mutfak için iki farklı düzenleme alternatifi sun."}
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": (
                "Alternatif 1 — Açık Plan: Salon ve mutfak birleştirilir.\n"
                "Alternatif 2 — Kapalı Plan: Salon ve mutfak ayrılır."
            ),
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    result = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(result, req)
    with pytest.raises(AlternativeQualityError, match="Temel fark"):
        validator.validate_semantic_integrity(sanitized, req)


def test_compare_alternatives_rejects_empty_alternative_content() -> None:
    req = conversation_request().model_copy(
        update={"message": "Salon ve mutfak için iki farklı düzenleme alternatifi sun."}
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": (
                "Alternatif 1 — Açık Plan: \n"
                "Alternatif 2 — Kapalı Plan: Mutfak ile salon arasında kapı yerleştirilir.\n"
                "Temel fark: Açık ve kapalı mekân farkıdır."
            ),
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    result = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(result, req)
    with pytest.raises(AlternativeQualityError, match="boş kalmamalıdır|çok kısa"):
        validator.validate_semantic_integrity(sanitized, req)


def test_compare_alternatives_rejects_too_short_alternative() -> None:
    req = conversation_request().model_copy(
        update={"message": "Salon ve mutfak için iki farklı düzenleme alternatifi sun."}
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": (
                "Alternatif 1 — Kısa: Kapı eklenir.\n"
                "Alternatif 2 — Kapalı Plan: Mutfak ile salon arasında cam kapı kurgulanır.\n"
                "Temel fark: Geçiş türüdür."
            ),
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    result = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(result, req)
    with pytest.raises(AlternativeQualityError, match="çok kısa"):
        validator.validate_semantic_integrity(sanitized, req)


def test_compare_alternatives_rejects_too_long_alternative() -> None:
    req = conversation_request().model_copy(
        update={"message": "Salon ve mutfak için iki farklı düzenleme alternatifi sun."}
    )
    long_text = " ".join(["detay"] * 75)
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": (
                f"Alternatif 1 — Uzun: {long_text}\n"
                "Alternatif 2 — Normal Plan: Mutfak ile salon arasında cam kapı kurgulanır.\n"
                "Temel fark: Detay seviyesidir."
            ),
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    result = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(result, req)
    with pytest.raises(AlternativeQualityError, match="çok uzun"):
        validator.validate_semantic_integrity(sanitized, req)


def test_compare_alternatives_rejects_repeated_filler_phrase() -> None:
    req = conversation_request().model_copy(
        update={"message": "Salon ve mutfak için iki farklı düzenleme alternatifi sun."}
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": (
                "Alternatif 1 — Açık Plan: Mutfak ile salon geniş kapıyla yakın "
                "bir konumda kurgulanır. Sosyal etkileşim artar.\n"
                "Alternatif 2 — Kapalı Plan: Teras ile oturma bölümü cam panelle "
                "yakın bir konumda kurgulanır. Ses yalıtımı sağlanır.\n"
                "Temel fark: Bölücü unsur türü ve mekan ayrımıdır."
            ),
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    result = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    with pytest.raises(AlternativeQualityError, match="Yapay dolgu ifadesi"):
        validator.validate_semantic_integrity(result, req)


def test_compare_alternatives_does_not_false_positive_on_shared_prompt_words() -> None:
    req = conversation_request().model_copy(
        update={
            "message": "Salon ile mutfak arasındaki ilişkiyi güçlendirmek için alternatif öner."
        }
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": (
                "Alternatif 1 — Ada Tezgah: Salon ve mutfağa ada kurgulanır.\n"
                "Alternatif 2 — Sürgü Cam: Akustik cam panel eklenir.\n"
                "Temel fark: Alternatif 1 açık alan sunarken Alternatif 2 yalıtım sağlar."
            ),
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    result = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(result, req)
    validator.validate_semantic_integrity(sanitized, req)


def test_other_intents_are_not_affected_by_alternative_quality_checks() -> None:
    req = conversation_request().model_copy(
        update={"message": "Salon ile mutfak arasına kapı ekle."}
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "modify_relationship",
            "assistant_message": "Salon ile mutfak arasında geçiş kapısı planlandı.",
        }
    )
    result = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(result, req)
    validator.validate_semantic_integrity(sanitized, req)


def test_compare_alternatives_accepts_open_integration_vs_controlled_separation() -> None:
    req = conversation_request().model_copy(
        update={
            "message": (
                "Salon ile mutfak arasındaki ilişkiyi güçlendirmek istiyorum. "
                "Teras da günlük oturma ve sohbet alanına yakın olsun. "
                "Bana iki farklı düzenleme alternatifi öner."
            )
        }
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": (
                "Alternatif 1 — Açık bütünleşme: Salon ve mutfak günlük kullanımda daha güçlü "
                "görsel ilişki kurar. Teras ortak yaşamın devamı olarak ele alınır.\n\n"
                "Alternatif 2 — Kontrollü ayrışma: Salon ve mutfak ilişkisi korunur ancak "
                "ayrışabilecek kurgu düşünülür. Teras ortak buluşma alanı olur.\n\n"
                "Temel fark: Birinci yaklaşım sürekliliği, ikinci yaklaşım esnekliği öne çıkarır."
            ),
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    result = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(result, req)
    validator.validate_semantic_integrity(sanitized, req)


def test_unsupported_relative_spatial_claims_are_rejected_or_sanitized() -> None:
    req = conversation_request()
    validator = ArchitecturalIntentPolicyValidator()

    unsupported_examples = [
        "Salon girişten sonra sağ tarafta yer alır.",
        "Mutfak salonun solundadır.",
        "Teras salonun karşısında yer alır.",
        "Salon ile teras ortak kenar paylaşır.",
        "Mutfak salonla ortak duvar paylaşır.",
        "Teras salona bitişiktir.",
        "Mutfak girişin hemen yanında yer alır.",
        "Salon ve mutfak ortak bir duvarla birleşir.",
        "Salon ile mutfak ortak bir duvar paylaşır.",
        "Salon ile mutfak aynı duvarı paylaşır.",
        "Salon ile mutfak bir duvarı paylaşır.",
    ]

    for text in unsupported_examples:
        data = valid_result_data()
        data["assistant_message"] = text
        res = ArchitecturalIntentResult.model_validate(data)
        sanitized = validator.sanitize(res, req)
        for claim in [
            "sağ tarafta",
            "solundadır",
            "karşısında yer alır",
            "ortak kenar",
            "ortak duvar",
            "ortak bir duvar",
            "aynı duvarı",
            "bir duvarı",
            "bitişiktir",
            "hemen yanında",
        ]:
            assert claim not in sanitized.assistant_message


def test_shared_wall_false_positives_not_flagged() -> None:
    req = conversation_request()
    validator = ArchitecturalIntentPolicyValidator()

    false_positive_examples = [
        "Duvar kalınlığı daha sonra belirlenecek.",
        "Duvar yüzeyi için malzeme seçilebilir.",
        "Duvar rengi henüz belirlenmedi.",
    ]

    for text in false_positive_examples:
        data = valid_result_data()
        data["assistant_message"] = text
        res = ArchitecturalIntentResult.model_validate(data)
        sanitized = validator.sanitize(res, req)
        validator.validate_semantic_integrity(sanitized, req)
        assert sanitized.assistant_message == text


def test_trusted_relative_spatial_claims_are_accepted() -> None:
    req = conversation_request().model_copy(
        update={"message": "Mutfak salonun solunda yer alsın ve terasla ortak kenar paylaşsın."}
    )
    data = valid_result_data()
    data["assistant_message"] = (
        "Mutfak salonun solunda yer alabilir ve terasla ortak kenar kurgulanabilir."
    )
    res = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(res, req)
    validator.validate_semantic_integrity(sanitized, req)
    assert "solunda" in sanitized.assistant_message.casefold()


def test_trusted_shared_wall_claim_accepted() -> None:
    req = conversation_request().model_copy(
        update={"message": "Salon ile mutfak aynı duvarı paylaşıyor."}
    )
    data = valid_result_data()
    data["assistant_message"] = "Salon ile mutfak aynı duvarı paylaşacak biçimde ele alınabilir."
    res = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(res, req)
    validator.validate_semantic_integrity(sanitized, req)
    assert "aynı duvarı" in sanitized.assistant_message.casefold()


def test_conceptual_relative_suggestions_are_accepted() -> None:
    req = conversation_request()
    data = valid_result_data()
    data["assistant_message"] = "Salon ve mutfak arasındaki geçiş daha açık kurulabilir."
    res = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize(res, req)
    validator.validate_semantic_integrity(sanitized, req)


def test_regression_failed_real_model_output_relative_spatial_claim() -> None:
    req = conversation_request().model_copy(
        update={
            "message": (
                "Salon ile mutfak arasındaki ilişkiyi güçlendirmek istiyorum. "
                "Teras da günlük oturma ve sohbet alanına yakın olsun. "
                "Bana iki farklı düzenleme alternatifi öner."
            )
        }
    )
    failed_output_msg = (
        "Alternatif 1 - Salon: Mutfak ile doğrudan bağlantılı olup, "
        "girişten sonra hemen sağ tarafta yer alır. "
        "Mutfak ve salonun birbirine yakın olması, günlük etkileşimleri artırır.\n"
        "Alternatif 2 - Salon: Terasın yakınındaki alanda yer alır ve teras ile "
        "doğrudan bir kenar ortaklığı oluşturur. Bu yapı, dış ortamla iç alan arasındaki "
        "geçişleri daha doğal hale getirir.\n"
        "Temel fark: Birinci alternatif, iç alanların birbirine yakın olmasıyla "
        "etkileşimi artırırken, ikinci alternatif dış alanla iç alanın "
        "fiziksel bağlantısını vurgular."
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": failed_output_msg,
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    res = ArchitecturalIntentResult.model_validate(data)
    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize_compare(res, req)
    with pytest.raises(PolicyValidationError):
        validator.validate_semantic_integrity(sanitized, req)


def test_regression_real_model_output_shared_wall_claim() -> None:
    req = conversation_request().model_copy(
        update={
            "message": (
                "Salon ile mutfak arasındaki ilişkiyi güçlendirmek istiyorum. "
                "Teras da günlük oturma ve sohbet alanına yakın olsun. "
                "Bana iki farklı düzenleme alternatifi öner."
            )
        }
    )
    real_output_msg = (
        "Alternatif 1 - Salon ile mutfak arasındaki ilişkiyi güçlendirmek için birbirine yakın "
        "yerleştirilme: Salon, mutfakın yakınında bir konumda yer alır ve ortak bir duvarla "
        "birleşir; bu, günlük etkileşimleri doğrudan destekler.\n"
        "Alternatif 2 - Mutfak ve teras arasında bir akış ilkesi: Mutfak, terasın ilişkili alanda "
        "kurgulanır, bir dizi oturma alanına doğrudan bağlanır.\n"
        "Temel fark: Birinci alternatif fiziksel yakınlığı, "
        "ikinci alternatif dolaşım akışını öne çıkarır."
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": real_output_msg,
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    res = ArchitecturalIntentResult.model_validate(data)
    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize_compare(res, req)
    with pytest.raises(PolicyValidationError):
        validator.validate_semantic_integrity(sanitized, req)


def test_full_real_browser_regression_fixture() -> None:
    req = conversation_request().model_copy(
        update={
            "message": (
                "Salon ile mutfak arasındaki ilişkiyi güçlendirmek istiyorum. "
                "Teras da günlük oturma ve sohbet alanına yakın olsun. "
                "Bana iki farklı düzenleme alternatifi öner."
            )
        }
    )
    browser_output_msg = (
        "Alternatif 1 - Salon & Yaşam Alanı ile Mutfak: ortak bir duvarla birleştirilmiş, "
        "doğrudan birbirine yakın bir konumda yer alır. Bu yapı, günlük etkileşimleri "
        "kolaylaştırır.\n"
        "Alternatif 2 - Salon & Yaşam Alanı ile Mutfak: Ayrık alanlar olup, birbirinden uzak, "
        "ancak teras ile bağlantılı bir yapıda yer alır. Bu yaklaşım, daha kontrollü bir "
        "ortam sağlar.\n"
        "Temel fark: İlk alternatif, salon ve mutfak arasında fiziksel ve fonksiyonel bir "
        "bütünlük sağlar; ikinci alternatif ise bu alanları ayrı tutar, ancak teras ile "
        "daha güçlü bir ilişki kurar."
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": browser_output_msg,
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    res = ArchitecturalIntentResult.model_validate(data)
    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize_compare(res, req)
    with pytest.raises(PolicyValidationError):
        validator.validate_semantic_integrity(sanitized, req)


def test_entity_pair_proximity_trust_isolation() -> None:
    req = conversation_request().model_copy(
        update={
            "message": (
                "Salon ile mutfak arasındaki ilişkiyi güçlendirmek istiyorum. "
                "Teras da günlük oturma ve sohbet alanına yakın olsun."
            )
        }
    )
    validator = ArchitecturalIntentPolicyValidator()

    # Supported pair: teras & oturma / sohbet / salon
    data_trusted = valid_result_data()
    data_trusted["assistant_message"] = "Teras, günlük oturma alanının yakınında kurgulanır."
    res_trusted = ArchitecturalIntentResult.model_validate(data_trusted)
    sanitized_trusted = validator.sanitize(res_trusted, req)
    validator.validate_semantic_integrity(sanitized_trusted, req)

    # Unsupported pair: mutfak & salon distance claim
    data_unsupported = valid_result_data()
    data_unsupported["assistant_message"] = "Mutfak salona yakındır."
    res_unsupported = ArchitecturalIntentResult.model_validate(data_unsupported)
    try:
        validator.validate_semantic_integrity(res_unsupported, req)
        unsupported_raised = False
    except UnsupportedSpatialClaimError:
        unsupported_raised = True
    assert unsupported_raised


def test_unsupported_distance_claim_rejection() -> None:
    req = conversation_request().model_copy(
        update={"message": "Salon ile mutfak arasındaki ilişkiyi güçlendirmek istiyorum."}
    )
    data = valid_result_data()
    data["assistant_message"] = "Mutfak salondan uzaktır."
    res = ArchitecturalIntentResult.model_validate(data)

    validator = ArchitecturalIntentPolicyValidator()
    try:
        validator.validate_semantic_integrity(res, req)
        raised = False
    except UnsupportedSpatialClaimError:
        raised = True
    assert raised


def test_language_artifact_rejection() -> None:
    req = conversation_request().model_copy(
        update={"message": "İki farklı düzenleme alternatifi öner."}
    )
    validator = ArchitecturalIntentPolicyValidator()

    for artifact_text in [
        "Salon ele alınır ile mutfak birleşir.",
        "Mutfak kurgulanır ile düzenlenir.",
        "Teras yer alır ile bağlanır.",
        "Kontrollü ayrıma ile sınırlar vurgulanır.",
    ]:
        data = valid_result_data()
        data.update(
            {
                "intent": "compare_alternatives",
                "assistant_message": (
                    f"Alternatif 1 - {artifact_text}\n"
                    "Alternatif 2 - İkinci yaklaşım esneklik sunar.\n"
                    "Temel fark: Yaklaşımlar farklıdır."
                ),
            }
        )
        res = ArchitecturalIntentResult.model_validate(data)
        try:
            validator.validate_semantic_integrity(res, req)
            raised = False
        except AlternativeQualityError:
            raised = True
        assert raised, f"Expected AlternativeQualityError for artifact: {artifact_text}"


def test_browser_regression_v2_kurgudaligi_kurgu_siralanma() -> None:
    req = conversation_request().model_copy(
        update={
            "message": (
                "Salon ile mutfak arasındaki ilişkiyi güçlendirmek istiyorum. "
                "Teras da günlük oturma ve sohbet alanına yakın olsun. "
                "Bana iki farklı düzenleme alternatifi öner."
            )
        }
    )
    browser_output_msg = (
        "Alternatif 1 - Salon ile mutfak arasındaki ilişkiyi doğrudan güçlendirmek "
        "için iki alanın ilişkili bir kurgu sıralanma ile birleştirilmesi önerilir. "
        "Bu yapı, günlük etkileşimleri kolaylaştırır ve yaşam alanlarının birbirine ait "
        "olduğunu vurgular.\n"
        "Alternatif 2 - Salon ve mutfak, birbirinden ayrılmış ama bütünleşik bir kurguyla "
        "bağlanan bir yapıda yer alır. Bu yaklaşım, her bir alanın kendi içsel bütünlüğünü "
        "korurken aynı zamanda ilişkili kurguda olma hissini yaratır.\n"
        "Temel fark: İlk alternatif, alanların fiziksel ilişkili kurgudalığını doğrudan "
        "ortaya koyar; ikincisi ise birbirine ait olma hissini koruyarak, her bir alanın "
        "özgün karakterini korur."
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": browser_output_msg,
            "needs_follow_up": False,
            "follow_up_question": None,
        }
    )
    res = ArchitecturalIntentResult.model_validate(data)
    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize_compare(res, req)
    with pytest.raises(AlternativeQualityError):
        validator.validate_semantic_integrity(sanitized, req)


def test_excessive_mechanical_phrase_repetition_rejected() -> None:
    req = conversation_request().model_copy(
        update={"message": "İki farklı düzenleme alternatifi öner."}
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": (
                "Alternatif 1 - İlişkili kurgu yaklaşımı: Salon ve mutfak ilişkili bir kurguda "
                "ele alınır. Teras da ilişkili kurguyla bağlanır.\n"
                "Alternatif 2 - Esnek kurgu: Alanlar ilişkili kurguda değerlendirilir.\n"
                "Temel fark: Birinci ilişkili kurguyu, ikinci esnekliği öne çıkarır."
            ),
        }
    )
    res = ArchitecturalIntentResult.model_validate(data)
    validator = ArchitecturalIntentPolicyValidator()
    with pytest.raises(AlternativeQualityError, match="mekanik kalıp"):
        validator.validate_semantic_integrity(res, req)


def test_sanitize_compare_preserves_clean_text() -> None:
    req = conversation_request()
    clean_message = (
        "Alternatif 1 - Açık bütünleşme: Salon ve mutfak arasındaki görsel ve "
        "işlevsel ilişki güçlendirilir. Teras, ortak yaşamla ilişkilendirilir.\n"
        "Alternatif 2 - Kontrollü ayrışma: Her alanın kendi bütünlüğü korunur.\n"
        "Temel fark: Birinci süreklilik, ikinci esneklik sağlar."
    )
    data = valid_result_data()
    data.update(
        {
            "intent": "compare_alternatives",
            "assistant_message": clean_message,
        }
    )
    res = ArchitecturalIntentResult.model_validate(data)
    validator = ArchitecturalIntentPolicyValidator()
    sanitized = validator.sanitize_compare(res, req)
    assert sanitized.assistant_message == clean_message
