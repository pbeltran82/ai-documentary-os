from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException

from ...schemas import AssetCandidate
from .common import ProviderSpec
from .library_of_congress import search as search_library_of_congress
from .met import search as search_met
from .openverse import search as search_openverse
from .wikimedia import search as search_wikimedia

ARCHIVE_SEARCHERS: tuple[
    tuple[str, Callable[[str, str, int], tuple[list[AssetCandidate], int | None]]],
    ...,
] = (
    ("Wikimedia Commons", search_wikimedia),
    ("Openverse", search_openverse),
    ("Library of Congress", search_library_of_congress),
    ("The Met", search_met),
)


def passes_hard_gate(candidate: AssetCandidate) -> bool:
    if not candidate.preview_url.startswith("https://"):
        return False
    if not candidate.download_url.startswith("https://"):
        return False
    if not candidate.source_url.startswith("https://"):
        return False
    if candidate.width and candidate.width < 1000:
        return False
    if candidate.height and candidate.height < 600:
        return False
    if candidate.width and candidate.height and candidate.width / candidate.height < 0.72:
        return False
    return True


def archive_candidate(candidate: AssetCandidate, source_label: str) -> AssetCandidate:
    original_provider = candidate.provider
    keywords = list(candidate.keywords)
    source_words = source_label.lower().replace("library of congress", "archive loc").split()
    for word in source_words:
        if word not in keywords:
            keywords.append(word)
    return candidate.model_copy(
        update={
            "provider": "wikimedia",
            "provider_asset_id": f"{original_provider}:{candidate.provider_asset_id}"[:200],
            "description": f"{candidate.description} Source collection: {source_label}"[:5000],
            "keywords": keywords[:40],
        }
    )


def search(query: str, media_type: str, per_page: int) -> tuple[list[AssetCandidate], int | None]:
    if media_type != "photo":
        return [], None

    batches: list[list[AssetCandidate]] = []
    remaining_values: list[int] = []
    source_limit = max(6, per_page)

    for source_label, searcher in ARCHIVE_SEARCHERS:
        try:
            candidates, remaining = searcher(query, media_type, source_limit)
        except HTTPException:
            continue
        filtered = [
            archive_candidate(candidate, source_label)
            for candidate in candidates
            if passes_hard_gate(candidate)
        ]
        batches.append(filtered)
        if remaining is not None:
            remaining_values.append(remaining)

    results: list[AssetCandidate] = []
    seen_urls: set[str] = set()
    position = 0
    while len(results) < per_page and any(position < len(batch) for batch in batches):
        for batch in batches:
            if position >= len(batch):
                continue
            candidate = batch[position]
            identity = candidate.download_url.split("?", 1)[0].lower()
            if identity in seen_urls:
                continue
            seen_urls.add(identity)
            results.append(candidate)
            if len(results) >= per_page:
                break
        position += 1

    return results, min(remaining_values) if remaining_values else None


SPEC = ProviderSpec(
    name="wikimedia",
    label="Open Archives",
    media_types=("photo",),
    env_key=None,
    setup_hint=(
        "No API key required. Aggregates Wikimedia Commons, Openverse, "
        "Library of Congress, and The Met with strict rights and quality gates."
    ),
    source_url="https://openverse.org",
    search=search,
)
