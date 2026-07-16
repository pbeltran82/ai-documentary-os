from __future__ import annotations

from typing import Any

from ..models import Scene


def _context(scene: Scene) -> str:
    return " ".join([scene.narration, scene.visual_intent, *scene.search_keywords]).lower()


def build_animation_plan(scene: Scene) -> dict[str, Any]:
    """Create a deterministic, editable performance plan from scene meaning."""
    context = _context(scene)

    if any(phrase in context for phrase in ("nothing left", "zero balance", "declined", "empty wallet")):
        action = "Raise phone, lean toward the screen, recoil, then let the shoulders collapse."
        expressions = ["neutral", "curious", "shocked", "sad"]
        props = ["phone", "zero-balance screen", "declined indicator"]
        camera = "Medium shot, slow push-in, quick punch-in on zero, hold the reaction."
        poses = ["phone", "tap", "recoil", "slump"]
    elif any(phrase in context for phrase in ("rent", "groceries", "spend first", "go out")):
        action = "Receive income, reach toward expenses, track the wallet draining, then slump."
        expressions = ["happy", "neutral", "concerned", "sad"]
        props = ["wallet", "rent card", "grocery bag", "payment card"]
        camera = "Wide setup, track the spending path, then push toward the empty wallet."
        poses = ["receive", "point", "recoil", "slump"]
    elif any(phrase in context for phrase in ("pay yourself first", "exact opposite", "wealthy people")):
        action = "Compare two characters receiving the same paycheck and making opposite choices."
        expressions = ["neutral", "thinking", "concerned", "confident"]
        props = ["paycheck", "wallet", "investment account"]
        camera = "Balanced split-screen, then favor the invest-first outcome."
        poses = ["receive", "point", "slump", "celebrate"]
    elif any(phrase in context for phrase in ("automatic", "recurring", "set it once", "like a bill")):
        action = "Tap the automation control once, step back, and watch recurring transfers continue."
        expressions = ["focused", "neutral", "relieved", "happy"]
        props = ["phone", "auto-invest control", "calendar", "investment account"]
        camera = "Medium interaction shot, then widen to reveal the system running alone."
        poses = ["tap", "point", "relaxed", "celebrate"]
    elif any(phrase in context for phrase in ("paycheck", "salary", "future self", "first 10")):
        action = "Receive the paycheck, anticipate the choice, separate ten percent, and point to the future account."
        expressions = ["neutral", "focused", "confident", "happy"]
        props = ["paycheck", "10 percent token", "future account"]
        camera = "Medium entrance, track the transfer, settle on the funded future account."
        poses = ["walk", "receive", "point", "celebrate"]
    else:
        action = "Enter, observe the key visual, gesture toward the main idea, and land on a clear reaction."
        expressions = ["neutral", "curious", "focused", "confident"]
        props = []
        camera = "Medium establishing shot with a restrained push-in on the final idea."
        poses = ["walk", "idle", "point", "relaxed"]

    return {
        "version": "1.9.1",
        "visual_strategy": "character_performance",
        "character_action": action,
        "expression_sequence": expressions,
        "pose_sequence": poses,
        "props": props,
        "camera_direction": camera,
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
