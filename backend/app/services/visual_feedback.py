from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .media_library import project_directory

ALLOWED_REASONS = {
    "wrong_concept",
    "too_generic",
    "repetitive",
    "poor_quality",
    "bad_style",
}


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def feedback_path(project_id: int) -> Path:
    path = project_directory(project_id) / "director" / "feedback.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_feedback(project_id: int) -> list[dict[str, Any]]:
    path = feedback_path(project_id)
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def write_feedback(project_id: int, records: list[dict[str, Any]]) -> None:
    path = feedback_path(project_id)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=".feedback-",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as temporary:
        json.dump(records, temporary, indent=2, ensure_ascii=False)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def record_rejection(
    project_id: int,
    scene_id: int,
    provider: str,
    provider_asset_id: str,
    reason: str,
) -> dict[str, Any]:
    normalized_reason = reason.strip().lower()
    if normalized_reason not in ALLOWED_REASONS:
        normalized_reason = "wrong_concept"

    records = load_feedback(project_id)
    records = [
        item
        for item in records
        if not (
            int(item.get("scene_id") or 0) == scene_id
            and str(item.get("provider") or "") == provider
            and str(item.get("provider_asset_id") or "") == provider_asset_id
        )
    ]
    record = {
        "scene_id": scene_id,
        "provider": provider,
        "provider_asset_id": provider_asset_id,
        "reason": normalized_reason,
        "created_at": utc_iso(),
    }
    records.append(record)
    write_feedback(project_id, records)
    return record


def scene_feedback(project_id: int, scene_id: int) -> list[dict[str, Any]]:
    return [
        item
        for item in load_feedback(project_id)
        if int(item.get("scene_id") or 0) == scene_id
    ]


def clear_scene_feedback(project_id: int, scene_id: int) -> int:
    records = load_feedback(project_id)
    remaining = [
        item for item in records if int(item.get("scene_id") or 0) != scene_id
    ]
    removed = len(records) - len(remaining)
    if removed:
        write_feedback(project_id, remaining)
    return removed
