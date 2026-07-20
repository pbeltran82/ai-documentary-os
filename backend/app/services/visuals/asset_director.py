from __future__ import annotations

import re
from collections.abc import Iterable

from .types import (
    AssetDirective,
    ExecutionMode,
    SceneIntent,
    ShotPlan,
    SourceMode,
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


def _keywords(text: str, limit: int = 8) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for word in _WORD_RE.findall(text.lower()):
        cleaned = word.strip("'")
        if len(cleaned) < 4 or cleaned in _STOP_WORDS or cleaned in seen:
            continue
        result.append(cleaned)
        seen.add(cleaned)
        if len(result) >= limit:
            break
    return tuple(result)


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
    """
    supplied = _unique(search_keywords, 6)
    semantic = _keywords(" ".join([visual_intent, narration]), 8)
    focal = _keywords(shot.focal_subject, 4)
    search_terms = _unique([*supplied, *focal, *semantic], 8)

    avoid_terms = _unique(
        (
            "presentation slide",
            "generic infographic",
            "primitive vector character",
            "visible watermark",
            "random filler",
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
