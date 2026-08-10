"""Developer acceptance matrix for the structured compare engine and a real Ollama model."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from brif_ai.llm.compare_engine import analyze_compare_request
from brif_ai.llm.contracts import (
    ActiveContextSnapshot,
    CompareMode,
    ConversationRequest,
    VisibleEntity,
)
from brif_ai.llm.ollama_provider import OllamaAttemptRecord, OllamaProvider
from brif_ai.llm.provider import LocalLLMError, ProviderResponseError
from brif_ai.llm.service import LocalLLMConversationService
from brif_ai.llm.settings import LocalLLMSettings

_RESIDENTIAL_CONTEXT_TERMS = (
    "yaşam düzeni",
    "gündelik yaşam",
    "aile birliği",
    "birlikte geçirilen zaman",
    "sohbet",
)


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    message: str
    entity_names: tuple[str, ...]
    expected_mode: CompareMode
    expected_context_signal_groups: tuple[tuple[str, ...], ...] = ()
    forbidden_unless_grounded: tuple[str, ...] = ()


SCENARIOS = (
    Scenario(
        name="A_OPEN_RESIDENTIAL",
        message=(
            "Salon ile mutfak arasındaki ilişkiyi güçlendirmek istiyorum. "
            "Teras da günlük oturma ve sohbet alanına yakın olsun. "
            "Bana iki farklı düzenleme alternatifi öner."
        ),
        entity_names=("Salon", "Mutfak", "Teras"),
        expected_mode=CompareMode.OPEN_ALTERNATIVES,
        expected_context_signal_groups=(("sohbet", "etkileşim"),),
    ),
    Scenario(
        name="B_EXPLICIT_AXES_BEDROOM",
        message=(
            "Ebeveyn yatak odası ile giyinme alanı için iki farklı düzenleme yaklaşımı öner. "
            "Birinde mahremiyet, diğerinde kullanım kolaylığı daha baskın olsun."
        ),
        entity_names=("Ebeveyn Yatak Odası", "Giyinme Alanı"),
        expected_mode=CompareMode.EXPLICIT_AXES,
    ),
    Scenario(
        name="C_EXPLICIT_AXES_WORK",
        message=(
            "Çalışma alanı ile aile yaşam alanı için iki yaklaşım öner. "
            "Birinde sessizlik ve odaklanma, diğerinde aileyle etkileşim daha önemli olsun."
        ),
        entity_names=("Çalışma Alanı", "Aile Yaşam Alanı"),
        expected_mode=CompareMode.EXPLICIT_AXES,
    ),
    Scenario(
        name="D_OPEN_UNKNOWN",
        message=(
            "Atölye ile sergi alanının birlikte çalışması için iki farklı organizasyon "
            "yaklaşımı öner."
        ),
        entity_names=("Atölye", "Sergi Alanı"),
        expected_mode=CompareMode.OPEN_ALTERNATIVES,
        expected_context_signal_groups=(("koordinasyon", "işlevsel", "işleyiş"),),
        forbidden_unless_grounded=_RESIDENTIAL_CONTEXT_TERMS,
    ),
    Scenario(
        name="E_OPEN_UNKNOWN_2",
        message=(
            "Kütüphane ile çok amaçlı salon arasındaki kullanım ilişkisi için iki alternatif öner."
        ),
        entity_names=("Kütüphane", "Çok Amaçlı Salon"),
        expected_mode=CompareMode.OPEN_ALTERNATIVES,
        expected_context_signal_groups=(("esnek", "değişen", "dönüş"),),
        forbidden_unless_grounded=_RESIDENTIAL_CONTEXT_TERMS,
    ),
    Scenario(
        name="F_ENTITY_CHOICE",
        message=(
            "Salon kullanımını mı teras kullanımını mı öne çıkarmalıyım? İki seçeneği karşılaştır."
        ),
        entity_names=("Salon", "Teras"),
        expected_mode=CompareMode.ENTITY_CHOICE,
    ),
    Scenario(
        name="G_ENTITY_CHOICE_2",
        message=(
            "Açık mutfak mı kapalı mutfak mı bizim kullanımımız için daha uygun? "
            "İki yaklaşımı karşılaştır."
        ),
        entity_names=("Açık Mutfak", "Kapalı Mutfak"),
        expected_mode=CompareMode.ENTITY_CHOICE,
    ),
    Scenario(
        name="H_CHILDREN",
        message=(
            "Çocukların oyun alanı için iki kullanım yaklaşımı öner. "
            "Birinde düzen ve kontrol, diğerinde esneklik ve serbest kullanım ön planda olsun."
        ),
        entity_names=("Oyun Alanı",),
        expected_mode=CompareMode.EXPLICIT_AXES,
    ),
    Scenario(
        name="I_NONRESIDENTIAL",
        message=(
            "Muayene alanı ile bekleme alanının kullanım ilişkisi için iki farklı yaklaşım öner. "
            "Hasta mahremiyeti önemli."
        ),
        entity_names=("Muayene Alanı", "Bekleme Alanı"),
        expected_mode=CompareMode.OPEN_ALTERNATIVES,
        expected_context_signal_groups=(("mahrem",), ("akış", "işleyiş")),
        forbidden_unless_grounded=_RESIDENTIAL_CONTEXT_TERMS,
    ),
    Scenario(
        name="J_EDUCATION",
        message=(
            "Sınıf ile ortak çalışma alanının ilişkisi için iki alternatif öner. "
            "Öğrencilerin hem odaklanabilmesini hem gerektiğinde birlikte "
            "çalışabilmesini istiyorum."
        ),
        entity_names=("Sınıf", "Ortak Çalışma Alanı"),
        expected_mode=CompareMode.OPEN_ALTERNATIVES,
        expected_context_signal_groups=(
            ("odak", "dikkat"),
            ("birlikte çalışma", "bilgi paylaş", "ortak çalışma"),
        ),
        forbidden_unless_grounded=_RESIDENTIAL_CONTEXT_TERMS,
    ),
    Scenario(
        name="K_TRUSTED_SPATIAL",
        message=(
            "Teras salonun hemen yanında olsun. "
            "Bu ilişkiyi koruyan iki farklı kullanım yaklaşımı öner."
        ),
        entity_names=("Teras", "Salon"),
        expected_mode=CompareMode.OPEN_ALTERNATIVES,
        forbidden_unless_grounded=_RESIDENTIAL_CONTEXT_TERMS,
    ),
    Scenario(
        name="L_DIRECTION_TRUST",
        message=(
            "Kuzeydeki çalışma odası için iki farklı kullanım yaklaşımı öner. "
            "Birinde bireysel çalışma, diğerinde iki kişinin birlikte çalışması önemli."
        ),
        entity_names=("Çalışma Odası",),
        expected_mode=CompareMode.EXPLICIT_AXES,
    ),
    Scenario(
        name="M_CONTEXT_LAB_PREP",
        message=(
            "Laboratuvar ile hazırlık alanının birlikte işleyişi için iki farklı "
            "organizasyon yaklaşımı öner."
        ),
        entity_names=("Laboratuvar", "Hazırlık Alanı"),
        expected_mode=CompareMode.OPEN_ALTERNATIVES,
        expected_context_signal_groups=(("koordinasyon", "işlevsel", "işleyiş"),),
        forbidden_unless_grounded=_RESIDENTIAL_CONTEXT_TERMS,
    ),
    Scenario(
        name="N_CONTEXT_MUSIC_RECORDING",
        message=(
            "Müzik stüdyosu ile kayıt alanının birlikte çalışması için iki farklı "
            "kullanım yaklaşımı öner."
        ),
        entity_names=("Müzik Stüdyosu", "Kayıt Alanı"),
        expected_mode=CompareMode.OPEN_ALTERNATIVES,
        expected_context_signal_groups=(("koordinasyon", "işlevsel", "işleyiş"),),
        forbidden_unless_grounded=_RESIDENTIAL_CONTEXT_TERMS,
    ),
    Scenario(
        name="O_CONTEXT_FOYER_EXHIBITION",
        message=(
            "Fuaye ile sergi alanının ziyaretçi işleyişini desteklemesi için iki farklı "
            "organizasyon yaklaşımı öner."
        ),
        entity_names=("Fuaye", "Sergi Alanı"),
        expected_mode=CompareMode.OPEN_ALTERNATIVES,
        expected_context_signal_groups=(("sıra", "işleyiş", "akış"),),
        forbidden_unless_grounded=_RESIDENTIAL_CONTEXT_TERMS,
    ),
    Scenario(
        name="P_CONTEXT_MEDITATION_FOCUS",
        message=(
            "Meditasyon odası ile çalışma nişinin odak gerektiren kullanımı için iki "
            "farklı yaklaşım öner."
        ),
        entity_names=("Meditasyon Odası", "Çalışma Nişi"),
        expected_mode=CompareMode.OPEN_ALTERNATIVES,
        expected_context_signal_groups=(("odak", "dikkat"),),
        forbidden_unless_grounded=_RESIDENTIAL_CONTEXT_TERMS,
    ),
    Scenario(
        name="Q_CONTEXT_PRODUCTION_SUPPORT",
        message=(
            "Üretim alanı ile malzeme hazırlık alanının üretim akışı için iki farklı "
            "organizasyon yaklaşımı öner."
        ),
        entity_names=("Üretim Alanı", "Malzeme Hazırlık Alanı"),
        expected_mode=CompareMode.OPEN_ALTERNATIVES,
        expected_context_signal_groups=(("koordinasyon", "işlevsel", "işleyiş"),),
        forbidden_unless_grounded=_RESIDENTIAL_CONTEXT_TERMS,
    ),
    Scenario(
        name="R_CONTEXT_TEAM_FLEX",
        message=(
            "Toplantı alanı ile proje alanının değişen ekip kullanımlarına uyumu için "
            "iki farklı yaklaşım öner."
        ),
        entity_names=("Toplantı Alanı", "Proje Alanı"),
        expected_mode=CompareMode.OPEN_ALTERNATIVES,
        expected_context_signal_groups=(("esnek", "değişen", "dönüş"),),
        forbidden_unless_grounded=_RESIDENTIAL_CONTEXT_TERMS,
    ),
)

_CROSS_LEAK_TERMS = (
    "salon",
    "mutfak",
    "teras",
    "mahremiyet",
    "kullanım kolaylığı",
)


def build_request(scenario: Scenario) -> ConversationRequest:
    active = ActiveContextSnapshot(
        project_id="acceptance_project",
        building_id="acceptance_building",
        level_id="acceptance_level",
        zone_id="acceptance_zone",
        entity_id=None,
        context_fingerprint=f"acceptance|{scenario.name.casefold()}",
        generation_id=1,
    )
    entities = [
        VisibleEntity(
            entity_id=f"acceptance_space_{scenario.name.casefold()}_{index}",
            entity_type="space",
            name=name,
            project_id=active.project_id,
            building_id=active.building_id,
            level_id=active.level_id,
            zone_id=active.zone_id,
        )
        for index, name in enumerate(scenario.entity_names)
    ]
    return ConversationRequest(
        message=scenario.message,
        active_context=active,
        visible_entities=entities,
    )


def _metric(record: OllamaAttemptRecord | None, field: str) -> int | float | None:
    if record is None or record.metrics is None:
        return None
    value = getattr(record.metrics, field)
    return value if isinstance(value, (int, float)) else None


def _acceptance_failure(
    scenario: Scenario,
    mode: CompareMode,
    assistant_message: str,
) -> str | None:
    if mode is not scenario.expected_mode:
        return f"mode mismatch: expected {scenario.expected_mode.value}, got {mode.value}"
    for heading in ("Alternatif 1", "Alternatif 2", "Temel fark:"):
        if heading not in assistant_message:
            return f"missing final heading: {heading}"
    lowered_message = scenario.message.casefold()
    lowered_output = assistant_message.casefold()
    for term in _CROSS_LEAK_TERMS:
        if term not in lowered_message and term in lowered_output:
            return f"semantic cross-leakage: {term}"
    for signal_group in scenario.expected_context_signal_groups:
        if not any(signal in lowered_output for signal in signal_group):
            return f"missing context signal: {' / '.join(signal_group)}"
    for forbidden in scenario.forbidden_unless_grounded:
        if forbidden not in lowered_message and forbidden in lowered_output:
            return f"ungrounded context language: {forbidden}"
    for forbidden in ("entity", "target", "enum", "visible_entities", "proposed_actions"):
        if forbidden in lowered_output:
            return f"internal jargon: {forbidden}"
    return None


async def run_scenario(
    scenario: Scenario,
    settings: LocalLLMSettings,
) -> dict[str, object]:
    request = build_request(scenario)
    analysis = analyze_compare_request(request)
    provider = OllamaProvider(settings)
    service = LocalLLMConversationService(settings, provider)
    started_at = time.perf_counter()
    response = None
    error: str | None = None
    try:
        response = await service.interpret(request)
    except LocalLLMError as caught:
        error = type(caught).__name__
    elapsed = time.perf_counter() - started_at

    final_record = provider.last_attempt_records[-1] if provider.last_attempt_records else None
    assistant_message = (
        response.result.assistant_message
        if response is not None and response.success and response.result is not None
        else None
    )
    intent = (
        response.result.intent.value
        if response is not None and response.success and response.result is not None
        else None
    )
    if error is None and assistant_message is not None:
        error = _acceptance_failure(scenario, analysis.mode, assistant_message)
        result = response.result
        if intent != "compare_alternatives":
            error = error or f"intent mismatch: {intent}"
        if result is not None and (
            result.proposed_actions
            or result.needs_user_confirmation
            or result.needs_follow_up
            or result.follow_up_question is not None
        ):
            error = error or "public compare contract invariant failed"
    elif error is None:
        error = response.error if response is not None else "missing response"

    return {
        "prompt_name": scenario.name,
        "mode": analysis.mode.value,
        "intent": intent,
        "attempt": final_record.attempt if final_record is not None else None,
        "call_count": provider.last_chat_call_count,
        "prompt_tokens": _metric(final_record, "prompt_tokens"),
        "generated_tokens": _metric(final_record, "generated_tokens"),
        "done_reason": final_record.done_reason if final_record is not None else None,
        "total_seconds": round(elapsed, 2),
        "success": error is None,
        "error": error,
        "attempt_records": [asdict(record) for record in provider.last_attempt_records],
        "assistant_message": assistant_message,
    }


def _diversity_failure(results: list[dict[str, object]]) -> str | None:
    messages = [
        str(result["assistant_message"]).casefold()
        for result in results
        if result.get("assistant_message")
    ]
    if not messages:
        return None
    mechanical = sum("bu seçenekte" in message for message in messages)
    if mechanical > 3:
        return f"mechanical sentence skeleton repeated in {mechanical} scenarios"
    if len(set(messages)) != len(messages):
        return "duplicate final responses detected"
    open_title_pairs: set[tuple[str, str]] = set()
    for result in results:
        if result.get("mode") != CompareMode.OPEN_ALTERNATIVES.value:
            continue
        message = str(result.get("assistant_message") or "")
        headings = re.findall(r"Alternatif [12] - ([^:]+):", message)
        if len(headings) == 2:
            open_title_pairs.add((headings[0], headings[1]))
    if len(open_title_pairs) < min(
        3, sum(result.get("mode") == "open_alternatives" for result in results)
    ):
        return "open-mode decision families are not diverse enough"
    return None


async def run_matrix(
    model: str,
    ollama_url: str,
    scenario_names: tuple[str, ...] = (),
) -> tuple[int, list[dict[str, object]]]:
    settings = LocalLLMSettings(
        enabled=True,
        base_url=ollama_url,
        model=model,
        timeout_seconds=300.0,
        temperature=0.0,
        think=False,
        num_predict=512,
    )
    prerequisite_provider = OllamaProvider(settings)
    try:
        models = await prerequisite_provider.list_models()
    except ProviderResponseError:
        print("SKIPPED: Ollama model list could not be validated.")
        return 0, []
    except LocalLLMError:
        print("SKIPPED: loopback Ollama is not reachable.")
        return 0, []
    if model not in {item.name for item in models}:
        print(f"SKIPPED: model '{model}' is not installed.")
        return 0, []

    selected_scenarios = (
        tuple(scenario for scenario in SCENARIOS if scenario.name in scenario_names)
        if scenario_names
        else SCENARIOS
    )
    results: list[dict[str, object]] = []
    for scenario in selected_scenarios:
        result = await run_scenario(scenario, settings)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))

    diversity_error = _diversity_failure(results)
    if diversity_error is not None:
        print(json.dumps({"matrix_error": diversity_error}, ensure_ascii=False))
    passed = diversity_error is None and all(result["success"] is True for result in results)
    print(
        json.dumps(
            {
                "summary": "PASSED" if passed else "FAILED",
                "passed": sum(result["success"] is True for result in results),
                "total": len(results),
                "diversity_error": diversity_error,
            },
            ensure_ascii=False,
        )
    )
    return (0 if passed else 1), results


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the real Ollama compare acceptance matrix")
    parser.add_argument("--model", default="qwen3:4b-instruct")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument(
        "--scenario",
        action="append",
        choices=[scenario.name for scenario in SCENARIOS],
        default=[],
        help="Run only a named scenario; repeat to select multiple scenarios",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    try:
        exit_code, results = asyncio.run(
            run_matrix(args.model, args.ollama_url, tuple(args.scenario))
        )
    except (OSError, ValueError):
        print("FAILED: acceptance configuration is invalid.")
        return 2
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
