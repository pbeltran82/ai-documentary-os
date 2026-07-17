from __future__ import annotations

from typing import Any

from . import timeline_subject_motion as subject
from . import timeline_builder as base
from .exact_visual_timing import is_subscribe_cta_clip


GENERATED_EDGE_TRIM_MAX_SECONDS = 0.12
NARRATION_TARGET_LUFS = -16.0
NARRATION_TRUE_PEAK_DB = -1.5
NARRATION_LRA = 11

_original_normalized_video_filter = base.normalized_video_filter
_original_build_filter_graph = base.build_filter_graph
_original_build_timeline_plan = base.build_timeline_plan


def generated_edge_trim_seconds(clip: dict[str, Any]) -> float:
    duration = max(0.1, float(clip.get("duration_seconds", 0.1)))
    return round(
        min(
            GENERATED_EDGE_TRIM_MAX_SECONDS,
            max(0.04, duration * 0.025),
            duration * 0.08,
        ),
        3,
    )


def generated_fit_filter(clip: dict[str, Any]) -> str:
    width, height = base.output_dimensions(clip)
    source_width = int(clip.get("source_width") or 0)
    source_height = int(clip.get("source_height") or 0)
    output_is_portrait = height > width
    source_is_portrait = source_height > source_width
    if source_width > 0 and source_height > 0 and output_is_portrait != source_is_portrait:
        index = clip["input_index"]
        background = f"generated_bg_{index}"
        foreground = f"generated_fg_{index}"
        blurred = f"generated_blur_{index}"
        framed = f"generated_frame_{index}"
        return (
            f"split=2[{background}][{foreground}];"
            f"[{background}]"
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            "gblur=sigma=32,"
            "eq=brightness=-0.22:saturation=0.75,"
            f"setsar=1[{blurred}];"
            f"[{foreground}]"
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"setsar=1[{framed}];"
            f"[{blurred}][{framed}]"
            "overlay=(W-w)/2:(H-h)/2:shortest=1,"
        )
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
    )


def normalized_video_filter(
    clip: dict[str, Any],
    processed_duration: float,
) -> str:
    if str(clip.get("provider", "")).lower() != "generated":
        return _original_normalized_video_filter(clip, processed_duration)

    index = clip["input_index"]
    fit_filter = generated_fit_filter(clip)
    if is_subscribe_cta_clip(clip):
        source_duration = max(
            0.2,
            float(clip.get("source_duration_seconds") or clip["duration_seconds"]),
        )
        source_clip = {**clip, "duration_seconds": source_duration}
        edge_trim = generated_edge_trim_seconds(source_clip)
        source_fade = max(0.15, min(0.35, source_duration / 6))
        clear_duration = max(
            0.1,
            source_duration - edge_trim - source_fade - (1 / base.OUTPUT_FPS),
        )
        hold_duration = max(0.0, float(processed_duration) - clear_duration)

        # The CTA owns its entrance animation, while Timeline Builder owns the
        # closing fade. Stop on the last fully clear Like + Subscribe frame and
        # hold it. This also upgrades older short CTA assets without replaying
        # their entrance or exposing their baked-in exit fade.
        return (
            f"[{index}:v]"
            f"trim=start={edge_trim:.3f}:duration={clear_duration:.3f},"
            "setpts=PTS-STARTPTS,"
            f"tpad=stop_mode=clone:stop_duration={hold_duration:.3f},"
            f"trim=duration={float(processed_duration):.3f},"
            f"{fit_filter}"
            "setsar=1,"
            f"fps={base.OUTPUT_FPS},"
            "format=yuv420p"
        )

    scene_duration = max(0.2, float(clip["duration_seconds"]))
    edge_trim = generated_edge_trim_seconds(clip)
    core_duration = max(0.1, scene_duration - edge_trim * 2)
    stretch = max(0.01, float(processed_duration) / core_duration)

    # Exact Visual Studio clips already contain their own short entrance and exit
    # fades. Timeline Builder also owns the project-level opening/closing fades and
    # crossfades. Trim the fully dark edge frames, then gently retime the useful
    # interior to provide transition handles without looping back through a fade.
    return (
        f"[{index}:v]"
        f"trim=start={edge_trim:.3f}:duration={core_duration:.3f},"
        f"setpts=(PTS-STARTPTS)*{stretch:.6f},"
        f"{fit_filter}"
        "setsar=1,"
        f"fps={base.OUTPUT_FPS},"
        "format=yuv420p"
    )


def build_filter_graph(
    clips: list[dict[str, Any]],
    runtime_seconds: float,
    style: dict[str, Any],
    voiceover_input_index: int | None = None,
) -> str:
    graph = _original_build_filter_graph(
        clips,
        runtime_seconds,
        style,
        voiceover_input_index,
    )
    if voiceover_input_index is None:
        return graph

    anchor = "aformat=sample_fmts=fltp:channel_layouts=stereo,"
    normalized = (
        anchor
        + f"loudnorm=I={NARRATION_TARGET_LUFS:g}:"
        + f"TP={NARRATION_TRUE_PEAK_DB:g}:LRA={NARRATION_LRA},"
    )
    return graph.replace(anchor, normalized, 1)


def build_timeline_plan(project, style=None) -> dict[str, Any]:
    plan = _original_build_timeline_plan(project, style)
    plan["settings"]["generated_edge_treatment"] = "trim_dark_fades_and_retime"
    plan["settings"]["generated_edge_trim_max_seconds"] = GENERATED_EDGE_TRIM_MAX_SECONDS
    plan["settings"]["narration_target_lufs"] = NARRATION_TARGET_LUFS
    plan["settings"]["narration_true_peak_db"] = NARRATION_TRUE_PEAK_DB
    return plan


base.normalized_video_filter = normalized_video_filter
base.build_filter_graph = build_filter_graph
base.build_timeline_plan = build_timeline_plan

render_first_cut = base.render_first_cut
write_timeline_plan = base.write_timeline_plan
