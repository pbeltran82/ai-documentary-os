from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import HTTPException

from ..models import Project, Scene
from ..schemas import TimelineStyleUpdate
from .caption_builder import write_caption_track
from .exact_visual_timing import effective_scene_duration, exact_visual_identity
from .media_library import MEDIA_ROOT, project_directory, public_media_url, resolve_media_path
from .video_format import SHORTS_FORMAT, video_format_profile
from .voiceover import load_voiceover

OUTPUT_WIDTH = int(os.getenv("TIMELINE_OUTPUT_WIDTH", "1920"))
OUTPUT_HEIGHT = int(os.getenv("TIMELINE_OUTPUT_HEIGHT", "1080"))
OUTPUT_FPS = int(os.getenv("TIMELINE_OUTPUT_FPS", "30"))
RENDER_TIMEOUT_SECONDS = int(os.getenv("TIMELINE_RENDER_TIMEOUT_SECONDS", "3600"))
FFMPEG_NAME = os.getenv("FFMPEG_BIN", "ffmpeg")
AUDIO_SAMPLE_RATE = int(os.getenv("TIMELINE_AUDIO_SAMPLE_RATE", "48000"))
AUDIO_BITRATE = os.getenv("TIMELINE_AUDIO_BITRATE", "192k")
ALIGNMENT_TOLERANCE_SECONDS = float(
    os.getenv("NARRATION_ALIGNMENT_TOLERANCE_SECONDS", "0.25")
)
EXACT_VISUAL_TEXT_TRANSITION_MAX_SECONDS = 0.24

DEFAULT_STYLE = {
    "transition_style": "crossfade",
    "transition_duration_seconds": 0.35,
    "photo_motion": "editorial",
    "edge_fade_seconds": 0.35,
}
TRANSITION_FILTERS = {
    "crossfade": "fade",
    "fade_black": "fadeblack",
}


def output_dimensions(values: dict[str, Any] | None = None) -> tuple[int, int]:
    values = values or {}
    return (
        int(values.get("output_width", OUTPUT_WIDTH)),
        int(values.get("output_height", OUTPUT_HEIGHT)),
    )


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def timeline_directory(project_id: int) -> Path:
    directory = project_directory(project_id) / "timeline"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def relative_media_path(path: Path) -> str:
    return path.resolve().relative_to(MEDIA_ROOT).as_posix()


def ffmpeg_executable() -> str | None:
    configured = Path(FFMPEG_NAME).expanduser()
    if configured.is_absolute():
        return str(configured) if configured.is_file() else None
    return shutil.which(FFMPEG_NAME)


def atomic_text_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f".{path.name}-",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def normalize_timeline_style(
    style: TimelineStyleUpdate | dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = dict(DEFAULT_STYLE)
    if style is not None:
        values = style.model_dump() if isinstance(style, TimelineStyleUpdate) else style
        normalized.update(
            {
                key: values[key]
                for key in DEFAULT_STYLE
                if key in values and values[key] is not None
            }
        )

    normalized["transition_duration_seconds"] = round(
        max(0.0, min(1.0, float(normalized["transition_duration_seconds"]))),
        3,
    )
    normalized["edge_fade_seconds"] = round(
        max(0.0, min(2.0, float(normalized["edge_fade_seconds"]))),
        3,
    )
    if normalized["transition_style"] == "cut":
        normalized["transition_duration_seconds"] = 0.0
    return normalized


def timeline_style_path(project_id: int) -> Path:
    return timeline_directory(project_id) / "style.json"


def load_timeline_style(project_id: int) -> dict[str, Any]:
    path = timeline_style_path(project_id)
    if not path.is_file():
        return normalize_timeline_style(None)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return normalize_timeline_style(None)
    return normalize_timeline_style(payload if isinstance(payload, dict) else None)


def save_timeline_style(
    project_id: int,
    style: TimelineStyleUpdate | dict[str, Any],
) -> dict[str, Any]:
    normalized = normalize_timeline_style(style)
    atomic_text_write(
        timeline_style_path(project_id),
        json.dumps(normalized, indent=2, ensure_ascii=False) + "\n",
    )
    return normalized


def transition_duration_for_boundary(
    previous_clip: dict[str, Any],
    next_clip: dict[str, Any],
    requested_seconds: float,
) -> float:
    if requested_seconds <= 0:
        return 0.0
    safe_limit = min(
        float(previous_clip["duration_seconds"]) * 0.25,
        float(next_clip["duration_seconds"]) * 0.25,
        0.75,
    )
    return round(max(0.0, min(requested_seconds, safe_limit)), 3)


def is_exact_visual_boundary(
    previous_clip: dict[str, Any],
    next_clip: dict[str, Any],
) -> bool:
    return bool(
        previous_clip.get("exact_visual_family_id")
        and next_clip.get("exact_visual_family_id")
    )


READABILITY_WORDS = {
    "app",
    "balance",
    "bill",
    "blueprint",
    "budget",
    "calendar",
    "chart",
    "document",
    "graph",
    "index",
    "interface",
    "map",
    "newspaper",
    "screen",
    "statement",
    "subscribe",
    "text",
}
EMPHASIS_WORDS = {
    "declined",
    "empty",
    "exact",
    "first",
    "important",
    "never",
    "nothing",
    "opposite",
    "warning",
    "zero",
}
REVEAL_WORDS = {
    "build",
    "compound",
    "future",
    "growth",
    "machine",
    "plan",
    "wealth",
}


def editorial_photo_motion(scene: Scene, clip_index: int) -> tuple[str, str]:
    asset = scene.selected_asset
    duration = float(scene.duration_seconds)
    context = " ".join(
        [scene.narration, scene.visual_intent, *scene.search_keywords]
    ).lower()
    context_words = set(context.replace("&", " ").split())
    width = int(asset.width if asset is not None else 0)
    height = int(asset.height if asset is not None else 0)
    ratio = width / height if width > 0 and height > 0 else 0.0

    if duration < 1.75:
        return "static", "Very short still held steady for immediate readability"
    if context_words & READABILITY_WORDS:
        return "static", "Text, chart, map, or interface content held steady for readability"
    if ratio >= 1.85 and duration >= 4:
        direction = "pan_left" if scene.scene_number % 2 else "pan_right"
        return direction, "Wide composition receives a slow documentary pan"
    if context_words & EMPHASIS_WORDS:
        return "zoom_in", "Narrative emphasis receives a restrained push-in"
    if context_words & REVEAL_WORDS:
        return "zoom_out", "Growth or reveal language receives a restrained pull-out"
    if ratio and ratio < 1.1:
        return "zoom_in", "Portrait-oriented source receives a subtle push-in over a soft background"
    fallback = "zoom_in" if clip_index % 2 == 0 else "zoom_out"
    return fallback, "Balanced editorial motion prevents a static slideshow feel"


def photo_motion_for_clip(
    scene: Scene,
    clip_index: int,
    media_type: str,
    photo_motion: str,
) -> tuple[str, str]:
    if media_type != "photo":
        return "static", "Stock video keeps its native motion"
    if photo_motion == "editorial":
        return editorial_photo_motion(scene, clip_index)
    if photo_motion == "static":
        return "static", "Still-photo motion disabled by the saved timeline style"
    if photo_motion == "alternate":
        motion = "zoom_in" if clip_index % 2 == 0 else "zoom_out"
        return motion, "Saved style alternates gentle zoom directions"
    return photo_motion, f"Saved style applies {photo_motion.replace('_', ' ')}"


def scene_clip(
    scene: Scene,
    input_index: int,
    style: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    asset = scene.selected_asset
    if asset is None or scene.asset_status != "ready" or not asset.local_path:
        return None, "No ready local asset"

    source = resolve_media_path(asset.local_path)
    if source is None or not source.is_file():
        return None, "Local asset file is missing"

    scene_duration = round(float(scene.duration_seconds), 3)
    duration = round(effective_scene_duration(scene), 3)
    source_duration = round(
        float(asset.duration_seconds or scene.duration_seconds),
        3,
    )
    exact_visual_family_id, exact_visual_template_id = exact_visual_identity(asset)
    motion, motion_reason = photo_motion_for_clip(
        scene,
        input_index,
        asset.media_type,
        str(style["photo_motion"]),
    )
    return (
        {
            "scene_id": scene.id,
            "scene_number": scene.scene_number,
            "input_index": input_index,
            "start_seconds": float(scene.start_seconds),
            "end_seconds": float(scene.end_seconds),
            "duration_seconds": duration,
            "source_scene_duration_seconds": scene_duration,
            "source_duration_seconds": source_duration,
            "source_width": int(asset.width or 0),
            "source_height": int(asset.height or 0),
            "output_width": int(style.get("output_width", OUTPUT_WIDTH)),
            "output_height": int(style.get("output_height", OUTPUT_HEIGHT)),
            "video_format": str(style.get("video_format", "youtube")),
            "duration_extension_seconds": round(duration - scene_duration, 3),
            "processed_duration_seconds": duration,
            "narration": scene.narration,
            "visual_intent": scene.visual_intent,
            "provider": asset.provider,
            "provider_asset_id": asset.provider_asset_id,
            "media_type": asset.media_type,
            "local_path": asset.local_path,
            "local_url": asset.download_url,
            "preview_url": asset.preview_url,
            "source_url": asset.source_url,
            "exact_visual_family_id": exact_visual_family_id,
            "exact_visual_template_id": exact_visual_template_id,
            "creator": asset.creator,
            "license_name": asset.license_name,
            "attribution": asset.attribution,
            "source_file": str(source),
            "motion_effect": motion,
            "motion_reason": motion_reason,
            "transition_out": "cut",
            "transition_duration_seconds": 0.0,
            "assembly_action": "",
        },
        None,
    )


def apply_edit_decisions(
    clips: list[dict[str, Any]],
    style: dict[str, Any],
) -> None:
    requested = float(style["transition_duration_seconds"])
    transition_style = str(style["transition_style"])

    for index, clip in enumerate(clips):
        transition_seconds = 0.0
        transition_out = "cut"
        if index < len(clips) - 1 and transition_style != "cut":
            next_clip = clips[index + 1]
            boundary_style = transition_style
            boundary_request = requested
            if (
                transition_style == "crossfade"
                and is_exact_visual_boundary(clip, next_clip)
            ):
                # Text-heavy exact visuals should never dissolve two titles and
                # two panel systems over each other. A short dip preserves the
                # transition rhythm while keeping every frame readable.
                boundary_style = "fade_black"
                boundary_request = min(
                    requested,
                    EXACT_VISUAL_TEXT_TRANSITION_MAX_SECONDS,
                )
            transition_seconds = transition_duration_for_boundary(
                clip,
                next_clip,
                boundary_request,
            )
            if transition_seconds > 0:
                transition_out = boundary_style

        clip["transition_out"] = transition_out
        clip["transition_duration_seconds"] = transition_seconds
        clip["processed_duration_seconds"] = round(
            float(clip["duration_seconds"]) + transition_seconds,
            3,
        )

        aspect_ratio = "9:16" if clip.get("video_format") == SHORTS_FORMAT else "16:9"
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
        transition_label = {
            "crossfade": f"{transition_seconds:g}s crossfade",
            "fade_black": f"{transition_seconds:g}s fade through black",
            "cut": "clean cut",
        }[transition_out]
        clip["assembly_action"] = (
            f"{base_action}; {motion_label}; {transition_label} to next scene"
            if index < len(clips) - 1
            else f"{base_action}; {motion_label}; closing fade"
        )


def narration_alignment(
    voiceover: dict[str, Any] | None,
    runtime_seconds: float,
) -> tuple[str, float | None, str]:
    if voiceover is None:
        return "missing", None, "Upload narration to render a voiced first cut."

    delta = round(float(voiceover["duration_seconds"]) - runtime_seconds, 3)
    if abs(delta) <= ALIGNMENT_TOLERANCE_SECONDS:
        return "aligned", delta, "Narration and visual timeline are aligned."
    if delta > 0:
        return (
            "longer",
            delta,
            f"Narration is {delta:g}s longer than the visual timeline and will be trimmed at render time.",
        )
    return (
        "shorter",
        delta,
        f"Narration is {abs(delta):g}s shorter than the visual timeline; silence will fill the remainder.",
    )


def normalized_video_filter(
    clip: dict[str, Any],
    processed_duration: float,
) -> str:
    index = clip["input_index"]
    width, height = output_dimensions(clip)
    vertical_stock = (
        str(clip.get("video_format")) == SHORTS_FORMAT
        and str(clip.get("provider", "")).lower() != "generated"
    )
    fit = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        if vertical_stock
        else (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        )
    )
    return (
        f"[{index}:v]"
        f"trim=duration={processed_duration:.3f},"
        "setpts=PTS-STARTPTS,"
        f"{fit}"
        "setsar=1,"
        f"fps={OUTPUT_FPS},"
        "format=yuv420p"
    )


def photo_zoom_expression(motion: str, frames: int, duration: float) -> tuple[str, str, str]:
    progress = f"on/{max(1, frames - 1)}"
    delta = 0.04 if duration <= 3 else 0.06 if duration <= 7 else 0.08
    if motion == "zoom_out":
        zoom = f"{1 + delta:.3f}-{delta:.3f}*{progress}"
        return zoom, "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if motion == "pan_left":
        return "1.060", f"(iw-iw/zoom)*(1-{progress})", "ih/2-(ih/zoom/2)"
    if motion == "pan_right":
        return "1.060", f"(iw-iw/zoom)*{progress}", "ih/2-(ih/zoom/2)"
    zoom = f"1.000+{delta:.3f}*{progress}"
    return zoom, "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"


def normalized_photo_filter(
    clip: dict[str, Any],
    processed_duration: float,
) -> str:
    index = clip["input_index"]
    width, height = output_dimensions(clip)
    motion = clip["motion_effect"]
    frames = max(2, int(round(processed_duration * OUTPUT_FPS)))
    background_label = f"photo_bg_{index}"
    foreground_label = f"photo_fg_{index}"
    blurred_label = f"photo_blur_{index}"
    framed_label = f"photo_frame_{index}"

    graph = (
        f"[{index}:v]"
        f"trim=duration={processed_duration:.3f},"
        "setpts=PTS-STARTPTS,"
        f"split=2[{background_label}][{foreground_label}];"
        f"[{background_label}]"
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        "gblur=sigma=28,"
        "eq=brightness=-0.18:saturation=0.78,"
        f"setsar=1[{blurred_label}];"
        f"[{foreground_label}]"
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"setsar=1[{framed_label}];"
        f"[{blurred_label}][{framed_label}]"
        "overlay=(W-w)/2:(H-h)/2:shortest=1,"
    )
    if motion == "static":
        return graph + f"fps={OUTPUT_FPS},format=yuv420p"

    zoom, x_position, y_position = photo_zoom_expression(
        motion,
        frames,
        processed_duration,
    )
    return (
        graph
        + f"zoompan=z='{zoom}':"
        f"x='{x_position}':"
        f"y='{y_position}':"
        f"d=1:s={width}x{height}:fps={OUTPUT_FPS},"
        "format=yuv420p"
    )


def build_filter_graph(
    clips: list[dict[str, Any]],
    runtime_seconds: float,
    style: dict[str, Any],
    voiceover_input_index: int | None = None,
) -> str:
    filters: list[str] = []
    edge_fade = min(float(style["edge_fade_seconds"]), runtime_seconds / 3)

    for clip_index, clip in enumerate(clips):
        processed_duration = float(clip["processed_duration_seconds"])
        chain = (
            normalized_photo_filter(clip, processed_duration)
            if clip["media_type"] == "photo"
            else normalized_video_filter(clip, processed_duration)
        )
        if clip_index == 0 and edge_fade > 0:
            chain += f",fade=t=in:st=0:d={edge_fade:.3f}"
        if clip_index == len(clips) - 1 and edge_fade > 0:
            fade_start = max(0.0, processed_duration - edge_fade)
            chain += f",fade=t=out:st={fade_start:.3f}:d={edge_fade:.3f}"
        chain += f"[v{clip_index}]"
        filters.append(chain)

    has_transitions = any(
        float(clip["transition_duration_seconds"]) > 0 for clip in clips[:-1]
    )
    if len(clips) == 1:
        filters.append("[v0]null[outv]")
    elif style["transition_style"] == "cut" or not has_transitions:
        concat_inputs = "".join(f"[v{index}]" for index in range(len(clips)))
        filters.append(f"{concat_inputs}concat=n={len(clips)}:v=1:a=0[outv]")
    else:
        previous_label = "v0"
        timeline_offset = 0.0
        for index in range(1, len(clips)):
            timeline_offset += float(clips[index - 1]["duration_seconds"])
            transition_seconds = float(
                clips[index - 1]["transition_duration_seconds"]
            )
            boundary_style = str(
                clips[index - 1].get(
                    "transition_out",
                    style["transition_style"],
                )
            )
            transition_filter = TRANSITION_FILTERS.get(
                boundary_style,
                TRANSITION_FILTERS[str(style["transition_style"])],
            )
            output_label = "outv" if index == len(clips) - 1 else f"x{index}"
            filters.append(
                f"[{previous_label}][v{index}]"
                f"xfade=transition={transition_filter}:"
                f"duration={transition_seconds:.3f}:"
                f"offset={timeline_offset:.3f}"
                f"[{output_label}]"
            )
            previous_label = output_label

    if voiceover_input_index is not None:
        filters.append(
            f"[{voiceover_input_index}:a]"
            "asetpts=PTS-STARTPTS,"
            f"aresample={AUDIO_SAMPLE_RATE},"
            "aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"apad=whole_dur={runtime_seconds:.3f},"
            f"atrim=duration={runtime_seconds:.3f}"
            "[outa]"
        )
    return ";".join(filters)


def build_ffmpeg_command(
    clips: list[dict[str, Any]],
    output_path: Path,
    executable: str | None = None,
    voiceover: dict[str, Any] | None = None,
    runtime_seconds: float | None = None,
    style: TimelineStyleUpdate | dict[str, Any] | None = None,
) -> list[str]:
    binary = executable or ffmpeg_executable() or FFMPEG_NAME
    runtime = runtime_seconds if runtime_seconds is not None else sum(
        float(clip["duration_seconds"]) for clip in clips
    )
    requested_video_format = (
        str(style.get("video_format", ""))
        if isinstance(style, dict)
        else str(getattr(style, "video_format", ""))
    )
    normalized_style = normalize_timeline_style(style)
    # Vertical typography and thin vector strokes show compression artifacts
    # sooner than landscape footage. Give Shorts two extra CRF quality steps
    # while leaving the established YouTube encode path unchanged.
    video_crf = "16" if requested_video_format == SHORTS_FORMAT else "18"
    command: list[str] = [binary, "-y", "-hide_banner"]

    for clip in clips:
        if clip["media_type"] == "photo":
            command.extend(
                [
                    "-loop",
                    "1",
                    "-framerate",
                    str(OUTPUT_FPS),
                    "-i",
                    clip["source_file"],
                ]
            )
        else:
            command.extend(["-stream_loop", "-1", "-i", clip["source_file"]])

    voiceover_input_index: int | None = None
    if voiceover is not None:
        voiceover_input_index = len(clips)
        command.extend(["-i", voiceover["source_file"]])

    command.extend(
        [
            "-filter_complex",
            build_filter_graph(
                clips,
                runtime,
                normalized_style,
                voiceover_input_index,
            ),
            "-map",
            "[outv]",
        ]
    )
    if voiceover_input_index is not None:
        command.extend(
            [
                "-map",
                "[outa]",
                "-c:a",
                "aac",
                "-b:a",
                AUDIO_BITRATE,
            ]
        )
    else:
        command.append("-an")

    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            video_crf,
            "-pix_fmt",
            "yuv420p",
            "-t",
            f"{runtime:.3f}",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    return command


def build_timeline_plan(
    project: Project,
    style: TimelineStyleUpdate | dict[str, Any] | None = None,
) -> dict[str, Any]:
    saved_style = (
        save_timeline_style(project.id, style)
        if style is not None
        else load_timeline_style(project.id)
    )
    profile = video_format_profile(project)
    normalized_style = {
        **saved_style,
        "video_format": profile.format_id,
        "output_width": profile.width,
        "output_height": profile.height,
    }
    clips: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for scene in sorted(project.scenes, key=lambda item: item.scene_number):
        clip, reason = scene_clip(scene, len(clips), normalized_style)
        if clip is None:
            missing.append(
                {
                    "scene_id": scene.id,
                    "scene_number": scene.scene_number,
                    "reason": reason or "Asset is not ready",
                }
            )
        else:
            clips.append(clip)

    apply_edit_decisions(clips, normalized_style)

    timeline_dir = timeline_directory(project.id)
    output_path = timeline_dir / "first-cut.mp4"
    caption_path = timeline_dir / "captions.srt"
    caption_cue_count = write_caption_track(project.scenes, caption_path)
    executable = ffmpeg_executable()
    source_runtime = max(
        (float(scene.end_seconds) for scene in project.scenes),
        default=0.0,
    )
    runtime = round(
        source_runtime
        + sum(float(clip.get("duration_extension_seconds", 0.0)) for clip in clips),
        3,
    )
    voiceover = load_voiceover(project.id)
    alignment_status, duration_delta, alignment_message = narration_alignment(
        voiceover,
        runtime,
    )
    command = (
        build_ffmpeg_command(
            clips,
            output_path,
            executable,
            voiceover=voiceover,
            runtime_seconds=runtime,
            style=normalized_style,
        )
        if clips and not missing
        else []
    )
    output_relative_path = relative_media_path(output_path)
    caption_relative_path = relative_media_path(caption_path)

    return {
        "schema_version": "0.5",
        "generated_at": utc_iso(),
        "project_id": project.id,
        "project_title": project.title,
        "ready": bool(clips) and not missing,
        "ffmpeg_available": executable is not None,
        "runtime_seconds": runtime,
        "clip_count": len(clips),
        "missing_scenes": missing,
        "settings": {
            "video_format": profile.format_id,
            "format_label": profile.label,
            "aspect_ratio": profile.aspect_ratio,
            "width": profile.width,
            "height": profile.height,
            "fps": OUTPUT_FPS,
            "video_codec": "libx264",
            "pixel_format": "yuv420p",
            "audio": "narration" if voiceover else "none",
            "audio_codec": "aac" if voiceover else None,
            "audio_bitrate": AUDIO_BITRATE if voiceover else None,
            "audio_sample_rate": AUDIO_SAMPLE_RATE if voiceover else None,
            **normalized_style,
        },
        "voiceover": voiceover,
        "captions": {
            "format": "SubRip",
            "cue_count": caption_cue_count,
            "relative_path": caption_relative_path,
            "public_url": public_media_url(caption_relative_path),
            "exists": caption_cue_count > 0 and caption_path.is_file(),
        },
        "alignment_status": alignment_status,
        "duration_delta_seconds": duration_delta,
        "alignment_message": alignment_message,
        "clips": clips,
        "command": command,
        "output_relative_path": output_relative_path,
        "output_url": public_media_url(output_relative_path),
        "output_exists": output_path.is_file(),
        "output_size_bytes": output_path.stat().st_size if output_path.is_file() else 0,
        "rendered_at": (
            datetime.fromtimestamp(output_path.stat().st_mtime, timezone.utc).isoformat()
            if output_path.is_file()
            else None
        ),
    }


def write_timeline_plan(
    project: Project,
    style: TimelineStyleUpdate | dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = build_timeline_plan(project, style)
    timeline_dir = timeline_directory(project.id)
    plan_path = timeline_dir / "render-plan.json"
    script_path = timeline_dir / "render.sh"

    plan_relative_path = relative_media_path(plan_path)
    script_relative_path = relative_media_path(script_path)
    plan["plan_relative_path"] = plan_relative_path
    plan["plan_url"] = public_media_url(plan_relative_path)
    plan["script_relative_path"] = script_relative_path
    plan["script_url"] = public_media_url(script_relative_path)

    atomic_text_write(
        plan_path,
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
    )
    script = "#!/bin/sh\nset -eu\n"
    script += (
        shlex.join(plan["command"]) + "\n"
        if plan["command"]
        else "echo 'Timeline is not ready to render.'\nexit 1\n"
    )
    atomic_text_write(script_path, script)
    script_path.chmod(0o755)
    return plan


def render_first_cut(
    project: Project,
    style: TimelineStyleUpdate | dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = write_timeline_plan(project, style)
    if not plan["ready"]:
        missing_numbers = ", ".join(
            str(item["scene_number"]) for item in plan["missing_scenes"]
        )
        raise HTTPException(
            status_code=409,
            detail=f"Timeline is missing ready assets for scene(s): {missing_numbers}",
        )

    executable = ffmpeg_executable()
    if executable is None:
        raise HTTPException(
            status_code=503,
            detail="FFmpeg was not found. Install it with: brew install ffmpeg",
        )

    output_path = resolve_media_path(plan["output_relative_path"])
    if output_path is None:
        raise HTTPException(status_code=500, detail="Timeline output path is invalid")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)

    command = build_ffmpeg_command(
        plan["clips"],
        output_path,
        executable,
        voiceover=plan["voiceover"],
        runtime_seconds=plan["runtime_seconds"],
        style=plan["settings"],
    )
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=RENDER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        output_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=504,
            detail="FFmpeg render exceeded the configured time limit",
        ) from exc
    except OSError as exc:
        output_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Could not start FFmpeg: {exc}") from exc

    if completed.returncode != 0 or not output_path.is_file():
        output_path.unlink(missing_ok=True)
        stderr_tail = (completed.stderr or "Unknown FFmpeg error")[-1800:]
        raise HTTPException(
            status_code=500,
            detail=f"FFmpeg could not render the first cut: {stderr_tail}",
        )

    rendered_plan = write_timeline_plan(project)
    rendered_plan["message"] = (
        "Narrated first-cut preview rendered with motion and transitions"
        if rendered_plan["voiceover"]
        else "Silent first-cut preview rendered with motion and transitions"
    )
    return rendered_plan
