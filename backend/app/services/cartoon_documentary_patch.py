from __future__ import annotations

"""Install the general cartoon renderer behind the existing documentary route.

This keeps the public exact-visual API stable while broad documentary scenes gain
beat-aware cartoon compositions. Existing algorithm-specific Tech templates still
render through the established Tech & Behavior engine.
"""

from types import SimpleNamespace

from . import cartoon_documentary as cartoon
from . import exact_visuals as exact
from . import native_shorts

_ORIGINAL_RECOMMEND_FAMILY = exact.recommend_family
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
    "algorithm", "artificial intelligence", "digital footprint", "digital twin",
    "behavioral twin", "recommendation system", "ranking", "prediction model",
    "predicting human behavior", "profile", "every scroll", "every pause",
    "deleted draft", "machine choose", "systems that learn how to navigate us",
    "scroll", "click", "highest bidder",
)


def _context(scene) -> str:
    return " ".join([scene.narration, scene.visual_intent, *scene.search_keywords]).lower()


def _algorithm_signal(scene) -> str | None:
    context = _context(scene)
    return next((signal for signal in ALGORITHM_SPECIFIC_SIGNALS if signal in context), None)


def _use_cartoon(scene) -> bool:
    context = _context(scene)
    plan = dict(getattr(scene, "animation_plan", None) or {})
    has_visual_beats = bool(plan.get("visual_beats"))
    general = any(signal in context for signal in GENERAL_DOCUMENTARY_SIGNALS)
    algorithmic = _algorithm_signal(scene) is not None
    return general or (has_visual_beats and not algorithmic)


def _preview_frame(template_id: str, duration_seconds: float, time_seconds: float, style_id: str | None = None):
    template = cartoon.TEMPLATE_BY_ID[template_id]
    scene = SimpleNamespace(
        narration=template.description,
        visual_intent=template.description,
        search_keywords=list(template.keywords),
        scene_number=1,
        animation_plan={},
        duration_seconds=duration_seconds,
    )
    return cartoon.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)


def _attach_style_metadata(generated, style_id: str | None):
    """Keep generated-motion metadata compatible with the exact-visual router."""
    if hasattr(generated, "style"):
        return generated
    resolved_style_id = style_id or exact.DEFAULT_STYLE_ID
    styles = {
        str(item["style_id"]): item
        for item in exact.style_catalog()
    }
    style = styles.get(
        resolved_style_id,
        {"style_id": resolved_style_id, "label": resolved_style_id},
    )
    object.__setattr__(
        generated,
        "style",
        SimpleNamespace(
            style_id=str(style["style_id"]),
            label=str(style["label"]),
        ),
    )
    return generated


def recommend_family(scene):
    family_id, confidence, reason = _ORIGINAL_RECOMMEND_FAMILY(scene)
    signal = _algorithm_signal(scene)
    if family_id == exact.TECH_FAMILY_ID and signal:
        return family_id, confidence, f"The scene centers on algorithmic behavior: {signal}."
    return family_id, confidence, reason


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
        return _preview_frame(template_id, duration_seconds, time_seconds, style_id)
    return _ORIGINAL_RENDER_FRAME(family_id, template_id, duration_seconds, time_seconds, style_id)


def render_exact_visual(scene, family_id: str, template_id: str | None = None, style_id: str | None = None):
    if family_id == exact.TECH_FAMILY_ID and (template_id in CARTOON_TEMPLATE_IDS or _use_cartoon(scene)):
        generated = cartoon.render_cartoon_documentary(scene, template_id, style_id)
    else:
        generated = _ORIGINAL_RENDER_EXACT_VISUAL(scene, family_id, template_id, style_id)
    return _attach_style_metadata(generated, style_id)


# Every exposed cartoon template has a native semantic Shorts composition and an
# explicit native renderer. The current v1 uses the established single-hero
# documentary renderer in 9:16 rather than cropping or reusing landscape pixels.
for template in cartoon.TEMPLATES:
    key = (exact.TECH_FAMILY_ID, template.template_id)
    native_shorts.COMPOSITIONS.setdefault(
        key,
        native_shorts.ShortsComposition(template.title),
    )
    native_shorts.RENDERERS.setdefault(key, native_shorts._generic)

cartoon.render_frame = _preview_frame
exact.recommend_family = recommend_family
exact.template_catalog = template_catalog
exact.template_definition = template_definition
exact.suggest_template = suggest_template
exact.storyboard_beats = storyboard_beats
exact.render_frame = render_frame
exact.render_exact_visual = render_exact_visual
