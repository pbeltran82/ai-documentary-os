from __future__ import annotations

"""Project-scoped background music with narration-safe ducking."""

import hashlib
import json
import mimetypes
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, AsyncIterator

from fastapi import HTTPException

from . import timeline_builder as base
from .media_library import MEDIA_ROOT, project_directory, public_media_url
from .video_format import SHORTS_FORMAT
from .voiceover import choose_extension, ffprobe_executable, probe_duration, utc_iso

MAX_BACKGROUND_MUSIC_BYTES = int(os.getenv("MAX_BACKGROUND_MUSIC_UPLOAD_BYTES", str(250 * 1024 * 1024)))
DEFAULT_SETTINGS = {
    "enabled": False,
    "gain_db": -22.0,
    "ducking_enabled": True,
    "ducking_threshold": 0.035,
    "ducking_ratio": 8.0,
    "ducking_attack_ms": 20,
    "ducking_release_ms": 500,
    "fade_seconds": 1.5,
}

_original_build_timeline_plan = base.build_timeline_plan
_original_build_ffmpeg_command = base.build_ffmpeg_command


def background_music_directory(project_id: int) -> Path:
    directory = project_directory(project_id) / "audio"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def background_music_metadata_path(project_id: int) -> Path:
    return background_music_directory(project_id) / "background-music.json"


def background_music_settings_path(project_id: int) -> Path:
    return background_music_directory(project_id) / "background-music-settings.json"


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", prefix=f".{path.name}-", suffix=".tmp", dir=path.parent, delete=False) as temporary:
        json.dump(payload, temporary, indent=2, ensure_ascii=False)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def default_music_settings(video_format: str = "youtube") -> dict[str, Any]:
    values = dict(DEFAULT_SETTINGS)
    if video_format == SHORTS_FORMAT:
        values["gain_db"] = -24.0
        values["fade_seconds"] = 0.6
    return values


def normalize_music_settings(values: dict[str, Any] | None, video_format: str = "youtube") -> dict[str, Any]:
    normalized = default_music_settings(video_format)
    if values:
        normalized.update({key: values[key] for key in normalized if key in values and values[key] is not None})
    normalized["enabled"] = bool(normalized["enabled"])
    normalized["gain_db"] = round(max(-36.0, min(-8.0, float(normalized["gain_db"]))), 1)
    normalized["ducking_enabled"] = bool(normalized["ducking_enabled"])
    normalized["ducking_threshold"] = round(max(0.005, min(0.25, float(normalized["ducking_threshold"]))), 3)
    normalized["ducking_ratio"] = round(max(1.0, min(20.0, float(normalized["ducking_ratio"]))), 1)
    normalized["ducking_attack_ms"] = int(max(5, min(500, int(normalized["ducking_attack_ms"]))))
    normalized["ducking_release_ms"] = int(max(50, min(3000, int(normalized["ducking_release_ms"]))))
    normalized["fade_seconds"] = round(max(0.0, min(5.0, float(normalized["fade_seconds"]))), 2)
    return normalized


def load_music_settings(project_id: int, video_format: str = "youtube") -> dict[str, Any]:
    path = background_music_settings_path(project_id)
    if not path.is_file():
        return normalize_music_settings(None, video_format)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return normalize_music_settings(None, video_format)
    return normalize_music_settings(payload if isinstance(payload, dict) else None, video_format)


def save_music_settings(project_id: int, values: dict[str, Any], video_format: str = "youtube") -> dict[str, Any]:
    normalized = normalize_music_settings(values, video_format)
    _atomic_json_write(background_music_settings_path(project_id), normalized)
    return normalized


async def save_background_music(project_id: int, filename: str, content_type: str, stream: AsyncIterator[bytes]) -> dict[str, Any]:
    probe = ffprobe_executable()
    if probe is None:
        raise HTTPException(status_code=503, detail="FFprobe was not found. Install it with: brew install ffmpeg")
    extension = choose_extension(filename, content_type)
    directory = background_music_directory(project_id)
    final_path = directory / f"background-music{extension}"
    temporary_path: Path | None = None
    digest = hashlib.sha256()
    total = 0
    try:
        with NamedTemporaryFile(mode="wb", prefix=".background-music-", suffix=".part", dir=directory, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            async for chunk in stream:
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_BACKGROUND_MUSIC_BYTES:
                    raise HTTPException(status_code=413, detail="Background music exceeded the local upload limit")
                digest.update(chunk)
                temporary.write(chunk)
        if total == 0:
            raise HTTPException(status_code=422, detail="Background music file was empty")
        duration = probe_duration(temporary_path, probe)
        temporary_path.replace(final_path)
        temporary_path = None
        for stale in directory.glob("background-music.*"):
            if stale not in {final_path, background_music_metadata_path(project_id)} and stale.is_file():
                stale.unlink(missing_ok=True)
        relative_path = final_path.relative_to(MEDIA_ROOT).as_posix()
        normalized_type = content_type.split(";", 1)[0].strip().lower()
        metadata = {
            "original_filename": Path(filename).name or final_path.name,
            "relative_path": relative_path,
            "public_url": public_media_url(relative_path),
            "content_type": normalized_type or mimetypes.guess_type(final_path.name)[0] or "audio/mpeg",
            "file_size_bytes": total,
            "checksum_sha256": digest.hexdigest(),
            "duration_seconds": duration,
            "uploaded_at": utc_iso(),
            "source_file": str(final_path.resolve()),
            "rights_notice": "User-supplied audio. The project creator is responsible for music licensing and publishing rights.",
        }
        _atomic_json_write(background_music_metadata_path(project_id), metadata)
        return metadata
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def load_background_music(project_id: int) -> dict[str, Any] | None:
    path = background_music_metadata_path(project_id)
    if not path.is_file():
        return None
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    relative_path = str(metadata.get("relative_path", ""))
    audio_path = (MEDIA_ROOT / relative_path).resolve()
    try:
        audio_path.relative_to(MEDIA_ROOT)
    except ValueError:
        return None
    if not audio_path.is_file():
        return None
    metadata["source_file"] = str(audio_path)
    metadata["public_url"] = public_media_url(relative_path)
    return metadata


def background_music_state(project_id: int, video_format: str = "youtube") -> dict[str, Any]:
    track = load_background_music(project_id)
    settings = load_music_settings(project_id, video_format)
    return {"track": track, "settings": settings, "ready": bool(track), "active": bool(track and settings["enabled"])}


def remove_background_music(project_id: int) -> None:
    directory = background_music_directory(project_id)
    for candidate in directory.glob("background-music.*"):
        if candidate.is_file():
            candidate.unlink(missing_ok=True)
    current = load_music_settings(project_id)
    current["enabled"] = False
    save_music_settings(project_id, current)


def _music_filter(index: int, runtime: float, settings: dict[str, Any]) -> str:
    fade = min(float(settings["fade_seconds"]), max(0.0, runtime / 4))
    fade_out = max(0.0, runtime - fade)
    chain = (
        f"[{index}:a]asetpts=PTS-STARTPTS,aresample={base.AUDIO_SAMPLE_RATE},"
        "aformat=sample_fmts=fltp:channel_layouts=stereo,"
        f"volume={float(settings['gain_db']):g}dB,atrim=duration={runtime:.3f}"
    )
    if fade > 0:
        chain += f",afade=t=in:st=0:d={fade:.3f},afade=t=out:st={fade_out:.3f}:d={fade:.3f}"
    return chain


def _inject_music_graph(graph: str, music_index: int, runtime: float, settings: dict[str, Any], has_narration: bool) -> str:
    bed = _music_filter(music_index, runtime, settings)
    if not has_narration:
        return f"{graph};{bed}[outa]" if graph else f"{bed}[outa]"
    parts = graph.rsplit("[outa]", 1)
    if len(parts) != 2:
        return graph
    graph = "[narration]".join(parts)
    if settings["ducking_enabled"]:
        mix = (
            f";{bed}[musicbed];[musicbed][narration]sidechaincompress="
            f"threshold={float(settings['ducking_threshold']):g}:ratio={float(settings['ducking_ratio']):g}:"
            f"attack={int(settings['ducking_attack_ms'])}:release={int(settings['ducking_release_ms'])}[duckedmusic];"
            "[narration][duckedmusic]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.95[outa]"
        )
    else:
        mix = f";{bed}[musicbed];[narration][musicbed]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.95[outa]"
    return graph + mix


def build_ffmpeg_command(clips, output_path, executable=None, voiceover=None, runtime_seconds=None, style=None):
    command = _original_build_ffmpeg_command(clips, output_path, executable, voiceover=voiceover, runtime_seconds=runtime_seconds, style=style)
    values = style if isinstance(style, dict) else {}
    state = values.get("background_music") if isinstance(values, dict) else None
    if not isinstance(state, dict) or not state.get("active"):
        return command
    track, settings = state.get("track"), state.get("settings")
    if not isinstance(track, dict) or not isinstance(settings, dict) or not track.get("source_file"):
        return command
    runtime = float(runtime_seconds if runtime_seconds is not None else sum(float(clip["duration_seconds"]) for clip in clips))
    music_index = len(clips) + (1 if voiceover is not None else 0)
    insert_at = command.index("-filter_complex")
    command[insert_at:insert_at] = ["-stream_loop", "-1", "-i", str(track["source_file"])]
    graph_index = command.index("-filter_complex") + 1
    command[graph_index] = _inject_music_graph(str(command[graph_index]), music_index, runtime, settings, voiceover is not None)
    if "-an" in command:
        index = command.index("-an")
        command[index:index + 1] = ["-map", "[outa]", "-c:a", "aac", "-b:a", base.AUDIO_BITRATE]
    return command


def build_timeline_plan(project, style=None) -> dict[str, Any]:
    plan = _original_build_timeline_plan(project, style)
    format_id = str(plan.get("settings", {}).get("video_format") or "youtube")
    state = background_music_state(project.id, format_id)
    plan["background_music"] = state
    plan["settings"]["background_music"] = state
    plan["settings"]["audio"] = "narration+music" if plan.get("voiceover") and state["active"] else "music" if state["active"] else "narration" if plan.get("voiceover") else "none"
    if plan.get("clips") and not plan.get("missing_scenes"):
        plan["command"] = build_ffmpeg_command(
            plan["clips"], base.timeline_directory(project.id) / "first-cut.mp4", base.ffmpeg_executable(),
            voiceover=plan.get("voiceover"), runtime_seconds=float(plan.get("runtime_seconds") or 0), style=plan["settings"]
        )
    return plan


base.build_ffmpeg_command = build_ffmpeg_command
base.build_timeline_plan = build_timeline_plan
