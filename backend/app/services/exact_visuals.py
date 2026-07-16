from __future__ import annotations

from fastapi import HTTPException
from PIL import Image

from ..models import Scene
from . import character_explainer as character
from . import finance_motion_choreography as finance

FINANCE_FAMILY_ID = "finance_motion"
CHARACTER_FAMILY_ID = "character_explainer"
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
        "description": "Use editorial icon-figures when a person's behavior, decision, reaction, or habit is the story.",
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


def recommend_family(scene: Scene) -> tuple[str, float, str]:
    context = _context(scene)
    character_score = _character_score(scene)
    finance_score = _finance_score(scene)
    explicit_character = [phrase for phrase in STRONG_CHARACTER_PHRASES if phrase in context]
    explicit_finance = [phrase for phrase in STRONG_FINANCE_PHRASES if phrase in context]

    # Explicit system language wins for charts, index funds, compounding, and CTAs
    # unless the scene also contains a stronger human-behavior phrase.
    if explicit_finance and not explicit_character:
        confidence = min(0.97, 0.68 + 0.025 * finance_score)
        return (
            FINANCE_FAMILY_ID,
            round(confidence, 2),
            f"The scene centers on the financial system: {explicit_finance[0]}.",
        )

    if explicit_character or character_score >= max(5, finance_score + 2):
        confidence = min(0.97, 0.62 + 0.025 * max(character_score, 1))
        signal = explicit_character[0] if explicit_character else "multiple behavior signals"
        return (
            CHARACTER_FAMILY_ID,
            round(confidence, 2),
            f"Human behavior is the visual subject: {signal}.",
        )

    confidence = min(0.94, 0.58 + 0.025 * max(finance_score, 1))
    return (
        FINANCE_FAMILY_ID,
        round(confidence, 2),
        "The money flow or financial mechanism is clearer than a character action for this scene.",
    )


def _validate_family(family_id: str | None) -> str:
    resolved = family_id or DEFAULT_FAMILY_ID
    if resolved not in {FINANCE_FAMILY_ID, CHARACTER_FAMILY_ID}:
        raise HTTPException(status_code=422, detail="Unknown exact visual family")
    return resolved


def template_catalog(family_id: str) -> list[dict[str, object]]:
    resolved = _validate_family(family_id)
    return (
        character.template_catalog()
        if resolved == CHARACTER_FAMILY_ID
        else finance.template_catalog()
    )


def suggest_template(
    scene: Scene,
    family_id: str,
):
    resolved = _validate_family(family_id)
    return (
        character.suggest_template(scene)
        if resolved == CHARACTER_FAMILY_ID
        else finance.suggest_template(scene)
    )


def storyboard_beats(
    family_id: str,
    template_id: str,
    duration_seconds: float,
) -> list[dict[str, object]]:
    resolved = _validate_family(family_id)
    return (
        character.storyboard_beats(template_id, duration_seconds)
        if resolved == CHARACTER_FAMILY_ID
        else finance.storyboard_beats(template_id, duration_seconds)
    )


def render_frame(
    family_id: str,
    template_id: str,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    resolved = _validate_family(family_id)
    return (
        character.render_frame(
            template_id,
            duration_seconds,
            time_seconds,
            style_id,
        )
        if resolved == CHARACTER_FAMILY_ID
        else finance.render_frame(
            template_id,
            duration_seconds,
            time_seconds,
            style_id,
        )
    )


def render_exact_visual(
    scene: Scene,
    family_id: str,
    template_id: str | None = None,
    style_id: str | None = None,
):
    resolved = _validate_family(family_id)
    return (
        character.render_character_motion(scene, template_id, style_id)
        if resolved == CHARACTER_FAMILY_ID
        else finance.render_finance_motion(scene, template_id, style_id)
    )


DEFAULT_STYLE_ID = finance.DEFAULT_STYLE_ID
style_catalog = finance.style_catalog
