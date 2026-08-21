"""BRIF.AI — Deterministic JSON File Repository for AuthoritativePlanInputState."""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from brif_ai.spatial.plan_input.errors import (
    PlanInputStatePersistenceError,
    PlanInputStateVersionConflictError,
)
from brif_ai.spatial.plan_input.models import AuthoritativePlanInputState

_PROJECT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class JSONPlanInputStateRepository:
    """Deterministic local JSON persistence repository for AuthoritativePlanInputState."""

    def __init__(self, root_dir: str | Path | None = None) -> None:
        if root_dir is None:
            env_dir = os.getenv("BRIF_AI_DATA_DIR")
            root_dir = Path(env_dir) if env_dir else Path.home() / ".brif_ai" / "data"
        self.root_dir = Path(root_dir).resolve()

    def _validate_project_id(self, project_id: str) -> str:
        if not isinstance(project_id, str) or not project_id.strip():
            raise PlanInputStatePersistenceError("Project ID must be a non-empty string.")
        pid = project_id.strip()
        if not _PROJECT_ID_PATTERN.match(pid):
            raise PlanInputStatePersistenceError(
                f"Invalid project ID format or illegal characters: {project_id!r}"
            )
        try:
            target_path = (self.root_dir / "projects" / pid).resolve()
            base_path = (self.root_dir / "projects").resolve()
            if not str(target_path).startswith(str(base_path)):
                raise PlanInputStatePersistenceError(
                    f"Path traversal detected in project ID: {project_id!r}"
                )
        except Exception as err:
            if isinstance(err, PlanInputStatePersistenceError):
                raise
            raise PlanInputStatePersistenceError(f"Failed to resolve project path: {err}") from err
        return pid

    def _get_project_plan_input_dir(self, project_id: str) -> Path:
        pid = self._validate_project_id(project_id)
        path = self.root_dir / "projects" / pid / "plan_input"
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
        fd, temp_path_str = tempfile.mkstemp(dir=str(parent_dir), prefix="tmp_plan_input_")
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
            raise PlanInputStatePersistenceError(
                f"Failed to atomically write {target_path}: {err}"
            ) from err

    def _publish_version_file_link(self, version_path: Path, canonical_str: str) -> None:
        """Publish canonical_str to version_path atomically without overwrite.

        Writes and fsyncs canonical_str into a temporary file in the same versions directory,
        then atomically links it to version_path via os.link.
        Raises FileExistsError if version_path already exists (destination is never replaced).
        Always cleans up the temporary file.
        """
        parent_dir = version_path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        fd, temp_path_str = tempfile.mkstemp(dir=str(parent_dir), prefix="tmp_ver_")
        temp_path = Path(temp_path_str)
        try:
            with open(fd, "w", encoding="utf-8") as f:
                f.write(canonical_str)
                f.flush()
                os.fsync(f.fileno())
            os.link(temp_path, version_path)
        finally:
            with contextlib.suppress(OSError):
                if temp_path.exists():
                    temp_path.unlink()

    def save(self, state: AuthoritativePlanInputState) -> AuthoritativePlanInputState:
        """Persist an AuthoritativePlanInputState deterministically.

        Version file key is derived from state.state_version.
        Uses atomic link publication (write temp file + os.link) for the immutable version file
        so the final version path is never exposed partially and cannot overwrite existing versions.
        Updates latest.json pointer atomically for the winning publisher.
        Rejects attempts to overwrite an existing version file with different content.
        """
        state_copy = state.model_copy(deep=True)
        pid = self._validate_project_id(state_copy.project_id)
        plan_input_dir = self._get_project_plan_input_dir(pid)

        version_filename = f"{state_copy.state_version:06d}.json"
        version_path = plan_input_dir / "versions" / version_filename
        latest_path = plan_input_dir / "latest.json"

        new_data = state_copy.model_dump(mode="json")
        canonical_str = self._canonical_json(new_data)

        # 1. Atomically publish immutable version file without overwrite
        try:
            self._publish_version_file_link(version_path, canonical_str)
        except FileExistsError:
            # File already exists: verify complete existing content for idempotency or conflict
            try:
                with open(version_path, encoding="utf-8") as f:
                    existing_data = json.load(f)
                if self._canonical_json(existing_data) != canonical_str:
                    raise PlanInputStateVersionConflictError(
                        f"Plan input state version {state_copy.state_version} for project '{pid}' "
                        f"already exists with different content and cannot be overwritten."
                    )
                # Identical content: idempotent success without rewriting latest.json pointer
                return state_copy
            except PlanInputStateVersionConflictError:
                raise
            except Exception as err:
                raise PlanInputStatePersistenceError(
                    f"Failed to verify existing version file '{version_path}': {err}"
                ) from err
        except Exception as err:
            raise PlanInputStatePersistenceError(
                f"Failed to publish version file '{version_path}': {err}"
            ) from err

        # 2. Atomically update latest.json mutable pointer for the winning publisher
        self._atomic_write_json(latest_path, new_data)

        return state_copy

    def get_latest(self, project_id: str) -> AuthoritativePlanInputState | None:
        """Retrieve the latest AuthoritativePlanInputState or None if not found."""
        pid = self._validate_project_id(project_id)
        latest_path = self.root_dir / "projects" / pid / "plan_input" / "latest.json"
        if not latest_path.exists():
            return None
        try:
            with open(latest_path, encoding="utf-8") as f:
                data = json.load(f)
            return AuthoritativePlanInputState.model_validate(data)
        except Exception as err:
            raise PlanInputStatePersistenceError(
                f"Failed to read latest plan input state for project '{pid}': {err}"
            ) from err

    def get_version(
        self, project_id: str, state_version: int
    ) -> AuthoritativePlanInputState | None:
        """Retrieve a specific state_version AuthoritativePlanInputState or None."""
        pid = self._validate_project_id(project_id)
        version_path = (
            self.root_dir
            / "projects"
            / pid
            / "plan_input"
            / "versions"
            / f"{state_version:06d}.json"
        )
        if not version_path.exists():
            return None
        try:
            with open(version_path, encoding="utf-8") as f:
                data = json.load(f)
            return AuthoritativePlanInputState.model_validate(data)
        except Exception as err:
            raise PlanInputStatePersistenceError(
                f"Failed to read plan input state v{state_version} for project '{pid}': {err}"
            ) from err

    def list_versions(self, project_id: str) -> list[int]:
        """List all available state_version numbers in ascending order."""
        pid = self._validate_project_id(project_id)
        versions_dir = self.root_dir / "projects" / pid / "plan_input" / "versions"
        if not versions_dir.exists():
            return []
        versions: list[int] = []
        for file in versions_dir.glob("*.json"):
            if file.stem.isdigit():
                versions.append(int(file.stem))
        return sorted(versions)
