from __future__ import annotations

from fastapi import HTTPException
from PIL import Image

from ..models import Scene
from . import character_expressive as character
from . import finance_motion_choreography as finance
from . import tech_behavior_route_patch as tech

FINANCE_FAMILY_ID = "finance_motion"
CHARACTER_FAMILY_ID = "character_explainer"
TECH_FAMILY_ID = "tech_behavior_motion"
DEFAULT_FAMILY_ID = FINANCE_FAMILY_ID

FAMILIES = (
    {
        "family_id": FINANCE_FAMILY_ID,
        "label": "Finance Motion",
        "description": "Use semantic accounts, charts, transfers, and money-system graphics when the financial mechanism is the story.",
    },
    {
        "family_id": CHARACTER_FAMILY_ID,
        "label": "Character Explainer",
        "description": "Use expressive editorial characters when a person's behavior, decision, reaction, or habit is the story.",
    },
    {
        "family_id": TECH_FAMILY_ID,
        "label": "Tech & Behavior Motion",
        "description": "Use recommendation systems, behavioral signals, prediction models, timelines, and digital twins when technology is the story.",
    },
)

STRONG_CHARACTER_PHRASES = (
    "most people",
    "wealthy people",
    "future self",
    "pay themselves first",
    "pay yourself first",
    "exact opposite",
    "never anything left",
    "nothing left",
    "pay their rent",
    "buy groceries",
    "go out",
    "treat it like a bill",
    "treat that ten percent like a bill",
    "ten percent like a bill",
    "treating that 10 percent like a bill",
)

STRONG_FINANCE_PHRASES = {
    "s&p 500": 8,
    "index fund": 7,
    "compound interest": 8,
    "market growth": 6,
    "recurring transfer": 5,
    "automatic transfer": 5,
    "growth chart": 5,
    "asset allocation": 6,
    "subscribe": 5,
    "blueprint": 4,
}

STRONG_TECH_PHRASES = {
    "artificial intelligence": 8,
    "silent algorithm": 10,
    "algorithm decided": 10,
    "recommendation system": 8,
    "predict human behavior": 10,
    "predicting human behavior": 10,
    "predictive behavioral modeling": 11,
    "digital footprint": 9,
    "digital twin": 10,
    "behavioral twin": 10,
    "behavioral version of you": 11,
    "every scroll": 7,
    "every pause": 7,
    "deleted draft": 7,
    "machine choose": 9,
    "machine chose": 9,
    "highest bidder": 6,
    "systems that learn how to navigate us": 14,
    "learn how to navigate us": 13,
    "navigate us": 9,
    "what reaches you": 7,
    "change your behavior": 8,
    "help us navigate the world": 7,
}

REAL_FOOTAGE_PREFERRED_PHRASES = (
    "help us navigate the world",
    "using technology to navigate",
    "person uses technology",
)


def family_catalog() -> list[dict[str, str]]:
    return [dict(item) for item in FAMILIES]


def _context(scene: Scene) -> str:
    return " ".join(
        [scene.narration, scene.visual_intent, *scene.search_keywords]
    ).lower()


def _words(value: str) -> set[str]:
    return {
        "".join(character for character in token.lower() if character.isalnum())
        for token in value.split()
    } - {""}


def _finance_score(scene: Scene) -> int:
    context = _context(scene)
    words = _words(context)
    template_scores = [
        len(words & set(template.keywords))
        for template in finance.TEMPLATES
    ]
    score = max(template_scores, default=0)
    for phrase, weight in STRONG_FINANCE_PHRASES.items():
        if phrase in context:
            score += weight
    return score


def _character_score(scene: Scene) -> int:
    return character.score_character_templates(scene)[0][0]


def _tech_score(scene: Scene) -> int:
    context = _context(scene)
    score = tech.score_templates(scene)[0][0]
    for phrase, weight in STRONG_TECH_PHRASES.items():
        if phrase in context:
            score += weight
    return score


def recommend_family(scene: Scene) -> tuple[str, float, str]:
    context = _context(scene)
    character_score = _character_score(scene)
    finance_score = _finance_score(scene)
    tech_score = _tech_score(scene)
    explicit_character = [phrase for phrase in STRONG_CHARACTER_PHRASES if phrase in context]
    explicit_finance = [phrase for phrase in STRONG_FINANCE_PHRASES if phrase in context]
    explicit_tech = [phrase for phrase in STRONG_TECH_PHRASES if phrase in context]
    real_footage_signal = next(
        (phrase for phrase in REAL_FOOTAGE_PREFERRED_PHRASES if phrase in context),
        None,
    )

    if real_footage_signal:
        return (
            TECH_FAMILY_ID,
            0.64,
            "Editorial recommendation: prefer strong real footage of a person using technology; use Tech & Behavior Motion only when no defensible real asset exists.",
        )

    if explicit_tech and tech_score >= max(6, finance_score):
        confidence = min(0.98, 0.68 + 0.018 * tech_score)
        return (
            TECH_FAMILY_ID,
            round(confidence, 2),
            f"The scene centers on algorithmic behavior: {explicit_tech[0]}.",
        )

    if explicit_finance and not explicit_character:
        confidence = min(0.97, 0.68 + 0.025 * finance_score)
        return (
            FINANCE_FAMILY_ID,
            round(confidence, 2),
            f"The scene centers on the financial system: {explicit_finance[0]}.",
        )

    if explicit_character or character_score >= max(5, finance_score + 2, tech_score + 2):
        confidence = min(0.97, 0.62 + 0.025 * max(character_score, 1))
        signal = explicit_character[0] if explicit_character else "multiple behavior signals"
        return (
            CHARACTER_FAMILY_ID,
            round(confidence, 2),
            f"Human behavior is the visual subject: {signal}.",
        )

    if tech_score > max(finance_score + 1, character_score + 1):
        confidence = min(0.94, 0.58 + 0.025 * max(tech_score, 1))
        return (
            TECH_FAMILY_ID,
            round(confidence, 2),
            "Technology, prediction, or behavioral data is clearer than a finance system or character action for this scene.",
        )

    confidence = min(0.94, 0.58 + 0.025 * max(finance_score, 1))
    return (
        FINANCE_FAMILY_ID,
        round(confidence, 2),
        "The money flow or financial mechanism is clearer than a character action or technology system for this scene.",
    )


def _validate_family(family_id: str | None) -> str:
    resolved = family_id or DEFAULT_FAMILY_ID
    if resolved not in {FINANCE_FAMILY_ID, CHARACTER_FAMILY_ID, TECH_FAMILY_ID}:
        raise HTTPException(status_code=422, detail="Unknown exact visual family")
    return resolved


def template_catalog(family_id: str) -> list[dict[str, object]]:
    resolved = _validate_family(family_id)
    if resolved == CHARACTER_FAMILY_ID:
        return character.template_catalog()
    if resolved == TECH_FAMILY_ID:
        return tech.template_catalog()
    return finance.template_catalog()


def suggest_template(
    scene: Scene,
    family_id: str,
):
    resolved = _validate_family(family_id)
    if resolved == CHARACTER_FAMILY_ID:
        return character.suggest_template(scene)
    if resolved == TECH_FAMILY_ID:
        return tech.suggest_template(scene)
    return finance.suggest_template(scene)


def storyboard_beats(
    family_id: str,
    template_id: str,
    duration_seconds: float,
) -> list[dict[str, object]]:
    resolved = _validate_family(family_id)
    if resolved == CHARACTER_FAMILY_ID:
        return character.storyboard_beats(template_id, duration_seconds)
    if resolved == TECH_FAMILY_ID:
        return tech.storyboard_beats(template_id, duration_seconds)
    return finance.storyboard_beats(template_id, duration_seconds)


def render_frame(
    family_id: str,
    template_id: str,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    resolved = _validate_family(family_id)
    if resolved == CHARACTER_FAMILY_ID:
        return character.render_frame(
            template_id,
            duration_seconds,
            time_seconds,
            style_id,
        )
    if resolved == TECH_FAMILY_ID:
        return tech.render_frame(
            template_id,
            duration_seconds,
            time_seconds,
            style_id,
        )
    return finance.render_frame(
        template_id,
        duration_seconds,
        time_seconds,
        style_id,
    )


def render_exact_visual(
    scene: Scene,
    family_id: str,
    template_id: str | None = None,
    style_id: str | None = None,
):
    resolved = _validate_family(family_id)
    if resolved == CHARACTER_FAMILY_ID:
        return character.render_character_motion(scene, template_id, style_id)
    if resolved == TECH_FAMILY_ID:
        return tech.render_tech_motion(scene, template_id, style_id)
    return finance.render_finance_motion(scene, template_id, style_id)


DEFAULT_STYLE_ID = finance.DEFAULT_STYLE_ID
style_catalog = finance.style_catalog
