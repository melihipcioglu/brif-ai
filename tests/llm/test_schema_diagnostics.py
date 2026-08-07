from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from brif_ai.llm.contracts import ArchitecturalIntentResult
from brif_ai.llm.ollama_provider import (
    OllamaPerformanceMetrics,
    _write_schema_diagnostic,
)


def test_schema_diagnostic_omits_model_and_user_text(tmp_path: Path) -> None:
    invalid = {
        "assistant_message": "özel kullanıcı metni",
        "intent": "modify_space",
        "target": {},
        "user_requirements": "dizi değil",
    }
    try:
        ArchitecturalIntentResult.model_validate(invalid)
    except ValidationError as error:
        diagnostic_path = tmp_path / "llm_schema_errors.jsonl"
        _write_schema_diagnostic(
            error,
            {"done": True, "done_reason": "stop", "message": {"content": "gizli model çıktısı"}},
            OllamaPerformanceMetrics(
                total_seconds=1.0,
                load_seconds=0.1,
                prompt_tokens=100,
                prompt_eval_seconds=0.2,
                generated_tokens=50,
                eval_seconds=0.5,
                tokens_per_second=100.0,
            ),
            attempt="repair",
            path=diagnostic_path,
        )
    else:  # pragma: no cover
        raise AssertionError("invalid result should fail validation")

    raw = diagnostic_path.read_text(encoding="utf-8")
    record = json.loads(raw)

    assert record["attempt"] == "repair"
    assert record["done_reason"] == "stop"
    assert record["metrics"]["generated_tokens"] == 50
    assert any(item["location"] == "user_requirements" for item in record["errors"])
    assert "özel kullanıcı metni" not in raw
    assert "gizli model çıktısı" not in raw


def test_timeout_diagnostic_omits_raw_text(tmp_path: Path) -> None:
    diagnostic_path = tmp_path / "llm_schema_errors.jsonl"
    _write_schema_diagnostic(
        TimeoutError("Yerel yapay zekâ isteği zaman aşımına uğradı."),
        {},
        None,
        attempt="timeout",
        path=diagnostic_path,
    )

    raw = diagnostic_path.read_text(encoding="utf-8")
    record = json.loads(raw)

    assert record["attempt"] == "timeout"
    assert record["done"] is None
    assert record["metrics"] is None
    assert any(item["type"] == "TimeoutError" for item in record["errors"])
