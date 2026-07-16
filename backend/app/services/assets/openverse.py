from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

from ...schemas import AssetCandidate
from .common import ProviderSpec, json_request, rate_limit_remaining

WORD_RE = re.compile(r"[a-z0-9]+")
ALLOWED_LICENSES = {"cc0", "pdm", "by", "by-sa"}
LICENSE_LABELS = {
    "cc0": "CC0 1.0",
    "pdm": "Public Domain Mark",
    "by": "Creative Commons Attribution",
    "by-sa": "Creative Commons Attribution-ShareAlike",
}


def tag_names(item: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for tag in item.get("tags") or []:
        if isinstance(tag, dict):
            value = str(tag.get("name") or "").strip()
        else:
            value = str(tag).strip()
        if value:
            values.append(value)
    return values


def normalize_photo(item: dict[str, Any]) -> AssetCandidate | None:
    license_code = str(item.get("license") or "").strip().lower()
    if license_code not in ALLOWED_LICENSES or bool(item.get("watermarked")):
        return None

    download_url = str(item.get("url") or "").strip()
    preview_url = str(item.get("thumbnail") or download_url).strip()
    source_url = str(
        item.get("foreign_landing_url")
        or item.get("detail_url")
        or item.get("related_url")
        or ""
    ).strip()
    if not download_url or not preview_url or not source_url:
        return None

    width = int(item.get("width") or 0)
    height = int(item.get("height") or 0)
    if width and width < 1000:
        return None
    if height and height < 600:
        return None

    title = str(item.get("title") or "Open image").strip()
    creator = str(item.get("creator") or "Openverse contributor").strip()
    creator_url = str(item.get("creator_url") or source_url).strip()
    tags = tag_names(item)
    description = " ".join(
        value
        for value in (
            title,
            " ".join(tags),
            str(item.get("category") or ""),
            str(item.get("source") or ""),
        )
        if value
    )
    keywords = sorted(set(WORD_RE.findall(description.lower())))[:40]
    license_name = LICENSE_LABELS.get(license_code, license_code.upper())
    license_url = str(item.get("license_url") or "").strip()
    attribution = str(item.get("attribution") or "").strip()
    if not attribution:
        attribution = f"{title} by {creator} · {license_name}"

    return AssetCandidate(
        provider="openverse",
        provider_asset_id=str(item.get("id") or source_url),
        media_type="photo",
        source_url=source_url,
        preview_url=preview_url,
        download_url=download_url,
        creator=creator[:200],
        creator_url=creator_url,
        width=width,
        height=height,
        duration_seconds=None,
        license_name=license_name[:200],
        license_url=license_url,
        attribution=attribution[:2000],
        description=description[:5000],
        keywords=keywords,
    )


def search(query: str, _media_type: str, per_page: int) -> tuple[list[AssetCandidate], int | None]:
    params = {
        "q": query,
        "page_size": min(max(per_page * 3, 12), 50),
        "license_type": "commercial",
        "mature": "false",
    }
    payload, headers = json_request(
        f"https://api.openverse.org/v1/images/?{urlencode(params)}",
        provider_label="Openverse",
    )
    candidates = [
        candidate
        for candidate in (normalize_photo(item) for item in payload.get("results", []))
        if candidate is not None
    ]
    return candidates[:per_page], rate_limit_remaining(headers)


SPEC = ProviderSpec(
    name="openverse",
    label="Openverse",
    media_types=("photo",),
    env_key=None,
    setup_hint="No API key required. Commercial-use licenses are filtered automatically.",
    source_url="https://openverse.org",
    search=search,
)
