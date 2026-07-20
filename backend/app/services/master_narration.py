from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Project
from .media_library import MEDIA_ROOT, public_media_url
from .script_audio_pipeline import load_narration_plan
from .voiceover import atomic_json_write, ffprobe_executable, metadata_path, probe_duration, utc_iso, voiceover_directory

FFMPEG_NAME = "ffmpeg"


def _ffmpeg_executable() -> str | None:
    return shutil.which(FFMPEG_NAME)


def _source_path(relative_path: str) -> Path:
    path = (MEDIA_ROOT / relative_path).resolve()
    try:
        path.relative_to(MEDIA_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Narration segment path escapes the media directory") from exc
    if not path.is_file():
        raise HTTPException(status_code=409, detail=f"Narration segment is missing: {path.name}")
    return path


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _retime_scenes_from_manifest(project: Project, manifest: dict[str, Any], db: Session) -> bool:
    by_number = {
        int(segment.get("scene_number", 0)): segment
        for segment in manifest.get("segments", [])
        if segment.get("status") == "complete" and segment.get("actual_duration_seconds")
    }
    cursor = 0.0
    changed = False
    for scene in sorted(project.scenes, key=lambda item: item.scene_number):
        segment = by_number.get(scene.scene_number)
        if segment is None:
            raise HTTPException(
                status_code=409,
                detail=f"Completed narration is missing for Scene {scene.scene_number}",
            )
        duration = max(0.25, round(float(segment["actual_duration_seconds"]), 3))
        start = round(cursor, 3)
        end = round(cursor + duration, 3)
        if (
            float(scene.start_seconds) != start
            or float(scene.end_seconds) != end
            or float(scene.duration_seconds) != duration
        ):
            scene.start_seconds = start
            scene.end_seconds = end
            scene.duration_seconds = duration
            changed = True
        cursor = end
    if changed:
        db.commit()
    return changed


def build_master_narration(project: Project, db: Session) -> dict[str, Any]:
    project_id = project.id
    manifest = load_narration_plan(project_id)
    if manifest is None or manifest.get("status") != "complete":
        raise HTTPException(status_code=409, detail="Complete scene narration before building the master track")

    segments = sorted(manifest.get("segments", []), key=lambda item: int(item.get("scene_number", 0)))
    if not segments or any(item.get("status") != "complete" for item in segments):
        raise HTTPException(status_code=409, detail="Every narration segment must be complete")

    timings_repaired = _retime_scenes_from_manifest(project, manifest, db)

    # If visual beats already exist, rebuild them against the repaired narration
    # timeline so absolute beat times continue to cover the full master track.
    beat_target: float | None = None
    for scene in project.scenes:
        plan = scene.animation_plan or {}
        if plan.get("kind") == "narration_visual_beats":
            beat_target = float(plan.get("target_beat_seconds") or 5.0)
            break
    if beat_target is not None:
        from .visual_beat_planning import plan_visual_beats

        plan_visual_beats(project, db, target_seconds=beat_target)

    ffmpeg = _ffmpeg_executable()
    probe = ffprobe_executable()
    if ffmpeg is None or probe is None:
        raise HTTPException(status_code=503, detail="FFmpeg and FFprobe are required. Install them with: brew install ffmpeg")

    source_paths = [_source_path(str(item.get("relative_path", ""))) for item in segments]
    directory = voiceover_directory(project_id)
    final_path = directory / "narration.wav"

    with NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".concat-", suffix=".txt", dir=directory, delete=False) as concat_file:
        concat_path = Path(concat_file.name)
        for source in source_paths:
            escaped = str(source).replace("'", "'\\''")
            concat_file.write(f"file '{escaped}'\n")

    temporary_path = directory / ".narration-master.part.wav"
    try:
        completed = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-c:a",
                "pcm_s16le",
                str(temporary_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or "FFmpeg could not assemble narration")[-1600:]
            raise HTTPException(status_code=422, detail=f"Master narration assembly failed: {detail}")

        duration = probe_duration(temporary_path, probe)
        temporary_path.replace(final_path)
        relative_path = final_path.relative_to(MEDIA_ROOT).as_posix()
        metadata = {
            "original_filename": "generated-master-narration.wav",
            "relative_path": relative_path,
            "public_url": public_media_url(relative_path),
            "content_type": "audio/wav",
            "file_size_bytes": final_path.stat().st_size,
            "checksum_sha256": _checksum(final_path),
            "duration_seconds": duration,
            "uploaded_at": utc_iso(),
            "source_file": str(final_path.resolve()),
            "source": "generated_scene_narration",
            "segment_count": len(segments),
            "voice_id": manifest.get("voice_id"),
            "speaking_rate": manifest.get("speaking_rate"),
            "scene_timings_repaired": timings_repaired,
            "normalization": {"integrated_lufs": -16.0, "true_peak_db": -1.5, "lra": 11},
        }
        atomic_json_write(metadata_path(project_id), metadata)
        return metadata
    finally:
        concat_path.unlink(missing_ok=True)
        temporary_path.unlink(missing_ok=True)
