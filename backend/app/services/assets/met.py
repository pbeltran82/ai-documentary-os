from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

from fastapi import HTTPException

from ...schemas import AssetCandidate
from .common import ProviderSpec, json_request

WORD_RE = re.compile(r"[a-z0-9]+")


def tag_terms(item: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for tag in item.get("tags") or []:
        if isinstance(tag, dict):
            value = str(tag.get("term") or "").strip()
        else:
            value = str(tag).strip()
        if value:
            values.append(value)
    return values


def normalize_photo(item: dict[str, Any]) -> AssetCandidate | None:
    if not bool(item.get("isPublicDomain")):
        return None

    download_url = str(item.get("primaryImage") or "").strip()
    preview_url = str(item.get("primaryImageSmall") or download_url).strip()
    source_url = str(item.get("objectURL") or "").strip()
    if not download_url or not preview_url or not source_url:
        return None

    title = str(item.get("title") or "Untitled").strip()
    creator = str(item.get("artistDisplayName") or "The Metropolitan Museum of Art").strip()
    tags = tag_terms(item)
    description = " ".join(
        value
        for value in (
            title,
            creator,
            str(item.get("objectName") or ""),
            str(item.get("classification") or ""),
            str(item.get("department") or ""),
            str(item.get("culture") or ""),
            str(item.get("period") or ""),
            str(item.get("objectDate") or ""),
            str(item.get("medium") or ""),
            " ".join(tags),
        )
        if value
    )
    keywords = sorted(set(WORD_RE.findall(description.lower())))[:40]
    attribution = f"{title}"
    if creator and creator != "The Metropolitan Museum of Art":
        attribution += f" by {creator}"
    attribution += " · The Metropolitan Museum of Art · CC0"

    return AssetCandidate(
        provider="met",
        provider_asset_id=str(item.get("objectID") or source_url),
        media_type="photo",
        source_url=source_url,
        preview_url=preview_url,
        download_url=download_url,
        creator=creator[:200],
        creator_url=source_url,
        width=0,
        height=0,
        duration_seconds=None,
        license_name="CC0 1.0",
        license_url="https://www.metmuseum.org/about-the-met/policies-and-documents/open-access",
        attribution=attribution[:2000],
        description=description[:5000],
        keywords=keywords,
    )


def relevance_score(candidate: AssetCandidate, query: str, highlight: bool) -> tuple[int, int]:
    query_words = set(WORD_RE.findall(query.lower()))
    candidate_words = set(candidate.keywords)
    return len(query_words & candidate_words), 1 if highlight else 0


def search(query: str, _media_type: str, per_page: int) -> tuple[list[AssetCandidate], int | None]:
    search_params = {
        "hasImages": "true",
        "q": query,
    }
    payload, _headers = json_request(
        "https://collectionapi.metmuseum.org/public/collection/v1/search?"
        + urlencode(search_params),
        provider_label="The Met",
    )
    object_ids = payload.get("objectIDs") or []
    fetch_limit = min(max(per_page * 5, 25), 50)
    normalized: list[tuple[AssetCandidate, bool]] = []

    for object_id in object_ids[:fetch_limit]:
        try:
            item, _item_headers = json_request(
                f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}",
                provider_label="The Met",
            )
        except HTTPException:
            continue
        candidate = normalize_photo(item)
        if candidate is not None:
            normalized.append((candidate, bool(item.get("isHighlight"))))

    normalized.sort(
        key=lambda pair: relevance_score(pair[0], query, pair[1]),
        reverse=True,
    )
    return [candidate for candidate, _highlight in normalized[:per_page]], None


SPEC = ProviderSpec(
    name="met",
    label="The Met Open Access",
    media_types=("photo",),
    env_key=None,
    setup_hint="No API key required. Only public-domain objects with downloadable images are shown.",
    source_url="https://www.metmuseum.org/art/collection",
    search=search,
)
