from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote, urlencode

from ...schemas import AssetCandidate
from .common import ProviderSpec, clean_html, json_request

WORD_RE = re.compile(r"[a-z0-9]+")
ALLOWED_LICENSE_MARKERS = (
    "cc0",
    "public domain",
    "public-domain",
    "cc by",
    "cc-by",
    "creative commons attribution",
)
BLOCKED_LICENSE_MARKERS = (
    "noncommercial",
    "non-commercial",
    "no derivatives",
    "no-derivatives",
    "all rights reserved",
)


def metadata_value(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key) or {}
    return clean_html(value.get("value") if isinstance(value, dict) else str(value))


def license_is_safe(license_name: str, license_url: str) -> bool:
    text = f"{license_name} {license_url}".lower()
    if any(marker in text for marker in BLOCKED_LICENSE_MARKERS):
        return False
    return any(marker in text for marker in ALLOWED_LICENSE_MARKERS)


def normalize_photo(page: dict[str, Any]) -> AssetCandidate | None:
    image_info = (page.get("imageinfo") or [None])[0]
    if not image_info or not str(image_info.get("mime") or "").startswith("image/"):
        return None

    width = int(image_info.get("width") or 0)
    height = int(image_info.get("height") or 0)
    if width and width < 1000:
        return None
    if height and height < 600:
        return None

    metadata = image_info.get("extmetadata") or {}
    title = str(page.get("title") or "")
    source_url = f"https://commons.wikimedia.org/wiki/{quote(title.replace(' ', '_'), safe=':_')}"
    creator = (
        metadata_value(metadata, "Artist")
        or metadata_value(metadata, "Credit")
        or "Wikimedia contributor"
    )
    license_name = (
        metadata_value(metadata, "LicenseShortName")
        or metadata_value(metadata, "UsageTerms")
        or ""
    )
    license_url = metadata_value(metadata, "LicenseUrl")
    if not license_is_safe(license_name, license_url):
        return None

    description = " ".join(
        value
        for value in (
            title.replace("File:", ""),
            metadata_value(metadata, "ObjectName"),
            metadata_value(metadata, "ImageDescription"),
            metadata_value(metadata, "Categories"),
        )
        if value
    )
    keywords = sorted(set(WORD_RE.findall(description.lower())))[:40]
    preview_url = image_info.get("thumburl") or image_info.get("url") or ""
    download_url = image_info.get("url") or ""
    if not preview_url or not download_url:
        return None

    return AssetCandidate(
        provider="wikimedia",
        provider_asset_id=str(page.get("pageid") or title),
        media_type="photo",
        source_url=source_url,
        preview_url=preview_url,
        download_url=download_url,
        creator=creator[:200],
        creator_url=source_url,
        width=width,
        height=height,
        duration_seconds=None,
        license_name=license_name[:200],
        license_url=license_url,
        attribution=f"{creator} · {license_name}"[:2000],
        description=description[:5000],
        keywords=keywords,
    )


def search(query: str, _media_type: str, per_page: int) -> tuple[list[AssetCandidate], int | None]:
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": min(max(per_page * 3, 12), 30),
        "prop": "imageinfo",
        "iiprop": "url|mime|mediatype|extmetadata|size",
        "iiurlwidth": "1280",
        "iiextmetadatalanguage": "en",
        "iiextmetadatafilter": (
            "Artist|Credit|LicenseShortName|LicenseUrl|UsageTerms|"
            "ObjectName|ImageDescription|Categories"
        ),
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
    return candidates[:per_page], None


SPEC = ProviderSpec(
    name="wikimedia",
    label="Wikimedia Commons",
    media_types=("photo",),
    env_key=None,
    setup_hint="No API key required. Commercial-safe and public-domain licenses only.",
    source_url="https://commons.wikimedia.org",
    search=search,
)
