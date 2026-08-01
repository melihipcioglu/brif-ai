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
