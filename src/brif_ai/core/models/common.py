"""Shared types for BRIF.AI core v0 contracts."""

from __future__ import annotations

import sys
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:  # pragma: no cover - Python 3.10 local tooling compatibility

    class StrEnum(str, Enum):  # noqa: UP042
        pass


OBJECT_ID_PATTERN = r"^[a-z][a-z0-9_-]{0,63}$"

ObjectId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=64, pattern=OBJECT_ID_PATTERN),
]
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ContractModel(BaseModel):
    """Base model configuration for strict v0 data contracts."""

    model_config = ConfigDict(extra="forbid")


class SpaceFunction(StrEnum):
    ENTRANCE = "ENTRANCE"
    CIRCULATION = "CIRCULATION"
    LIVING = "LIVING"
    SLEEPING = "SLEEPING"
    COOKING = "COOKING"
    SANITARY = "SANITARY"
    WORK = "WORK"
    STORAGE = "STORAGE"
    TECHNICAL = "TECHNICAL"
    OTHER = "OTHER"


class EntryRole(StrEnum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    SERVICE = "SERVICE"


class DoorType(StrEnum):
    STANDARD = "STANDARD"
    SLIDING = "SLIDING"
    OTHER = "OTHER"


class PassageDirection(StrEnum):
    BIDIRECTIONAL = "BIDIRECTIONAL"
    A_TO_B = "A_TO_B"
    B_TO_A = "B_TO_A"


class VerticalConnectorType(StrEnum):
    STAIR = "STAIR"
    ELEVATOR = "ELEVATOR"
    RAMP = "RAMP"


class IssueSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ValidationStatus(StrEnum):
    PASS = "PASS"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    BLOCKED = "BLOCKED"


class ObjectType(StrEnum):
    PROJECT = "PROJECT"
    LEVEL = "LEVEL"
    SPACE = "SPACE"
    ENTRY_POINT = "ENTRY_POINT"
    DOOR = "DOOR"
    OPEN_PASSAGE = "OPEN_PASSAGE"
    VERTICAL_CONNECTOR = "VERTICAL_CONNECTOR"
