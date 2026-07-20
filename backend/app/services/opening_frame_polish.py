from __future__ import annotations

"""Release guard for immediate non-black openings on generated documentaries.

The sixth Mars exports proved that internal transitions were clean, but both
formats retained two dark source frames at the beginning. Landscape timelines
also applied a project-level fade-in. This guard removes the opening fade for an
authored exact visual and trims a small first-clip-only decoder/fade safety
handle without changing the scene slot or final runtime.
"""

from typing import Any

from . import timeline_builder as timeline
from . import timeline_playback_polish as playback
from .exact_visual_timing import is_subscribe_cta_clip

OPENING_SAFETY_TRIM_FRAMES = 3

_previous_normalized_video_filter = timeline.normalized_video_filter
_previous_build_filter_graph = timeline.build_filter_graph


def _is_generated_exact_visual(clip: dict[str, Any]) -> bool:
    return bool(
        str(clip.get("provider", "")).lower() == "generated"
        and clip.get("exact_visual_family_id")
    )


def _is_authored_opening(clip: dict[str, Any]) -> bool:
    return bool(int(clip.get("input_index", -1)) == 0 and _is_generated_exact_visual(clip))


def opening_safety_trim_seconds() -> float:
    return OPENING_SAFETY_TRIM_FRAMES / max(1, timeline.OUTPUT_FPS)


def normalized_video_filter(
    clip: dict[str, Any],
    processed_duration: float,
) -> str:
    if not _is_authored_opening(clip) or is_subscribe_cta_clip(clip):
        return _previous_normalized_video_filter(clip, processed_duration)

    index = clip["input_index"]
    scene_duration = max(0.2, float(clip["duration_seconds"]))
    normal_trim = playback.generated_edge_trim_seconds(clip)
    start_trim = min(
        scene_duration * 0.2,
        normal_trim + opening_safety_trim_seconds(),
    )
    end_trim = normal_trim
    core_duration = max(0.1, scene_duration - start_trim - end_trim)
    stretch = max(0.01, float(processed_duration) / core_duration)
    fit_filter = playback.generated_fit_filter(clip)

    return (
        f"[{index}:v]"
        f"trim=start={start_trim:.3f}:duration={core_duration:.3f},"
        "setpts=(PTS-STARTPTS)*"
        f"{stretch:.6f},"
        f"{fit_filter}"
        "setsar=1,"
        f"fps={timeline.OUTPUT_FPS},"
        "format=yuv420p"
    )


def build_filter_graph(
    clips: list[dict[str, Any]],
    runtime_seconds: float,
    style: dict[str, Any],
    voiceover_input_index: int | None = None,
) -> str:
    resolved = dict(style)
    if clips and _is_authored_opening(clips[0]):
        # The exact visual already authors its own entrance. A timeline fade-in
        # makes frame zero black and weakens autoplay hooks in both formats.
        resolved["edge_fade_seconds"] = 0.0
    return _previous_build_filter_graph(
        clips,
        runtime_seconds,
        resolved,
        voiceover_input_index,
    )


timeline.normalized_video_filter = normalized_video_filter
timeline.build_filter_graph = build_filter_graph
