from __future__ import annotations

from .cinematic_renderer import (
    CINEMATIC_RENDERERS,
    cinematic_beat_indicator,
    cinematic_common,
)
from .types import VisualFamily
from .visual_pipeline import build_scene_visual_plan

_INSTALLED = False


def _template_for_plan(plan) -> str:
    family = plan.strategy.family
    intent = plan.intent
    if family == VisualFamily.CONCLUSION_CTA:
        return "machine_choice_cta"
    if family == VisualFamily.COMPARISON_CONTRAST:
        return "machine_choice_explainer"
    if family == VisualFamily.TIMELINE_HISTORICAL:
        return "life_event_timeline"
    if family == VisualFamily.INTERFACE_OBSERVATIONAL:
        if {"scroll", "click", "search", "digital"} & set(intent.action_terms + intent.concept_terms):
            return "digital_footprint_collector"
        return "algorithm_chose_you"
    if family == VisualFamily.DATA_EXPLAINER:
        return "behavior_prediction_engine"
    if family == VisualFamily.CINEMATIC_REAL_WORLD:
        return "digital_footprint_collector" if intent.interface_score else "behavioral_twin"
    return "behavioral_twin"


def _architectural_suggest_template(scene):
    from .. import tech_behavior_motion as tech

    plan = build_scene_visual_plan(scene)
    template_id = _template_for_plan(plan)
    template = tech.TEMPLATE_BY_ID[template_id]
    confidence = 0.9 if plan.intent.human_score + plan.intent.interface_score + plan.intent.data_score >= 2 else 0.78
    reason = (
        f"Visual Architecture selected {plan.strategy.family.value}; "
        f"{plan.strategy.reason} Shot: {plan.shot.shot_type.value}, "
        f"{plan.shot.composition.value}, {plan.shot.camera_move.value}."
    )
    return template, confidence, reason


def install_visual_architecture() -> None:
    """Install one global visual system for every current and future project.

    The registration is idempotent and replaces topic-specific presentation
    layouts with the shared cinematic renderer family. It does not wrap render
    functions, so development reloads cannot create recursive call chains.
    """
    global _INSTALLED
    from .. import tech_behavior_motion as tech

    tech.RENDERERS.update(CINEMATIC_RENDERERS)
    tech._common = cinematic_common
    tech._beat_indicator = cinematic_beat_indicator
    tech.suggest_template = _architectural_suggest_template
    _INSTALLED = True


def visual_architecture_installed() -> bool:
    return _INSTALLED
