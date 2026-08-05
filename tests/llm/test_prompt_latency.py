from __future__ import annotations

import copy
import json

from brif_ai.llm.contracts import ConversationRequest
from brif_ai.llm.prompts import SYSTEM_PROMPT, build_user_prompt

from .test_prompts import request_data


def test_system_prompt_has_a_compact_cpu_output_budget() -> None:
    normalized = SYSTEM_PROMPT.casefold()

    assert len(SYSTEM_PROMPT) <= 1300
    assert "aynı bilgiyi alanlar arasında tekrarlama" in normalized
    assert "her metin listesinde en fazla bir" in normalized
    assert "önerilen eylemlerde normalde en fazla bir" in normalized
    assert "boş liste kullan" in normalized


def test_user_prompt_deduplicates_validated_scope_without_losing_safety_context() -> None:
    data = request_data()
    request = ConversationRequest.model_validate(data)

    serialized = build_user_prompt(request)
    payload = json.loads(serialized)

    active = payload["active_context"]
    assert active["context_fingerprint"] == "house|main|upper|private|master-bath"
    assert active["generation_id"] == 7
    assert serialized.count("house|main|upper|private|master-bath") == 1
    assert serialized.count('"generation_id"') == 1
    assert serialized.count("proj_house_2story") == 1
    assert serialized.count("bldg_main") == 1
    assert serialized.count("lvl_upper") == 1

    assert payload["visible_entities"] == [
        {
            "entity_id": "space_master_bath",
            "entity_type": "space",
            "name": "Ebeveyn Banyosu",
            "zone_id": "zone_private",
        }
    ]
    assert payload["conversation_summary"] == data["conversation_summary"]
    assert payload["current_decisions"] == []
    pending = data["pending_proposals"]
    assert isinstance(pending, list)
    first_pending = pending[0]
    assert isinstance(first_pending, dict)
    assert payload["pending_proposals"] == [
        {
            "status": "pending_user_confirmation",
            "action": first_pending["action"],
        }
    ]
    assert len(serialized) <= 1200


def test_broad_active_scope_keeps_entity_scope_needed_for_visibility() -> None:
    data = copy.deepcopy(request_data())
    active = data["active_context"]
    assert isinstance(active, dict)
    active["building_id"] = None
    active["level_id"] = None
    request = ConversationRequest.model_validate(data)

    payload = json.loads(build_user_prompt(request))
    visible = payload["visible_entities"][0]

    assert visible["building_id"] == "bldg_main"
    assert visible["level_id"] == "lvl_upper"
    assert visible["zone_id"] == "zone_private"


def test_prompt_excludes_visible_entity_outside_active_scope() -> None:
    data = copy.deepcopy(request_data())
    visible_entities = data["visible_entities"]
    assert isinstance(visible_entities, list)
    visible_entities.append(
        {
            "entity_id": "space_foreign",
            "entity_type": "space",
            "name": "Başka Projedeki Oda",
            "project_id": "proj_foreign",
            "building_id": "bldg_foreign",
            "level_id": "lvl_foreign",
            "zone_id": "zone_foreign",
        }
    )
    request = ConversationRequest.model_validate(data)

    payload = json.loads(build_user_prompt(request))
    visible_ids = {entity["entity_id"] for entity in payload["visible_entities"]}

    assert visible_ids == {"space_master_bath"}
    assert "space_foreign" not in json.dumps(payload)
