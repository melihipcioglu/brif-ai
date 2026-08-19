from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest

from brif_ai.llm.contracts import ArchitecturalIntentResult, ConversationRequest
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
    assert defaults.num_predict == 1024
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
    assert requests[0]["options"] == {"temperature": 0.0, "num_predict": 1024}


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


def compare_request() -> ConversationRequest:
    data = conversation_request().model_dump(mode="json")
    data["message"] = "Salon ile mutfak ilişkisi için iki alternatif öner."
    data["visible_entities"] = [
        {
            "entity_id": "space_salon",
            "entity_type": "space",
            "name": "Salon",
            "project_id": "proj_house_2story",
            "building_id": "bldg_main",
            "level_id": "lvl_upper",
            "zone_id": "zone_private",
        },
        {
            "entity_id": "space_mutfak",
            "entity_type": "space",
            "name": "Mutfak",
            "project_id": "proj_house_2story",
            "building_id": "bldg_main",
            "level_id": "lvl_upper",
            "zone_id": "zone_private",
        },
    ]
    return ConversationRequest.model_validate(data)


def valid_compare_plan_data() -> dict[str, Any]:
    return {
        "mode": "open_alternatives",
        "approach_1": "integrated_flow",
        "outcome_1": "continuous_interaction",
        "approach_2": "parallel_rhythms",
        "outcome_2": "independent_simultaneous_use",
        "confidence": 0.95,
    }


def test_quality_initial_response_uses_exactly_one_ollama_call() -> None:
    chat_calls = 0

    valid_response = valid_compare_plan_data()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        return httpx.Response(200, json={"message": {"content": json.dumps(valid_response)}})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            schema = ArchitecturalIntentResult.model_json_schema()
            res = await provider.interpret(compare_request(), schema)
            assert res.intent.value == "compare_alternatives"
            assert res.proposed_actions == []
            assert res.needs_user_confirmation is False
            assert res.needs_follow_up is False
            assert provider.last_chat_call_count == 1
            assert len(provider.last_attempt_records) == 1
            assert provider.last_attempt_records[0].failure_category is None

    asyncio.run(run())
    assert chat_calls == 1


def test_low_quality_initial_triggers_exactly_one_repair_and_succeeds() -> None:
    chat_calls = 0

    bad_initial = valid_compare_plan_data()
    bad_initial["approach_2"] = bad_initial["approach_1"]
    bad_initial["outcome_2"] = bad_initial["outcome_1"]
    good_repair = valid_compare_plan_data()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        content = bad_initial if chat_calls == 1 else good_repair
        return httpx.Response(200, json={"message": {"content": json.dumps(content)}})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            schema = ArchitecturalIntentResult.model_json_schema()
            res = await provider.interpret(compare_request(), schema)
            assert res.intent.value == "compare_alternatives"
            assert res.proposed_actions == []
            assert res.needs_user_confirmation is False
            assert provider.last_chat_call_count == 2
            assert [record.failure_category for record in provider.last_attempt_records] == [
                "ALTERNATIVES_TOO_SIMILAR",
                None,
            ]

    asyncio.run(run())
    assert chat_calls == 2


def test_low_quality_initial_and_low_quality_repair_raises_provider_response_error() -> None:
    chat_calls = 0

    bad_response = valid_compare_plan_data()
    bad_response["approach_2"] = bad_response["approach_1"]
    bad_response["outcome_2"] = bad_response["outcome_1"]

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        return httpx.Response(200, json={"message": {"content": json.dumps(bad_response)}})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            schema = ArchitecturalIntentResult.model_json_schema()
            with pytest.raises(ProviderResponseError, match="doğrulanabilir bir mimari niyet"):
                await provider.interpret(compare_request(), schema)
            assert provider.last_chat_call_count == 2
            assert len(provider.last_attempt_records) == 2

    asyncio.run(run())
    assert chat_calls == 2


def test_sanitize_and_quality_validator_preserve_structured_target_and_action_fields() -> None:
    chat_calls = 0

    response_data = valid_compare_plan_data()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        payload = json.loads(request.content.decode("utf-8"))
        # Verify structured decision-plan schema is sent for compare requests.
        assert "format" in payload
        assert "assistant_message" not in payload["format"]["properties"]
        assert "approach_1" in payload["format"]["properties"]
        assert "outcome_2" in payload["format"]["properties"]
        return httpx.Response(200, json={"message": {"content": json.dumps(response_data)}})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            schema = ArchitecturalIntentResult.model_json_schema()
            result = await provider.interpret(compare_request(), schema)
            assert result.intent.value == "compare_alternatives"
            assert result.target.project_id is None
            assert result.target.building_id is None
            assert result.target.level_id is None
            assert result.target.zone_id is None
            assert result.target.entity_id is None
            assert result.user_requirements == []
            assert result.interpreted_priorities == []
            assert result.constraints_to_check == []
            assert result.missing_information == []
            assert result.proposed_actions == []
            assert result.warnings == []
            assert result.needs_user_confirmation is False
            assert result.needs_follow_up is False
            assert result.follow_up_question is None

    asyncio.run(run())
    assert chat_calls == 1


def test_other_intents_use_full_schema() -> None:
    chat_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        payload = json.loads(request.content.decode("utf-8"))
        # Verify full schema format is sent for non-compare requests
        assert "format" in payload
        assert "user_requirements" in payload["format"]["properties"]
        return httpx.Response(200, json={"message": {"content": json.dumps(valid_result_data())}})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            schema = ArchitecturalIntentResult.model_json_schema()
            result = await provider.interpret(conversation_request(), schema)
            assert result.intent.value == "modify_space"

    asyncio.run(run())
    assert chat_calls == 1


def test_compare_free_text_compass_injection_triggers_repair_not_sanitize() -> None:
    """The enum-only schema rejects injected public text before rendering."""
    chat_calls = 0

    bad_initial = valid_compare_plan_data()
    bad_initial["summary_1"] = (
        "Mutfak salonun doğusunda kullanılarak gündelik yaşam akışı belirgin biçimde desteklenir."
    )
    good_repair = valid_compare_plan_data()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        content = bad_initial if chat_calls == 1 else good_repair
        return httpx.Response(200, json={"message": {"content": json.dumps(content)}})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            schema = ArchitecturalIntentResult.model_json_schema()
            res = await provider.interpret(compare_request(), schema)
            assert res.intent.value == "compare_alternatives"
            assert "doğusunda" not in res.assistant_message.casefold()

    asyncio.run(run())
    assert chat_calls == 2  # initial rejected, repair succeeded


def test_compare_free_text_shared_wall_injection_triggers_repair() -> None:
    """The enum-only schema cannot carry a shared-wall hallucination."""
    chat_calls = 0

    bad_initial = valid_compare_plan_data()
    bad_initial["summary_1"] = (
        "Salon ile mutfak ortak bir duvar paylaşarak gündelik işleyişi birlikte destekler."
    )
    good_repair = valid_compare_plan_data()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        content = bad_initial if chat_calls == 1 else good_repair
        return httpx.Response(200, json={"message": {"content": json.dumps(content)}})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            schema = ArchitecturalIntentResult.model_json_schema()
            res = await provider.interpret(compare_request(), schema)
            assert res.intent.value == "compare_alternatives"
            assert (
                "ortak" not in res.assistant_message.casefold()
                or "duvar" not in res.assistant_message.casefold()
            )

    asyncio.run(run())
    assert chat_calls == 2


def test_compare_free_text_proximity_injection_triggers_repair() -> None:
    """The enum-only schema rejects an untrusted proximity sentence."""
    chat_calls = 0

    # User says 'Teras salona yakın olsun', model says 'Mutfak salona yakındır' (untrusted pair)
    bad_initial = valid_compare_plan_data()
    bad_initial["summary_1"] = (
        "Mutfak salona yakındır ve gündelik yaşam akışı belirgin biçimde desteklenir."
    )
    good_repair = valid_compare_plan_data()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        content = bad_initial if chat_calls == 1 else good_repair
        return httpx.Response(200, json={"message": {"content": json.dumps(content)}})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            schema = ArchitecturalIntentResult.model_json_schema()
            # Use a request where user says 'Teras salona yakın' but NOT 'mutfak salona yakın'
            req = compare_request().model_copy(
                update={
                    "message": (
                        "Teras salona yakın olsun. Bana iki farklı düzenleme alternatifi öner."
                    )
                }
            )
            res = await provider.interpret(req, schema)
            assert res.intent.value == "compare_alternatives"

    asyncio.run(run())
    assert chat_calls == 2


def test_compare_trusted_proximity_accepted() -> None:
    """The renderer preserves a trusted pair while the model returns only enums."""
    chat_calls = 0

    response = valid_compare_plan_data()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chat_calls
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local-model:latest"}]})
        chat_calls += 1
        return httpx.Response(200, json={"message": {"content": json.dumps(response)}})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            schema = ArchitecturalIntentResult.model_json_schema()
            base_request = compare_request()
            active = base_request.active_context
            salon = base_request.visible_entities[0].model_copy(
                update={"level_id": active.level_id, "zone_id": active.zone_id}
            )
            teras = salon.model_copy(update={"entity_id": "space_teras", "name": "Teras"})
            req = base_request.model_copy(
                update={
                    "message": (
                        "Teras salona yakın olsun. Bana iki farklı düzenleme alternatifi öner."
                    ),
                    "visible_entities": [teras, salon],
                }
            )
            res = await provider.interpret(req, schema)
            assert res.intent.value == "compare_alternatives"
            assert res.proposed_actions == []
            assert res.assistant_message.count("yakın") == 2

    asyncio.run(run())
    assert chat_calls == 1  # No repair needed


def test_non_compare_sanitization_unchanged() -> None:
    """Non-compare requests should still use full sanitize with spatial neutralization."""
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

    from .test_policy_validator import conversation_request as conv_req

    req = conv_req()

    async def run() -> ArchitecturalIntentResult:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(settings(), client)
            schema = ArchitecturalIntentResult.model_json_schema()
            return await provider.interpret(req, schema)

    result = asyncio.run(run())
    assert chat_calls == 1
    assert "doğusunda" not in result.assistant_message.casefold()
    assert "ilişkili" in result.assistant_message.casefold()
