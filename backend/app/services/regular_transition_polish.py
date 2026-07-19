from __future__ import annotations

"""Regular exact-visual transition contract: clean cuts, never a dip to black.

The general timeline builder protects text-heavy exact visuals by replacing a
crossfade with ``fade_black``. Frame-level QA of the fifth Mars export showed
that this produces one fully black frame at every internal scene boundary.
Regular generated documentary scenes already contain authored composition and
motion, so a clean cut is the safer editorial contract.
"""

from typing import Any

from . import timeline_builder as timeline
from .video_format import SHORTS_FORMAT

_previous_apply_edit_decisions = timeline.apply_edit_decisions


def _regular_exact_visual_boundary(
    current: dict[str, Any],
    following: dict[str, Any],
) -> bool:
    return bool(
        str(current.get("video_format")) != SHORTS_FORMAT
        and str(following.get("video_format")) != SHORTS_FORMAT
        and timeline.is_exact_visual_boundary(current, following)
    )


def _base_action(clip: dict[str, Any]) -> str:
    aspect_ratio = "16:9"
    if clip["media_type"] == "video":
        return f"Loop if needed, trim to {clip['duration_seconds']:g}s, fit {aspect_ratio}"
    return f"Hold for {clip['duration_seconds']:g}s, fit {aspect_ratio}"


def _motion_label(clip: dict[str, Any]) -> str:
    return {
        "zoom_in": "gentle zoom in",
        "zoom_out": "gentle zoom out",
        "pan_left": "slow pan left",
        "pan_right": "slow pan right",
        "static": "static frame" if clip["media_type"] == "photo" else "native motion",
    }[clip["motion_effect"]]


def apply_edit_decisions(clips: list[dict[str, Any]], style: dict[str, Any]) -> None:
    _previous_apply_edit_decisions(clips, style)
    for index, clip in enumerate(clips[:-1]):
        following = clips[index + 1]
        if not _regular_exact_visual_boundary(clip, following):
            continue
        clip["transition_out"] = "cut"
        clip["transition_duration_seconds"] = 0.0
        clip["processed_duration_seconds"] = round(float(clip["duration_seconds"]), 3)
        clip["assembly_action"] = (
            f"{_base_action(clip)}; {_motion_label(clip)}; clean cut to next scene"
        )


timeline.apply_edit_decisions = apply_edit_decisions
