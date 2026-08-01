from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from brif_ai.llm.contracts import ArchitecturalIntentResult


def valid_result_data() -> dict[str, object]:
    return {
        "assistant_message": "Çalışma odasının akustik ilişkisini değerlendirebilirim.",
        "intent": "modify_space",
        "target": {
            "project_id": "proj_house_2story",
            "building_id": "bldg_main",
            "level_id": "lvl_ground",
            "zone_id": "zone_living",
            "entity_id": "space_study",
        },
        "user_requirements": ["Çalışma odası sessiz olsun."],
        "interpreted_priorities": ["akustik mahremiyet"],
        "constraints_to_check": ["komşu mekân gürültüsü"],
        "missing_information": [],
        "proposed_actions": [
            {
                "action_type": "suggest_space_resize",
                "target_entity_id": "space_study",
                "description": "Alan değişikliğini değerlendirin.",
                "requires_user_confirmation": True,
            }
        ],
        "needs_follow_up": False,
        "follow_up_question": None,
        "needs_user_confirmation": True,
        "confidence": 0.8,
        "warnings": [],
    }


def test_valid_structured_output() -> None:
    result = ArchitecturalIntentResult.model_validate(valid_result_data())

    assert result.target.entity_id == "space_study"
    assert result.proposed_actions[0].requires_user_confirmation is True


def test_invalid_json_rejected() -> None:
    with pytest.raises(ValidationError):
        ArchitecturalIntentResult.model_validate_json("{not-json")


def test_extra_field_rejected() -> None:
    data = valid_result_data()
    data["unexpected"] = "forbidden"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ArchitecturalIntentResult.model_validate(data)


def test_unknown_intent_rejected() -> None:
    data = valid_result_data()
    data["intent"] = "move_wall"

    with pytest.raises(ValidationError):
        ArchitecturalIntentResult.model_validate(data)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_range_validation(confidence: float) -> None:
    data = valid_result_data()
    data["confidence"] = confidence

    with pytest.raises(ValidationError):
        ArchitecturalIntentResult.model_validate(data)


def test_follow_up_invariant() -> None:
    data = valid_result_data()
    data["proposed_actions"] = []
    data["needs_user_confirmation"] = False
    data["needs_follow_up"] = True
    data["follow_up_question"] = None

    with pytest.raises(ValidationError, match="follow_up_question"):
        ArchitecturalIntentResult.model_validate(data)


def test_proposed_action_confirmation_invariant() -> None:
    data = valid_result_data()
    data["needs_user_confirmation"] = False

    with pytest.raises(ValidationError, match="proposed actions require"):
        ArchitecturalIntentResult.model_validate(data)


def test_plan_change_action_confirmation_invariant() -> None:
    data = valid_result_data()
    action = data["proposed_actions"]
    assert isinstance(action, list)
    action[0]["requires_user_confirmation"] = False

    with pytest.raises(ValidationError, match="explicit user confirmation"):
        ArchitecturalIntentResult.model_validate(data)


def test_explain_plan_rejects_plan_change_action() -> None:
    data = valid_result_data()
    data["intent"] = "explain_plan"

    with pytest.raises(ValidationError, match="explain_plan"):
        ArchitecturalIntentResult.model_validate(data)


def test_json_schema_forbids_extra_fields_and_lists_only_safe_actions() -> None:
    schema_text = json.dumps(ArchitecturalIntentResult.model_json_schema())

    assert '"additionalProperties": false' in schema_text
    assert "move_wall" not in schema_text
    assert "apply_geometry" not in schema_text
    assert "suggest_space_resize" in schema_text
