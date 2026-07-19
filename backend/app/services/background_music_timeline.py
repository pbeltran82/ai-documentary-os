from __future__ import annotations

"""Optional, narration-safe background music for Timeline Builder.

This module installs last. It extends the established timeline stack without
changing narration files: music is looped, faded, attenuated, sidechain-ducked
under speech, mixed, and limited only in the final FFmpeg render graph.
"""

import json
from pathlib import Path
from typing import Any

from . import timeline_builder as base
from .background_music import load_background_music
from .media_library import resolve_media_path

MUSIC_STYLE_DEFAULTS = {
    "music_enabled": False,
    "music_gain_db": -22.0,
    "music_ducking_db": -8.0,
    "music_fade_seconds": 1.5,
}
MUSIC_STYLE_KEYS = tuple(MUSIC_STYLE_DEFAULTS)

base.DEFAULT_STYLE.update(MUSIC_STYLE_DEFAULTS)

_original_normalize_timeline_style = base.normalize_timeline_style
_original_build_filter_graph = base.build_filter_graph
_original_build_ffmpeg_command = base.build_ffmpeg_command
_original_build_timeline_plan = base.build_timeline_plan


def _style_values(style: Any) -> dict[str, Any]:
    if style is None:
        return {}
    if hasattr(style, "model_dump"):
        return dict(style.model_dump(exclude_none=True))
    return dict(style)


def normalize_timeline_style(style=None) -> dict[str, Any]:
    normalized = _original_normalize_timeline_style(style)
    values = _style_values(style)
    normalized["music_enabled"] = bool(normalized.get("music_enabled", False))
    normalized["music_gain_db"] = round(
        max(-36.0, min(-10.0, float(normalized.get("music_gain_db", -22.0)))),
        1,
    )
    normalized["music_ducking_db"] = round(
        max(-18.0, min(0.0, float(normalized.get("music_ducking_db", -8.0)))),
        1,
    )
    normalized["music_fade_seconds"] = round(
        max(0.0, min(8.0, float(normalized.get("music_fade_seconds", 1.5)))),
        2,
    )
    # Private render-only values are intentionally not persisted in style.json.
    for key in ("music_source_file", "music_project_id"):
        if key in values:
            normalized[key] = values[key]
    return normalized


def save_timeline_style(project_id: int, style) -> dict[str, Any]:
    """Merge partial updates so legacy frontend payloads cannot disable music."""
    path = base.timeline_style_path(project_id)
    current: dict[str, Any] = {}
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                current = payload
        except (OSError, json.JSONDecodeError):
            current = {}
    merged = {**current, **_style_values(style)}
    normalized = normalize_timeline_style(merged)
    persistent = {key: value for key, value in normalized.items() if key in base.DEFAULT_STYLE}
    base.atomic_text_write(path, json.dumps(persistent, indent=2, ensure_ascii=False) + "\n")
    return persistent


def _music_filter(
    music_input_index: int,
    runtime_seconds: float,
    style: dict[str, Any],
    output_label: str,
) -> str:
    gain_db = float(style.get("music_gain_db", -22.0))
    fade_seconds = min(float(style.get("music_fade_seconds", 1.5)), runtime_seconds / 3)
    filters = (
        f"[{music_input_index}:a]"
        "asetpts=PTS-STARTPTS,"
        f"aresample={base.AUDIO_SAMPLE_RATE},"
        "aformat=sample_fmts=fltp:channel_layouts=stereo,"
        f"volume={gain_db:g}dB,"
        f"atrim=duration={runtime_seconds:.3f}"
    )
    if fade_seconds > 0:
        fade_out_start = max(0.0, runtime_seconds - fade_seconds)
        filters += (
            f",afade=t=in:st=0:d={fade_seconds:.3f}"
            f",afade=t=out:st={fade_out_start:.3f}:d={fade_seconds:.3f}"
        )
    return filters + f"[{output_label}]"


def build_filter_graph(
    clips: list[dict[str, Any]],
    runtime_seconds: float,
    style: dict[str, Any],
    voiceover_input_index: int | None = None,
    music_input_index: int | None = None,
) -> str:
    graph = _original_build_filter_graph(
        clips,
        runtime_seconds,
        style,
        voiceover_input_index,
    )
    if music_input_index is None:
        return graph

    music_chain = _music_filter(music_input_index, runtime_seconds, style, "music_bed")
    if voiceover_input_index is None:
        return ";".join(
            part for part in (graph, music_chain, "[music_bed]alimiter=limit=0.95[outa]") if part
        )

    if not graph.endswith("[outa]"):
        return graph
    graph = graph[: -len("[outa]")] + "[narration_raw]"
    ducking_db = abs(float(style.get("music_ducking_db", -8.0)))
    ratio = max(2.0, min(20.0, 1.0 + ducking_db / 1.5))
    audio_mix = (
        "[narration_raw]asplit=2[narration_mix][narration_side];"
        f"{music_chain};"
        "[music_bed][narration_side]"
        f"sidechaincompress=threshold=0.018:ratio={ratio:.2f}:"
        "attack=20:release=450[ducked_music];"
        "[narration_mix][ducked_music]"
        "amix=inputs=2:duration=first:dropout_transition=0,"
        "alimiter=limit=0.95[outa]"
    )
    return f"{graph};{audio_mix}"


def build_ffmpeg_command(
    clips: list[dict[str, Any]],
    output_path: Path,
    executable: str | None = None,
    voiceover: dict[str, Any] | None = None,
    runtime_seconds: float | None = None,
    style=None,
    music: dict[str, Any] | None = None,
) -> list[str]:
    raw_style = _style_values(style)
    music_source = str(
        (music or {}).get("source_file")
        or raw_style.get("music_source_file")
        or ""
    )
    enabled = bool(raw_style.get("music_enabled", False) and music_source)
    command = _original_build_ffmpeg_command(
        clips,
        output_path,
        executable,
        voiceover,
        runtime_seconds,
        style,
    )
    if not enabled:
        return command

    runtime = runtime_seconds if runtime_seconds is not None else sum(
        float(clip["duration_seconds"]) for clip in clips
    )
    voiceover_input_index = len(clips) if voiceover is not None else None
    music_input_index = len(clips) + (1 if voiceover is not None else 0)
    normalized_style = normalize_timeline_style(raw_style)

    filter_flag = command.index("-filter_complex")
    command[filter_flag:filter_flag] = ["-stream_loop", "-1", "-i", music_source]
    filter_value_index = command.index("-filter_complex") + 1
    command[filter_value_index] = build_filter_graph(
        clips,
        float(runtime),
        normalized_style,
        voiceover_input_index,
        music_input_index,
    )

    if voiceover is None and "-an" in command:
        audio_index = command.index("-an")
        command[audio_index : audio_index + 1] = [
            "-map",
            "[outa]",
            "-c:a",
            "aac",
            "-b:a",
            base.AUDIO_BITRATE,
        ]
    return command


def build_timeline_plan(project, style=None) -> dict[str, Any]:
    plan = _original_build_timeline_plan(project, style)
    music = load_background_music(project.id)
    settings = plan["settings"]
    enabled = bool(settings.get("music_enabled", False) and music)
    settings["music_available"] = music is not None
    settings["music_active"] = enabled
    settings["music_project_id"] = project.id
    if music is not None:
        settings["music_source_file"] = music["source_file"]

    if enabled and plan.get("voiceover"):
        settings["audio"] = "narration + ducked background music"
    elif enabled:
        settings["audio"] = "background music"

    plan["background_music"] = music
    output_path = resolve_media_path(plan["output_relative_path"])
    if plan.get("command") and output_path is not None:
        plan["command"] = build_ffmpeg_command(
            plan["clips"],
            output_path,
            base.ffmpeg_executable(),
            voiceover=plan.get("voiceover"),
            runtime_seconds=plan["runtime_seconds"],
            style=settings,
            music=music if enabled else None,
        )
    return plan


base.normalize_timeline_style = normalize_timeline_style
base.save_timeline_style = save_timeline_style
base.build_filter_graph = build_filter_graph
base.build_ffmpeg_command = build_ffmpeg_command
base.build_timeline_plan = build_timeline_plan

render_first_cut = base.render_first_cut
write_timeline_plan = base.write_timeline_plan
load_timeline_style = base.load_timeline_style
