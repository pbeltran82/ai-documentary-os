from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

from ...schemas import AssetCandidate
from .common import ProviderSpec, clean_html, json_request

WORD_RE = re.compile(r"[a-z0-9]+")
SAFE_RIGHTS_PHRASES = (
    "no known restrictions on publication",
    "no known restrictions",
    "no known copyright restrictions",
    "no known copyright restriction",
    "public domain",
    "free to use and reuse",
)


def text_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = clean_html(value)
        return [cleaned] if cleaned else []
    if isinstance(value, dict):
        result: list[str] = []
        for nested in value.values():
            result.extend(text_values(nested))
        return result
    if isinstance(value, (list, tuple, set)):
        result = []
        for nested in value:
            result.extend(text_values(nested))
        return result
    return [str(value)]


def rights_statement(item: dict[str, Any]) -> str:
    nested = item.get("item") if isinstance(item.get("item"), dict) else {}
    values: list[str] = []
    for source in (item, nested):
        for key in (
            "rights",
            "rights_advisory",
            "rights_information",
            "restriction",
            "restrictions",
        ):
            values.extend(text_values(source.get(key)))
    return " ".join(values).strip()


def rights_are_safe(statement: str) -> bool:
    lowered = statement.lower()
    return bool(lowered) and any(phrase in lowered for phrase in SAFE_RIGHTS_PHRASES)


def image_urls(item: dict[str, Any]) -> list[str]:
    urls: list[str] = []

    def add(value: Any) -> None:
        for candidate in text_values(value):
            url = candidate.strip()
            if url.startswith("//"):
                url = f"https:{url}"
            if url.startswith("https://") and url not in urls:
                urls.append(url)

    add(item.get("image_url"))
    for resource in item.get("resources") or []:
        if not isinstance(resource, dict):
            continue
        add(resource.get("image"))
        add(resource.get("url"))
        for file_item in resource.get("files") or []:
            if isinstance(file_item, dict):
                add(file_item.get("url"))
                add(file_item.get("fulltext_file"))

    def quality_score(url: str) -> tuple[int, int]:
        lowered = url.lower()
        score = 0
        if any(token in lowered for token in ("original", "master", "full")):
            score += 6
        if any(token in lowered for token in ("1140", "2000", "3000")):
            score += 4
        if lowered.endswith((".jpg", ".jpeg", ".png", ".webp")):
            score += 3
        if lowered.endswith((".tif", ".tiff")):
            score -= 2
        return score, len(url)

    return sorted(urls, key=quality_score)


def creator_name(item: dict[str, Any]) -> str:
    for key in ("contributor_names", "contributors", "creator", "partof"):
        values = text_values(item.get(key))
        if values:
            return values[0][:200]
    return "Library of Congress"


def normalize_photo(item: dict[str, Any]) -> AssetCandidate | None:
    statement = rights_statement(item)
    if not rights_are_safe(statement):
        return None

    urls = image_urls(item)
    if not urls:
        return None

    source_url = str(item.get("id") or item.get("url") or "").strip()
    if not source_url:
        return None
    title = clean_html(str(item.get("title") or "Library of Congress item"))
    creator = creator_name(item)
    subjects = text_values(item.get("subject")) + text_values(item.get("subjects"))
    formats = text_values(item.get("format")) + text_values(item.get("original_format"))
    dates = text_values(item.get("date"))
    descriptions = text_values(item.get("description")) + text_values(item.get("summary"))
    description = " ".join(
        value
        for value in [title, creator, *subjects, *formats, *dates, *descriptions]
        if value
    )
    keywords = sorted(set(WORD_RE.findall(description.lower())))[:40]
    provider_asset_id = source_url.rstrip("/").rsplit("/", 1)[-1] or source_url

    return AssetCandidate(
        provider="loc",
        provider_asset_id=provider_asset_id[:200],
        media_type="photo",
        source_url=source_url,
        preview_url=urls[0],
        download_url=urls[-1],
        creator=creator,
        creator_url=source_url,
        width=0,
        height=0,
        duration_seconds=None,
        license_name="No known restrictions on publication",
        license_url="https://www.loc.gov/free-to-use/",
        attribution=f"{creator} · Library of Congress"[:2000],
        description=description[:5000],
        keywords=keywords,
    )


def search(query: str, _media_type: str, per_page: int) -> tuple[list[AssetCandidate], int | None]:
    params = {
        "fo": "json",
        "q": query,
        "c": min(max(per_page * 4, 20), 100),
        "sp": 1,
        "sb": "relevance",
        "fa": "online-format:image",
        "at": "results",
    }
    payload, _headers = json_request(
        f"https://www.loc.gov/photos/?{urlencode(params)}",
        provider_label="Library of Congress",
    )
    candidates = [
        candidate
        for candidate in (normalize_photo(item) for item in payload.get("results", []))
        if candidate is not None
    ]
    return candidates[:per_page], None


SPEC = ProviderSpec(
    name="loc",
    label="Library of Congress",
    media_types=("photo",),
    env_key=None,
    setup_hint="No API key required. Only records with explicit public-use rights are shown.",
    source_url="https://www.loc.gov/pictures/",
    search=search,
)
