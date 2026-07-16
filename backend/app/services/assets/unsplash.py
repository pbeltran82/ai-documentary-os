from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import quote, urlencode

from ...schemas import AssetCandidate
from .common import ProviderSpec, json_request, rate_limit_remaining

WORD_RE = re.compile(r"[a-z0-9]+")


def with_utm(url: str) -> str:
    if not url:
        return ""
    return f"{url}{'&' if '?' in url else '?'}utm_source=ai_documentary_os&utm_medium=referral"


def normalize_photo(item: dict[str, Any]) -> AssetCandidate:
    urls = item.get("urls") or {}
    links = item.get("links") or {}
    user = item.get("user") or {}
    creator = user.get("name") or user.get("username") or ""
    description = str(item.get("description") or item.get("alt_description") or "")
    keywords = sorted(set(WORD_RE.findall(description.lower())))[:40]
    return AssetCandidate(
        provider="unsplash",
        provider_asset_id=str(item["id"]),
        media_type="photo",
        source_url=with_utm(links.get("html") or ""),
        preview_url=urls.get("regular") or urls.get("small") or "",
        download_url=urls.get("full") or urls.get("regular") or "",
        creator=creator,
        creator_url=with_utm((user.get("links") or {}).get("html") or ""),
        width=int(item.get("width") or 0),
        height=int(item.get("height") or 0),
        duration_seconds=None,
        license_name="Unsplash License",
        license_url="https://unsplash.com/license",
        attribution=f"Photo by {creator} on Unsplash" if creator else "Photo on Unsplash",
        description=description,
        keywords=keywords,
    )


def auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Client-ID {os.getenv('UNSPLASH_ACCESS_KEY', '').strip()}",
        "Accept-Version": "v1",
    }


def search(query: str, _media_type: str, per_page: int) -> tuple[list[AssetCandidate], int | None]:
    params = {
        "query": query,
        "per_page": min(per_page, 30),
        "orientation": "landscape",
        "content_filter": "high",
    }
    payload, headers = json_request(
        f"https://api.unsplash.com/search/photos?{urlencode(params)}",
        provider_label="Unsplash",
        headers=auth_headers(),
    )
    return [normalize_photo(item) for item in payload.get("results", [])], rate_limit_remaining(headers)


def track_selection(provider_asset_id: str) -> None:
    json_request(
        f"https://api.unsplash.com/photos/{quote(provider_asset_id, safe='')}/download",
        provider_label="Unsplash",
        headers=auth_headers(),
    )


SPEC = ProviderSpec(
    name="unsplash",
    label="Unsplash",
    media_types=("photo",),
    env_key="UNSPLASH_ACCESS_KEY",
    setup_hint="Add UNSPLASH_ACCESS_KEY=your_access_key to backend/.env, then restart the app.",
    source_url="https://unsplash.com",
    search=search,
    track_selection=track_selection,
)
