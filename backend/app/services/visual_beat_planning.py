from __future__ import annotations

import math
import re
from typing import Any

from sqlalchemy.orm import Session

from ..models import Project, Scene
from .render_invalidation import invalidate_render_artifacts


def _phrases(value: str) -> list[str]:
    parts = [
        " ".join(part.split()).strip(" ,;:.-")
        for part in re.split(r"[;,.]|\band\b|\bthen\b|\bwhile\b", value, flags=re.IGNORECASE)
    ]
    return [part for part in parts if len(part) >= 8]


def _beat_intent(scene: Scene, index: int, count: int) -> str:
    phrases = _phrases(scene.visual_intent)
    if phrases:
        selected = phrases[min(index, len(phrases) - 1)]
        return selected[0].upper() + selected[1:]
    return f"Visual beat {index + 1} of {count}: {scene.visual_intent or scene.narration[:180]}"


def plan_visual_beats(
    project: Project,
    db: Session,
    *,
    target_seconds: float = 5.0,
) -> dict[str, Any]:
    target = min(15.0, max(3.0, float(target_seconds)))
    total_beats = 0

    for scene in sorted(project.scenes, key=lambda item: item.scene_number):
        duration = max(0.25, float(scene.duration_seconds))
        beat_count = max(1, math.ceil(duration / target))
        beat_duration = duration / beat_count
        beats: list[dict[str, Any]] = []

        for index in range(beat_count):
            relative_start = round(index * beat_duration, 3)
            relative_end = round(duration if index == beat_count - 1 else (index + 1) * beat_duration, 3)
            beats.append(
                {
                    "beat_number": index + 1,
                    "relative_start_seconds": relative_start,
                    "relative_end_seconds": relative_end,
                    "start_seconds": round(float(scene.start_seconds) + relative_start, 3),
                    "end_seconds": round(float(scene.start_seconds) + relative_end, 3),
                    "duration_seconds": round(relative_end - relative_start, 3),
                    "visual_intent": _beat_intent(scene, index, beat_count),
                    "search_keywords": list(scene.search_keywords)[:20],
                    "preferred_asset_type": scene.preferred_asset_type,
                    "asset_status": "missing",
                }
            )

        plan = dict(scene.animation_plan or {})
        plan.update(
            {
                "kind": "narration_visual_beats",
                "target_beat_seconds": target,
                "audio_scene_number": scene.scene_number,
                "audio_continuous": True,
                "visual_beats": beats,
            }
        )
        scene.animation_plan = plan
        scene.asset_status = "missing"
        total_beats += beat_count

    project.status = "storyboard"
    db.commit()
    invalidate_render_artifacts(project.id)
    return {
        "project_id": project.id,
        "scene_count": len(project.scenes),
        "visual_beat_count": total_beats,
        "target_beat_seconds": target,
    }
