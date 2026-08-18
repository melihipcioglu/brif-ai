"""BRIF.AI — Deterministic JSON File Repository for SpatialRelationshipGraph."""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from brif_ai.spatial.models import SpatialRelationshipGraph
from brif_ai.spatial.persistence.errors import (
    SpatialGraphPersistenceError,
)

_PROJECT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class JSONSpatialRelationshipRepository:
    """Deterministic local JSON persistence repository for SpatialRelationshipGraph."""

    def __init__(self, root_dir: str | Path | None = None) -> None:
        if root_dir is None:
            env_dir = os.getenv("BRIF_AI_DATA_DIR")
            root_dir = Path(env_dir) if env_dir else Path.home() / ".brif_ai" / "data"
        self.root_dir = Path(root_dir).resolve()

    def _validate_project_id(self, project_id: str) -> str:
        if not isinstance(project_id, str) or not project_id.strip():
            raise SpatialGraphPersistenceError("Project ID must be a non-empty string.")
        pid = project_id.strip()
        if not _PROJECT_ID_PATTERN.match(pid):
            raise SpatialGraphPersistenceError(
                f"Invalid project ID format or illegal characters: {project_id!r}"
            )
        try:
            target_path = (self.root_dir / "projects" / pid).resolve()
            base_path = (self.root_dir / "projects").resolve()
            if not str(target_path).startswith(str(base_path)):
                raise SpatialGraphPersistenceError(
                    f"Path traversal detected in project ID: {project_id!r}"
                )
        except Exception as err:
            if isinstance(err, SpatialGraphPersistenceError):
                raise
            raise SpatialGraphPersistenceError(f"Failed to resolve project path: {err}") from err
        return pid

    def _get_project_spatial_dir(self, project_id: str) -> Path:
        pid = self._validate_project_id(project_id)
        path = self.root_dir / "projects" / pid / "spatial"
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
        fd, temp_path_str = tempfile.mkstemp(dir=str(parent_dir), prefix="tmp_spatial_")
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
            raise SpatialGraphPersistenceError(
                f"Failed to atomically write {target_path}: {err}"
            ) from err

    def save(self, graph: SpatialRelationshipGraph) -> SpatialRelationshipGraph:
        """Persist a SpatialRelationshipGraph deterministically.

        Version file key is derived from graph.source_brief_version.
        Writes version file and latest file atomically via temp-file + replace.
        """
        graph_copy = graph.model_copy(deep=True)
        pid = self._validate_project_id(graph_copy.project_id)
        spatial_dir = self._get_project_spatial_dir(pid)

        version_filename = f"{graph_copy.source_brief_version:06d}.json"
        version_path = spatial_dir / "versions" / version_filename
        latest_path = spatial_dir / "latest.json"

        new_data = graph_copy.model_dump(mode="json")

        # Atomically write version file and latest file
        self._atomic_write_json(version_path, new_data)
        self._atomic_write_json(latest_path, new_data)

        return graph_copy

    def get_latest(self, project_id: str) -> SpatialRelationshipGraph | None:
        """Retrieve the latest SpatialRelationshipGraph or None."""
        pid = self._validate_project_id(project_id)
        latest_path = self.root_dir / "projects" / pid / "spatial" / "latest.json"
        if not latest_path.exists():
            return None
        try:
            with open(latest_path, encoding="utf-8") as f:
                data = json.load(f)
            return SpatialRelationshipGraph.model_validate(data)
        except Exception as err:
            raise SpatialGraphPersistenceError(
                f"Failed to read latest spatial graph for project '{pid}': {err}"
            ) from err

    def get_version(self, project_id: str, version: int) -> SpatialRelationshipGraph | None:
        """Retrieve a specific source_brief_version SpatialRelationshipGraph or None."""
        pid = self._validate_project_id(project_id)
        version_path = (
            self.root_dir / "projects" / pid / "spatial" / "versions" / f"{version:06d}.json"
        )
        if not version_path.exists():
            return None
        try:
            with open(version_path, encoding="utf-8") as f:
                data = json.load(f)
            return SpatialRelationshipGraph.model_validate(data)
        except Exception as err:
            raise SpatialGraphPersistenceError(
                f"Failed to read spatial graph v{version} for project '{pid}': {err}"
            ) from err

    def list_versions(self, project_id: str) -> list[int]:
        """List all available source_brief_version numbers in ascending order."""
        pid = self._validate_project_id(project_id)
        versions_dir = self.root_dir / "projects" / pid / "spatial" / "versions"
        if not versions_dir.exists():
            return []
        versions: list[int] = []
        for file in versions_dir.glob("*.json"):
            if file.stem.isdigit():
                versions.append(int(file.stem))
        return sorted(versions)
