from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PerformancePreset:
    preset_id: str
    label: str
    description: str
    triggers: tuple[str, ...]
    character_action: str
    expressions: tuple[str, ...]
    poses: tuple[str, ...]
    props: tuple[str, ...]
    camera_direction: str
    camera_motion: dict[str, Any]


PRESETS = (
    PerformancePreset(
        "investigate", "Investigate", "Question, examine evidence, and arrive at a supported answer.",
        ("why", "question", "wonder", "consider", "think", "mystery"),
        "Look toward the question, pause to think, weigh the uncertainty, and nod into the explanation.",
        ("curious", "thinking", "concerned", "confident"),
        ("look", "think", "confused", "nod"),
        ("question marker", "evidence card"),
        "Slow investigative push-in, hold the thinking beat, then ease wider for the answer.",
        {"mode": "push_in", "intensity": 0.58, "focus": [0.48, 0.48]},
    ),
    PerformancePreset(
        "research", "Research & Explain", "Work through sources and present the key finding.",
        ("research", "data", "keyboard", "type", "dashboard", "computer"),
        "Study the source, type the key finding, swipe through the evidence, and point to the conclusion.",
        ("focused", "curious", "thinking", "confident"),
        ("look", "type", "swipe", "point"),
        ("computer", "research cards", "evidence panel"),
        "Over-shoulder research setup, insert on the evidence, then settle into a readable medium shot.",
        {"mode": "drift", "intensity": 0.42, "focus": [0.56, 0.50]},
    ),
    PerformancePreset(
        "correct_myth", "Correct a Myth", "Reject a familiar claim and land on the verified fact.",
        ("wrong", "myth", "not true", "reject", "never", "don't"),
        "Present the familiar claim, shake it off, reveal the correction, and nod on the verified fact.",
        ("neutral", "concerned", "focused", "confident"),
        ("point", "shake_head", "swipe", "nod"),
        ("claim card", "correction marker"),
        "Locked medium shot with a brief claim insert and a clean push toward the correction.",
        {"mode": "settle", "intensity": 0.52, "focus": [0.55, 0.48]},
    ),
    PerformancePreset(
        "uncertainty", "Explain Uncertainty", "Show competing possibilities while protecting what is known.",
        ("uncertain", "unknown", "maybe", "perhaps", "unclear"),
        "Inspect both possibilities, acknowledge the uncertainty, shrug, and point toward what is known.",
        ("curious", "thinking", "concerned", "confident"),
        ("look", "confused", "shrug", "point"),
        ("option cards", "known-facts panel"),
        "Balanced medium shot, gentle lateral drift across the options, then hold the known evidence.",
        {"mode": "drift", "intensity": 0.34, "focus": [0.50, 0.50]},
    ),
    PerformancePreset(
        "urgent_action", "Urgent Action", "Build pace, move decisively, and stabilize on the result.",
        ("race", "rush", "urgent", "quickly", "fast", "chase"),
        "Accelerate into the scene, run through the urgent beat, stop on the key fact, and signal the result.",
        ("focused", "concerned", "confident", "happy"),
        ("walk", "run", "point", "celebrate"),
        ("pace marker", "result card"),
        "Tracking entrance with restrained speed, then stabilize for the explanatory finish.",
        {"mode": "track", "intensity": 0.62, "focus": [0.50, 0.52]},
    ),
    PerformancePreset(
        "welcome", "Welcome & Introduce", "Greet the audience and establish a new subject.",
        ("hello", "welcome", "meet", "introduce"),
        "Enter naturally, greet the audience, introduce the subject, and settle into an attentive stance.",
        ("neutral", "happy", "confident", "neutral"),
        ("walk", "wave", "point", "idle"),
        ("subject title",),
        "Welcoming medium-wide entrance followed by a gentle push toward the introduction.",
        {"mode": "push_in", "intensity": 0.32, "focus": [0.46, 0.50]},
    ),
    PerformancePreset(
        "explain", "Explain Clearly", "A neutral reusable arc for a direct documentary explanation.",
        (),
        "Enter, observe the key visual, gesture toward the main idea, and land on a clear reaction.",
        ("neutral", "curious", "focused", "confident"),
        ("walk", "idle", "point", "relaxed"),
        (),
        "Medium establishing shot with a restrained push-in on the final idea.",
        {"mode": "settle", "intensity": 0.28, "focus": [0.50, 0.50]},
    ),
)
PRESET_BY_ID = {preset.preset_id: preset for preset in PRESETS}


def _mentions(context: str, phrases: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", context) for phrase in phrases)


def suggest_preset(context: str) -> PerformancePreset:
    return next(
        (preset for preset in PRESETS if preset.triggers and _mentions(context, preset.triggers)),
        PRESET_BY_ID["explain"],
    )


def preset_catalog() -> list[dict[str, Any]]:
    return [
        {
            **asdict(preset),
            "triggers": list(preset.triggers),
            "expressions": list(preset.expressions),
            "poses": list(preset.poses),
            "props": list(preset.props),
        }
        for preset in PRESETS
    ]


def plan_from_preset(preset_id: str) -> dict[str, Any]:
    preset = PRESET_BY_ID[preset_id]
    return {
        "version": "1.9.5",
        "visual_strategy": "character_performance",
        "preset_id": preset.preset_id,
        "character_action": preset.character_action,
        "expression_sequence": list(preset.expressions),
        "pose_sequence": list(preset.poses),
        "props": list(preset.props),
        "camera_direction": preset.camera_direction,
        "camera_motion": dict(preset.camera_motion),
        "animation_beats": {
            "anticipation": 0.15,
            "action": 0.35,
            "overshoot": 0.15,
            "recovery": 0.35,
        },
        "transition_intention": "Hold the final readable pose before the timeline transition.",
    }
