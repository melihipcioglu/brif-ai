from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from brif_ai.llm.contracts import ArchitecturalIntentResult
from brif_ai.llm.ollama_provider import OllamaProvider
from brif_ai.llm.provider import (
    ModelNotAvailableError,
    ModelNotSelectedError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from brif_ai.llm.settings import LocalLLMSettings

from .test_contracts import valid_result_data
from .test_policy_validator import conversation_request


def settings(model: str = "local-model:latest") -> LocalLLMSettings:
    return LocalLLMSettings(enabled=True, model=model)


def test_structured_schema_is_sent_in_ollama_format_field() -> None:
    requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        payload = json.loads(request.content)
        requests.append(payload)
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(valid_result_data())}},
        )

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            schema = ArchitecturalIntentResult.model_json_schema()
            result = await provider.interpret(conversation_request(), schema)
            assert result.intent.value == "modify_space"

    asyncio.run(run())
    assert requests[0]["format"] == ArchitecturalIntentResult.model_json_schema()
    assert requests[0]["stream"] is False
    assert requests[0]["options"] == {"temperature": 0.0}


def test_invalid_model_json_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        return httpx.Response(200, json={"message": {"content": "not-json"}})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            with pytest.raises(ProviderResponseError):
                await OllamaProvider(settings(), client).interpret(
                    conversation_request(), ArchitecturalIntentResult.model_json_schema()
                )

    asyncio.run(run())


def test_forbidden_action_type_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        data = valid_result_data()
        actions = data["proposed_actions"]
        assert isinstance(actions, list)
        actions[0]["action_type"] = "apply_geometry"
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(data, ensure_ascii=False)}},
        )

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            with pytest.raises(ProviderResponseError):
                await OllamaProvider(settings(), client).interpret(
                    conversation_request(), ArchitecturalIntentResult.model_json_schema()
                )

    asyncio.run(run())


def test_model_must_be_selected_before_provider_call() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"models": []})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            with pytest.raises(ModelNotSelectedError, match="Yerel model seçilmedi"):
                await OllamaProvider(settings(model=""), client).interpret(
                    conversation_request(), ArchitecturalIntentResult.model_json_schema()
                )

    asyncio.run(run())
    assert calls == 0


def test_ollama_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            with pytest.raises(ProviderUnavailableError, match="Ollamanın çalıştığını"):
                await OllamaProvider(settings(), client).list_models()

    asyncio.run(run())


def test_model_not_installed() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "another-model:latest"}]})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            with pytest.raises(ModelNotAvailableError, match="kurulu değil"):
                await OllamaProvider(settings(), client).interpret(
                    conversation_request(), ArchitecturalIntentResult.model_json_schema()
                )

    asyncio.run(run())


def test_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            with pytest.raises(ProviderTimeoutError, match="zaman aşımına"):
                await OllamaProvider(settings(), client).list_models()

    asyncio.run(run())


@pytest.mark.local_llm
def test_real_ollama_health_when_available() -> None:
    real_settings = LocalLLMSettings.from_env()

    async def run() -> None:
        health = await OllamaProvider(real_settings).health()
        if not health.reachable:
            pytest.skip("Local Ollama is not running")

    asyncio.run(run())
