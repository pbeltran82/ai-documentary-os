from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import quote, urlencode

from ...schemas import AssetCandidate
from .common import ProviderSpec, json_request, rate_limit_remaining

WORD_RE = re.compile(r"[a-z0-9]+")
GENERIC_WORDS = {
    "animation",
    "footage",
    "growth",
    "lapse",
    "motion",
    "photo",
    "time",
    "timelapse",
    "video",
}

TAG_GROUPS: dict[str, set[str]] = {
    "calendar": {
        "agenda",
        "calendar",
        "date",
        "deadline",
        "month",
        "planner",
        "schedule",
        "year",
    },
    "clock": {
        "clock",
        "hourglass",
        "stopwatch",
        "timepiece",
        "timer",
        "watch",
    },
    "chart": {
        "analytics",
        "candlestick",
        "chart",
        "data",
        "diagram",
        "graph",
        "statistics",
    },
    "finance": {
        "business",
        "economy",
        "finance",
        "financial",
        "investing",
        "investment",
        "market",
        "money",
        "portfolio",
        "stock",
        "stocks",
        "trade",
        "trading",
    },
}

NATURE_NOISE = {
    "blossom",
    "cloud",
    "clouds",
    "flower",
    "flowers",
    "forest",
    "landscape",
    "mountain",
    "mountains",
    "nature",
    "plant",
    "sky",
    "tree",
    "trees",
}


def word_set(value: str) -> set[str]:
    return set(WORD_RE.findall(value.lower()))


def required_groups(query_words: set[str]) -> list[str]:
    groups: list[str] = []
    if query_words & TAG_GROUPS["calendar"]:
        groups.append("calendar")
    if query_words & TAG_GROUPS["clock"]:
        groups.append("clock")
    if query_words & {"chart", "graph", "analytics", "candlestick", "diagram"}:
        groups.append("chart")
    if query_words & TAG_GROUPS["finance"]:
        groups.append("finance")
    return groups


def pixabay_filters(query: str, media_type: str) -> dict[str, str]:
    words = word_set(query)
    filters: dict[str, str] = {}

    if words & TAG_GROUPS["finance"] or words & TAG_GROUPS["chart"]:
        filters["category"] = "business"

    if media_type == "video":
        if words & {"animation", "chart", "graph", "diagram", "analytics"}:
            filters["video_type"] = "animation"
        elif words & {"calendar", "clock", "hourglass", "watch"}:
            filters["video_type"] = "film"

    return filters


def rank_hits(hits: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Return only defensible matches; never backfill the grid with random media."""
    query_words = word_set(query)
    anchors = query_words - GENERIC_WORDS
    groups = required_groups(query_words)

    def metrics(item: dict[str, Any]) -> tuple[bool, int, int, int, int, int]:
        tag_words = word_set(str(item.get("tags") or ""))
        matched_groups = sum(bool(tag_words & TAG_GROUPS[group]) for group in groups)
        groups_satisfied = matched_groups == len(groups) if groups else True
        exact_overlap = len(anchors & tag_words)
        noise_count = len(tag_words & NATURE_NOISE)
        likes = int(item.get("likes") or 0)
        downloads = int(item.get("downloads") or 0)
        return (
            groups_satisfied,
            matched_groups,
            exact_overlap,
            -noise_count,
            likes,
            downloads,
        )

    strong: list[dict[str, Any]] = []
    for item in hits:
        groups_satisfied, _matched, exact_overlap, noise_score, _likes, _downloads = metrics(item)
        has_semantic_anchor = groups_satisfied and (bool(groups) or exact_overlap > 0)
        is_noise_only = noise_score < 0 and exact_overlap == 0
        if has_semantic_anchor and not is_noise_only:
            strong.append(item)

    return sorted(strong, key=metrics, reverse=True)


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
        preview_url=(
            item.get("largeImageURL")
            or item.get("webformatURL")
            or item.get("previewURL")
            or ""
        ),
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
        return (
            1 if height > width else 0,
            abs(width - 1920) + abs(height - 1080),
        )

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


def search(
    query: str,
    media_type: str,
    per_page: int,
) -> tuple[list[AssetCandidate], int | None]:
    endpoint = (
        "https://pixabay.com/api/videos/"
        if media_type == "video"
        else "https://pixabay.com/api/"
    )
    params: dict[str, str | int] = {
        "key": os.getenv("PIXABAY_API_KEY", "").strip(),
        "q": query[:100],
        "per_page": max(12, per_page * 3),
        "safesearch": "true",
        "order": "popular",
        **pixabay_filters(query, media_type),
    }
    if media_type == "photo":
        params.update(
            {
                "image_type": "photo",
                "orientation": "horizontal",
                "min_width": 1280,
            }
        )

    payload, headers = json_request(
        f"{endpoint}?{urlencode(params)}",
        provider_label="Pixabay",
    )
    hits = rank_hits(list(payload.get("hits", [])), query)[:per_page]
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
