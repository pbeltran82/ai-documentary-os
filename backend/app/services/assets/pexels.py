from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

from ...schemas import AssetCandidate
from .common import ProviderSpec, json_request, rate_limit_remaining


def choose_video(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    mp4_files = [item for item in files if item.get("file_type") == "video/mp4" and item.get("link")]
    if not mp4_files:
        return None

    def score(item: dict[str, Any]) -> tuple[int, int, int]:
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        return (
            1 if height > width else 0,
            0 if item.get("quality") == "hd" else 1,
            abs(width - 1920) + abs(height - 1080),
        )

    return min(mp4_files, key=score)


def normalize_video(item: dict[str, Any]) -> AssetCandidate | None:
    selected = choose_video(item.get("video_files") or [])
    if selected is None:
        return None
    user = item.get("user") or {}
    creator = user.get("name") or ""
    return AssetCandidate(
        provider="pexels",
        provider_asset_id=str(item["id"]),
        media_type="video",
        source_url=item.get("url") or "",
        preview_url=item.get("image") or "",
        download_url=selected.get("link") or "",
        creator=creator,
        creator_url=user.get("url") or "",
        width=int(selected.get("width") or 0),
        height=int(selected.get("height") or 0),
        duration_seconds=float(item.get("duration") or 0),
        license_name="Pexels License",
        license_url="https://www.pexels.com/license/",
        attribution=f"{creator} on Pexels" if creator else "Media from Pexels",
    )


def normalize_photo(item: dict[str, Any]) -> AssetCandidate:
    sources = item.get("src") or {}
    creator = item.get("photographer") or ""
    return AssetCandidate(
        provider="pexels",
        provider_asset_id=str(item["id"]),
        media_type="photo",
        source_url=item.get("url") or "",
        preview_url=sources.get("large") or sources.get("medium") or "",
        download_url=sources.get("original") or sources.get("large2x") or "",
        creator=creator,
        creator_url=item.get("photographer_url") or "",
        width=int(item.get("width") or 0),
        height=int(item.get("height") or 0),
        duration_seconds=None,
        license_name="Pexels License",
        license_url="https://www.pexels.com/license/",
        attribution=f"{creator} on Pexels" if creator else "Media from Pexels",
    )


def search(query: str, media_type: str, per_page: int) -> tuple[list[AssetCandidate], int | None]:
    path = "/v1/videos/search" if media_type == "video" else "/v1/search"
    params: dict[str, str | int] = {
        "query": query,
        "orientation": "landscape",
        "per_page": per_page,
    }
    if media_type == "video":
        params["size"] = "medium"
    payload, headers = json_request(
        f"https://api.pexels.com{path}?{urlencode(params)}",
        provider_label="Pexels",
        headers={"Authorization": os.getenv("PEXELS_API_KEY", "").strip()},
    )
    if media_type == "video":
        candidates = [
            candidate
            for candidate in (normalize_video(item) for item in payload.get("videos", []))
            if candidate is not None
        ]
    else:
        candidates = [normalize_photo(item) for item in payload.get("photos", [])]
    return candidates, rate_limit_remaining(headers)


SPEC = ProviderSpec(
    name="pexels",
    label="Pexels",
    media_types=("video", "photo"),
    env_key="PEXELS_API_KEY",
    setup_hint="Optional: add PEXELS_API_KEY=your_key to backend/.env, then restart the app.",
    source_url="https://www.pexels.com",
    search=search,
)
