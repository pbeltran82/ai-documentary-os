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
from .media_library import MEDIA_ROOT, project_directory, public_media_url, resolve_media_path

OUTPUT_WIDTH = int(os.getenv("TIMELINE_OUTPUT_WIDTH", "1920"))
OUTPUT_HEIGHT = int(os.getenv("TIMELINE_OUTPUT_HEIGHT", "1080"))
OUTPUT_FPS = int(os.getenv("TIMELINE_OUTPUT_FPS", "30"))
RENDER_TIMEOUT_SECONDS = int(os.getenv("TIMELINE_RENDER_TIMEOUT_SECONDS", "3600"))
FFMPEG_NAME = os.getenv("FFMPEG_BIN", "ffmpeg")


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


def scene_clip(scene: Scene, input_index: int) -> tuple[dict[str, Any] | None, str | None]:
    asset = scene.selected_asset
    if asset is None or scene.asset_status != "ready" or not asset.local_path:
        return None, "No ready local asset"

    source = resolve_media_path(asset.local_path)
    if source is None or not source.is_file():
        return None, "Local asset file is missing"

    duration = round(float(scene.duration_seconds), 3)
    return (
        {
            "scene_id": scene.id,
            "scene_number": scene.scene_number,
            "input_index": input_index,
            "start_seconds": float(scene.start_seconds),
            "end_seconds": float(scene.end_seconds),
            "duration_seconds": duration,
            "narration": scene.narration,
            "visual_intent": scene.visual_intent,
            "provider": asset.provider,
            "provider_asset_id": asset.provider_asset_id,
            "media_type": asset.media_type,
            "local_path": asset.local_path,
            "local_url": asset.download_url,
            "preview_url": asset.preview_url,
            "source_url": asset.source_url,
            "creator": asset.creator,
            "license_name": asset.license_name,
            "attribution": asset.attribution,
            "source_file": str(source),
            "assembly_action": (
                f"Loop if needed, trim to {duration:g}s, fit 16:9"
                if asset.media_type == "video"
                else f"Hold for {duration:g}s, fit 16:9"
            ),
        },
        None,
    )


def build_filter_graph(clips: list[dict[str, Any]]) -> str:
    filters: list[str] = []
    for clip in clips:
        index = clip["input_index"]
        duration = clip["duration_seconds"]
        filters.append(
            f"[{index}:v]"
            f"trim=duration={duration:.3f},"
            "setpts=PTS-STARTPTS,"
            f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
            "setsar=1,"
            f"fps={OUTPUT_FPS},"
            "format=yuv420p"
            f"[v{index}]"
        )

    concat_inputs = "".join(f"[v{clip['input_index']}]" for clip in clips)
    filters.append(f"{concat_inputs}concat=n={len(clips)}:v=1:a=0[outv]")
    return ";".join(filters)


def build_ffmpeg_command(
    clips: list[dict[str, Any]],
    output_path: Path,
    executable: str | None = None,
) -> list[str]:
    binary = executable or ffmpeg_executable() or FFMPEG_NAME
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

    command.extend(
        [
            "-filter_complex",
            build_filter_graph(clips),
            "-map",
            "[outv]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    return command


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


def build_timeline_plan(project: Project) -> dict[str, Any]:
    clips: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for scene in sorted(project.scenes, key=lambda item: item.scene_number):
        clip, reason = scene_clip(scene, len(clips))
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

    timeline_dir = timeline_directory(project.id)
    output_path = timeline_dir / "first-cut.mp4"
    executable = ffmpeg_executable()
    command = build_ffmpeg_command(clips, output_path, executable) if clips and not missing else []
    runtime = max((float(scene.end_seconds) for scene in project.scenes), default=0.0)
    output_relative_path = relative_media_path(output_path)

    return {
        "schema_version": "0.1",
        "generated_at": utc_iso(),
        "project_id": project.id,
        "project_title": project.title,
        "ready": bool(clips) and not missing,
        "ffmpeg_available": executable is not None,
        "runtime_seconds": runtime,
        "clip_count": len(clips),
        "missing_scenes": missing,
        "settings": {
            "width": OUTPUT_WIDTH,
            "height": OUTPUT_HEIGHT,
            "fps": OUTPUT_FPS,
            "video_codec": "libx264",
            "pixel_format": "yuv420p",
            "audio": "none",
        },
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


def write_timeline_plan(project: Project) -> dict[str, Any]:
    plan = build_timeline_plan(project)
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
    script += (shlex.join(plan["command"]) + "\n") if plan["command"] else "echo 'Timeline is not ready to render.'\nexit 1\n"
    atomic_text_write(script_path, script)
    script_path.chmod(0o755)
    return plan


def render_first_cut(project: Project) -> dict[str, Any]:
    plan = write_timeline_plan(project)
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

    command = build_ffmpeg_command(plan["clips"], output_path, executable)
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
    rendered_plan["message"] = "Silent first-cut preview rendered successfully"
    return rendered_plan
