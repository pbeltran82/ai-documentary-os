from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, AsyncIterator

from fastapi import HTTPException

from .media_library import MEDIA_ROOT, project_directory, public_media_url

MAX_VOICEOVER_BYTES = int(
    os.getenv("MAX_NARRATION_UPLOAD_BYTES", str(250 * 1024 * 1024))
)
FFPROBE_NAME = os.getenv("FFPROBE_BIN", "ffprobe")
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".webm"}
CONTENT_TYPE_EXTENSIONS = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/aac": ".aac",
    "audio/flac": ".flac",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
}


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def voiceover_directory(project_id: int) -> Path:
    directory = project_directory(project_id) / "audio"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def metadata_path(project_id: int) -> Path:
    return voiceover_directory(project_id) / "narration.json"


def ffprobe_executable() -> str | None:
    configured = Path(FFPROBE_NAME).expanduser()
    if configured.is_absolute():
        return str(configured) if configured.is_file() else None
    return shutil.which(FFPROBE_NAME)


def choose_extension(filename: str, content_type: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in ALLOWED_EXTENSIONS:
        return suffix

    normalized_type = content_type.split(";", 1)[0].strip().lower()
    if normalized_type in CONTENT_TYPE_EXTENSIONS:
        return CONTENT_TYPE_EXTENSIONS[normalized_type]

    guessed = mimetypes.guess_extension(normalized_type) if normalized_type else None
    if guessed in ALLOWED_EXTENSIONS:
        return guessed

    raise HTTPException(
        status_code=415,
        detail="Narration must be MP3, WAV, M4A, AAC, FLAC, OGG, or WebM audio",
    )


def probe_duration(path: Path, executable: str | None = None) -> float:
    binary = executable or ffprobe_executable()
    if binary is None:
        raise HTTPException(
            status_code=503,
            detail="FFprobe was not found. Install it with: brew install ffmpeg",
        )

    try:
        completed = subprocess.run(
            [
                binary,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not inspect narration audio: {exc}",
        ) from exc

    if completed.returncode != 0:
        error = (completed.stderr or "FFprobe could not read the audio file")[-1200:]
        raise HTTPException(status_code=422, detail=f"Invalid narration audio: {error}")

    try:
        duration = float(completed.stdout.strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="Narration duration could not be determined",
        ) from exc

    if duration <= 0:
        raise HTTPException(status_code=422, detail="Narration audio has no usable duration")
    return round(duration, 3)


def atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f".{path.name}-",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as temporary:
        json.dump(payload, temporary, indent=2, ensure_ascii=False)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


async def save_voiceover(
    project_id: int,
    filename: str,
    content_type: str,
    stream: AsyncIterator[bytes],
) -> dict[str, Any]:
    probe = ffprobe_executable()
    if probe is None:
        raise HTTPException(
            status_code=503,
            detail="FFprobe was not found. Install it with: brew install ffmpeg",
        )

    extension = choose_extension(filename, content_type)
    directory = voiceover_directory(project_id)
    final_path = directory / f"narration{extension}"
    temporary_path: Path | None = None
    digest = hashlib.sha256()
    total = 0

    try:
        with NamedTemporaryFile(
            mode="wb",
            prefix=".narration-",
            suffix=".part",
            dir=directory,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            async for chunk in stream:
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_VOICEOVER_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Narration audio exceeded the local upload limit",
                    )
                digest.update(chunk)
                temporary.write(chunk)

        if total == 0:
            raise HTTPException(status_code=422, detail="Narration audio file was empty")

        duration = probe_duration(temporary_path, probe)
        temporary_path.replace(final_path)
        temporary_path = None

        for stale in directory.glob("narration.*"):
            if stale not in {final_path, metadata_path(project_id)} and stale.is_file():
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
        }
        atomic_json_write(metadata_path(project_id), metadata)
        return metadata
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def load_voiceover(project_id: int) -> dict[str, Any] | None:
    path = metadata_path(project_id)
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


def remove_voiceover(project_id: int) -> None:
    directory = voiceover_directory(project_id)
    for candidate in directory.glob("narration.*"):
        if candidate.is_file():
            candidate.unlink(missing_ok=True)
