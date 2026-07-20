from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import wave
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from ..models import Project, Scene
from .media_library import MEDIA_ROOT
from .render_invalidation import invalidate_render_artifacts
from .script_audio_pipeline import WORDS_PER_SECOND, _write_json, load_narration_plan


class NarrationSynthesisError(RuntimeError):
    pass


def _manifest_path(project_id: int) -> Path:
    return MEDIA_ROOT / f"project-{project_id:04d}" / "production" / "narration" / "manifest.json"


def _absolute(relative_path: str) -> Path:
    path = (MEDIA_ROOT / relative_path).resolve()
    if MEDIA_ROOT not in path.parents:
        raise NarrationSynthesisError("Narration output path escapes the media directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _wav_data_bytes(path: Path) -> int:
    """Return the real PCM payload size, including streamed WAV sentinel headers."""
    content = path.read_bytes()
    if len(content) < 12 or content[:4] not in {b"RIFF", b"RF64"} or content[8:12] != b"WAVE":
        raise NarrationSynthesisError(f"Invalid WAV container for {path.name}")

    offset = 12
    while offset + 8 <= len(content):
        chunk_id = content[offset : offset + 4]
        declared_size = struct.unpack_from("<I", content, offset + 4)[0]
        payload_start = offset + 8
        available = max(0, len(content) - payload_start)

        if chunk_id == b"data":
            if declared_size == 0xFFFFFFFF or declared_size > available:
                return available
            return declared_size

        if declared_size == 0xFFFFFFFF:
            break
        offset = payload_start + declared_size + (declared_size & 1)

    raise NarrationSynthesisError(f"WAV data chunk not found for {path.name}")


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        frames = audio.getnframes()
        rate = audio.getframerate()
        channels = audio.getnchannels()
        sample_width = audio.getsampwidth()

    if rate <= 0 or channels <= 0 or sample_width <= 0:
        raise NarrationSynthesisError(f"Invalid WAV format for {path.name}")

    try:
        payload_bytes = _wav_data_bytes(path)
        duration = payload_bytes / (rate * channels * sample_width)
    except NarrationSynthesisError:
        duration = frames / rate

    if duration <= 0:
        raise NarrationSynthesisError(f"Empty WAV audio for {path.name}")
    return round(duration, 3)


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_local_test_wav(path: Path, text: str, speaking_rate: float) -> None:
    """Create deterministic PCM audio for tests and offline pipeline exercises."""
    duration = max(0.6, len(text.split()) / (WORDS_PER_SECOND * speaking_rate))
    sample_rate = 16_000
    frame_count = max(1, round(duration * sample_rate))
    frequency = 180.0
    amplitude = 900
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        for index in range(frame_count):
            envelope = min(1.0, index / 320, (frame_count - index) / 320)
            sample = int(amplitude * max(0.0, envelope) * math.sin(2 * math.pi * frequency * index / sample_rate))
            audio.writeframesraw(struct.pack("<h", sample))


def _openai_tts(path: Path, text: str, voice_id: str, speaking_rate: float) -> None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise NarrationSynthesisError("OPENAI_API_KEY is not configured")

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    payload = json.dumps(
        {
            "model": model,
            "voice": voice_id,
            "input": text,
            "response_format": "wav",
            "speed": speaking_rate,
        }
    ).encode("utf-8")
    request = Request(
        f"{base_url}/audio/speech",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "audio/wav",
            "User-Agent": "AI-Documentary-OS/2.0",
        },
    )
    temporary = path.with_suffix(path.suffix + ".part")
    try:
        with urlopen(request, timeout=180) as response:
            temporary.write_bytes(response.read())
        temporary.replace(path)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:600]
        temporary.unlink(missing_ok=True)
        raise NarrationSynthesisError(f"OpenAI TTS returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        temporary.unlink(missing_ok=True)
        raise NarrationSynthesisError(f"OpenAI TTS request failed: {exc}") from exc


def _synthesize_segment(segment: dict[str, Any]) -> tuple[float, str]:
    provider = str(segment.get("provider") or "").strip().lower()
    path = _absolute(str(segment["relative_path"]))
    text = str(segment.get("text") or "").strip()
    if not text:
        raise NarrationSynthesisError("Narration segment text is empty")
    voice_id = str(segment.get("voice_id") or "alloy")
    speaking_rate = float(segment.get("speaking_rate") or 1.0)

    if provider == "openai":
        _openai_tts(path, text, voice_id, speaking_rate)
    elif provider == "local-test":
        _write_local_test_wav(path, text, speaking_rate)
    else:
        raise NarrationSynthesisError(f"Unsupported narration provider: {provider}")

    return _wav_duration(path), _checksum(path)


def _refresh_completed_segment(segment: dict[str, Any]) -> bool:
    """Re-measure an existing file without spending another provider request."""
    path = _absolute(str(segment["relative_path"]))
    if not path.is_file():
        raise NarrationSynthesisError(f"Completed narration file is missing: {path.name}")
    duration = _wav_duration(path)
    checksum = _checksum(path)
    changed = (
        float(segment.get("actual_duration_seconds") or 0) != duration
        or str(segment.get("checksum_sha256") or "") != checksum
    )
    segment["actual_duration_seconds"] = duration
    segment["checksum_sha256"] = checksum
    segment["error"] = None
    return changed


def _retime_project_scenes(project: Project, manifest: dict[str, Any], db: Session) -> None:
    by_number = {
        int(segment.get("scene_number", 0)): segment
        for segment in manifest.get("segments", [])
        if segment.get("status") == "complete" and segment.get("actual_duration_seconds")
    }
    cursor = 0.0
    changed = False
    for scene in sorted(project.scenes, key=lambda item: item.scene_number):
        segment = by_number.get(scene.scene_number)
        duration = (
            float(segment["actual_duration_seconds"])
            if segment is not None
            else float(scene.duration_seconds)
        )
        duration = max(0.25, round(duration, 3))
        new_start = round(cursor, 3)
        new_end = round(cursor + duration, 3)
        if (
            scene.start_seconds != new_start
            or scene.end_seconds != new_end
            or scene.duration_seconds != duration
        ):
            scene.start_seconds = new_start
            scene.end_seconds = new_end
            scene.duration_seconds = duration
            changed = True
        cursor = new_end
    if changed:
        project.status = "narrated"
        db.commit()
        invalidate_render_artifacts(project.id)


def repair_existing_narration_timings(project: Project, db: Session) -> bool:
    """Repair impossible persisted scene durations from completed local WAV files.

    This is intentionally provider-free: it only re-measures files already on disk.
    It allows a project poisoned by the streamed-WAV sentinel bug to load again.
    """
    manifest = load_narration_plan(project.id)
    if manifest is None:
        return False

    repaired = False
    for segment in manifest.get("segments", []):
        if segment.get("status") != "complete":
            continue
        try:
            repaired = _refresh_completed_segment(segment) or repaired
        except NarrationSynthesisError:
            continue

    if not repaired:
        return False

    manifest["actual_runtime_seconds"] = round(
        sum(float(item.get("actual_duration_seconds") or 0) for item in manifest.get("segments", [])),
        3,
    )
    _write_json(_manifest_path(project.id), manifest)
    _retime_project_scenes(project, manifest, db)
    return True


def synthesize_narration(
    project: Project,
    db: Session,
    *,
    scene_numbers: set[int] | None = None,
    force: bool = False,
    retime_scenes: bool = True,
) -> dict[str, Any]:
    manifest = load_narration_plan(project.id)
    if manifest is None:
        raise NarrationSynthesisError("Plan narration before synthesis")

    attempted = completed = failed = skipped = filtered_out = repaired = 0
    for segment in manifest.get("segments", []):
        scene_number = int(segment.get("scene_number", 0))
        if scene_numbers and scene_number not in scene_numbers:
            filtered_out += 1
            continue
        if segment.get("status") == "complete" and not force:
            try:
                if _refresh_completed_segment(segment):
                    repaired += 1
            except NarrationSynthesisError as exc:
                segment["status"] = "failed"
                segment["error"] = str(exc)
                failed += 1
                _write_json(_manifest_path(project.id), manifest)
                continue
            skipped += 1
            _write_json(_manifest_path(project.id), manifest)
            continue

        attempted += 1
        segment["status"] = "generating"
        segment["error"] = None
        _write_json(_manifest_path(project.id), manifest)
        try:
            duration, checksum = _synthesize_segment(segment)
            segment["actual_duration_seconds"] = duration
            segment["checksum_sha256"] = checksum
            segment["status"] = "complete"
            completed += 1
        except NarrationSynthesisError as exc:
            segment["status"] = "failed"
            segment["error"] = str(exc)
            failed += 1
        _write_json(_manifest_path(project.id), manifest)

    statuses = [str(item.get("status")) for item in manifest.get("segments", [])]
    manifest["status"] = (
        "complete"
        if statuses and all(status == "complete" for status in statuses)
        else "partial"
        if any(status == "complete" for status in statuses)
        else "failed"
        if any(status == "failed" for status in statuses)
        else "planned"
    )
    manifest["actual_runtime_seconds"] = round(
        sum(float(item.get("actual_duration_seconds") or 0) for item in manifest.get("segments", [])),
        3,
    )
    manifest["last_run"] = {
        "attempted": attempted,
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
        "filtered_out": filtered_out,
        "repaired": repaired,
    }
    _write_json(_manifest_path(project.id), manifest)

    if retime_scenes and (completed or repaired):
        _retime_project_scenes(project, manifest, db)
    return load_narration_plan(project.id) or manifest
