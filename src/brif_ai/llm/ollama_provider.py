"""Ollama implementation of the provider-neutral local LLM interface."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import httpx
from pydantic import ValidationError

from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    ConversationRequest,
    LocalModelInfo,
    ProviderHealth,
)
from brif_ai.llm.prompts import SCHEMA_REPAIR_PROMPT, SYSTEM_PROMPT, build_user_prompt
from brif_ai.llm.provider import (
    ModelNotAvailableError,
    ModelNotSelectedError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from brif_ai.llm.settings import LocalLLMSettings

_NANOSECONDS_PER_SECOND = 1_000_000_000
_SCHEMA_DIAGNOSTIC_PATH = Path(".demo_logs") / "llm_schema_errors.jsonl"


def _duration_seconds(payload: dict[str, Any], field: str) -> float | None:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    seconds = float(value) / _NANOSECONDS_PER_SECOND
    return seconds if seconds >= 0 and math.isfinite(seconds) else None


def _token_count(payload: dict[str, Any], field: str) -> int | None:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


@dataclass(frozen=True, slots=True)
class OllamaPerformanceMetrics:
    """Non-sensitive timing and token counters returned by Ollama."""

    total_seconds: float | None
    load_seconds: float | None
    prompt_tokens: int | None
    prompt_eval_seconds: float | None
    generated_tokens: int | None
    eval_seconds: float | None
    tokens_per_second: float | None

    @classmethod
    def from_response(cls, payload: dict[str, Any]) -> OllamaPerformanceMetrics:
        eval_seconds = _duration_seconds(payload, "eval_duration")
        generated_tokens = _token_count(payload, "eval_count")
        tokens_per_second = (
            generated_tokens / eval_seconds
            if generated_tokens is not None and eval_seconds is not None and eval_seconds > 0
            else None
        )
        return cls(
            total_seconds=_duration_seconds(payload, "total_duration"),
            load_seconds=_duration_seconds(payload, "load_duration"),
            prompt_tokens=_token_count(payload, "prompt_eval_count"),
            prompt_eval_seconds=_duration_seconds(payload, "prompt_eval_duration"),
            generated_tokens=generated_tokens,
            eval_seconds=eval_seconds,
            tokens_per_second=tokens_per_second,
        )


def _safe_error_details(error: Exception) -> list[dict[str, str]]:
    if isinstance(error, ValidationError):
        details: list[dict[str, str]] = []
        for item in error.errors():
            location = ".".join(str(part) for part in item.get("loc", ()))
            details.append(
                {
                    "location": location,
                    "type": str(item.get("type", "validation_error")),
                    "message": str(item.get("msg", "Schema doğrulama hatası.")),
                }
            )
        return details
    return [
        {
            "location": "response",
            "type": type(error).__name__,
            "message": str(error),
        }
    ]


def _write_schema_diagnostic(
    error: Exception,
    payload: dict[str, Any],
    metrics: OllamaPerformanceMetrics | None,
    *,
    attempt: str,
    path: Path = _SCHEMA_DIAGNOSTIC_PATH,
) -> None:
    """Write validation locations and performance only; never persist model/user text."""

    record: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        "attempt": attempt,
        "done": payload.get("done"),
        "done_reason": payload.get("done_reason"),
        "errors": _safe_error_details(error),
        "metrics": asdict(metrics) if metrics is not None else None,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
    except OSError:
        pass


class OllamaProvider:
    """Use Ollama's local HTTP API without exposing it to the service layer."""

    def __init__(
        self,
        settings: LocalLLMSettings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self._client = client
        self.last_performance_metrics: OllamaPerformanceMetrics | None = None

    async def health(self) -> ProviderHealth:
        try:
            await self.list_models()
        except (ProviderUnavailableError, ProviderTimeoutError) as error:
            return ProviderHealth(provider="ollama", reachable=False, message=str(error))
        except ProviderResponseError as error:
            return ProviderHealth(provider="ollama", reachable=True, message=str(error))
        return ProviderHealth(provider="ollama", reachable=True)

    async def list_models(self) -> list[LocalModelInfo]:
        response = await self._request("GET", "/api/tags")
        try:
            payload = cast(dict[str, Any], response.json())
            raw_models = payload["models"]
            if not isinstance(raw_models, list):
                raise TypeError("models must be a list")
            models: list[LocalModelInfo] = []
            for raw_model in raw_models:
                if not isinstance(raw_model, dict):
                    raise TypeError("model entry must be an object")
                models.append(
                    LocalModelInfo(
                        name=raw_model["name"],
                        digest=raw_model.get("digest"),
                        size=raw_model.get("size"),
                        modified_at=raw_model.get("modified_at"),
                    )
                )
            return models
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            raise ProviderResponseError(
                "Ollama model listesi geçersiz bir yanıt döndürdü."
            ) from error

    async def interpret(
        self,
        request: ConversationRequest,
        output_schema: dict[str, object],
    ) -> ArchitecturalIntentResult:
        self.last_performance_metrics = None
        if not self.settings.model:
            raise ModelNotSelectedError(
                "Yerel model seçilmedi. Önce bilgisayarınızda kurulu bir model seçin."
            )

        installed_models = await self.list_models()
        if self.settings.model not in {model.name for model in installed_models}:
            raise ModelNotAvailableError("Seçilen model bu bilgisayarda kurulu değil.")

        payload = self._build_chat_payload(request, output_schema)
        response = await self._request("POST", "/api/chat", json=payload)
        try:
            return self._parse_chat_response(response, attempt="initial")
        except ProviderResponseError:
            repair_payload = self._build_chat_payload(
                request,
                output_schema,
                repair=True,
            )
            repair_response = await self._request("POST", "/api/chat", json=repair_payload)
            return self._parse_chat_response(repair_response, attempt="repair")

    def _build_chat_payload(
        self,
        request: ConversationRequest,
        output_schema: dict[str, object],
        *,
        repair: bool = False,
    ) -> dict[str, object]:
        system_prompt = SCHEMA_REPAIR_PROMPT if repair else SYSTEM_PROMPT
        return {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": build_user_prompt(request)},
            ],
            "stream": False,
            "think": self.settings.think,
            "format": output_schema,
            "keep_alive": self.settings.keep_alive,
            "options": {
                "temperature": self.settings.temperature,
                "num_predict": self.settings.num_predict,
            },
        }

    def _parse_chat_response(
        self,
        response: httpx.Response,
        *,
        attempt: str,
    ) -> ArchitecturalIntentResult:
        raw_payload: object | None = None
        response_payload: dict[str, Any] = {}
        try:
            raw_payload = response.json()
            if not isinstance(raw_payload, dict):
                raise TypeError("response payload must be an object")
            response_payload = cast(dict[str, Any], raw_payload)
            self.last_performance_metrics = OllamaPerformanceMetrics.from_response(response_payload)
            message = response_payload["message"]
            if not isinstance(message, dict):
                raise TypeError("message must be an object")
            content = message["content"]
            if not isinstance(content, str):
                raise TypeError("message content must be a string")
            return ArchitecturalIntentResult.model_validate_json(content)
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            _write_schema_diagnostic(
                error,
                response_payload,
                self.last_performance_metrics,
                attempt=attempt,
            )
            raise ProviderResponseError(
                "Yerel model doğrulanabilir bir mimari niyet yanıtı üretmedi."
            ) from error

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, object] | None = None,
    ) -> httpx.Response:
        try:
            if self._client is not None:
                response = await self._client.request(method, path, json=json)
            else:
                timeout = httpx.Timeout(self.settings.timeout_seconds)
                async with httpx.AsyncClient(
                    base_url=self.settings.base_url,
                    timeout=timeout,
                ) as client:
                    response = await client.request(method, path, json=json)
            response.raise_for_status()
            return response
        except httpx.TimeoutException as error:
            raise ProviderTimeoutError("Yerel yapay zekâ isteği zaman aşımına uğradı.") from error
        except (httpx.ConnectError, httpx.NetworkError, httpx.HTTPStatusError) as error:
            raise ProviderUnavailableError(
                "Yerel yapay zekâ servisine ulaşılamadı. Ollamanın çalıştığını kontrol edin."
            ) from error
