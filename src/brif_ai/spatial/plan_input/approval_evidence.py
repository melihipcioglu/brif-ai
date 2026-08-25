"""Immutable provenance storage for conversational plan-input approvals."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

from brif_ai.brief.models.common import EvidenceSource
from brif_ai.core.models.common import NonEmptyString, ObjectId

_PROJECT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
_EVIDENCE_ID_PATTERN = re.compile(r"^ev_[a-f0-9]{16}$")


class PlanInputApprovalEvidencePersistenceError(RuntimeError):
    """Raised when plan-input approval evidence cannot be read or published."""


class PlanInputApprovalEvidence(BaseModel):
    """One immutable, source-exact CHAT evidence record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["plan_input_approval_evidence.v0"] = "plan_input_approval_evidence.v0"
    id: ObjectId
    project_id: ObjectId
    source_type: Literal[EvidenceSource.CHAT] = EvidenceSource.CHAT
    source_reference: NonEmptyString
    user_message: NonEmptyString
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("created_at must be a timezone-aware UTC datetime.")
        return value


def generate_plan_input_approval_evidence_id(
    project_id: str,
    source_reference: str,
    user_message: str,
) -> str:
    """Generate a deterministic identity from the exact canonical source content."""
    seed = f"{project_id.strip()}|{source_reference.strip()}|{user_message.strip()}".encode()
    digest = hashlib.sha256(seed).hexdigest()[:16]
    return f"ev_{digest}"


class PlanInputApprovalEvidenceRepository:
    """Append-only JSON repository using immutable one-file-per-evidence publication."""

    def __init__(self, root_dir: str | Path | None = None) -> None:
        if root_dir is None:
            env_dir = os.getenv("BRIF_AI_DATA_DIR")
            root_dir = Path(env_dir) if env_dir else Path.home() / ".brif_ai" / "data"
        self.root_dir = Path(root_dir).resolve()

    def _validate_project_id(self, project_id: str) -> str:
        if not isinstance(project_id, str) or not project_id.strip():
            raise PlanInputApprovalEvidencePersistenceError(
                "Project ID must be a non-empty string."
            )
        clean_project_id = project_id.strip()
        if not _PROJECT_ID_PATTERN.fullmatch(clean_project_id):
            raise PlanInputApprovalEvidencePersistenceError(
                f"Invalid project ID format or illegal characters: {project_id!r}"
            )
        projects_dir = self.root_dir / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        projects_dir = projects_dir.resolve()
        project_dir = (projects_dir / clean_project_id).resolve()
        if project_dir.parent != projects_dir:
            raise PlanInputApprovalEvidencePersistenceError(
                f"Path traversal detected in project ID: {project_id!r}"
            )
        return clean_project_id

    def _evidence_dir(self, project_id: str) -> Path:
        clean_project_id = self._validate_project_id(project_id)
        path = self.root_dir / "projects" / clean_project_id / "plan_input" / "approval_evidence"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _evidence_path(self, project_id: str, evidence_id: str) -> Path:
        if not _EVIDENCE_ID_PATTERN.fullmatch(evidence_id):
            raise PlanInputApprovalEvidencePersistenceError(
                f"Invalid plan-input evidence ID: {evidence_id!r}"
            )
        return self._evidence_dir(project_id) / f"{evidence_id}.json"

    @staticmethod
    def _canonical_json(data: dict[str, Any]) -> str:
        return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def build_chat_evidence(
        cls,
        *,
        project_id: str,
        source_reference: str,
        user_message: str,
        created_at: datetime,
    ) -> PlanInputApprovalEvidence:
        clean_reference = source_reference.strip()
        clean_message = user_message.strip()
        return PlanInputApprovalEvidence(
            id=generate_plan_input_approval_evidence_id(
                project_id,
                clean_reference,
                clean_message,
            ),
            project_id=project_id,
            source_reference=clean_reference,
            user_message=clean_message,
            created_at=created_at,
        )

    def get_evidence(
        self,
        project_id: str,
        evidence_id: str,
    ) -> PlanInputApprovalEvidence | None:
        path = self._evidence_path(project_id, evidence_id)
        if not path.exists():
            return None
        try:
            with path.open(encoding="utf-8") as evidence_file:
                return PlanInputApprovalEvidence.model_validate(json.load(evidence_file))
        except Exception as error:
            raise PlanInputApprovalEvidencePersistenceError(
                f"Failed to read plan-input approval evidence '{path}': {error}"
            ) from error

    def list_evidence(self, project_id: str) -> list[PlanInputApprovalEvidence]:
        evidence_dir = self._evidence_dir(project_id)
        records: list[PlanInputApprovalEvidence] = []
        for path in sorted(evidence_dir.glob("ev_*.json"), key=lambda candidate: candidate.name):
            evidence_id = path.stem
            record = self.get_evidence(project_id, evidence_id)
            if record is not None:
                records.append(record)
        return records

    def save_chat_evidence(
        self,
        *,
        project_id: str,
        source_reference: str,
        user_message: str,
        created_at: datetime | None = None,
    ) -> PlanInputApprovalEvidence:
        """Publish or reuse an immutable deterministic CHAT evidence record."""
        timestamp = created_at or datetime.now(UTC)
        candidate = self.build_chat_evidence(
            project_id=project_id,
            source_reference=source_reference,
            user_message=user_message,
            created_at=timestamp,
        )
        path = self._evidence_path(project_id, candidate.id)
        canonical = self._canonical_json(candidate.model_dump(mode="json"))

        file_descriptor, temporary_path_string = tempfile.mkstemp(
            dir=str(path.parent), prefix="tmp_plan_input_ev_"
        )
        temporary_path = Path(temporary_path_string)
        try:
            with open(file_descriptor, "w", encoding="utf-8") as temporary_file:
                temporary_file.write(canonical)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            try:
                os.link(temporary_path, path)
                return candidate
            except FileExistsError:
                existing = self.get_evidence(project_id, candidate.id)
                if existing is None:  # pragma: no cover - defensive race guard
                    raise PlanInputApprovalEvidencePersistenceError(
                        f"Evidence path '{path}' exists but could not be read."
                    ) from None
                if (
                    existing.project_id != candidate.project_id
                    or existing.source_type != candidate.source_type
                    or existing.source_reference != candidate.source_reference
                    or existing.user_message != candidate.user_message
                ):
                    raise PlanInputApprovalEvidencePersistenceError(
                        f"Evidence ID collision for immutable record {candidate.id!r}."
                    ) from None
                return existing
        except PlanInputApprovalEvidencePersistenceError:
            raise
        except Exception as error:
            raise PlanInputApprovalEvidencePersistenceError(
                f"Failed to publish plan-input approval evidence '{path}': {error}"
            ) from error
        finally:
            with contextlib.suppress(OSError):
                temporary_path.unlink()


__all__ = [
    "PlanInputApprovalEvidence",
    "PlanInputApprovalEvidencePersistenceError",
    "PlanInputApprovalEvidenceRepository",
    "generate_plan_input_approval_evidence_id",
]
