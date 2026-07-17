from __future__ import annotations

import re
from typing import Any

from ..models import Scene
from .character_performance_library import plan_from_preset, suggest_preset


def _context(scene: Scene) -> str:
    return " ".join([scene.narration, scene.visual_intent, *scene.search_keywords]).lower()


def _mentions(context: str, phrases: tuple[str, ...]) -> bool:
    """Match semantic triggers as words or phrases, never inside other words."""
    return any(
        re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", context) is not None
        for phrase in phrases
    )


def build_animation_plan(scene: Scene) -> dict[str, Any]:
    """Create a deterministic, editable performance plan from scene meaning."""
    context = _context(scene)

    if _mentions(context, ("nothing left", "zero balance", "declined", "empty wallet")):
        action = "Raise phone, lean toward the screen, recoil, then let the shoulders collapse."
        expressions = ["neutral", "curious", "shocked", "sad"]
        props = ["phone", "zero-balance screen", "declined indicator"]
        camera = "Medium shot, slow push-in, quick punch-in on zero, hold the reaction."
        camera_motion = {"mode": "push_in", "intensity": 0.72, "focus": [0.58, 0.48]}
        poses = ["phone", "tap", "recoil", "slump"]
    elif _mentions(context, ("rent", "groceries", "spend first", "go out")):
        action = "Receive income, reach toward expenses, track the wallet draining, then slump."
        expressions = ["happy", "neutral", "concerned", "sad"]
        props = ["wallet", "rent card", "grocery bag", "payment card"]
        camera = "Wide setup, track the spending path, then push toward the empty wallet."
        camera_motion = {"mode": "track", "intensity": 0.48, "focus": [0.50, 0.54]}
        poses = ["receive", "point", "recoil", "slump"]
    elif _mentions(context, ("pay yourself first", "exact opposite", "wealthy people")):
        action = "Compare two characters receiving the same paycheck and making opposite choices."
        expressions = ["neutral", "thinking", "concerned", "confident"]
        props = ["paycheck", "wallet", "investment account"]
        camera = "Balanced split-screen, then favor the invest-first outcome."
        camera_motion = {"mode": "settle", "intensity": 0.38, "focus": [0.58, 0.50]}
        poses = ["receive", "point", "slump", "celebrate"]
    elif _mentions(context, ("automatic", "recurring", "set it once", "like a bill")):
        action = "Tap the automation control once, step back, and watch recurring transfers continue."
        expressions = ["focused", "neutral", "relieved", "happy"]
        props = ["phone", "auto-invest control", "calendar", "investment account"]
        camera = "Medium interaction shot, then widen to reveal the system running alone."
        camera_motion = {"mode": "pull_back", "intensity": 0.34, "focus": [0.56, 0.50]}
        poses = ["tap", "point", "relaxed", "celebrate"]
    elif _mentions(context, ("paycheck", "salary", "future self", "first 10")):
        action = "Receive the paycheck, anticipate the choice, separate ten percent, and point to the future account."
        expressions = ["neutral", "focused", "confident", "happy"]
        props = ["paycheck", "10 percent token", "future account"]
        camera = "Medium entrance, track the transfer, settle on the funded future account."
        camera_motion = {"mode": "track", "intensity": 0.42, "focus": [0.54, 0.52]}
        poses = ["walk", "receive", "point", "celebrate"]
    else:
        return plan_from_preset(suggest_preset(context).preset_id)

    return {
        "version": "1.9.5",
        "visual_strategy": "character_performance",
        "preset_id": None,
        "character_action": action,
        "expression_sequence": expressions,
        "pose_sequence": poses,
        "props": props,
        "camera_direction": camera,
        "camera_motion": camera_motion,
        "animation_beats": {
            "anticipation": 0.15,
            "action": 0.35,
            "overshoot": 0.15,
            "recovery": 0.35,
        },
        "transition_intention": "Hold the final readable pose before the timeline transition.",
    }


def ensure_animation_plan(scene: Scene) -> dict[str, Any]:
    plan = scene.animation_plan or {}
    if not plan:
        plan = build_animation_plan(scene)
        scene.animation_plan = plan
    return plan
