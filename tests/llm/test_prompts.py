from __future__ import annotations

import copy
import json

import pytest
from pydantic import ValidationError

from brif_ai.llm.contracts import ConversationRequest
from brif_ai.llm.prompts import SYSTEM_PROMPT, build_user_prompt


def request_data() -> dict[str, object]:
    return {
        "message": "Şimdi ne yapacağım?",
        "active_context": {
            "project_id": "proj_house_2story",
            "building_id": "bldg_main",
            "level_id": "lvl_upper",
            "zone_id": "zone_private",
            "entity_id": "space_master_bath",
            "context_fingerprint": "house|main|upper|private|master-bath",
            "generation_id": 7,
        },
        "visible_entities": [
            {
                "entity_id": "space_master_bath",
                "entity_type": "space",
                "name": "Ebeveyn Banyosu",
                "project_id": "proj_house_2story",
                "building_id": "bldg_main",
                "level_id": "lvl_upper",
                "zone_id": "zone_private",
            }
        ],
        "conversation_summary": (
            "user: Ebeveyn banyosunu kuzeye alalım.\n"
            "assistant: Kuzey kenarı için bir öneri oluşturdum.\n"
            "user: Şimdi ne yapacağım?"
        ),
        "current_decisions": [],
        "pending_proposals": [
            {
                "status": "pending_user_confirmation",
                "context_fingerprint": "house|main|upper|private|master-bath",
                "generation_id": 7,
                "action": {
                    "action_type": "suggest_relationship_change",
                    "target_entity_id": "space_master_bath",
                    "description": "Ebeveyn banyosunu kuzey kenarına taşı.",
                    "requires_user_confirmation": True,
                },
            }
        ],
    }


def test_pending_proposal_is_validated_and_serialized_for_model() -> None:
    request = ConversationRequest.model_validate(request_data())

    payload = json.loads(build_user_prompt(request))

    assert payload["message"] == "Şimdi ne yapacağım?"
    assert payload["current_decisions"] == []
    assert payload["pending_proposals"] == request_data()["pending_proposals"]
    assert "proposal_id" not in json.dumps(payload)


def test_pending_proposals_default_to_empty_for_existing_clients() -> None:
    data = request_data()
    data.pop("pending_proposals")

    request = ConversationRequest.model_validate(data)

    assert request.pending_proposals == []


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("context_fingerprint", "stale-context", "fingerprint"),
        ("generation_id", 6, "generation"),
    ],
)
def test_stale_pending_proposal_is_rejected(
    field: str,
    value: str | int,
    message: str,
) -> None:
    data = copy.deepcopy(request_data())
    pending = data["pending_proposals"]
    assert isinstance(pending, list)
    pending[0][field] = value

    with pytest.raises(ValidationError, match=message):
        ConversationRequest.model_validate(data)


def test_pending_proposal_requires_confirmation() -> None:
    data = copy.deepcopy(request_data())
    pending = data["pending_proposals"]
    assert isinstance(pending, list)
    pending[0]["action"]["requires_user_confirmation"] = False

    with pytest.raises(ValidationError, match="require user confirmation"):
        ConversationRequest.model_validate(data)


def test_pending_proposal_target_must_be_visible() -> None:
    data = copy.deepcopy(request_data())
    pending = data["pending_proposals"]
    assert isinstance(pending, list)
    pending[0]["action"]["target_entity_id"] = "space_foreign"

    with pytest.raises(ValidationError, match="visible"):
        ConversationRequest.model_validate(data)


def test_system_prompt_preserves_pending_proposal_continuity() -> None:
    assert "doğal Türkçe" in SYSTEM_PROMPT
    assert "iç alan veya enum adlarını" in SYSTEM_PROMPT
    assert "ilk analizi tekrarlama" in SYSTEM_PROMPT
    assert "henüz onaylanmış karar değildir" in SYSTEM_PROMPT
    assert "onaylama, ayrıntılandırma veya vazgeçme" in SYSTEM_PROMPT
