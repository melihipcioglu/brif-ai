from __future__ import annotations

import pytest
from scripts.smoke_test_real_ollama import (
    SmokeValidationError,
    build_smoke_request,
    validate_smoke_response,
)

from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    ConversationInterpretationResponse,
)


def response_for_smoke() -> ConversationInterpretationResponse:
    request = build_smoke_request()
    data = {
        "assistant_message": "Çalışma odası için akustik bir geçiş önerilebilir.",
        "intent": "modify_relationship",
        "target": {
            "project_id": "smoke_project",
            "building_id": "smoke_building",
            "level_id": "smoke_ground",
            "zone_id": "smoke_living",
            "entity_id": "smoke_study",
        },
        "user_requirements": ["Sessiz fakat yaşam alanından tamamen kopmayan çalışma odası"],
        "interpreted_priorities": ["Akustik mahremiyet ve erişilebilir ilişki"],
        "constraints_to_check": ["Kapı ve tampon alan yerleşimi"],
        "missing_information": [],
        "proposed_actions": [
            {
                "action_type": "suggest_relationship_change",
                "target_entity_id": "smoke_study",
                "description": "Çalışma odası ile salon arasına akustik tampon öner.",
                "requires_user_confirmation": True,
            }
        ],
        "needs_follow_up": False,
        "follow_up_question": None,
        "needs_user_confirmation": True,
        "confidence": 0.9,
        "warnings": [],
    }
    return ConversationInterpretationResponse(
        success=True,
        llm_enabled=True,
        provider="ollama",
        model="local-model:latest",
        context_fingerprint=request.active_context.context_fingerprint,
        generation_id=request.active_context.generation_id,
        result=ArchitecturalIntentResult.model_validate(data),
        error=None,
    )


def test_smoke_request_is_fixed_and_safely_scoped() -> None:
    request = build_smoke_request()

    assert request.active_context.entity_id == "smoke_study"
    assert {entity.entity_id for entity in request.visible_entities} == {"smoke_study"}
    assert request.pending_proposals == []


def test_smoke_response_validation_accepts_schema_valid_safe_result() -> None:
    request = build_smoke_request()

    validate_smoke_response(response_for_smoke(), request)


def test_smoke_response_validation_rejects_stale_context() -> None:
    request = build_smoke_request()
    response = response_for_smoke().model_copy(update={"context_fingerprint": "stale"})

    with pytest.raises(SmokeValidationError, match="context"):
        validate_smoke_response(response, request)
