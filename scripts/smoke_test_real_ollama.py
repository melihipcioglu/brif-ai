"""Optional end-to-end smoke test against a real loopback Ollama instance."""

from __future__ import annotations

import argparse
import asyncio
import time

from brif_ai.llm.contracts import ConversationInterpretationResponse, ConversationRequest
from brif_ai.llm.ollama_provider import OllamaProvider
from brif_ai.llm.policy_validator import (
    ArchitecturalIntentPolicyValidator,
    PolicyValidationError,
)
from brif_ai.llm.provider import (
    LocalLLMError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from brif_ai.llm.service import LocalLLMConversationService
from brif_ai.llm.settings import LocalLLMSettings


class SmokeValidationError(RuntimeError):
    """A real response failed the smoke test's public safety checks."""


def build_smoke_request() -> ConversationRequest:
    """Build a small fixed request without accepting or logging user content."""

    return ConversationRequest.model_validate(
        {
            "message": "Çalışma odası sessiz olsun ama salondan tamamen kopmasın.",
            "active_context": {
                "project_id": "smoke_project",
                "building_id": "smoke_building",
                "level_id": "smoke_ground",
                "zone_id": "smoke_living",
                "entity_id": "smoke_study",
                "context_fingerprint": "smoke|building|ground|living|study",
                "generation_id": 1,
            },
            "visible_entities": [
                {
                    "entity_id": "smoke_study",
                    "entity_type": "space",
                    "name": "Çalışma Odası",
                    "project_id": "smoke_project",
                    "building_id": "smoke_building",
                    "level_id": "smoke_ground",
                    "zone_id": "smoke_living",
                }
            ],
            "conversation_summary": "",
            "current_decisions": [],
            "pending_proposals": [],
        }
    )


def validate_smoke_response(
    response: ConversationInterpretationResponse,
    request: ConversationRequest,
) -> None:
    """Recheck schema, public language, context, and safe targeting invariants."""

    if not response.success or response.result is None:
        raise SmokeValidationError("interpretation was not successful")
    if response.context_fingerprint != request.active_context.context_fingerprint:
        raise SmokeValidationError("response context does not match the request")

    ArchitecturalIntentPolicyValidator().validate_semantic_integrity(response.result, request)
    visible_ids = {entity.entity_id for entity in request.visible_entities}
    for action in response.result.proposed_actions:
        if action.target_entity_id is not None and action.target_entity_id not in visible_ids:
            raise SmokeValidationError("response targets an entity outside the visible context")


async def run_smoke(model: str, ollama_url: str) -> int:
    settings = LocalLLMSettings(
        enabled=True,
        base_url=ollama_url,
        model=model,
        timeout_seconds=300.0,
        temperature=0.0,
        think=False,
        num_predict=512,
    )
    provider = OllamaProvider(settings)

    try:
        models = await provider.list_models()
    except (ProviderUnavailableError, ProviderTimeoutError):
        print("SKIPPED / prerequisites missing: loopback Ollama is not reachable.")
        return 0
    except ProviderResponseError:
        print("FAILED: Ollama model list response is invalid.")
        return 1

    if model not in {item.name for item in models}:
        print(f"SKIPPED / prerequisites missing: model '{model}' is not installed.")
        return 0

    request = build_smoke_request()
    service = LocalLLMConversationService(settings, provider)
    started_at = time.perf_counter()
    try:
        response = await service.interpret(request)
        validate_smoke_response(response, request)
    except (LocalLLMError, PolicyValidationError, SmokeValidationError):
        print("FAILED: real Ollama response did not pass schema and safety validation.")
        return 1
    elapsed = time.perf_counter() - started_at

    metrics = provider.last_performance_metrics
    generated_tokens = metrics.generated_tokens if metrics is not None else None
    tokens_per_second = metrics.tokens_per_second if metrics is not None else None
    print("PASSED: real Ollama smoke test completed.")
    print(f"model={model}")
    print(f"total_seconds={elapsed:.2f}")
    print(f"generated_tokens={generated_tokens if generated_tokens is not None else 'n/a'}")
    print(f"tokens_per_second={tokens_per_second if tokens_per_second is not None else 'n/a'}")
    return 0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BRIF.AI real loopback Ollama smoke test")
    parser.add_argument("--model", required=True, help="Exact installed Ollama model name")
    parser.add_argument(
        "--ollama-url",
        default="http://127.0.0.1:11434",
        help="Loopback Ollama base URL",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    try:
        return asyncio.run(run_smoke(args.model, args.ollama_url))
    except (ValueError, OSError):
        print("FAILED: smoke test configuration is invalid.")
        return 2
    except Exception:
        print("FAILED: smoke test could not be completed safely.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
