from __future__ import annotations

"""Project-scoped background music upload and metadata management."""

import hashlib
import json
import mimetypes
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, AsyncIterator

from fastapi import HTTPException

from .media_library import MEDIA_ROOT, project_directory, public_media_url
from .voiceover import choose_extension, ffprobe_executable, probe_duration, utc_iso

MAX_BACKGROUND_MUSIC_BYTES = int(
    os.getenv("MAX_BACKGROUND_MUSIC_UPLOAD_BYTES", str(250 * 1024 * 1024))
)


def background_music_directory(project_id: int) -> Path:
    directory = project_directory(project_id) / "audio"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def background_music_metadata_path(project_id: int) -> Path:
    return background_music_directory(project_id) / "background-music.json"


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
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


async def save_background_music(
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
    directory = background_music_directory(project_id)
    final_path = directory / f"background-music{extension}"
    temporary_path: Path | None = None
    digest = hashlib.sha256()
    total = 0

    try:
        with NamedTemporaryFile(
            mode="wb",
            prefix=".background-music-",
            suffix=".part",
            dir=directory,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            async for chunk in stream:
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_BACKGROUND_MUSIC_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Background music exceeded the local upload limit",
                    )
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


def remove_background_music(project_id: int) -> None:
    directory = background_music_directory(project_id)
    for candidate in directory.glob("background-music.*"):
        if candidate.is_file():
            candidate.unlink(missing_ok=True)
