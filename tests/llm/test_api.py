from __future__ import annotations

from pathlib import Path

from apps.api.main import ALLOWED_ORIGINS, create_app
from fastapi.testclient import TestClient

from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    ConversationRequest,
    LocalModelInfo,
    ProviderHealth,
)
from brif_ai.llm.provider import (
    ModelNotAvailableError,
    ModelNotSelectedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from brif_ai.llm.settings import LocalLLMSettings

from .test_contracts import valid_result_data


class APIProvider:
    def __init__(self) -> None:
        self.result = ArchitecturalIntentResult.model_validate(valid_result_data())
        self.error: Exception | None = None

    async def health(self) -> ProviderHealth:
        return ProviderHealth(provider="ollama", reachable=True)

    async def list_models(self) -> list[LocalModelInfo]:
        return [LocalModelInfo(name="local-model:latest", size=42)]

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
    test_client, _provider = client()

    response = test_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "llm_enabled": True,
        "provider": "ollama",
        "provider_reachable": True,
        "selected_model": "local-model:latest",
        "model_available": True,
    }


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
