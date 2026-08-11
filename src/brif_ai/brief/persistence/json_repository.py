"""BRIF.AI — Deterministic JSON File Repository Implementation."""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from brif_ai.brief.models.snapshot import BriefSnapshot
from brif_ai.brief.persistence.errors import (
    BriefPersistenceError,
    BriefVersionConflictError,
    InvalidProjectIdError,
)

_PROJECT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class JSONBriefRepository:
    """Deterministic local JSON persistence repository for BriefSnapshots."""

    def __init__(self, root_dir: str | Path | None = None) -> None:
        if root_dir is None:
            env_dir = os.getenv("BRIF_AI_DATA_DIR")
            root_dir = Path(env_dir) if env_dir else Path.home() / ".brif_ai" / "data"
        self.root_dir = Path(root_dir).resolve()

    def _validate_project_id(self, project_id: str) -> str:
        if not isinstance(project_id, str) or not project_id.strip():
            raise InvalidProjectIdError("Project ID must be a non-empty string.")
        pid = project_id.strip()
        if not _PROJECT_ID_PATTERN.match(pid):
            raise InvalidProjectIdError(
                f"Invalid project ID format or illegal characters: {project_id!r}"
            )
        try:
            target_path = (self.root_dir / "projects" / pid).resolve()
            base_path = (self.root_dir / "projects").resolve()
            if not str(target_path).startswith(str(base_path)):
                raise InvalidProjectIdError(
                    f"Path traversal detected in project ID: {project_id!r}"
                )
        except Exception as err:
            if isinstance(err, InvalidProjectIdError):
                raise
            raise InvalidProjectIdError(f"Failed to resolve project path: {err}") from err
        return pid

    def _get_project_brief_dir(self, project_id: str) -> Path:
        pid = self._validate_project_id(project_id)
        path = self.root_dir / "projects" / pid / "brief"
        path.mkdir(parents=True, exist_ok=True)
        (path / "versions").mkdir(parents=True, exist_ok=True)
        return path

    def _canonical_json(self, data: dict[str, Any]) -> str:
        return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    def _atomic_write_json(self, target_path: Path, data: dict[str, Any]) -> None:
        parent_dir = target_path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        canonical_str = self._canonical_json(data)

        # Write to temp file in same directory then atomically replace
        fd, temp_path_str = tempfile.mkstemp(dir=str(parent_dir), prefix="tmp_brief_")
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
            raise BriefPersistenceError(f"Failed to atomically write {target_path}: {err}") from err

    def save(self, snapshot: BriefSnapshot) -> BriefSnapshot:
        """Persist a BriefSnapshot deterministically."""
        # Immutable copy of caller object
        snap_copy = snapshot.model_copy(deep=True)
        pid = self._validate_project_id(snap_copy.project_id)
        brief_dir = self._get_project_brief_dir(pid)

        version_filename = f"{snap_copy.brief_version:06d}.json"
        version_path = brief_dir / "versions" / version_filename
        latest_path = brief_dir / "latest.json"

        new_data = snap_copy.model_dump(mode="json")
        new_canonical = self._canonical_json(new_data)

        # Check existing version file immutability
        if version_path.exists():
            try:
                with open(version_path, encoding="utf-8") as f:
                    existing_data = json.load(f)
                existing_canonical = self._canonical_json(existing_data)
                if existing_canonical == new_canonical:
                    # Idempotent write of exact same content
                    return snap_copy
                raise BriefVersionConflictError(
                    f"Version {snap_copy.brief_version} already exists for project {pid} "
                    "with different content."
                )
            except json.JSONDecodeError as err:
                raise BriefPersistenceError(
                    f"Existing version file {version_path} is corrupted: {err}"
                ) from err

        # Write version file first then latest pointer
        self._atomic_write_json(version_path, new_data)
        self._atomic_write_json(latest_path, new_data)

        return snap_copy

    def get_version(self, project_id: str, brief_version: int) -> BriefSnapshot | None:
        """Retrieve a specific historical BriefSnapshot version."""
        pid = self._validate_project_id(project_id)
        brief_dir = self.root_dir / "projects" / pid / "brief"
        version_path = brief_dir / "versions" / f"{brief_version:06d}.json"

        if not version_path.exists():
            return None

        try:
            with open(version_path, encoding="utf-8") as f:
                data = json.load(f)
            snapshot = BriefSnapshot.model_validate(data)
            if snapshot.project_id != pid or snapshot.brief_version != brief_version:
                raise BriefPersistenceError(
                    f"Persisted version file content mismatch for project {pid} v{brief_version}"
                )
            return snapshot
        except BriefPersistenceError:
            raise
        except Exception as err:
            raise BriefPersistenceError(
                f"Failed to read/validate brief snapshot at {version_path}: {err}"
            ) from err

    def get_latest(self, project_id: str) -> BriefSnapshot | None:
        """Retrieve the latest persisted BriefSnapshot."""
        pid = self._validate_project_id(project_id)
        brief_dir = self.root_dir / "projects" / pid / "brief"
        latest_path = brief_dir / "latest.json"

        if not latest_path.exists():
            return None

        try:
            with open(latest_path, encoding="utf-8") as f:
                latest_data = json.load(f)
            latest_snap = BriefSnapshot.model_validate(latest_data)
            if latest_snap.project_id != pid:
                raise BriefPersistenceError(
                    f"latest.json project_id mismatch: expected {pid}, got {latest_snap.project_id}"
                )

            # Consistency check against version file
            version_path = brief_dir / "versions" / f"{latest_snap.brief_version:06d}.json"
            if not version_path.exists():
                raise BriefPersistenceError(
                    f"Latest pointer references version {latest_snap.brief_version} "
                    "which is missing."
                )

            with open(version_path, encoding="utf-8") as f:
                version_data = json.load(f)

            if self._canonical_json(latest_data) != self._canonical_json(version_data):
                raise BriefPersistenceError(
                    f"Inconsistency detected between latest.json and "
                    f"versions/{latest_snap.brief_version:06d}.json for project {pid}."
                )

            return latest_snap
        except BriefPersistenceError:
            raise
        except Exception as err:
            raise BriefPersistenceError(
                f"Failed to read/validate latest brief snapshot at {latest_path}: {err}"
            ) from err

    def list_versions(self, project_id: str) -> list[int]:
        """Return a sorted list of all persisted brief version numbers."""
        pid = self._validate_project_id(project_id)
        versions_dir = self.root_dir / "projects" / pid / "brief" / "versions"

        if not versions_dir.exists():
            return []

        versions: list[int] = []
        for file_path in versions_dir.glob("*.json"):
            name = file_path.stem
            if name.isdigit():
                versions.append(int(name))
        return sorted(versions)
