from __future__ import annotations

import re
from collections.abc import Iterable

from .types import (
    AssetDirective,
    ExecutionMode,
    SceneIntent,
    ShotPlan,
    SourceMode,
    VisualFamily,
    VisualStrategy,
)

_WORD_RE = re.compile(r"[a-z0-9']+")
_STOP_WORDS = {
    "about", "after", "again", "also", "because", "before", "being",
    "could", "does", "from", "have", "into", "more", "most", "over",
    "same", "should", "some", "such", "than", "that", "their", "there",
    "these", "they", "this", "those", "through", "under", "very", "what",
    "when", "where", "which", "while", "with", "would", "your", "you",
    "show", "clear", "cinematic", "visual", "representing", "documentary",
    "every", "time", "only", "need", "needs", "result", "whether",
    "designed", "like", "just", "then", "next", "comes", "thing",
    "skip", "replay", "watch", "look", "make", "made", "gets", "using",
    "open", "invisible", "predicts", "pause", "even", "moments", "slows",
    "down", "feed", "feels", "compete", "important", "choosing", "deserves",
    "recognize", "patterns",
}
_GENERIC_SINGLE_WORDS = {
    "person", "people", "human", "system", "world", "moment", "subject",
    "choice", "future", "power", "technology", "digital", "attention",
}
_CONCRETE_SINGLE_WORDS = {
    "app", "calendar", "camera", "child", "city", "commuter", "computer",
    "crowd", "dashboard", "document", "driver", "factory", "family", "graph",
    "hospital", "laptop", "market", "office", "parent", "phone", "platform",
    "researcher", "screen", "smartphone", "station", "student", "teacher",
    "viewer", "worker",
}


def _unique(values: Iterable[str], limit: int) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = " ".join(str(value).strip().lower().split())
        if cleaned and cleaned not in seen:
            result.append(cleaned)
            seen.add(cleaned)
        if len(result) >= limit:
            break
    return tuple(result)


def _meaningful_phrase(value: str) -> str:
    words = []
    for word in _WORD_RE.findall(str(value).lower()):
        cleaned = word.strip("'")
        if len(cleaned) < 4 or cleaned in _STOP_WORDS:
            continue
        words.append(cleaned)
    if not words:
        return ""
    if len(words) == 1 and words[0] not in _CONCRETE_SINGLE_WORDS:
        return ""
    return " ".join(words[:5])


def _clean_supplied(values: tuple[str, ...] | list[str], limit: int = 6) -> tuple[str, ...]:
    return _unique((_meaningful_phrase(value) for value in values), limit)


def _keywords(text: str, limit: int = 8) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for word in _WORD_RE.findall(text.lower()):
        cleaned = word.strip("'")
        if (
            len(cleaned) < 4
            or cleaned in _STOP_WORDS
            or cleaned in _GENERIC_SINGLE_WORDS
            or cleaned in seen
        ):
            continue
        result.append(cleaned)
        seen.add(cleaned)
        if len(result) >= limit:
            break
    return tuple(result)


def _semantic_anchors(
    intent: SceneIntent,
    strategy: VisualStrategy,
    shot: ShotPlan,
) -> tuple[str, ...]:
    concepts = set(intent.concept_terms)
    actions = set(intent.action_terms)
    anchors: list[str] = []

    if intent.interface_score:
        if "scroll" in actions:
            anchors.append("person scrolling smartphone")
        elif "search" in actions:
            anchors.append("person searching on smartphone")
        else:
            anchors.append("person using smartphone")
        anchors.extend(("social media feed", "phone screen over shoulder"))

    if "attention" in concepts:
        anchors.append("person distracted by smartphone")
    if concepts & {"behavior", "prediction"}:
        anchors.append("behavioral data on screen")
    if concepts & {"choice", "control", "agency"}:
        anchors.append("person choosing on smartphone")

    if strategy.family == VisualFamily.CINEMATIC_REAL_WORLD and intent.human_score:
        anchors.append("person in everyday environment")
    elif strategy.family == VisualFamily.EDITORIAL_SYMBOLIC:
        if concepts:
            anchors.append(f"{sorted(concepts)[0]} in everyday life")
        else:
            anchors.append("thoughtful person everyday setting")
    elif strategy.family == VisualFamily.TIMELINE_HISTORICAL:
        anchors.append("archival documentary photograph")

    focal = _meaningful_phrase(shot.focal_subject)
    if focal:
        anchors.append(focal)
    return _unique(anchors, 6)


def build_asset_directive(
    intent: SceneIntent,
    strategy: VisualStrategy,
    shot: ShotPlan,
    *,
    narration: str,
    visual_intent: str = "",
    search_keywords: tuple[str, ...] | list[str] = (),
) -> AssetDirective:
    """Translate visual meaning into an executable source decision.

    Asset-first scenes use the existing rights-aware Visual Director. Exact
    Visual rendering is kept only for data relationships and the terminal CTA.
    Search phrases deliberately favor concrete observable situations over weak
    narration glue words that often produce unrelated stock media.
    """
    supplied = _clean_supplied(search_keywords, 6)
    anchors = _semantic_anchors(intent, strategy, shot)
    visual_semantic = _keywords(visual_intent, 6)
    narration_semantic = _keywords(narration, 8)
    search_terms = _unique(
        [*anchors, *supplied, *visual_semantic, *narration_semantic],
        8,
    )

    avoid_terms = _unique(
        (
            "presentation slide",
            "generic infographic",
            "primitive vector character",
            "visible watermark",
            "random filler",
            "unrelated insect or animal",
            "religious graffiti without narrative relevance",
        ),
        8,
    )

    if strategy.source_mode == SourceMode.PROCEDURAL_GRAPHIC:
        return AssetDirective(
            execution_mode=ExecutionMode.EXACT_VISUAL,
            preferred_media_type="video",
            fallback_media_type=None,
            overlay_mode="native_explainer",
            search_terms=search_terms,
            avoid_terms=avoid_terms,
            allow_generated_still=False,
            reason=(
                "The narration requires a controlled data/explainer composition or "
                "a branded ending, so procedural rendering is justified."
            ),
        )

    if strategy.source_mode == SourceMode.PHOTOGRAPHY:
        preferred = "photo"
        fallback = "video"
        overlay = "editorial_motion"
    elif strategy.source_mode == SourceMode.HYBRID_COMPOSITE:
        preferred = "video"
        fallback = "photo"
        overlay = "restrained_editorial_overlay"
    else:
        preferred = "video"
        fallback = "photo"
        overlay = "none"

    return AssetDirective(
        execution_mode=ExecutionMode.ASSET_FIRST,
        preferred_media_type=preferred,
        fallback_media_type=fallback,
        overlay_mode=overlay,
        search_terms=search_terms,
        avoid_terms=avoid_terms,
        allow_generated_still=True,
        reason=(
            "A believable person, environment, object, or archival source should carry "
            "the scene. Generated graphics are a fallback, not the default."
        ),
    )
