"""Shared enums for BRIF.AI user brief v0 contracts."""

from __future__ import annotations

import sys
from enum import Enum

if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:  # pragma: no cover - Python 3.10 local tooling compatibility

    class StrEnum(str, Enum):  # noqa: UP042
        pass


class BriefItemKind(StrEnum):
    NEED = "NEED"
    PREFERENCE = "PREFERENCE"
    CONSTRAINT = "CONSTRAINT"
    GOAL = "GOAL"


class Priority(StrEnum):
    MUST = "MUST"
    SHOULD = "SHOULD"
    COULD = "COULD"
    UNSPECIFIED = "UNSPECIFIED"


class ConfirmationStatus(StrEnum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class EvidenceSource(StrEnum):
    CHAT = "CHAT"
    FORM = "FORM"
    VISUAL_STIMULUS = "VISUAL_STIMULUS"
    ARCHITECT_NOTE = "ARCHITECT_NOTE"


class ContradictionStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class OpenQuestionStatus(StrEnum):
    OPEN = "OPEN"
    ANSWERED = "ANSWERED"
    DISMISSED = "DISMISSED"
