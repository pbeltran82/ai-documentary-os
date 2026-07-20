from __future__ import annotations

"""Native Shorts transition contract: immediate hook, clean semantic cuts, no black flashes."""

from typing import Any

from . import timeline_builder as timeline
from .video_format import SHORTS_FORMAT

_original_apply_edit_decisions = timeline.apply_edit_decisions
_original_build_filter_graph = timeline.build_filter_graph


def _native_shorts_boundary(current: dict[str, Any], following: dict[str, Any]) -> bool:
    return bool(
        str(current.get("video_format")) == SHORTS_FORMAT
        and str(following.get("video_format")) == SHORTS_FORMAT
        and timeline.is_exact_visual_boundary(current, following)
    )


def apply_edit_decisions(clips: list[dict[str, Any]], style: dict[str, Any]) -> None:
    _original_apply_edit_decisions(clips, style)
    for index, clip in enumerate(clips[:-1]):
        following = clips[index + 1]
        if not _native_shorts_boundary(clip, following):
            continue
        clip["transition_out"] = "cut"
        clip["transition_duration_seconds"] = 0.0
        clip["processed_duration_seconds"] = round(float(clip["duration_seconds"]), 3)
        aspect_ratio = "9:16"
        base_action = (
            f"Loop if needed, trim to {clip['duration_seconds']:g}s, fit {aspect_ratio}"
            if clip["media_type"] == "video"
            else f"Hold for {clip['duration_seconds']:g}s, fit {aspect_ratio}"
        )
        motion_label = {
            "zoom_in": "gentle zoom in",
            "zoom_out": "gentle zoom out",
            "pan_left": "slow pan left",
            "pan_right": "slow pan right",
            "static": "static frame" if clip["media_type"] == "photo" else "native motion",
        }[clip["motion_effect"]]
        clip["assembly_action"] = f"{base_action}; {motion_label}; clean cut to next scene"


def build_filter_graph(
    clips: list[dict[str, Any]],
    runtime_seconds: float,
    style: dict[str, Any],
    voiceover_input_index: int | None = None,
) -> str:
    resolved = dict(style)
    if str(resolved.get("video_format")) == SHORTS_FORMAT and any(
        clip.get("exact_visual_family_id") for clip in clips
    ):
        # Vertical stories must begin on the designed hook and end on the authored
        # conclusion. Per-export edge fades created visible black frames at both ends.
        resolved["edge_fade_seconds"] = 0.0
    return _original_build_filter_graph(
        clips,
        runtime_seconds,
        resolved,
        voiceover_input_index,
    )


timeline.apply_edit_decisions = apply_edit_decisions
timeline.build_filter_graph = build_filter_graph
