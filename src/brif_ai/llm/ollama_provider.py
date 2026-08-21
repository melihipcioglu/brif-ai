"""Ollama implementation of the provider-neutral local LLM interface."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import httpx
from pydantic import ValidationError

from brif_ai.llm.compare_engine import (
    CompareFailureCategory,
    ComparePlanValidationError,
    CompareRequestAnalysis,
    analyze_compare_request,
    build_compare_plan_schema,
    render_compare_plan,
    sanitize_compare_plan,
    validate_compare_plan,
    validate_rendered_compare,
)
from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    CompareDecisionPlan,
    ConversationRequest,
    LocalModelInfo,
    MetricConversationContext,
    ProviderHealth,
)
from brif_ai.llm.policy_validator import (
    AlternativeQualityError,
    ArchitecturalIntentPolicyValidator,
    PolicyValidationError,
    UnsupportedSpatialClaimError,
    is_compare_request,
)
from brif_ai.llm.prompts import (
    COMPARE_SYSTEM_PROMPT,
    ELICITATION_ANSWER_SYSTEM_PROMPT,
    SCHEMA_REPAIR_PROMPT,
    SYSTEM_PROMPT,
    build_compare_repair_prompt,
    build_compare_user_prompt,
    build_elicitation_user_prompt,
    build_user_prompt,
)
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
    return seconds if seconds >= 0 and float(seconds) == seconds else None


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
        eval_count = _token_count(payload, "eval_count")
        eval_duration = _duration_seconds(payload, "eval_duration")
        tps: float | None = None
        if eval_count is not None and eval_duration is not None and eval_duration > 0:
            tps = round(eval_count / eval_duration, 2)
        return cls(
            total_seconds=_duration_seconds(payload, "total_duration"),
            load_seconds=_duration_seconds(payload, "load_duration"),
            prompt_tokens=_token_count(payload, "prompt_eval_count"),
            prompt_eval_seconds=_duration_seconds(payload, "prompt_eval_duration"),
            generated_tokens=eval_count,
            eval_seconds=eval_duration,
            tokens_per_second=tps,
        )


@dataclass(frozen=True, slots=True)
class OllamaAttemptRecord:
    """Safe metadata for one initial or repair generation."""

    attempt: str
    done_reason: str | None
    metrics: OllamaPerformanceMetrics | None
    failure_category: str | None


class _AttemptFailure(ProviderResponseError):
    def __init__(self, message: str, category: CompareFailureCategory) -> None:
        super().__init__(message)
        self.category = category


def _write_schema_diagnostic(
    error: Exception,
    payload: dict[str, Any],
    metrics: OllamaPerformanceMetrics | None,
    *,
    attempt: str,
    path: Path = _SCHEMA_DIAGNOSTIC_PATH,
) -> None:
    errors_list: list[dict[str, str]] = []
    if isinstance(error, ValidationError):
        for raw_err in error.errors():
            errors_list.append(
                {
                    "location": " -> ".join(str(loc) for loc in raw_err.get("loc", ())),
                    "type": str(raw_err.get("type", "validation_error")),
                    "message": str(raw_err.get("msg", "")),
                }
            )
    else:
        errors_list.append(
            {
                "location": "root",
                "type": type(error).__name__,
                "message": str(error),
            }
        )

    record: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        "attempt": attempt,
        "done": payload.get("done"),
        "done_reason": payload.get("done_reason"),
        "errors": errors_list,
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
        policy_validator: ArchitecturalIntentPolicyValidator | None = None,
    ) -> None:
        self.settings = settings
        self._client = client
        self.policy_validator = policy_validator or ArchitecturalIntentPolicyValidator()
        self.last_performance_metrics: OllamaPerformanceMetrics | None = None
        self.last_attempt_records: list[OllamaAttemptRecord] = []
        self.last_chat_call_count = 0

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
        *,
        metric_context: MetricConversationContext | None = None,
    ) -> ArchitecturalIntentResult:
        self.last_performance_metrics = None
        self.last_attempt_records = []
        self.last_chat_call_count = 0
        if not self.settings.model:
            raise ModelNotSelectedError(
                "Yerel model seçilmedi. Önce bilgisayarınızda kurulu bir model seçin."
            )

        installed_models = await self.list_models()
        if self.settings.model not in {model.name for model in installed_models}:
            raise ModelNotAvailableError("Seçilen model bu bilgisayarda kurulu değil.")

        is_compact = is_compare_request(request)
        compare_analysis = analyze_compare_request(request) if is_compact else None
        active_schema = (
            build_compare_plan_schema(compare_analysis)
            if compare_analysis is not None
            else output_schema
        )

        payload = self._build_chat_payload(
            request,
            active_schema,
            is_compact=is_compact,
            compare_analysis=compare_analysis,
            metric_context=metric_context,
        )
        self.last_chat_call_count += 1
        response = await self._request("POST", "/api/chat", json=payload)
        try:
            return self._parse_chat_response(
                response,
                request,
                attempt="initial",
                is_compact=is_compact,
                compare_analysis=compare_analysis,
                metric_context=metric_context,
            )
        except _AttemptFailure as error:
            repair_payload = self._build_chat_payload(
                request,
                active_schema,
                repair=True,
                is_compact=is_compact,
                compare_analysis=compare_analysis,
                failure_category=error.category,
                metric_context=metric_context,
            )
            self.last_chat_call_count += 1
            repair_response = await self._request("POST", "/api/chat", json=repair_payload)
            return self._parse_chat_response(
                repair_response,
                request,
                attempt="repair",
                is_compact=is_compact,
                compare_analysis=compare_analysis,
                metric_context=metric_context,
            )

    def _build_chat_payload(
        self,
        request: ConversationRequest,
        output_schema: dict[str, object],
        *,
        repair: bool = False,
        is_compact: bool = False,
        compare_analysis: CompareRequestAnalysis | None = None,
        failure_category: CompareFailureCategory | None = None,
        metric_context: MetricConversationContext | None = None,
    ) -> dict[str, object]:
        active_oq = None
        if (
            not is_compact
            and request.elicitation_context is not None
            and request.elicitation_context.open_question_topics
            and request.brief_snapshot is not None
        ):
            active_topic_val = request.elicitation_context.open_question_topics[0].value
            from brif_ai.brief.models.common import OpenQuestionStatus

            active_oq = next(
                (
                    oq
                    for oq in request.brief_snapshot.open_questions
                    if oq.status == OpenQuestionStatus.OPEN and oq.topic_key == active_topic_val
                ),
                None,
            )

        if is_compact:
            if compare_analysis is None:
                raise ValueError("compare analysis is required for a compare request")
            system_prompt = (
                build_compare_repair_prompt(
                    failure_category or CompareFailureCategory.SCHEMA_INVALID
                )
                if repair
                else COMPARE_SYSTEM_PROMPT
            )
            user_prompt = build_compare_user_prompt(request, compare_analysis)
        elif active_oq is not None:
            system_prompt = SCHEMA_REPAIR_PROMPT if repair else ELICITATION_ANSWER_SYSTEM_PROMPT
            user_prompt = build_elicitation_user_prompt(
                active_oq.id,
                active_oq.topic_key or "",
                active_oq.question,
                request.message,
                request.brief_snapshot,
            )
        else:
            system_prompt = SCHEMA_REPAIR_PROMPT if repair else SYSTEM_PROMPT
            user_prompt = build_user_prompt(request, metric_context=metric_context)

        return {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
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
        request: ConversationRequest,
        *,
        attempt: str,
        is_compact: bool = False,
        compare_analysis: CompareRequestAnalysis | None = None,
        metric_context: MetricConversationContext | None = None,
    ) -> ArchitecturalIntentResult:
        raw_payload: object | None = None
        response_payload: dict[str, Any] = {}
        metrics: OllamaPerformanceMetrics | None = None
        done_reason: str | None = None
        try:
            raw_payload = response.json()
            if not isinstance(raw_payload, dict):
                raise TypeError("response payload must be an object")
            response_payload = cast(dict[str, Any], raw_payload)
            metrics = OllamaPerformanceMetrics.from_response(response_payload)
            self.last_performance_metrics = metrics
            raw_done_reason = response_payload.get("done_reason")
            done_reason = raw_done_reason if isinstance(raw_done_reason, str) else None
            message = response_payload["message"]
            if not isinstance(message, dict):
                raise TypeError("message must be an object")
            content = message["content"]
            if not isinstance(content, str):
                raise TypeError("message content must be a string")

            if is_compact:
                if compare_analysis is None:
                    raise ValueError("compare analysis is required for compare parsing")
                plan = CompareDecisionPlan.model_validate_json(content)
                sanitized_plan = sanitize_compare_plan(plan, request)
                validate_compare_plan(sanitized_plan, request, compare_analysis)
                parsed_result = render_compare_plan(
                    sanitized_plan,
                    request,
                    compare_analysis,
                )
                validate_rendered_compare(parsed_result, request, compare_analysis)
            else:
                data = json.loads(content)
                if isinstance(data, dict):
                    if (
                        request.elicitation_context is not None
                        and request.elicitation_context.open_question_topics
                    ):
                        data["proposed_actions"] = []
                    mutations = data.get("proposed_brief_mutations")
                    if isinstance(mutations, list):
                        valid_muts = []
                        for m in mutations:
                            if isinstance(m, dict) and any(
                                m.get(k) is not None
                                for k in ("brief_item", "space_request", "usage_scenario")
                            ):
                                valid_muts.append(m)
                        data["proposed_brief_mutations"] = valid_muts
                    if (
                        data.get("proposed_brief_mutations")
                        or data.get("proposed_actions")
                        or data.get("proposed_spatial_relationships")
                        or data.get("proposed_metric_requirements")
                    ):
                        data["needs_user_confirmation"] = True
                        data["needs_follow_up"] = False
                        data["follow_up_question"] = None
                        data["follow_up_topic"] = None
                    parsed_result = ArchitecturalIntentResult.model_validate(data)
                else:
                    parsed_result = ArchitecturalIntentResult.model_validate_json(content)

            if is_compact:
                sanitized = parsed_result
            else:
                sanitized = self.policy_validator.sanitize(
                    parsed_result, request, metric_context=metric_context
                )
            self.policy_validator.validate_semantic_integrity(
                sanitized, request, metric_context=metric_context
            )
            self.last_attempt_records.append(
                OllamaAttemptRecord(
                    attempt=attempt,
                    done_reason=done_reason,
                    metrics=metrics,
                    failure_category=None,
                )
            )
            return sanitized
        except (KeyError, TypeError, ValueError, ValidationError, PolicyValidationError) as error:
            if isinstance(error, ComparePlanValidationError):
                category = error.category
            elif isinstance(error, UnsupportedSpatialClaimError):
                category = CompareFailureCategory.UNSUPPORTED_SPATIAL_CLAIM
            elif isinstance(error, AlternativeQualityError):
                category = CompareFailureCategory.LANGUAGE_QUALITY
            else:
                category = CompareFailureCategory.SCHEMA_INVALID
            self.last_attempt_records.append(
                OllamaAttemptRecord(
                    attempt=attempt,
                    done_reason=done_reason,
                    metrics=metrics,
                    failure_category=category.value,
                )
            )
            _write_schema_diagnostic(
                error,
                response_payload,
                metrics,
                attempt=attempt,
            )
            raise _AttemptFailure(
                "Yerel model doğrulanabilir bir mimari niyet yanıtı üretmedi.", category
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
                    trust_env=False,
                ) as client:
                    response = await client.request(method, path, json=json)
            response.raise_for_status()
            return response
        except httpx.TimeoutException as error:
            _write_schema_diagnostic(
                error,
                {},
                self.last_performance_metrics,
                attempt="timeout",
            )
            raise ProviderTimeoutError("Yerel yapay zekâ isteği zaman aşımına uğradı.") from error
        except (httpx.ConnectError, httpx.NetworkError, httpx.HTTPStatusError) as error:
            raise ProviderUnavailableError(
                "Yerel yapay zekâ servisine ulaşılamadı. Ollamanın çalıştığını kontrol edin."
            ) from error
