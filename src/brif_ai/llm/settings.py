"""Environment-backed settings for the local-only LLM connection."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from urllib.parse import urlparse


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError(f"invalid boolean setting: {value!r}")


@dataclass(frozen=True, slots=True)
class LocalLLMSettings:
    enabled: bool = False
    provider: str = "ollama"
    base_url: str = "http://127.0.0.1:11434"
    model: str = ""
    timeout_seconds: float = 120.0
    temperature: float = 0.0
    think: bool = False
    keep_alive: str = "30m"
    num_predict: int = 1024

    def __post_init__(self) -> None:
        if self.provider != "ollama":
            raise ValueError(f"unsupported local LLM provider: {self.provider!r}")
        if self.timeout_seconds <= 0:
            raise ValueError("BRIF_AI_LLM_TIMEOUT_SECONDS must be greater than zero")
        if self.temperature != 0:
            raise ValueError("BRIF_AI_LLM_TEMPERATURE must be 0 for the MVP")
        if self.think:
            raise ValueError("BRIF_AI_LLM_THINK must be false for the MVP")
        if not self.keep_alive.strip():
            raise ValueError("BRIF_AI_LLM_KEEP_ALIVE must not be empty")
        if not 1 <= self.num_predict <= 4096:
            raise ValueError("BRIF_AI_LLM_NUM_PREDICT must be between 1 and 4096")

        parsed = urlparse(self.base_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("BRIF_AI_LLM_BASE_URL must use HTTP on a loopback host")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> LocalLLMSettings:
        values = environ if environ is not None else MappingProxyType(os.environ)
        return cls(
            enabled=_parse_bool(values.get("BRIF_AI_LLM_ENABLED", "false")),
            provider=values.get("BRIF_AI_LLM_PROVIDER", "ollama").strip().lower(),
            base_url=values.get("BRIF_AI_LLM_BASE_URL", "http://127.0.0.1:11434").rstrip("/"),
            model=values.get("BRIF_AI_LLM_MODEL", "").strip(),
            timeout_seconds=float(values.get("BRIF_AI_LLM_TIMEOUT_SECONDS", "120")),
            temperature=float(values.get("BRIF_AI_LLM_TEMPERATURE", "0")),
            think=_parse_bool(values.get("BRIF_AI_LLM_THINK", "false")),
            keep_alive=values.get("BRIF_AI_LLM_KEEP_ALIVE", "30m").strip(),
            num_predict=int(values.get("BRIF_AI_LLM_NUM_PREDICT", "1024")),
        )
