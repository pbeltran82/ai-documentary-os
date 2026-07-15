from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode

from ...schemas import AssetCandidate
from .common import ProviderSpec, clean_html, json_request


def metadata_value(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key) or {}
    return clean_html(value.get("value") if isinstance(value, dict) else str(value))


def normalize_photo(page: dict[str, Any]) -> AssetCandidate | None:
    image_info = (page.get("imageinfo") or [None])[0]
    if not image_info or not str(image_info.get("mime") or "").startswith("image/"):
        return None
    metadata = image_info.get("extmetadata") or {}
    title = str(page.get("title") or "")
    source_url = f"https://commons.wikimedia.org/wiki/{quote(title.replace(' ', '_'), safe=':_')}"
    creator = metadata_value(metadata, "Artist") or metadata_value(metadata, "Credit") or "Wikimedia contributor"
    license_name = metadata_value(metadata, "LicenseShortName") or metadata_value(metadata, "UsageTerms") or "See file page"
    return AssetCandidate(
        provider="wikimedia",
        provider_asset_id=str(page.get("pageid") or title),
        media_type="photo",
        source_url=source_url,
        preview_url=image_info.get("thumburl") or image_info.get("url") or "",
        download_url=image_info.get("url") or "",
        creator=creator[:200],
        creator_url=source_url,
        width=int(image_info.get("width") or 0),
        height=int(image_info.get("height") or 0),
        duration_seconds=None,
        license_name=license_name[:200],
        license_url=metadata_value(metadata, "LicenseUrl"),
        attribution=f"{creator} · {license_name}"[:2000],
    )


def search(query: str, _media_type: str, per_page: int) -> tuple[list[AssetCandidate], int | None]:
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": min(per_page, 20),
        "prop": "imageinfo",
        "iiprop": "url|mime|mediatype|extmetadata|size",
        "iiurlwidth": "960",
        "iiextmetadatalanguage": "en",
        "iiextmetadatafilter": "Artist|Credit|LicenseShortName|LicenseUrl|UsageTerms",
        "origin": "*",
    }
    payload, _headers = json_request(
        f"https://commons.wikimedia.org/w/api.php?{urlencode(params)}",
        provider_label="Wikimedia Commons",
    )
    candidates = [
        candidate
        for candidate in (
            normalize_photo(page)
            for page in (payload.get("query") or {}).get("pages", [])
        )
        if candidate is not None and candidate.preview_url
    ]
    return candidates, None


SPEC = ProviderSpec(
    name="wikimedia",
    label="Wikimedia Commons",
    media_types=("photo",),
    env_key=None,
    setup_hint="No API key required.",
    source_url="https://commons.wikimedia.org",
    search=search,
)
