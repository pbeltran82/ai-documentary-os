from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from fastapi import HTTPException

from ..models import Asset, Project, Scene
from ..schemas import AssetSelect

BACKEND_DIR = Path(__file__).resolve().parents[2]
MEDIA_ROOT = Path(
    os.getenv("MEDIA_ROOT", str(BACKEND_DIR / "data" / "projects"))
).expanduser().resolve()
PUBLIC_BACKEND_URL = os.getenv(
    "PUBLIC_BACKEND_URL", "http://localhost:8000"
).rstrip("/")
MAX_DOWNLOAD_BYTES = int(os.getenv("MAX_ASSET_DOWNLOAD_BYTES", str(500 * 1024 * 1024)))

MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

SAFE_COMPONENT_RE = re.compile(r"[^a-zA-Z0-9._-]+")
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}


@dataclass(frozen=True)
class DownloadedFile:
    relative_path: str
    public_url: str
    content_type: str
    size_bytes: int
    checksum_sha256: str


@dataclass(frozen=True)
class LocalAssetFiles:
    media: DownloadedFile
    preview: DownloadedFile


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_component(value: str, fallback: str = "asset") -> str:
    cleaned = SAFE_COMPONENT_RE.sub("-", value.strip()).strip("-._")
    return cleaned[:80] or fallback


def project_relative_directory(project_id: int) -> Path:
    return Path(f"project-{project_id:04d}")


def project_directory(project_id: int) -> Path:
    directory = MEDIA_ROOT / project_relative_directory(project_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def public_media_url(relative_path: str) -> str:
    return f"{PUBLIC_BACKEND_URL}/media/{quote(relative_path, safe='/')}"


def extension_for(url: str, content_type: str, media_type: str) -> str:
    normalized_type = content_type.split(";", 1)[0].strip().lower()
    if normalized_type in CONTENT_TYPE_EXTENSIONS:
        return CONTENT_TYPE_EXTENSIONS[normalized_type]

    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".webm"}:
        return ".jpg" if suffix == ".jpeg" else suffix

    guessed = mimetypes.guess_extension(normalized_type) if normalized_type else None
    if guessed:
        return ".jpg" if guessed in {".jpeg", ".jpe"} else guessed
    return ".mp4" if media_type == "video" else ".jpg"


def download_remote_file(
    url: str,
    destination_stem: Path,
    media_type: str,
) -> DownloadedFile:
    if not url.startswith(("https://", "http://")):
        raise HTTPException(status_code=422, detail="Asset download URL is not valid")

    request = Request(
        url,
        headers={
            "Accept": "*/*",
            "User-Agent": "AI-Documentary-OS/0.5",
        },
    )

    try:
        with urlopen(request, timeout=120) as response:
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="Selected asset is larger than the local download limit",
                )

            extension = extension_for(response.geturl(), content_type, media_type)
            destination = destination_stem.with_suffix(extension)
            destination.parent.mkdir(parents=True, exist_ok=True)

            digest = hashlib.sha256()
            total = 0
            with NamedTemporaryFile(
                mode="wb",
                prefix=f".{destination.stem}-",
                suffix=".part",
                dir=destination.parent,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        temporary_path.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=413,
                            detail="Selected asset exceeded the local download limit",
                        )
                    digest.update(chunk)
                    temporary.write(chunk)

            temporary_path.replace(destination)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not download the selected media: {exc}",
        ) from exc

    relative_path = destination.relative_to(MEDIA_ROOT).as_posix()
    return DownloadedFile(
        relative_path=relative_path,
        public_url=public_media_url(relative_path),
        content_type=content_type.split(";", 1)[0].strip().lower(),
        size_bytes=total,
        checksum_sha256=digest.hexdigest(),
    )


def download_candidate(scene: Scene, payload: AssetSelect) -> LocalAssetFiles:
    asset_directory = project_directory(scene.project_id) / "assets"
    identity = safe_component(payload.provider_asset_id, "media")
    stem = asset_directory / (
        f"scene-{scene.scene_number:03d}-{safe_component(payload.provider)}-{identity}"
    )

    media = download_remote_file(payload.download_url, stem, payload.media_type)
    if payload.media_type == "photo":
        preview = media
    else:
        preview = download_remote_file(
            payload.preview_url,
            Path(f"{stem}-poster"),
            "photo",
        )
    return LocalAssetFiles(media=media, preview=preview)


def resolve_media_path(relative_path: str) -> Path | None:
    if not relative_path:
        return None
    candidate = (MEDIA_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(MEDIA_ROOT)
    except ValueError:
        return None
    return candidate


def remove_asset_files(asset: Asset | None) -> None:
    if asset is None:
        return
    paths = {asset.local_path, asset.local_preview_path}
    for relative_path in paths:
        path = resolve_media_path(relative_path)
        if path is not None and path.is_file():
            path.unlink(missing_ok=True)


def timeline_manifest(project: Project) -> dict[str, Any]:
    scenes: list[dict[str, Any]] = []
    for scene in sorted(project.scenes, key=lambda item: item.scene_number):
        asset = scene.selected_asset
        scenes.append(
            {
                "scene_id": scene.id,
                "scene_number": scene.scene_number,
                "start_seconds": scene.start_seconds,
                "end_seconds": scene.end_seconds,
                "duration_seconds": scene.duration_seconds,
                "narration": scene.narration,
                "visual_intent": scene.visual_intent,
                "asset_status": scene.asset_status,
                "asset": None
                if asset is None
                else {
                    "provider": asset.provider,
                    "provider_asset_id": asset.provider_asset_id,
                    "media_type": asset.media_type,
                    "local_path": asset.local_path,
                    "local_preview_path": asset.local_preview_path,
                    "content_type": asset.content_type,
                    "file_size_bytes": asset.file_size_bytes,
                    "checksum_sha256": asset.checksum_sha256,
                    "source_url": asset.source_url,
                    "remote_download_url": asset.remote_download_url,
                    "creator": asset.creator,
                    "creator_url": asset.creator_url,
                    "license_name": asset.license_name,
                    "license_url": asset.license_url,
                    "attribution": asset.attribution,
                },
            }
        )

    ready_scenes = sum(
        1
        for scene in scenes
        if scene["asset"] is not None and scene["asset_status"] == "ready"
    )
    return {
        "schema_version": "0.1",
        "generated_at": utc_iso(),
        "project": {
            "id": project.id,
            "title": project.title,
            "topic": project.topic,
            "status": project.status,
            "target_minutes": project.target_minutes,
            "visual_style": project.visual_style,
        },
        "summary": {
            "scene_count": len(scenes),
            "ready_scene_count": ready_scenes,
            "missing_scene_count": len(scenes) - ready_scenes,
            "runtime_seconds": max(
                (float(scene["end_seconds"]) for scene in scenes),
                default=0.0,
            ),
        },
        "scenes": scenes,
    }


def write_timeline_manifest(project: Project) -> tuple[str, str, dict[str, Any]]:
    manifest = timeline_manifest(project)
    manifest_directory = project_directory(project.id) / "timeline"
    manifest_directory.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_directory / "manifest.json"
    temporary_path = manifest_directory / ".manifest.json.tmp"
    temporary_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(manifest_path)
    relative_path = manifest_path.relative_to(MEDIA_ROOT).as_posix()
    return relative_path, public_media_url(relative_path), manifest
