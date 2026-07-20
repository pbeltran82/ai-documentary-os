from __future__ import annotations

import re

from .types import SceneIntent

_WORD_RE = re.compile(r"[a-z0-9']+")

_HUMAN = {
    "person", "people", "viewer", "worker", "family", "child", "parent",
    "researcher", "driver", "student", "consumer", "creator", "patient",
    "human", "woman", "man", "crowd", "community", "citizen",
}
_ENVIRONMENT = {
    "home", "office", "street", "city", "school", "hospital", "factory",
    "room", "store", "market", "station", "airport", "farm", "lab",
    "neighborhood", "landscape", "world", "workplace",
}
_INTERFACE = {
    "phone", "screen", "feed", "app", "website", "dashboard", "scroll",
    "click", "search", "notification", "recommendation", "algorithm",
    "profile", "platform", "interface", "video", "digital",
}
_DATA = {
    "data", "chart", "graph", "timeline", "percentage", "percent", "rate",
    "records", "score", "ranking", "probability", "estimate", "model",
    "statistics", "trend", "compare", "comparison", "versus", "process",
}
_COMPARISON = {
    "before", "after", "versus", "vs", "contrast", "difference", "choice",
    "option", "either", "instead", "compared", "comparison",
}
_HISTORICAL = {
    "history", "historical", "archive", "archival", "past", "century",
    "decade", "year", "timeline", "records", "documents", "photograph",
}
_ACTIONS = {
    "walk", "watch", "scroll", "pause", "search", "choose", "build",
    "move", "work", "drive", "buy", "sell", "speak", "type", "read",
    "open", "close", "follow", "track", "rank", "predict", "decide",
}
_SETTINGS = _ENVIRONMENT | {"online", "offline", "indoors", "outdoors"}
_CONCEPTS = {
    "system", "power", "attention", "agency", "freedom", "risk", "trust",
    "behavior", "prediction", "identity", "influence", "future", "choice",
    "control", "privacy", "wealth", "inequality", "culture", "technology",
}
_CLOSING = {
    "conclusion", "finally", "ultimately", "remember", "subscribe", "like",
    "next story", "final idea", "what comes next", "the choice is yours",
}
_TONES = {
    "urgent": {"danger", "crisis", "threat", "warning", "urgent", "collapse"},
    "ominous": {"hidden", "invisible", "surveillance", "control", "shadow", "fear"},
    "hopeful": {"hope", "better", "restore", "opportunity", "solution", "future"},
    "reflective": {"consider", "question", "meaning", "remember", "perhaps", "why"},
}


def _tokens(*parts: str) -> tuple[str, ...]:
    return tuple(_WORD_RE.findall(" ".join(part for part in parts if part).lower()))


def _matched(tokens: tuple[str, ...], vocabulary: set[str]) -> tuple[str, ...]:
    return tuple(sorted(set(tokens) & vocabulary))


def _tone(tokens: tuple[str, ...]) -> str:
    token_set = set(tokens)
    scored = [(len(token_set & words), name) for name, words in _TONES.items()]
    score, name = max(scored, default=(0, "curious"))
    return name if score else "curious"


def analyze_scene_intent(
    narration: str,
    visual_intent: str = "",
    search_keywords: tuple[str, ...] | list[str] = (),
) -> SceneIntent:
    """Convert a scene brief into provider-neutral documentary intent.

    The result deliberately describes meaning rather than selecting a drawing
    template. Renderers and asset providers can change without rewriting this
    analysis layer.
    """
    tokens = _tokens(narration, visual_intent, " ".join(search_keywords))
    token_set = set(tokens)
    combined = " ".join(tokens)
    closing = any(phrase in combined for phrase in _CLOSING)
    return SceneIntent(
        subject_terms=_matched(tokens, _HUMAN),
        action_terms=_matched(tokens, _ACTIONS),
        setting_terms=_matched(tokens, _SETTINGS),
        concept_terms=_matched(tokens, _CONCEPTS),
        human_score=len(token_set & _HUMAN),
        environmental_score=len(token_set & _ENVIRONMENT),
        interface_score=len(token_set & _INTERFACE),
        data_score=len(token_set & _DATA),
        comparison_score=len(token_set & _COMPARISON),
        historical_score=len(token_set & _HISTORICAL),
        emotional_tone=_tone(tokens),
        closing=closing,
    )
