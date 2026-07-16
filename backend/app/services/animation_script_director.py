from __future__ import annotations

import re
from typing import Any

from ..models import Scene


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
        poses = ["phone", "tap", "recoil", "slump"]
    elif _mentions(context, ("rent", "groceries", "spend first", "go out")):
        action = "Receive income, reach toward expenses, track the wallet draining, then slump."
        expressions = ["happy", "neutral", "concerned", "sad"]
        props = ["wallet", "rent card", "grocery bag", "payment card"]
        camera = "Wide setup, track the spending path, then push toward the empty wallet."
        poses = ["receive", "point", "recoil", "slump"]
    elif _mentions(context, ("pay yourself first", "exact opposite", "wealthy people")):
        action = "Compare two characters receiving the same paycheck and making opposite choices."
        expressions = ["neutral", "thinking", "concerned", "confident"]
        props = ["paycheck", "wallet", "investment account"]
        camera = "Balanced split-screen, then favor the invest-first outcome."
        poses = ["receive", "point", "slump", "celebrate"]
    elif _mentions(context, ("automatic", "recurring", "set it once", "like a bill")):
        action = "Tap the automation control once, step back, and watch recurring transfers continue."
        expressions = ["focused", "neutral", "relieved", "happy"]
        props = ["phone", "auto-invest control", "calendar", "investment account"]
        camera = "Medium interaction shot, then widen to reveal the system running alone."
        poses = ["tap", "point", "relaxed", "celebrate"]
    elif _mentions(context, ("paycheck", "salary", "future self", "first 10")):
        action = "Receive the paycheck, anticipate the choice, separate ten percent, and point to the future account."
        expressions = ["neutral", "focused", "confident", "happy"]
        props = ["paycheck", "10 percent token", "future account"]
        camera = "Medium entrance, track the transfer, settle on the funded future account."
        poses = ["walk", "receive", "point", "celebrate"]
    elif _mentions(context, ("research", "data", "keyboard", "type", "dashboard", "computer")):
        action = "Study the source, type the key finding, swipe through the evidence, and point to the conclusion."
        expressions = ["focused", "curious", "thinking", "confident"]
        props = ["computer", "research cards", "evidence panel"]
        camera = "Over-shoulder research setup, insert on the evidence, then settle into a readable medium shot."
        poses = ["look", "type", "swipe", "point"]
    elif _mentions(context, ("why", "question", "wonder", "consider", "think", "mystery")):
        action = "Look toward the question, pause to think, weigh the uncertainty, and nod into the explanation."
        expressions = ["curious", "thinking", "concerned", "confident"]
        props = ["question marker", "evidence card"]
        camera = "Slow investigative push-in, hold the thinking beat, then ease wider for the answer."
        poses = ["look", "think", "confused", "nod"]
    elif _mentions(context, ("wrong", "myth", "not true", "reject", "never", "don't")):
        action = "Present the familiar claim, shake it off, reveal the correction, and nod on the verified fact."
        expressions = ["neutral", "concerned", "focused", "confident"]
        props = ["claim card", "correction marker"]
        camera = "Locked medium shot with a brief claim insert and a clean push toward the correction."
        poses = ["point", "shake_head", "swipe", "nod"]
    elif _mentions(context, ("uncertain", "unknown", "maybe", "perhaps", "unclear")):
        action = "Inspect both possibilities, acknowledge the uncertainty, shrug, and point toward what is known."
        expressions = ["curious", "thinking", "concerned", "confident"]
        props = ["option cards", "known-facts panel"]
        camera = "Balanced medium shot, gentle lateral drift across the options, then hold the known evidence."
        poses = ["look", "confused", "shrug", "point"]
    elif _mentions(context, ("race", "rush", "urgent", "quickly", "fast", "chase")):
        action = "Accelerate into the scene, run through the urgent beat, stop on the key fact, and signal the result."
        expressions = ["focused", "concerned", "confident", "happy"]
        props = ["pace marker", "result card"]
        camera = "Tracking entrance with restrained speed, then stabilize for the explanatory finish."
        poses = ["walk", "run", "point", "celebrate"]
    elif _mentions(context, ("hello", "welcome", "meet", "introduce")):
        action = "Enter naturally, greet the audience, introduce the subject, and settle into an attentive stance."
        expressions = ["neutral", "happy", "confident", "neutral"]
        props = ["subject title"]
        camera = "Welcoming medium-wide entrance followed by a gentle push toward the introduction."
        poses = ["walk", "wave", "point", "idle"]
    else:
        action = "Enter, observe the key visual, gesture toward the main idea, and land on a clear reaction."
        expressions = ["neutral", "curious", "focused", "confident"]
        props = []
        camera = "Medium establishing shot with a restrained push-in on the final idea."
        poses = ["walk", "idle", "point", "relaxed"]

    return {
        "version": "1.9.3",
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
