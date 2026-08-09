from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from brif_ai.llm.contracts import ArchitecturalIntentResult
from brif_ai.llm.ollama_provider import OllamaPerformanceMetrics, OllamaProvider
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


def test_inference_performance_settings_defaults_and_environment() -> None:
    defaults = LocalLLMSettings.from_env({})
    configured = LocalLLMSettings.from_env(
        {
            "BRIF_AI_LLM_THINK": "false",
            "BRIF_AI_LLM_KEEP_ALIVE": "15m",
            "BRIF_AI_LLM_NUM_PREDICT": "256",
        }
    )

    assert defaults.think is False
    assert defaults.keep_alive == "30m"
    assert defaults.num_predict == 512
    assert configured.think is False
    assert configured.keep_alive == "15m"
    assert configured.num_predict == 256


def test_thinking_mode_cannot_be_enabled_for_mvp() -> None:
    with pytest.raises(ValueError, match="BRIF_AI_LLM_THINK"):
        LocalLLMSettings(think=True)


@pytest.mark.parametrize("num_predict", [0, 4097])
def test_num_predict_must_stay_within_safe_bounds(num_predict: int) -> None:
    with pytest.raises(ValueError, match="BRIF_AI_LLM_NUM_PREDICT"):
        LocalLLMSettings(num_predict=num_predict)


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
    assert requests[0]["think"] is False
    assert requests[0]["keep_alive"] == "30m"
    assert requests[0]["options"] == {"temperature": 0.0, "num_predict": 512}


def test_performance_metrics_are_calculated_from_ollama_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        return httpx.Response(
            200,
            json={
                "message": {"content": json.dumps(valid_result_data())},
                "total_duration": 2_500_000_000,
                "load_duration": 500_000_000,
                "prompt_eval_count": 120,
                "prompt_eval_duration": 600_000_000,
                "eval_count": 40,
                "eval_duration": 2_000_000_000,
            },
        )

    async def run() -> OllamaPerformanceMetrics:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            await provider.interpret(
                conversation_request(), ArchitecturalIntentResult.model_json_schema()
            )
            assert provider.last_performance_metrics is not None
            return provider.last_performance_metrics

    metrics = asyncio.run(run())

    assert metrics == OllamaPerformanceMetrics(
        total_seconds=2.5,
        load_seconds=0.5,
        prompt_tokens=120,
        prompt_eval_seconds=0.6,
        generated_tokens=40,
        eval_seconds=2.0,
        tokens_per_second=20.0,
    )


def test_missing_performance_metrics_do_not_reject_valid_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(valid_result_data())}},
        )

    async def run() -> tuple[ArchitecturalIntentResult, OllamaPerformanceMetrics]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            result = await provider.interpret(
                conversation_request(), ArchitecturalIntentResult.model_json_schema()
            )
            assert provider.last_performance_metrics is not None
            return result, provider.last_performance_metrics

    result, metrics = asyncio.run(run())

    assert result.intent.value == "modify_space"
    assert metrics == OllamaPerformanceMetrics(
        total_seconds=None,
        load_seconds=None,
        prompt_tokens=None,
        prompt_eval_seconds=None,
        generated_tokens=None,
        eval_seconds=None,
        tokens_per_second=None,
    )


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


def test_default_ollama_client_ignores_environment_proxies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_options: dict[str, object] = {}

    class FakeClient:
        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: object,
        ) -> None:
            return None

        async def request(
            self,
            method: str,
            path: str,
            *,
            json: dict[str, object] | None = None,
        ) -> httpx.Response:
            return httpx.Response(
                200,
                request=httpx.Request(method, f"http://127.0.0.1:11434{path}"),
                json={"models": [{"name": "local-model:latest"}]},
            )

    def fake_async_client(**options: object) -> FakeClient:
        captured_options.update(options)
        return FakeClient()

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    models = asyncio.run(OllamaProvider(settings()).list_models())

    assert models[0].name == "local-model:latest"
    assert captured_options["trust_env"] is False


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
