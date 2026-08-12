from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from apps.api.main import create_app
from fastapi.testclient import TestClient

from brif_ai.brief.models.snapshot import BriefSnapshot, Stakeholder
from brif_ai.brief.persistence.json_repository import JSONBriefRepository
from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    ConversationInterpretationResponse,
    ConversationRequest,
)
from brif_ai.llm.ollama_provider import OllamaProvider
from brif_ai.llm.provider import (
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from brif_ai.llm.service import LocalLLMConversationService
from brif_ai.llm.settings import LocalLLMSettings

from .test_contracts import valid_result_data
from .test_ollama_provider import valid_compare_plan_data
from .test_policy_validator import conversation_request, public_texts
from .test_prompts import request_data


def settings() -> LocalLLMSettings:
    return LocalLLMSettings(enabled=True, model="local-model:latest")


def schema() -> dict[str, object]:
    return ArchitecturalIntentResult.model_json_schema()


def _seeded_brief_repository(root: Path) -> JSONBriefRepository:
    repo = JSONBriefRepository(root)
    repo.save(
        BriefSnapshot(
            project_id="proj_house_2story",
            schema_version="brief.v0",
            brief_version=1,
            created_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            stakeholders=[
                Stakeholder(
                    id="stk_owner",
                    display_name="Ev Sahibi",
                    role="CLIENT_OWNER",
                    active=True,
                )
            ],
            evidence=[],
            brief_items=[],
            space_requests=[],
            usage_scenarios=[],
            contradictions=[],
            open_questions=[],
        )
    )
    return repo


def test_schema_invalid_response_is_repaired_once_without_reusing_untrusted_output() -> None:
    chat_payloads: list[dict[str, Any]] = []
    invalid_content = '{"assistant_message":"yarım'

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        payload = json.loads(request.content)
        chat_payloads.append(payload)
        content = invalid_content if len(chat_payloads) == 1 else json.dumps(valid_result_data())
        return httpx.Response(200, json={"message": {"content": content}})

    async def run() -> ArchitecturalIntentResult:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            return await OllamaProvider(settings(), client).interpret(
                conversation_request(), schema()
            )

    result = asyncio.run(run())

    assert result.intent.value == "modify_space"
    assert len(chat_payloads) == 2
    first, repair = chat_payloads
    assert repair["format"] == first["format"] == schema()
    assert repair["messages"][1] == first["messages"][1]
    repair_instruction = repair["messages"][0]["content"].casefold()
    assert "yalnızca" in repair_instruction
    assert "json schema" in repair_instruction
    assert invalid_content not in json.dumps(repair, ensure_ascii=False)


def test_length_limited_json_gets_one_repair_with_the_full_output_budget() -> None:
    chat_payloads: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        payload = json.loads(request.content)
        chat_payloads.append(payload)
        if len(chat_payloads) == 1:
            return httpx.Response(
                200,
                json={
                    "message": {"content": '{"assistant_message":"yarım'},
                    "done_reason": "length",
                    "eval_count": payload["options"]["num_predict"],
                },
            )
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(valid_result_data())}},
        )

    async def run() -> ArchitecturalIntentResult:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            return await OllamaProvider(settings(), client).interpret(
                conversation_request(), schema()
            )

    result = asyncio.run(run())

    assert result.intent.value == "modify_space"
    assert len(chat_payloads) == 2
    assert chat_payloads[0]["options"]["num_predict"] == 512
    assert chat_payloads[1]["options"]["num_predict"] == 512


def test_valid_json_with_invalid_schema_is_repaired_once() -> None:
    chat_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        data = valid_result_data()
        if chat_calls == 1:
            data.pop("assistant_message")
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(data, ensure_ascii=False)}},
        )

    async def run() -> ArchitecturalIntentResult:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            return await OllamaProvider(settings(), client).interpret(
                conversation_request(), schema()
            )

    result = asyncio.run(run())

    assert result.intent.value == "modify_space"
    assert chat_calls == 2


def test_second_invalid_response_preserves_safe_error_without_a_third_attempt() -> None:
    chat_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        return httpx.Response(200, json={"message": {"content": "not-json"}})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            with pytest.raises(ProviderResponseError):
                await OllamaProvider(settings(), client).interpret(conversation_request(), schema())

    asyncio.run(run())
    assert chat_calls == 2


def test_second_invalid_response_returns_existing_safe_502(tmp_path: Path) -> None:
    chat_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        return httpx.Response(200, json={"message": {"content": "not-json"}})

    async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://127.0.0.1:11434",
    )
    provider = OllamaProvider(settings(), async_client)
    brief_repository = _seeded_brief_repository(tmp_path)
    test_client = TestClient(create_app(settings(), provider, brief_repository=brief_repository))
    try:
        response = test_client.post(
            "/api/v1/conversation/interpret",
            json=conversation_request().model_dump(mode="json"),
        )
    finally:
        asyncio.run(async_client.aclose())

    assert response.status_code == 502
    assert response.json()["error"] == (
        "Yerel model doğrulanabilir bir mimari niyet yanıtı üretmedi."
    )
    assert chat_calls == 2


def test_repair_does_not_weaken_plan_change_confirmation_rules() -> None:
    chat_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        if chat_calls == 1:
            return httpx.Response(200, json={"message": {"content": "not-json"}})
        data = valid_result_data()
        data["needs_user_confirmation"] = False
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(data, ensure_ascii=False)}},
        )

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            with pytest.raises(ProviderResponseError):
                await OllamaProvider(settings(), client).interpret(conversation_request(), schema())

    asyncio.run(run())
    assert chat_calls == 2


def test_repair_preserves_validated_context_and_pending_proposal() -> None:
    chat_payloads: list[dict[str, Any]] = []
    request_with_pending = ConversationRequest.model_validate(request_data())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        payload = json.loads(request.content)
        chat_payloads.append(payload)
        content = "not-json" if len(chat_payloads) == 1 else json.dumps(valid_result_data())
        return httpx.Response(200, json={"message": {"content": content}})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            await OllamaProvider(settings(), client).interpret(request_with_pending, schema())

    asyncio.run(run())

    assert len(chat_payloads) == 2
    original_context = json.loads(chat_payloads[0]["messages"][1]["content"])
    repair_context = json.loads(chat_payloads[1]["messages"][1]["content"])
    assert repair_context == original_context
    assert repair_context["active_context"]["context_fingerprint"] == (
        "house|main|upper|private|master-bath"
    )
    assert repair_context["active_context"]["generation_id"] == 7
    pending = request_data()["pending_proposals"]
    assert isinstance(pending, list)
    first_pending = pending[0]
    assert isinstance(first_pending, dict)
    assert repair_context["pending_proposals"] == [
        {
            "status": first_pending["status"],
            "action": first_pending["action"],
        }
    ]


@pytest.mark.parametrize(
    ("provider_error", "expected_error"),
    [
        (httpx.ReadTimeout, ProviderTimeoutError),
        (httpx.ConnectError, ProviderUnavailableError),
    ],
)
def test_transport_failure_is_not_retried(
    provider_error: type[httpx.RequestError],
    expected_error: type[Exception],
) -> None:
    chat_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        raise provider_error("transport failed", request=request)

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            with pytest.raises(expected_error):
                await OllamaProvider(settings(), client).interpret(conversation_request(), schema())

    asyncio.run(run())
    assert chat_calls == 1


def test_recovered_response_still_hides_internal_terms_from_user_text() -> None:
    chat_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        if chat_calls == 1:
            return httpx.Response(200, json={"message": {"content": "not-json"}})
        data = valid_result_data()
        data["assistant_message"] = (
            "pending_proposals, modify_space, contextFingerprint ve generationId hazır."
        )
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(data, ensure_ascii=False)}},
        )

    async def run() -> ConversationInterpretationResponse:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            service = LocalLLMConversationService(settings(), provider)
            return await service.interpret(conversation_request())

    response = asyncio.run(run())

    assert response.result is not None
    combined = "\n".join(public_texts(response.result)).casefold()
    for technical_term in (
        "pending_proposals",
        "modify_space",
        "contextfingerprint",
        "generationid",
    ):
        assert technical_term not in combined
    assert chat_calls == 2


def test_compare_free_text_schema_injection_triggers_single_repair_call() -> None:
    chat_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        data = valid_compare_plan_data()
        if chat_calls == 1:
            data["summary_1"] = (
                "Salon ve mutfak birlikte ele alınır; plan için öğe bilgisi kullanıcıya gösterilir."
            )
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(data, ensure_ascii=False)}},
        )

    req = conversation_request().model_copy(
        update={"message": "Salon ve teras için iki farklı düzenleme alternatifi sun."}
    )

    async def run() -> ArchitecturalIntentResult:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            return await provider.interpret(req, schema())

    result = asyncio.run(run())

    assert chat_calls == 2
    assert result.intent.value == "compare_alternatives"
    assert "Alternatif 1" in result.assistant_message
    assert "Alternatif 2" in result.assistant_message


def test_semantic_validation_failure_triggers_single_repair_and_succeeds_if_repair_is_safe() -> (
    None
):
    chat_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        data = valid_compare_plan_data()
        if chat_calls == 1:
            data["mode"] = "entity_choice"
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(data, ensure_ascii=False)}},
        )

    req = conversation_request().model_copy(
        update={"message": "Salon ve teras için iki farklı düzenleme alternatifi sun."}
    )

    async def run() -> ArchitecturalIntentResult:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            return await provider.interpret(req, schema())

    result = asyncio.run(run())

    assert chat_calls == 2
    assert result.intent.value == "compare_alternatives"
    assert "Alternatif 1" in result.assistant_message
    assert "Alternatif 2" in result.assistant_message


def test_repair_fails_if_repair_response_is_also_invalid() -> None:
    chat_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        data = valid_result_data()
        data["intent"] = "modify_space"
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(data, ensure_ascii=False)}},
        )

    req = conversation_request().model_copy(
        update={"message": "Salon ve teras için iki farklı düzenleme alternatifi sun."}
    )

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            with pytest.raises(ProviderResponseError, match="doğrulanabilir bir mimari niyet"):
                await provider.interpret(req, schema())

    asyncio.run(run())
    assert chat_calls == 2


def test_initial_response_containing_target_succeeds_via_sanitization_without_repair() -> None:
    chat_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        data = valid_result_data()
        data["assistant_message"] = "Plan üzerinde target alanı düzenlenmiştir."
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(data, ensure_ascii=False)}},
        )

    req = conversation_request()

    async def run() -> ArchitecturalIntentResult:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            return await provider.interpret(req, schema())

    result = asyncio.run(run())

    assert chat_calls == 1
    assert "target" not in result.assistant_message.casefold()
    assert "hedef" in result.assistant_message.casefold()


def test_initial_response_with_unsupported_direction_succeeds_via_sanitization() -> None:
    chat_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        data = valid_result_data()
        data["assistant_message"] = "Teras salonun doğusundadır."
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(data, ensure_ascii=False)}},
        )

    req = conversation_request()

    async def run() -> ArchitecturalIntentResult:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            return await provider.interpret(req, schema())

    result = asyncio.run(run())

    assert chat_calls == 1
    assert "doğusunda" not in result.assistant_message.casefold()
    assert "ilişkili" in result.assistant_message.casefold()
