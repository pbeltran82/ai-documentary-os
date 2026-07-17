from __future__ import annotations

from collections import Counter

from sqlalchemy.orm.exc import DetachedInstanceError

from ..models import Scene
from . import tech_behavior_motion as base
from . import tech_behavior_truthful as truthful


DECISIVE_ROUTES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "behavioral_twin",
        (
            "systems that learn how to navigate us",
            "learn how to navigate us",
            "behavioral version of you",
            "behavioral twin",
            "digital twin",
        ),
    ),
    (
        "life_event_timeline",
        (
            "life records",
            "six million people",
            "early mortality",
            "personality traits",
        ),
    ),
    (
        "behavior_prediction_engine",
        (
            "predicts behavior",
            "predict human behavior",
            "predicting human behavior",
            "predictive behavioral modeling",
            "prediction engine",
        ),
    ),
    (
        "machine_choice_cta",
        (
            "did you choose",
            "machine choose the moment",
            "help us navigate the world",
            "subscribe if you're still awake",
            "subscribe if you’re still awake",
        ),
    ),
    (
        "algorithm_chose_you",
        (
            "exact video would reach you",
            "what reaches you",
            "most likely to change your behavior",
        ),
    ),
    (
        "digital_footprint_collector",
        (
            "every scroll",
            "every pause",
            "every click",
            "abandoned draft",
            "digital footprint",
        ),
    ),
)

TECH_FAMILY_ID = "tech_behavior_motion"
CTA_TEMPLATE_ID = "machine_choice_cta"
DECISIVE_BOOST = 48
PRIOR_USE_PENALTY = 10
RECENT_USE_PENALTY = 85
IMMEDIATE_REPEAT_PENALTY = 90
PROJECT_REUSE_LIMIT = 2
PROJECT_OVERUSE_PENALTY = 240
EARLY_CTA_FALLBACK_TEMPLATE_ID = "machine_choice_explainer"
EARLY_CTA_FALLBACK_BOOST = 36
SEMANTIC_VARIANT_GROUPS = {
    "ranking": {"algorithm_chose_you", "machine_choice_explainer"},
    "behavioral_signals": {
        "behavior_prediction_engine",
        "digital_footprint_collector",
        "behavioral_twin",
    },
}
OUTSIDE_VARIANT_GROUP_PENALTY = 160


def _context(scene: Scene) -> str:
    return " ".join(
        [scene.narration, scene.visual_intent, *scene.search_keywords]
    ).lower()


def _project_scenes(scene: Scene) -> list[Scene]:
    project = getattr(scene, "project", None)
    if project is None:
        return [scene]
    try:
        scenes = list(project.scenes)
    except DetachedInstanceError:
        return [scene]
    if not scenes:
        return [scene]
    return sorted(scenes, key=lambda item: item.scene_number)


def is_terminal_scene(scene: Scene) -> bool:
    scenes = _project_scenes(scene)
    return scene.scene_number >= max(item.scene_number for item in scenes)


def _persisted_template_id(scene: Scene) -> str | None:
    try:
        asset = getattr(scene, "selected_asset", None)
    except DetachedInstanceError:
        return None
    if asset is None or str(getattr(asset, "provider", "")).lower() != "generated":
        return None

    source_url = str(getattr(asset, "source_url", ""))
    prefix = f"local://exact-visual/{TECH_FAMILY_ID}/"
    if source_url.startswith(prefix):
        template_id = source_url[len(prefix):].split("/", 1)[0]
        if template_id in base.TEMPLATE_BY_ID:
            return template_id

    provider_asset_id = str(getattr(asset, "provider_asset_id", ""))
    for template_id in base.TEMPLATE_BY_ID:
        if template_id in provider_asset_id:
            return template_id
    return None


def _decisive_match(scene: Scene) -> tuple[str, str] | None:
    context = _context(scene)
    for template_id, phrases in DECISIVE_ROUTES:
        for phrase in phrases:
            if phrase in context:
                return template_id, phrase
    return None


def _raw_template_id(scene: Scene) -> str:
    decisive = _decisive_match(scene)
    if decisive is not None:
        template_id, _phrase = decisive
        if template_id == CTA_TEMPLATE_ID and not is_terminal_scene(scene):
            return EARLY_CTA_FALLBACK_TEMPLATE_ID
        if template_id != CTA_TEMPLATE_ID or is_terminal_scene(scene):
            return template_id

    for _score, template in truthful.score_templates(scene):
        if template.template_id != CTA_TEMPLATE_ID or is_terminal_scene(scene):
            return template.template_id
    return "algorithm_chose_you"


def prior_template_ids(scene: Scene) -> list[str]:
    prior: list[str] = []
    for candidate in _project_scenes(scene):
        if candidate.scene_number >= scene.scene_number:
            break
        persisted = _persisted_template_id(candidate)
        if persisted is not None:
            prior.append(persisted)
            continue
        planned = _score_templates_with_prior(candidate, prior)[0][1]
        prior.append(planned.template_id)
    return prior


def _score_templates_with_prior(
    scene: Scene,
    prior: list[str],
) -> list[tuple[int, base.TechTemplate]]:
    scored = truthful.score_templates(scene)
    decisive = _decisive_match(scene)
    decisive_template_id = decisive[0] if decisive is not None else None
    raw_template_id = _raw_template_id(scene)
    variant_group = next(
        (
            members
            for members in SEMANTIC_VARIANT_GROUPS.values()
            if raw_template_id in members
        ),
        None,
    )
    counts = Counter(prior)
    recent = set(prior[-3:])
    diversity_pool = variant_group or {
        template.template_id
        for _score, template in scored
        if template.template_id != CTA_TEMPLATE_ID
    }
    underused_variant_available = any(
        counts[template_id] < PROJECT_REUSE_LIMIT
        for template_id in diversity_pool
    )
    adjusted: list[tuple[int, base.TechTemplate]] = []
    for score, template in scored:
        template_id = template.template_id
        value = score
        if template_id == decisive_template_id:
            value += DECISIVE_BOOST
        if (
            decisive_template_id == CTA_TEMPLATE_ID
            and not is_terminal_scene(scene)
            and template_id == EARLY_CTA_FALLBACK_TEMPLATE_ID
        ):
            value += EARLY_CTA_FALLBACK_BOOST
        if template_id == CTA_TEMPLATE_ID and not is_terminal_scene(scene):
            value -= 10_000
        elif template_id == CTA_TEMPLATE_ID and decisive_template_id != CTA_TEMPLATE_ID:
            value -= 12
        if variant_group is not None and template_id not in variant_group:
            value -= OUTSIDE_VARIANT_GROUP_PENALTY
        value -= counts[template_id] * PRIOR_USE_PENALTY
        if (
            template_id in diversity_pool
            and counts[template_id] >= PROJECT_REUSE_LIMIT
            and underused_variant_available
        ):
            value -= PROJECT_OVERUSE_PENALTY
        if template_id in recent:
            value -= RECENT_USE_PENALTY
        if prior and template_id == prior[-1]:
            value -= IMMEDIATE_REPEAT_PENALTY
        adjusted.append((value, template))
    adjusted.sort(key=lambda pair: (pair[0], pair[1].template_id), reverse=True)
    return adjusted


def score_templates(scene: Scene) -> list[tuple[int, base.TechTemplate]]:
    return _score_templates_with_prior(scene, prior_template_ids(scene))


def suggest_template(scene: Scene) -> tuple[base.TechTemplate, float, str]:
    selected_score, selected = score_templates(scene)[0]
    raw_template_id = _raw_template_id(scene)
    decisive = _decisive_match(scene)
    if selected.template_id != raw_template_id:
        return (
            selected,
            0.82,
            f"Selected {selected.label} to avoid repeating "
            f"{base.TEMPLATE_BY_ID[raw_template_id].label} in the recent project sequence.",
        )
    if decisive is not None and (
        decisive[0] != CTA_TEMPLATE_ID or is_terminal_scene(scene)
    ):
        template_id, phrase = decisive
        return (
            base.TEMPLATE_BY_ID[template_id],
            0.97,
            f'Decisive scene phrase: “{phrase}”.',
        )
    template, confidence, reason = truthful.suggest_template(scene)
    if template.template_id == selected.template_id:
        return template, confidence, reason
    confidence = min(0.92, max(0.58, 0.58 + max(0, selected_score) * 0.025))
    return selected, round(confidence, 2), "Balanced semantic fit with project-level visual variety."


base.score_templates = score_templates
base.suggest_template = suggest_template

DEFAULT_STYLE_ID = truthful.DEFAULT_STYLE_ID
STYLES = truthful.STYLES
TEMPLATES = truthful.TEMPLATES
TEMPLATE_BY_ID = truthful.TEMPLATE_BY_ID
OUTPUT_WIDTH = truthful.OUTPUT_WIDTH
OUTPUT_HEIGHT = truthful.OUTPUT_HEIGHT
OUTPUT_FPS = truthful.OUTPUT_FPS
ffmpeg_encoder_command = truthful.ffmpeg_encoder_command
style_catalog = truthful.style_catalog
template_catalog = truthful.template_catalog
storyboard_beats = truthful.storyboard_beats
prediction_confidence_state = truthful.prediction_confidence_state
render_frame = truthful.render_frame
render_tech_motion = truthful.render_tech_motion
