"""BRIF.AI — Deterministic Persistent Storage for Site Geometry Approval Evidence."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from brif_ai.brief.models.common import EvidenceSource
from brif_ai.brief.models.snapshot import Evidence

_PROJECT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class SiteEvidencePersistenceError(RuntimeError):
    """Raised when persistence of site approval evidence fails."""


def _generate_site_evidence_id(project_id: str, source_reference: str, excerpt: str) -> str:
    """Deterministic Evidence ID generated from project_id, source_reference, and excerpt."""
    content = f"{project_id}|{source_reference}|{excerpt}".encode()
    digest = hashlib.sha256(content).hexdigest()[:16]
    return f"ev_{digest}"


class SiteApprovalEvidenceRepository:
    """Persistent JSON storage for site geometry Evidence records."""

    def __init__(self, root_dir: str | Path | None = None) -> None:
        if root_dir is None:
            env_dir = os.getenv("BRIF_AI_DATA_DIR")
            root_dir = Path(env_dir) if env_dir else Path.home() / ".brif_ai" / "data"
        self.root_dir = Path(root_dir).resolve()

    def _validate_project_id(self, project_id: str) -> str:
        if not isinstance(project_id, str) or not project_id.strip():
            raise SiteEvidencePersistenceError("Project ID must be a non-empty string.")
        pid = project_id.strip()
        if not _PROJECT_ID_PATTERN.match(pid):
            raise SiteEvidencePersistenceError(
                f"Invalid project ID format or illegal characters: {project_id!r}"
            )
        try:
            base_path = (self.root_dir / "projects").resolve()
            target_path = (base_path / pid).resolve()
            if target_path.parent != base_path or not str(target_path).startswith(str(base_path)):
                raise SiteEvidencePersistenceError(
                    f"Path traversal detected in project ID: {project_id!r}"
                )
        except Exception as err:
            if isinstance(err, SiteEvidencePersistenceError):
                raise
            raise SiteEvidencePersistenceError(f"Failed to resolve project path: {err}") from err
        return pid

    def _get_evidence_file_path(self, project_id: str) -> Path:
        pid = self._validate_project_id(project_id)
        path = self.root_dir / "projects" / pid / "site"
        path.mkdir(parents=True, exist_ok=True)
        return path / "evidence.json"

    def _canonical_json(self, data: Any) -> str:
        return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    def _atomic_write_json(self, target_path: Path, data: Any) -> None:
        parent_dir = target_path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        canonical_str = self._canonical_json(data)

        fd, temp_path_str = tempfile.mkstemp(dir=str(parent_dir), prefix="tmp_site_ev_")
        temp_path = Path(temp_path_str)
        try:
            with open(fd, "w", encoding="utf-8") as f:
                f.write(canonical_str)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, target_path)
        except Exception as err:
            if temp_path.exists():
                with contextlib.suppress(OSError):
                    temp_path.unlink()
            raise SiteEvidencePersistenceError(
                f"Failed to atomically write {target_path}: {err}"
            ) from err

    def list_evidence(self, project_id: str) -> list[Evidence]:
        """List all persisted site geometry Evidence records for project_id."""
        file_path = self._get_evidence_file_path(project_id)
        if not file_path.exists():
            return []
        try:
            with open(file_path, encoding="utf-8") as f:
                raw_data = json.load(f)
            if not isinstance(raw_data, list):
                raise SiteEvidencePersistenceError(
                    f"Corrupted site evidence file at {file_path}: expected JSON list."
                )
            return [Evidence.model_validate(item) for item in raw_data]
        except Exception as err:
            if isinstance(err, SiteEvidencePersistenceError):
                raise
            raise SiteEvidencePersistenceError(
                f"Failed to read site evidence file {file_path}: {err}"
            ) from err

    def get_evidence(self, project_id: str, evidence_id: str) -> Evidence | None:
        """Retrieve a specific Evidence record by ID."""
        records = self.list_evidence(project_id)
        for ev in records:
            if ev.id == evidence_id:
                return ev
        return None

    def save_site_evidence(
        self,
        project_id: str,
        source_reference: str,
        user_message: str,
    ) -> Evidence:
        """Deterministically save or reuse an Evidence record for site approval."""
        clean_msg = user_message.strip()
        excerpt = clean_msg[:500] if len(clean_msg) > 500 else clean_msg
        src_ref = (
            source_reference.strip()[:250]
            if len(source_reference.strip()) > 250
            else source_reference.strip()
        )
        if not src_ref:
            src_ref = "site_approval_msg"

        ev_id = _generate_site_evidence_id(project_id, src_ref, excerpt)
        existing_records = self.list_evidence(project_id)

        for ev in existing_records:
            if ev.id == ev_id or (
                ev.source_type == EvidenceSource.CHAT
                and ev.source_reference == src_ref
                and ev.excerpt == excerpt
            ):
                return ev

        new_evidence = Evidence(
            id=ev_id,
            source_type=EvidenceSource.CHAT,
            source_reference=src_ref,
            excerpt=excerpt,
        )

        updated_records = [*existing_records, new_evidence]
        raw_list = [ev.model_dump(mode="json") for ev in updated_records]
        file_path = self._get_evidence_file_path(project_id)
        self._atomic_write_json(file_path, raw_list)

        return new_evidence
