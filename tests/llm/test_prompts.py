from __future__ import annotations

import copy
import json
import re

import pytest
from pydantic import ValidationError

from brif_ai.llm.contracts import ConversationRequest
from brif_ai.llm.prompts import (
    COMPARE_REPAIR_PROMPT,
    COMPARE_SYSTEM_PROMPT,
    SCHEMA_REPAIR_PROMPT,
    SYSTEM_PROMPT,
    build_user_prompt,
)


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
    data = request_data()
    request = ConversationRequest.model_validate(data)

    payload = json.loads(build_user_prompt(request))
    pending = data["pending_proposals"]
    assert isinstance(pending, list)
    first_pending = pending[0]
    assert isinstance(first_pending, dict)

    assert payload["message"] == "Şimdi ne yapacağım?"
    assert payload["current_decisions"] == []
    assert payload["active_context"]["context_fingerprint"] == first_pending["context_fingerprint"]
    assert payload["active_context"]["generation_id"] == first_pending["generation_id"]
    assert payload["pending_proposals"] == [
        {
            "status": first_pending["status"],
            "action": first_pending["action"],
        }
    ]
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


def test_system_prompt_requires_real_alternatives_without_unnecessary_follow_up() -> None:
    assert "intent compare_alternatives" in SYSTEM_PROMPT
    assert "istenen alternatif sayısını" in SYSTEM_PROMPT
    assert "gerçekten üret" in SYSTEM_PROMPT
    assert "olmayan yön" in SYSTEM_PROMPT
    assert "Kesin yön ve konum belirtmeden" in SYSTEM_PROMPT
    assert "kavramsal" in SYSTEM_PROMPT
    assert "tek takip sorusu sor" in SYSTEM_PROMPT


def test_schema_repair_prompt_states_cross_field_consistency_rules() -> None:
    assert "target her zaman bir JSON nesnesi" in SCHEMA_REPAIR_PROMPT
    assert "her zaman JSON dizisi" in SCHEMA_REPAIR_PROMPT
    assert "needs_follow_up=true" in SCHEMA_REPAIR_PROMPT
    assert "needs_user_confirmation=true" in SCHEMA_REPAIR_PROMPT
    assert "requires_user_confirmation=true" in SCHEMA_REPAIR_PROMPT
    assert "yalnız görünür kapsamdaki gerçek target_entity_id" in SCHEMA_REPAIR_PROMPT
    assert "confidence 0 ile 1 arasında" in SCHEMA_REPAIR_PROMPT
    assert "şema dışı hiçbir alan ekleme" in SCHEMA_REPAIR_PROMPT
    assert "Verilmeyen yön" in SCHEMA_REPAIR_PROMPT
    assert "kesin yön ve konum belirtmeden" in SCHEMA_REPAIR_PROMPT


def test_spatial_assumptions_prevention_guidance_for_conceptual_requests() -> None:
    data = request_data()
    data["message"] = "Salon, mutfak ve teras ilişkisi için iki alternatif öner"
    request = ConversationRequest.model_validate(data)
    prompt_str = build_user_prompt(request)

    assert "olmayan yön" in SYSTEM_PROMPT
    assert "kesin konum/yön bilgisi henüz verilmedi" in SYSTEM_PROMPT
    assert "Kesin yön ve konum belirtmeden" in SYSTEM_PROMPT
    payload = json.loads(prompt_str)
    assert payload["message"] == "Salon, mutfak ve teras ilişkisi için iki alternatif öner"


def test_compare_prompts_do_not_lexically_prime_forbidden_spatial_claims() -> None:
    forbidden_terms = (
        "kuzey",
        "güney",
        "doğu",
        "batı",
        "sağ",
        "sol",
        "ön",
        "arka",
        "karşı",
        "bitişik",
        "ortak duvar",
        "ortak kenar",
        "yakın",
        "uzak",
    )

    for prompt in (COMPARE_SYSTEM_PROMPT, COMPARE_REPAIR_PROMPT):
        for term in forbidden_terms:
            pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
            assert re.search(pattern, prompt, re.IGNORECASE) is None, term
