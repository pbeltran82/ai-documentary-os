from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import quote, urlencode

from ...schemas import AssetCandidate
from .common import ProviderSpec, json_request, rate_limit_remaining

WORD_RE = re.compile(r"[a-z0-9]+")
GENERIC_MOTION_WORDS = {
    "animation",
    "footage",
    "lapse",
    "motion",
    "photo",
    "time",
    "timelapse",
    "video",
}


def word_set(value: str) -> set[str]:
    return set(WORD_RE.findall(value.lower()))


def rank_hits(hits: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    query_words = word_set(query)
    anchor_words = query_words - GENERIC_MOTION_WORDS

    def relevance(item: dict[str, Any]) -> tuple[int, int, int, int]:
        tag_words = word_set(str(item.get("tags") or ""))
        anchor_overlap = len(anchor_words & tag_words)
        total_overlap = len(query_words & tag_words)
        likes = int(item.get("likes") or 0)
        downloads = int(item.get("downloads") or 0)
        return anchor_overlap, total_overlap, likes, downloads

    anchored = [item for item in hits if relevance(item)[0] > 0]
    ranked_pool = anchored if len(anchored) >= 3 else hits
    return sorted(ranked_pool, key=relevance, reverse=True)


def normalize_photo(item: dict[str, Any]) -> AssetCandidate:
    creator = str(item.get("user") or "")
    creator_id = item.get("user_id")
    creator_url = (
        f"https://pixabay.com/users/{quote(creator, safe='')}-{creator_id}/"
        if creator and creator_id
        else "https://pixabay.com"
    )
    return AssetCandidate(
        provider="pixabay",
        provider_asset_id=str(item["id"]),
        media_type="photo",
        source_url=item.get("pageURL") or "",
        preview_url=item.get("largeImageURL") or item.get("webformatURL") or item.get("previewURL") or "",
        download_url=item.get("largeImageURL") or item.get("webformatURL") or "",
        creator=creator,
        creator_url=creator_url,
        width=int(item.get("imageWidth") or item.get("webformatWidth") or 0),
        height=int(item.get("imageHeight") or item.get("webformatHeight") or 0),
        duration_seconds=None,
        license_name="Pixabay Content License",
        license_url="https://pixabay.com/service/license-summary/",
        attribution=f"{creator} on Pixabay" if creator else "Media from Pixabay",
    )


def choose_video(videos: dict[str, Any]) -> dict[str, Any] | None:
    candidates = [value for value in videos.values() if value and value.get("url")]
    if not candidates:
        return None

    def score(item: dict[str, Any]) -> tuple[int, int]:
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        return (1 if height > width else 0, abs(width - 1920) + abs(height - 1080))

    return min(candidates, key=score)


def normalize_video(item: dict[str, Any]) -> AssetCandidate | None:
    selected = choose_video(item.get("videos") or {})
    if selected is None:
        return None
    creator = str(item.get("user") or "")
    creator_id = item.get("user_id")
    creator_url = (
        f"https://pixabay.com/users/{quote(creator, safe='')}-{creator_id}/"
        if creator and creator_id
        else "https://pixabay.com"
    )
    return AssetCandidate(
        provider="pixabay",
        provider_asset_id=str(item["id"]),
        media_type="video",
        source_url=item.get("pageURL") or "",
        preview_url=selected.get("thumbnail") or "",
        download_url=selected.get("url") or "",
        creator=creator,
        creator_url=creator_url,
        width=int(selected.get("width") or 0),
        height=int(selected.get("height") or 0),
        duration_seconds=float(item.get("duration") or 0),
        license_name="Pixabay Content License",
        license_url="https://pixabay.com/service/license-summary/",
        attribution=f"{creator} on Pixabay" if creator else "Media from Pixabay",
    )


def search(query: str, media_type: str, per_page: int) -> tuple[list[AssetCandidate], int | None]:
    endpoint = "https://pixabay.com/api/videos/" if media_type == "video" else "https://pixabay.com/api/"
    params: dict[str, str | int] = {
        "key": os.getenv("PIXABAY_API_KEY", "").strip(),
        "q": query[:100],
        "per_page": max(3, per_page),
        "safesearch": "true",
        "order": "popular",
    }
    if media_type == "photo":
        params.update({"image_type": "photo", "orientation": "horizontal"})
    payload, headers = json_request(
        f"{endpoint}?{urlencode(params)}", provider_label="Pixabay"
    )
    hits = rank_hits(list(payload.get("hits", [])), query)
    if media_type == "video":
        candidates = [
            candidate
            for candidate in (normalize_video(item) for item in hits)
            if candidate is not None
        ]
    else:
        candidates = [normalize_photo(item) for item in hits]
    return candidates, rate_limit_remaining(headers)


SPEC = ProviderSpec(
    name="pixabay",
    label="Pixabay",
    media_types=("video", "photo"),
    env_key="PIXABAY_API_KEY",
    setup_hint="Add PIXABAY_API_KEY=your_key to backend/.env, then restart the app.",
    source_url="https://pixabay.com",
    search=search,
)
