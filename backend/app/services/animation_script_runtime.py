from __future__ import annotations

from typing import Any

from . import character_expressive as character
from .animation_script_director import ensure_animation_plan

_ACTIVE_PLAN: dict[str, Any] | None = None
_ORIGINAL_PERSON = character._expressive_person
_ORIGINAL_RENDER = character.render_character_motion


def _sequence_position(progress: float, count: int, beats: object) -> float:
    """Map normalized scene progress through editable performance beat weights."""
    if count <= 0:
        return 0.0
    fallback = max(0.0, min(0.999999, progress)) * count
    if not isinstance(beats, dict) or len(beats) != count:
        return fallback
    try:
        weights = [max(0.0, float(value)) for value in beats.values()]
    except (TypeError, ValueError):
        return fallback
    total = sum(weights)
    if total <= 0:
        return fallback
    target = max(0.0, min(0.999999, progress)) * total
    elapsed = 0.0
    for index, weight in enumerate(weights):
        end = elapsed + weight
        if target < end or index == count - 1:
            local = 0.0 if weight <= 0 else (target - elapsed) / weight
            return index + max(0.0, min(0.999999, local))
        elapsed = end
    return fallback


def _mapped_expression(value: str) -> str:
    normalized = value.lower().strip()
    return {
        "shocked": "surprised",
        "surprise": "surprised",
        "relieved": "happy",
        "focused": "confident",
        "curious": "neutral",
        "thinking": "concerned",
    }.get(normalized, normalized)


def _planned_person(*args, pose: str = "idle", mood: str = "neutral", **kwargs):
    if _ACTIVE_PLAN:
        progress = character._CURRENT_TIME / max(0.01, character._CURRENT_DURATION)
        poses = list(_ACTIVE_PLAN.get("pose_sequence") or [])
        expressions = list(_ACTIVE_PLAN.get("expression_sequence") or [])
        beats = _ACTIVE_PLAN.get("animation_beats")
        if poses:
            pose_position = _sequence_position(progress, len(poses), beats)
            pose = str(poses[min(len(poses) - 1, int(pose_position))])
        if expressions:
            expression_position = _sequence_position(progress, len(expressions), beats)
            mood = _mapped_expression(
                str(expressions[min(len(expressions) - 1, int(expression_position))])
            )
    return _ORIGINAL_PERSON(*args, pose=pose, mood=mood, **kwargs)


def render_character_motion(scene, template_id=None, style_id=None):
    global _ACTIVE_PLAN
    _ACTIVE_PLAN = ensure_animation_plan(scene)
    try:
        return _ORIGINAL_RENDER(scene, template_id, style_id)
    finally:
        _ACTIVE_PLAN = None


def render_planned_frame(
    scene,
    template_id: str,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
):
    """Render one review frame using the scene's saved animation direction."""
    global _ACTIVE_PLAN
    previous_plan = _ACTIVE_PLAN
    _ACTIVE_PLAN = ensure_animation_plan(scene)
    try:
        return character.render_frame(
            template_id,
            duration_seconds,
            time_seconds,
            style_id,
        )
    finally:
        _ACTIVE_PLAN = previous_plan


character.staged.base._person = _planned_person
character.render_character_motion = render_character_motion
