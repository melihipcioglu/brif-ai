from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from apps.api.main import (
    ALLOWED_ORIGINS,
    UI_ORIGIN_ENV,
    create_app,
    resolve_allowed_origins,
)
from fastapi.testclient import TestClient

from brif_ai.brief.models.snapshot import BriefSnapshot, Stakeholder
from brif_ai.brief.persistence.json_repository import JSONBriefRepository
from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    ConversationRequest,
    LocalModelInfo,
    ProviderHealth,
)
from brif_ai.llm.provider import (
    ModelNotAvailableError,
    ModelNotSelectedError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from brif_ai.llm.settings import LocalLLMSettings

from .test_contracts import valid_result_data


def _seed_authoritative_brief(root: Path) -> None:
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


@pytest.fixture(autouse=True)
def _isolated_authoritative_brief(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Every API test gets a clean authoritative repository.
    # This prevents dependence on ~/.brif_ai/data from the developer machine.
    monkeypatch.setenv("BRIF_AI_DATA_DIR", str(tmp_path))
    _seed_authoritative_brief(tmp_path)


class APIProvider:
    def __init__(self) -> None:
        self.result = ArchitecturalIntentResult.model_validate(valid_result_data())
        self.error: Exception | None = None
        self.list_models_error: Exception | None = None
        self.models = [LocalModelInfo(name="local-model:latest", size=42)]
        self.health_calls = 0
        self.list_models_calls = 0

    async def health(self) -> ProviderHealth:
        self.health_calls += 1
        return ProviderHealth(provider="ollama", reachable=True)

    async def list_models(self) -> list[LocalModelInfo]:
        self.list_models_calls += 1
        if self.list_models_error is not None:
            raise self.list_models_error
        return self.models

    async def interpret(
        self, request: ConversationRequest, output_schema: dict[str, object]
    ) -> ArchitecturalIntentResult:
        if self.error is not None:
            raise self.error
        return self.result


def client(
    *, enabled: bool = True, model: str = "local-model:latest"
) -> tuple[TestClient, APIProvider]:
    provider = APIProvider()
    settings = LocalLLMSettings(enabled=enabled, model=model)
    return TestClient(create_app(settings, provider)), provider


def request_data(message: str = "Çalışma odasını biraz büyüt.") -> dict[str, object]:
    return {
        "message": message,
        "active_context": {
            "project_id": "proj_house_2story",
            "building_id": "bldg_main",
            "level_id": "lvl_ground",
            "zone_id": "zone_living",
            "entity_id": "space_study",
            "context_fingerprint": "house|main|ground|living|study",
            "generation_id": 4,
        },
        "visible_entities": [
            {
                "entity_id": "space_study",
                "entity_type": "space",
                "name": "Çalışma Odası",
                "project_id": "proj_house_2story",
                "building_id": "bldg_main",
                "level_id": "lvl_ground",
                "zone_id": "zone_living",
            }
        ],
        "conversation_summary": "",
        "current_decisions": [],
    }


def test_health_endpoint() -> None:
    test_client, provider = client()

    response = test_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "llm_enabled": True,
        "provider": "ollama",
        "provider_reachable": True,
        "selected_model": "local-model:latest",
        "model_available": True,
        "message": "Yerel yapay zekâ bağlantısı hazır.",
    }
    assert provider.list_models_calls == 1
    assert provider.health_calls == 0


def test_health_disabled_is_degraded_without_provider_call() -> None:
    test_client, provider = client(enabled=False)

    payload = test_client.get("/api/v1/health").json()

    assert payload["status"] == "degraded"
    assert payload["llm_enabled"] is False
    assert payload["provider_reachable"] is False
    assert provider.list_models_calls == 0


def test_health_without_selected_model_is_degraded() -> None:
    test_client, provider = client(model="")

    payload = test_client.get("/api/v1/health").json()

    assert payload["status"] == "degraded"
    assert payload["provider_reachable"] is True
    assert payload["selected_model"] is None
    assert provider.list_models_calls == 1


def test_health_missing_model_is_degraded() -> None:
    test_client, provider = client()
    provider.models = [LocalModelInfo(name="another-model:latest")]

    payload = test_client.get("/api/v1/health").json()

    assert payload["status"] == "degraded"
    assert payload["provider_reachable"] is True
    assert payload["model_available"] is False
    assert provider.list_models_calls == 1


@pytest.mark.parametrize(
    "error",
    [
        ProviderUnavailableError("offline"),
        ProviderTimeoutError("timeout"),
    ],
)
def test_health_provider_access_failure_is_unavailable(error: Exception) -> None:
    test_client, provider = client()
    provider.list_models_error = error

    response = test_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["provider_reachable"] is False
    assert provider.list_models_calls == 1


def test_health_invalid_provider_response_is_degraded() -> None:
    test_client, provider = client()
    provider.list_models_error = ProviderResponseError("invalid")

    response = test_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["provider_reachable"] is True
    assert provider.list_models_calls == 1


def test_health_unexpected_error_returns_typed_safe_response() -> None:
    test_client, provider = client()
    provider.list_models_error = RuntimeError("must-not-leak")

    response = test_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert "must-not-leak" not in response.text


def test_default_cors_origins_remain_backward_compatible() -> None:
    assert resolve_allowed_origins({}) == ALLOWED_ORIGINS
    assert "*" not in resolve_allowed_origins({})


def test_custom_loopback_ui_origin_adds_both_host_spellings() -> None:
    origins = resolve_allowed_origins({UI_ORIGIN_ENV: "http://127.0.0.1:8090"})

    assert "http://127.0.0.1:8090" in origins
    assert "http://localhost:8090" in origins
    assert "*" not in origins


@pytest.mark.parametrize(
    "origin",
    [
        "https://127.0.0.1:8090",
        "http://example.com:8090",
        "http://user:pass@localhost:8090",
        "http://localhost:8090/path",
        "http://localhost:8090?wide=true",
        "http://localhost:8090#fragment",
        "http://localhost",
        "*",
    ],
)
def test_invalid_or_external_ui_origin_is_rejected(origin: str) -> None:
    with pytest.raises(ValueError, match=UI_ORIGIN_ENV):
        resolve_allowed_origins({UI_ORIGIN_ENV: origin})


def test_invalid_ui_origin_fails_app_startup() -> None:
    provider = APIProvider()
    settings = LocalLLMSettings(enabled=True, model="local-model:latest")

    with pytest.raises(ValueError, match=UI_ORIGIN_ENV):
        create_app(settings, provider, {UI_ORIGIN_ENV: "http://example.com:8090"})


def test_custom_ui_origin_is_accepted_by_cors_middleware() -> None:
    provider = APIProvider()
    settings = LocalLLMSettings(enabled=True, model="local-model:latest")
    test_client = TestClient(
        create_app(settings, provider, {UI_ORIGIN_ENV: "http://127.0.0.1:8090"})
    )

    response = test_client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:8090",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:8090"


def test_models_endpoint_lists_installed_local_models() -> None:
    test_client, _provider = client()

    response = test_client.get("/api/v1/llm/models")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "local-model:latest"


def test_interpret_endpoint() -> None:
    test_client, _provider = client()

    response = test_client.post("/api/v1/conversation/interpret", json=request_data())

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["context_fingerprint"] == "house|main|ground|living|study"


def test_empty_message_is_422() -> None:
    test_client, _provider = client()

    response = test_client.post("/api/v1/conversation/interpret", json=request_data(message="   "))

    assert response.status_code == 422


def test_llm_disabled() -> None:
    test_client, _provider = client(enabled=False)

    response = test_client.post("/api/v1/conversation/interpret", json=request_data())

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert "Demo konuşma modu" in response.json()["error"]


def test_model_not_selected() -> None:
    test_client, provider = client(model="")
    provider.error = ModelNotSelectedError(
        "Yerel model seçilmedi. Önce bilgisayarınızda kurulu bir model seçin."
    )

    response = test_client.post("/api/v1/conversation/interpret", json=request_data())

    assert response.status_code == 409
    assert "Yerel model seçilmedi" in response.json()["error"]


def test_model_not_installed() -> None:
    test_client, provider = client()
    provider.error = ModelNotAvailableError("Seçilen model bu bilgisayarda kurulu değil.")

    response = test_client.post("/api/v1/conversation/interpret", json=request_data())

    assert response.status_code == 409
    assert "kurulu değil" in response.json()["error"]


def test_ollama_unreachable() -> None:
    test_client, provider = client()
    provider.error = ProviderUnavailableError(
        "Yerel yapay zekâ servisine ulaşılamadı. Ollamanın çalıştığını kontrol edin."
    )

    response = test_client.post("/api/v1/conversation/interpret", json=request_data())

    assert response.status_code == 503
    assert "Ollamanın çalıştığını" in response.json()["error"]


def test_timeout() -> None:
    test_client, provider = client()
    provider.error = ProviderTimeoutError("Yerel yapay zekâ isteği zaman aşımına uğradı.")

    response = test_client.post("/api/v1/conversation/interpret", json=request_data())

    assert response.status_code == 504
    assert "zaman aşımına" in response.json()["error"]


def test_allowed_cors_origin() -> None:
    test_client, _provider = client()

    response = test_client.options(
        "/api/v1/conversation/interpret",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:8080"
    assert "*" not in ALLOWED_ORIGINS


def test_rejected_cors_origin() -> None:
    test_client, _provider = client()

    response = test_client.options(
        "/api/v1/conversation/interpret",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_no_external_llm_api_key_or_dependency() -> None:
    root = Path(__file__).parents[2]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8").lower()
    example_env = (root / ".env.example").read_text(encoding="utf-8")

    assert '"openai' not in pyproject
    assert "OPENAI_API_KEY" not in example_env
    assert "api_key" not in example_env.lower()
