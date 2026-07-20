from __future__ import annotations

"""Rendered-delivery clock for the Internet and human-attention visual family.

The first topic-aware release correctly chose Internet visuals, but a regenerated
exact visual could still collapse to one composition when persisted visual-beat
metadata was missing, incomplete, or carried timing from an earlier narration
revision.  This module makes the delivered pixels independent of that fragile
state: every long Internet scene receives deterministic equal-time windows and a
scene-specific visual arc.  The final scene always resolves on the authored
attention-choice conclusion.
"""

import math
from typing import Any

from . import cartoon_documentary as cartoon
from . import cartoon_visual_overhaul_v63 as v63
from . import cartoon_visual_overhaul_v65 as v65
from . import cartoon_visual_overhaul_v66 as v66
from . import internet_attention_visuals as internet
from . import regular_transition_polish as transitions

TARGET_WINDOW_SECONDS = 6.0
MIN_LONG_SCENE_WINDOWS = 4
MAX_WINDOWS = 10

# Scene 2 begins with growth rather than replaying Scene 1's CRT composition.
# Every arc has intentionally different silhouettes and spatial structures.
DELIVERY_ARCS: dict[int, tuple[str, ...]] = {
    1: (
        "internet_early_web",
        "internet_search_growth",
        "internet_smartphone_shift",
        "internet_notification_lab",
        "internet_fragmented_day",
    ),
    2: (
        "internet_search_growth",
        "internet_early_web",
        "internet_smartphone_shift",
        "internet_connected_benefits",
        "internet_algorithm_feed",
    ),
    3: (
        "internet_smartphone_shift",
        "internet_algorithm_feed",
        "internet_notification_lab",
        "internet_fragmented_day",
        "internet_evidence_review",
    ),
    4: (
        "internet_notification_lab",
        "internet_evidence_review",
        "internet_fragmented_day",
        "internet_attention_choice",
    ),
    5: (
        "internet_connected_benefits",
        "internet_algorithm_feed",
        "internet_fragmented_day",
        "internet_evidence_review",
        "internet_connected_benefits",
    ),
    6: (
        "internet_fragmented_day",
        "internet_notification_lab",
        "internet_connected_benefits",
        "internet_intentional_design",
        "internet_attention_choice",
    ),
    7: (
        "internet_intentional_design",
        "internet_connected_benefits",
        "internet_fragmented_day",
        "internet_attention_choice",
    ),
}


def _duration(scene: Any) -> float:
    return max(0.25, float(getattr(scene, "duration_seconds", 0.0) or 0.0))


def _raw_intents(scene: Any) -> list[str]:
    plan = dict(getattr(scene, "animation_plan", None) or {})
    beats = list(plan.get("visual_beats") or [])
    return [str(item.get("visual_intent") or "") for item in beats if isinstance(item, dict)]


def delivery_window_count(scene: Any) -> int:
    """Return a stable edit count even when stored beat metadata is unusable."""
    duration = _duration(scene)
    stored_count = len(_raw_intents(scene))
    duration_count = math.ceil(duration / TARGET_WINDOW_SECONDS)
    minimum = MIN_LONG_SCENE_WINDOWS if duration >= 20.0 else 1
    return max(minimum, min(MAX_WINDOWS, max(stored_count, duration_count, 1)))


def effective_visual_beats(scene: Any) -> list[dict[str, Any]]:
    """Build contiguous equal-time windows covering the exact rendered duration."""
    duration = _duration(scene)
    count = delivery_window_count(scene)
    intents = _raw_intents(scene)
    window = duration / count
    beats: list[dict[str, Any]] = []
    for index in range(count):
        start = index * window
        end = duration if index == count - 1 else (index + 1) * window
        intent = intents[min(index, len(intents) - 1)] if intents else str(
            getattr(scene, "visual_intent", "") or getattr(scene, "narration", "")
        )
        beats.append(
            {
                "beat_number": index + 1,
                "relative_start_seconds": round(start, 3),
                "relative_end_seconds": round(end, 3),
                "duration_seconds": round(end - start, 3),
                "visual_intent": intent,
            }
        )
    return beats


def _scene_arc(scene: Any) -> tuple[str, ...]:
    number = int(getattr(scene, "scene_number", 1) or 1)
    return DELIVERY_ARCS.get(number, tuple(internet.INTERNET_TEMPLATE_BY_ID))


def beat_template_sequence(scene: Any, template_id: str | None = None) -> list[str]:
    """Resolve a deterministic, non-adjacent composition for every delivery window."""
    count = delivery_window_count(scene)
    arc = _scene_arc(scene)
    sequence = [arc[index % len(arc)] for index in range(count)]

    # A stale selected-asset identity must never force an old Mars or prior scene
    # composition back into the delivered frames.  The scene arc is authoritative.
    for index in range(1, len(sequence)):
        if sequence[index] == sequence[index - 1]:
            sequence[index] = arc[(index + 1) % len(arc)]

    number = int(getattr(scene, "scene_number", 1) or 1)
    if number == 7:
        sequence[-1] = "internet_attention_choice"
        if len(sequence) > 1 and sequence[-2] == sequence[-1]:
            sequence[-2] = "internet_intentional_design"
    return sequence


def beat_state(
    scene: Any,
    time_seconds: float,
    duration_seconds: float,
) -> tuple[int, float]:
    """Map absolute render time to a delivery window and local animation clock."""
    beats = effective_visual_beats(scene)
    time_value = max(0.0, min(float(time_seconds), max(0.001, float(duration_seconds))))
    for index, beat in enumerate(beats):
        start = float(beat["relative_start_seconds"])
        end = float(beat["relative_end_seconds"])
        if time_value < end or index == len(beats) - 1:
            progress = (time_value - start) / max(0.001, end - start)
            return index, max(0.0, min(1.0, progress))
    return len(beats) - 1, 1.0


# The v1 frame renderer looks these names up dynamically inside its own module.
# Replacing them here changes actual encoded frames, not only planning metadata.
internet._visual_beats = effective_visual_beats
internet.beat_template_sequence = beat_template_sequence
internet._beat_state = beat_state
internet.SCENE_ARCS.update(DELIVERY_ARCS)

# Keep every compatibility surface pointed at the topic-aware renderer.
cartoon.render_planned_frame = internet.render_planned_frame
v63.render_planned_frame = internet.render_planned_frame
v65.render_planned_frame = internet.render_planned_frame
v66.render_planned_frame = internet.render_planned_frame

# Internet exact visuals are text-bearing authored documentary scenes.  A clean cut
# is safer than the generic fade-to-black policy and prevents one-frame flashes.
transitions.DOCUMENTARY_TEMPLATE_IDS.update(internet.INTERNET_TEMPLATE_IDS)
