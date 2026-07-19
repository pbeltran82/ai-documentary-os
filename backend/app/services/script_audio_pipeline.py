from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models import Project
from .media_library import MEDIA_ROOT, project_directory, public_media_url
from .video_format import SHORTS_FORMAT, project_video_format

WORDS_PER_SECOND = 2.45
SCRIPT_SCHEMA_VERSION = "1.0"
NARRATION_SCHEMA_VERSION = "1.1"
SHORTS_TARGET_RUNTIME_SECONDS = 48.0
SHORTS_MAX_SCENES = 7
SHORTS_MIN_SCENES = 5


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _production_directory(project_id: int) -> Path:
    directory = project_directory(project_id) / "production"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _relative(path: Path) -> str:
    return path.relative_to(MEDIA_ROOT).as_posix()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


ACT_BLUEPRINTS = (
    ("Hook", "Open with the central tension and make the audience feel why the subject matters now."),
    ("Context", "Establish the world, history, and assumptions surrounding the subject."),
    ("Mechanism", "Explain the system or causal mechanism in concrete, visual terms."),
    ("Evidence", "Introduce evidence, examples, and the strongest support for the thesis."),
    ("Complication", "Show limits, tradeoffs, uncertainty, or the strongest counterpoint."),
    ("Consequence", "Trace what the mechanism changes for people, institutions, or the future."),
    ("Conclusion", "Resolve the opening tension with a documentary thesis and restrained call to action."),
)


def build_local_script_draft(
    project: Project,
    *,
    angle: str = "",
    target_scene_seconds: float = 8.0,
) -> dict[str, Any]:
    """Create a provider-neutral, editable script scaffold."""
    total_seconds = max(60, int(project.target_minutes * 60))
    scene_count = max(len(ACT_BLUEPRINTS), round(total_seconds / target_scene_seconds))
    angle_text = angle.strip() or f"Explain {project.topic} through a clear causal story."
    segments: list[dict[str, Any]] = []
    cursor = 0.0

    for index in range(scene_count):
        act_index = min(len(ACT_BLUEPRINTS) - 1, int(index * len(ACT_BLUEPRINTS) / scene_count))
        act_name, act_goal = ACT_BLUEPRINTS[act_index]
        position = index + 1
        narration = (
            f"{project.topic}: scene {position} develops the {act_name.lower()} of the story. "
            f"{act_goal} The editorial angle is: {angle_text}"
        )
        duration = round(max(4.0, len(narration.split()) / WORDS_PER_SECOND), 2)
        visual_intent = (
            f"Create a {project.visual_style.lower()} visual that advances the "
            f"{act_name.lower()} without repeating the previous composition."
        )
        segment_id = _stable_id(f"{project.id}:{position}:{narration}")
        segments.append(
            {
                "segment_id": segment_id,
                "scene_number": position,
                "act": act_name,
                "narration": narration,
                "visual_intent": visual_intent,
                "search_keywords": [project.topic.lower(), act_name.lower(), project.tone.lower()],
                "estimated_duration_seconds": duration,
                "start_seconds": round(cursor, 2),
                "end_seconds": round(cursor + duration, 2),
                "status": "draft",
            }
        )
        cursor += duration

    payload: dict[str, Any] = {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "project_id": project.id,
        "project_title": project.title,
        "topic": project.topic,
        "target_minutes": project.target_minutes,
        "audience": project.audience,
        "tone": project.tone,
        "visual_style": project.visual_style,
        "provider": "local-outline",
        "status": "draft",
        "angle": angle_text,
        "generated_at": utc_iso(),
        "revision": 1,
        "estimated_runtime_seconds": round(cursor, 2),
        "word_count": sum(len(item["narration"].split()) for item in segments),
        "segments": segments,
    }
    path = _production_directory(project.id) / "script.json"
    _write_json(path, payload)
    relative_path = _relative(path)
    payload["relative_path"] = relative_path
    payload["public_url"] = public_media_url(relative_path)
    return payload


def load_script(project_id: int) -> dict[str, Any] | None:
    path = _production_directory(project_id) / "script.json"
    payload = _read_json(path)
    if payload is None:
        return None
    relative_path = _relative(path)
    payload["relative_path"] = relative_path
    payload["public_url"] = public_media_url(relative_path)
    return payload


def _evenly_spaced_segments(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if len(items) <= limit:
        return items
    indexes = {round(index * (len(items) - 1) / (limit - 1)) for index in range(limit)}
    return [item for index, item in enumerate(items) if index in indexes]


def _concise_narration(value: str, target_words: int) -> str:
    clean = " ".join(str(value or "").split())
    if not clean:
        return "The story moves forward."
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean) if part.strip()]
    chosen: list[str] = []
    count = 0
    for sentence in sentences:
        words = sentence.split()
        if chosen and count + len(words) > target_words:
            break
        chosen.extend(words)
        count += len(words)
        if count >= max(8, target_words - 4):
            break
    if not chosen:
        chosen = clean.split()[:target_words]
    if len(chosen) > target_words:
        chosen = chosen[:target_words]
    text = " ".join(chosen).rstrip(" ,;:-")
    if not text.endswith((".", "!", "?")):
        text += "."
    return text


def _narration_source_segments(project: Project, script: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    items = [dict(item) for item in script.get("segments", []) if str(item.get("narration") or "").strip()]
    if project_video_format(project) != SHORTS_FORMAT:
        return items, "full"
    selected = _evenly_spaced_segments(items, SHORTS_MAX_SCENES)
    if len(selected) > SHORTS_MIN_SCENES and len(items) <= SHORTS_MAX_SCENES:
        selected = items
    target_words = max(14, round(SHORTS_TARGET_RUNTIME_SECONDS * WORDS_PER_SECOND / max(1, len(selected))))
    for item in selected:
        item["narration"] = _concise_narration(str(item.get("narration") or ""), target_words)
    return selected, "shorts"


def build_narration_plan(
    project: Project,
    script: dict[str, Any],
    *,
    provider: str,
    voice_id: str,
    speaking_rate: float,
) -> dict[str, Any]:
    source_segments, story_mode = _narration_source_segments(project, script)
    segments: list[dict[str, Any]] = []
    for item in source_segments:
        narration = str(item.get("narration") or "").strip()
        scene_number = int(item.get("scene_number", 0))
        segment_id = _stable_id(f"{story_mode}:{scene_number}:{narration}")
        output_relative = (
            Path(f"project-{project.id:04d}")
            / "production"
            / "narration"
            / f"segment-{scene_number:03d}-{segment_id}.wav"
        ).as_posix()
        segments.append(
            {
                "segment_id": segment_id,
                "source_segment_id": str(item.get("segment_id") or ""),
                "scene_number": scene_number,
                "act": str(item.get("act") or ""),
                "text": narration,
                "provider": provider,
                "voice_id": voice_id,
                "speaking_rate": speaking_rate,
                "status": "planned",
                "estimated_duration_seconds": round(max(1.0, len(narration.split()) / (WORDS_PER_SECOND * speaking_rate)), 2),
                "relative_path": output_relative,
                "public_url": public_media_url(output_relative),
                "checksum_sha256": "",
                "actual_duration_seconds": None,
                "error": None,
            }
        )

    payload: dict[str, Any] = {
        "schema_version": NARRATION_SCHEMA_VERSION,
        "project_id": project.id,
        "project_title": project.title,
        "script_revision": int(script.get("revision", 1)),
        "provider": provider,
        "voice_id": voice_id,
        "speaking_rate": speaking_rate,
        "story_mode": story_mode,
        "target_runtime_seconds": SHORTS_TARGET_RUNTIME_SECONDS if story_mode == "shorts" else None,
        "selected_scene_numbers": [item["scene_number"] for item in segments],
        "status": "planned",
        "generated_at": utc_iso(),
        "segment_count": len(segments),
        "estimated_runtime_seconds": round(sum(float(item["estimated_duration_seconds"]) for item in segments), 2),
        "segments": segments,
    }
    path = _production_directory(project.id) / "narration" / "manifest.json"
    _write_json(path, payload)
    relative_path = _relative(path)
    payload["relative_path"] = relative_path
    payload["public_url"] = public_media_url(relative_path)
    return payload


def load_narration_plan(project_id: int) -> dict[str, Any] | None:
    path = _production_directory(project_id) / "narration" / "manifest.json"
    payload = _read_json(path)
    if payload is None:
        return None
    relative_path = _relative(path)
    payload["relative_path"] = relative_path
    payload["public_url"] = public_media_url(relative_path)
    return payload
