from __future__ import annotations

import pytest

from brif_ai.llm.contracts import (
    ActiveContextSnapshot,
    ArchitecturalIntentResult,
    ConversationRequest,
    VisibleEntity,
)
from brif_ai.llm.policy_validator import (
    ArchitecturalIntentPolicyValidator,
    PolicyValidationError,
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
        ("targetEntityId", "ilgili öğe bilgisi"),
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

    assert "ilgili mekân" in safe_result.warnings[0]
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
