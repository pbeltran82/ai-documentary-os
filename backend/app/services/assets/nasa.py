from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode

from ...schemas import AssetCandidate
from .common import ProviderSpec, json_request

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v")


def asset_file(manifest_url: str, media_type: str) -> str:
    payload, _headers = json_request(manifest_url, provider_label="NASA Images")
    items = (payload.get("collection") or {}).get("items", [])
    extensions = VIDEO_EXTENSIONS if media_type == "video" else IMAGE_EXTENSIONS
    urls = [
        str(item.get("href") or "")
        for item in items
        if str(item.get("href") or "").lower().split("?")[0].endswith(extensions)
    ]
    if not urls:
        return ""

    def score(url: str) -> tuple[int, int]:
        lowered = url.lower()
        original_penalty = 0 if ("~orig" in lowered or "original" in lowered) else 1
        preview_penalty = 1 if any(token in lowered for token in ("thumb", "small", "~preview")) else 0
        return original_penalty, preview_penalty

    return min(urls, key=score)


def normalize_item(item: dict[str, Any], media_type: str) -> AssetCandidate | None:
    data = (item.get("data") or [None])[0]
    if not data:
        return None
    preview = next(
        (link.get("href") for link in item.get("links") or [] if link.get("href")),
        "",
    )
    nasa_id = str(data.get("nasa_id") or "")
    download_url = asset_file(item.get("href") or "", media_type) if item.get("href") else ""
    creator = data.get("photographer") or data.get("secondary_creator") or data.get("center") or "NASA"
    return AssetCandidate(
        provider="nasa",
        provider_asset_id=nasa_id or str(data.get("title") or ""),
        media_type=media_type,
        source_url=f"https://images.nasa.gov/details/{quote(nasa_id, safe='')}" if nasa_id else "https://images.nasa.gov",
        preview_url=preview or download_url,
        download_url=download_url or preview,
        creator=str(creator),
        creator_url="https://images.nasa.gov",
        width=0,
        height=0,
        duration_seconds=None,
        license_name="NASA Media Usage Guidelines",
        license_url="https://www.nasa.gov/nasa-brand-center/images-and-media/",
        attribution=f"Courtesy of {creator}",
    )


def search(query: str, media_type: str, per_page: int) -> tuple[list[AssetCandidate], int | None]:
    params = {
        "q": query,
        "media_type": "image" if media_type == "photo" else "video",
        "page_size": min(per_page, 12),
    }
    payload, _headers = json_request(
        f"https://images-api.nasa.gov/search?{urlencode(params)}",
        provider_label="NASA Images",
    )
    candidates = [
        candidate
        for candidate in (
            normalize_item(item, media_type)
            for item in (payload.get("collection") or {}).get("items", [])
        )
        if candidate is not None and candidate.preview_url
    ]
    return candidates, None


SPEC = ProviderSpec(
    name="nasa",
    label="NASA Images",
    media_types=("video", "photo"),
    env_key=None,
    setup_hint="No API key required.",
    source_url="https://images.nasa.gov",
    search=search,
)
