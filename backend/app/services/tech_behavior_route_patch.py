from __future__ import annotations

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


def _context(scene: Scene) -> str:
    return " ".join(
        [scene.narration, scene.visual_intent, *scene.search_keywords]
    ).lower()


def _decisive_match(scene: Scene) -> tuple[str, str] | None:
    context = _context(scene)
    for template_id, phrases in DECISIVE_ROUTES:
        for phrase in phrases:
            if phrase in context:
                return template_id, phrase
    return None


def score_templates(scene: Scene) -> list[tuple[int, base.TechTemplate]]:
    scored = truthful.score_templates(scene)
    decisive = _decisive_match(scene)
    if decisive is None:
        return scored
    template_id, _phrase = decisive
    boosted = [
        (score + 1000 if template.template_id == template_id else score, template)
        for score, template in scored
    ]
    boosted.sort(key=lambda pair: (pair[0], pair[1].template_id), reverse=True)
    return boosted


def suggest_template(scene: Scene) -> tuple[base.TechTemplate, float, str]:
    decisive = _decisive_match(scene)
    if decisive is not None:
        template_id, phrase = decisive
        return (
            base.TEMPLATE_BY_ID[template_id],
            0.97,
            f'Decisive scene phrase: “{phrase}”.',
        )
    return truthful.suggest_template(scene)


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
