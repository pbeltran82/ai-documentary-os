from __future__ import annotations

"""Install the general cartoon renderer behind the existing documentary route.

This keeps the public exact-visual API stable while broad documentary scenes gain
beat-aware cartoon compositions. Existing algorithm-specific Tech templates still
render through the established Tech & Behavior engine.
"""

from . import cartoon_documentary as cartoon
from . import exact_visuals as exact

_ORIGINAL_TEMPLATE_CATALOG = exact.template_catalog
_ORIGINAL_TEMPLATE_DEFINITION = exact.template_definition
_ORIGINAL_SUGGEST_TEMPLATE = exact.suggest_template
_ORIGINAL_STORYBOARD_BEATS = exact.storyboard_beats
_ORIGINAL_RENDER_FRAME = exact.render_frame
_ORIGINAL_RENDER_EXACT_VISUAL = exact.render_exact_visual

CARTOON_TEMPLATE_IDS = set(cartoon.TEMPLATE_BY_ID)
GENERAL_DOCUMENTARY_SIGNALS = (
    "mars", "martian", "spacecraft", "evacuation", "relocation", "migration",
    "crowd", "survivor", "community", "family", "governance", "council",
    "habitat", "colony", "robotic", "robots", "life support", "launch",
    "city", "hospital", "school", "factory", "history", "archival",
    "government", "court", "public", "environment", "planet", "journey",
)
ALGORITHM_SPECIFIC_SIGNALS = (
    "algorithm", "digital footprint", "behavioral twin", "recommendation system",
    "ranking", "prediction model", "profile", "scroll", "click", "highest bidder",
)


def _context(scene) -> str:
    return " ".join([scene.narration, scene.visual_intent, *scene.search_keywords]).lower()


def _use_cartoon(scene) -> bool:
    context = _context(scene)
    plan = dict(getattr(scene, "animation_plan", None) or {})
    has_visual_beats = bool(plan.get("visual_beats"))
    general = any(signal in context for signal in GENERAL_DOCUMENTARY_SIGNALS)
    algorithmic = any(signal in context for signal in ALGORITHM_SPECIFIC_SIGNALS)
    return general or (has_visual_beats and not algorithmic)


def template_catalog(family_id: str):
    items = _ORIGINAL_TEMPLATE_CATALOG(family_id)
    if family_id == exact.TECH_FAMILY_ID:
        return [*cartoon.template_catalog(), *items]
    return items


def template_definition(family_id: str, template_id: str):
    if template_id in CARTOON_TEMPLATE_IDS:
        return cartoon.TEMPLATE_BY_ID[template_id]
    return _ORIGINAL_TEMPLATE_DEFINITION(family_id, template_id)


def suggest_template(scene, family_id: str):
    if family_id == exact.TECH_FAMILY_ID and _use_cartoon(scene):
        return cartoon.suggest_template(scene)
    return _ORIGINAL_SUGGEST_TEMPLATE(scene, family_id)


def storyboard_beats(family_id: str, template_id: str, duration_seconds: float):
    if template_id in CARTOON_TEMPLATE_IDS:
        return cartoon.storyboard_beats(template_id, duration_seconds)
    return _ORIGINAL_STORYBOARD_BEATS(family_id, template_id, duration_seconds)


def render_frame(family_id: str, template_id: str, duration_seconds: float, time_seconds: float, style_id: str | None = None):
    if template_id in CARTOON_TEMPLATE_IDS:
        return cartoon.render_frame(template_id, duration_seconds, time_seconds, style_id)
    return _ORIGINAL_RENDER_FRAME(family_id, template_id, duration_seconds, time_seconds, style_id)


def render_exact_visual(scene, family_id: str, template_id: str | None = None, style_id: str | None = None):
    if family_id == exact.TECH_FAMILY_ID and (template_id in CARTOON_TEMPLATE_IDS or _use_cartoon(scene)):
        return cartoon.render_cartoon_documentary(scene, template_id, style_id)
    return _ORIGINAL_RENDER_EXACT_VISUAL(scene, family_id, template_id, style_id)


exact.template_catalog = template_catalog
exact.template_definition = template_definition
exact.suggest_template = suggest_template
exact.storyboard_beats = storyboard_beats
exact.render_frame = render_frame
exact.render_exact_visual = render_exact_visual
