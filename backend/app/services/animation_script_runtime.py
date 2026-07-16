from __future__ import annotations

from typing import Any

from . import character_expressive as character
from .animation_script_director import ensure_animation_plan

_ACTIVE_PLAN: dict[str, Any] | None = None
_ORIGINAL_PERSON = character._expressive_person
_ORIGINAL_RENDER = character.render_character_motion


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
        if poses:
            pose = str(poses[min(len(poses) - 1, int(progress * len(poses)))])
        if expressions:
            mood = _mapped_expression(
                str(expressions[min(len(expressions) - 1, int(progress * len(expressions)))])
            )
    return _ORIGINAL_PERSON(*args, pose=pose, mood=mood, **kwargs)


def render_character_motion(scene, template_id=None, style_id=None):
    global _ACTIVE_PLAN
    _ACTIVE_PLAN = ensure_animation_plan(scene)
    try:
        return _ORIGINAL_RENDER(scene, template_id, style_id)
    finally:
        _ACTIVE_PLAN = None


character.staged.base._person = _planned_person
character.render_character_motion = render_character_motion
