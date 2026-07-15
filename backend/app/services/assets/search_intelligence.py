from __future__ import annotations

import re
from collections.abc import Iterable

from ...schemas import AssetCandidate

SEPARATOR_RE = re.compile(r"\s*(?:,|;|\||\n)\s*")
WORD_RE = re.compile(r"[a-z0-9]+")

ABSTRACT_WORDS = {
    "change",
    "concept",
    "future",
    "growth",
    "idea",
    "impact",
    "importance",
    "power",
    "strategy",
    "success",
    "value",
}

MOTION_WORDS = {"animation", "footage", "lapse", "motion", "timelapse", "video"}

VISUAL_WORDS = {
    "airplane",
    "building",
    "calendar",
    "chart",
    "city",
    "clock",
    "coins",
    "computer",
    "document",
    "earth",
    "factory",
    "graph",
    "hands",
    "hourglass",
    "laptop",
    "map",
    "market",
    "money",
    "office",
    "person",
    "portfolio",
    "rocket",
    "satellite",
    "screen",
    "space",
    "stock",
    "street",
    "timeline",
}


def normalize_phrase(value: str) -> str:
    return " ".join(value.strip().lower().split())


def tokens(value: str) -> set[str]:
    return set(WORD_RE.findall(value.lower()))


def rewrite_abstract_phrase(phrase: str, media_type: str) -> str:
    words = tokens(phrase)

    if "calendar" in words and ({"lapse", "timelapse", "time"} & words):
        return "calendar time lapse" if media_type == "video" else "calendar pages"

    finance_words = {
        "compound",
        "finance",
        "financial",
        "investment",
        "market",
        "stock",
        "wealth",
    }
    if "growth" in words and words & finance_words:
        return (
            "stock market chart animation"
            if media_type == "video"
            else "stock market growth chart"
        )

    if "stock" in words and "chart" in words:
        return "stock market chart animation" if media_type == "video" else "stock market chart"

    if "investment" in words and not words & {"chart", "portfolio", "money", "coins"}:
        return (
            "investment portfolio screen"
            if media_type == "video"
            else "investment portfolio desk"
        )

    if "time" in words and not words & VISUAL_WORDS:
        return "clock calendar" if media_type == "photo" else "clock time lapse"

    return phrase


def phrase_score(phrase: str) -> tuple[int, int, int]:
    words = tokens(phrase)
    visual_count = len(words & VISUAL_WORDS)
    abstract_count = len(words & ABSTRACT_WORDS)
    return visual_count - abstract_count, visual_count, -len(words)


def too_similar(left: str, right: str) -> bool:
    left_tokens = tokens(left) - MOTION_WORDS
    right_tokens = tokens(right) - MOTION_WORDS
    if not left_tokens or not right_tokens:
        return normalize_phrase(left) == normalize_phrase(right)
    overlap = len(left_tokens & right_tokens)
    smaller = min(len(left_tokens), len(right_tokens))
    return overlap / smaller >= 0.75


def build_search_plan(
    query: str,
    scene_keywords: Iterable[str],
    visual_intent: str,
    media_type: str,
    *,
    max_queries: int = 3,
) -> list[str]:
    """Build focused provider queries without diluting an explicit user concept."""
    normalized_query = normalize_phrase(query)
    keyword_phrases = [
        normalize_phrase(value)
        for value in scene_keywords
        if normalize_phrase(value)
    ]
    comma_joined_keywords = normalize_phrase(", ".join(keyword_phrases))
    space_joined_keywords = normalize_phrase(" ".join(keyword_phrases))
    has_separators = any(separator in query for separator in (",", ";", "|", "\n"))
    query_is_scene_bundle = bool(
        keyword_phrases
        and normalized_query in {comma_joined_keywords, space_joined_keywords}
    )
    query_is_explicit_concept = normalized_query in keyword_phrases

    if query_is_explicit_concept:
        raw_phrases = [normalized_query]
        expand_scene_context = False
    elif has_separators:
        raw_phrases = [normalize_phrase(value) for value in SEPARATOR_RE.split(query)]
        expand_scene_context = True
    elif query_is_scene_bundle:
        raw_phrases = keyword_phrases
        expand_scene_context = True
    else:
        raw_phrases = [normalized_query]
        expand_scene_context = False

    if expand_scene_context and visual_intent.strip():
        raw_phrases.extend(
            normalize_phrase(value)
            for value in re.split(
                r"\s+(?:and|with|beside|into)\s+",
                visual_intent.lower(),
            )
        )

    candidates: list[tuple[int, str]] = []
    seen: set[str] = set()
    for position, raw_phrase in enumerate(raw_phrases):
        if not raw_phrase:
            continue
        phrase = normalize_phrase(rewrite_abstract_phrase(raw_phrase, media_type))[:100]
        if len(phrase) < 2 or phrase in seen:
            continue
        seen.add(phrase)
        candidates.append((position, phrase))

    candidates.sort(
        key=lambda item: (phrase_score(item[1]), -item[0]),
        reverse=True,
    )

    plan: list[str] = []
    for _position, phrase in candidates:
        if any(too_similar(phrase, existing) for existing in plan):
            continue
        plan.append(phrase)
        if len(plan) >= max_queries:
            break

    return plan or [normalized_query[:100]]


def merge_candidate_batches(
    batches: list[list[AssetCandidate]],
    limit: int,
) -> list[AssetCandidate]:
    merged: list[AssetCandidate] = []
    seen: set[tuple[str, str]] = set()
    max_length = max((len(batch) for batch in batches), default=0)

    for index in range(max_length):
        for batch in batches:
            if index >= len(batch):
                continue
            candidate = batch[index]
            identity = (candidate.provider, candidate.provider_asset_id)
            if identity in seen:
                continue
            seen.add(identity)
            merged.append(candidate)
            if len(merged) >= limit:
                return merged

    return merged
