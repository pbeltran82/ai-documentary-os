from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .media_library import MEDIA_ROOT, project_directory, public_media_url
from .script_audio_pipeline import _read_json, _relative, _write_json, utc_iso


def _script_path(project_id: int) -> Path:
    return project_directory(project_id) / "production" / "script.json"


def _revision_path(project_id: int, revision: int) -> Path:
    return (
        project_directory(project_id)
        / "production"
        / "script-revisions"
        / f"script-r{revision:03d}.json"
    )


def approve_script(project_id: int, *, notes: str = "") -> dict[str, Any]:
    path = _script_path(project_id)
    script = _read_json(path)
    if script is None:
        raise FileNotFoundError("No generated script exists for this project")

    revision = max(1, int(script.get("revision", 1)))
    script["status"] = "approved"
    script["approved_at"] = utc_iso()
    script["approval_notes"] = notes.strip()
    for segment in script.get("segments", []):
        segment["status"] = "approved"

    snapshot = deepcopy(script)
    snapshot_path = _revision_path(project_id, revision)
    _write_json(snapshot_path, snapshot)
    _write_json(path, script)

    relative = _relative(path)
    revision_relative = _relative(snapshot_path)
    script["relative_path"] = relative
    script["public_url"] = public_media_url(relative)
    script["revision_relative_path"] = revision_relative
    script["revision_public_url"] = public_media_url(revision_relative)
    return script


def list_script_revisions(project_id: int) -> list[dict[str, Any]]:
    directory = project_directory(project_id) / "production" / "script-revisions"
    if not directory.is_dir():
        return []
    results: list[dict[str, Any]] = []
    for path in sorted(directory.glob("script-r*.json"), reverse=True):
        payload = _read_json(path)
        if payload is None:
            continue
        relative = path.relative_to(MEDIA_ROOT).as_posix()
        results.append(
            {
                "revision": int(payload.get("revision", 0)),
                "status": str(payload.get("status", "")),
                "approved_at": payload.get("approved_at"),
                "word_count": int(payload.get("word_count", 0)),
                "estimated_runtime_seconds": float(payload.get("estimated_runtime_seconds", 0)),
                "relative_path": relative,
                "public_url": public_media_url(relative),
            }
        )
    return results
