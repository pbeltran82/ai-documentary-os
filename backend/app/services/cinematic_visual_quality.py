from __future__ import annotations

"""Cinematic routing and slide-likeness guard for exact documentary visuals.

This module changes only visual template selection. It deliberately leaves scene
narration, timestamps, duration, audio, captions, persistence, and rendering
contracts untouched.
"""

from dataclasses import dataclass
from typing import Iterable

from . import tech_behavior_route_patch as route


LAYOUT_BY_TEMPLATE: dict[str, str] = {
    "algorithm_chose_you": "interface_closeup",
    "behavior_prediction_engine": "process_diagram",
    "life_event_timeline": "comparison_scene",
    "digital_footprint_collector": "environment_scene",
    "behavioral_twin": "editorial_hero",
    "machine_choice_explainer": "interface_closeup",
    "attention_auction": "symbolic_metaphor",
    "signal_feedback_loop": "process_diagram",
    "profile_forecast": "editorial_hero",
    "consequence_map": "environment_scene",
    "machine_choice_cta": "editorial_hero",
}

PROCESS_DIAGRAM = "process_diagram"
MAX_CONSECUTIVE_LAYOUTS = 2
SLIDE_THRESHOLD = 0.58

# Deterministic editorial fallbacks. The order is intentional and stable so the
# same project state always produces the same visual plan.
EDITORIAL_FALLBACKS = (
    "editorial_hero",
    "environment_scene",
    "interface_closeup",
    "symbolic_metaphor",
    "comparison_scene",
)


@dataclass(frozen=True)
class SlideQualitySignals:
    text_density: float = 0.0
    empty_space_ratio: float = 0.0
    centered_symmetry: float = 0.0
    repeated_layout: float = 0.0
    subject_presence: float = 1.0
    depth_layering: float = 1.0
    motion_richness: float = 1.0


@dataclass(frozen=True)
class SlideQualityResult:
    score: float
    rejected: bool
    reasons: tuple[str, ...]


def layout_family(template_id: str) -> str:
    return LAYOUT_BY_TEMPLATE.get(template_id, "editorial_hero")


def shorten_headline(value: str, *, max_words: int = 7, max_characters: int = 54) -> str:
    """Return compact display copy without mutating the underlying narration."""
    words = " ".join(str(value).strip().split()).split(" ") if str(value).strip() else []
    shortened = " ".join(words[:max_words])
    if len(shortened) <= max_characters:
        return shortened
    return shortened[:max_characters].rsplit(" ", 1)[0].rstrip(" ,.;:-")


def slide_likeness(signals: SlideQualitySignals) -> SlideQualityResult:
    components = {
        "too much text": signals.text_density * 0.24,
        "excess empty space": signals.empty_space_ratio * 0.18,
        "centered slide symmetry": signals.centered_symmetry * 0.14,
        "repeated layout": signals.repeated_layout * 0.16,
        "weak subject presence": (1.0 - signals.subject_presence) * 0.12,
        "insufficient depth": (1.0 - signals.depth_layering) * 0.08,
        "limited motion": (1.0 - signals.motion_richness) * 0.08,
    }
    score = round(max(0.0, min(1.0, sum(components.values()))), 3)
    reasons = tuple(name for name, value in components.items() if value >= 0.075)
    return SlideQualityResult(score=score, rejected=score >= SLIDE_THRESHOLD, reasons=reasons)


def _recent_layouts(prior_template_ids: Iterable[str]) -> list[str]:
    return [layout_family(template_id) for template_id in prior_template_ids]


def _would_create_third_consecutive(layout: str, prior_template_ids: list[str]) -> bool:
    recent = _recent_layouts(prior_template_ids)[-MAX_CONSECUTIVE_LAYOUTS:]
    return len(recent) == MAX_CONSECUTIVE_LAYOUTS and all(item == layout for item in recent)


def _diagram_is_overrepresented(candidate_layout: str, prior_template_ids: list[str]) -> bool:
    layouts = _recent_layouts(prior_template_ids)
    if candidate_layout != PROCESS_DIAGRAM or len(layouts) < 2:
        return False
    projected = layouts + [candidate_layout]
    return projected.count(PROCESS_DIAGRAM) * 2 >= len(projected)


def choose_cinematic_template(
    scored_templates: list[tuple[int, object]],
    prior_template_ids: list[str],
) -> tuple[int, object]:
    """Choose the highest semantic result that also passes sequence quality gates."""
    if not scored_templates:
        raise ValueError("At least one scored visual template is required")

    eligible: list[tuple[int, object]] = []
    for score, template in scored_templates:
        template_id = str(getattr(template, "template_id"))
        layout = layout_family(template_id)
        adjusted = int(score)
        if _would_create_third_consecutive(layout, prior_template_ids):
            adjusted -= 20_000
        if _diagram_is_overrepresented(layout, prior_template_ids):
            adjusted -= 4_000
        # Repeated centered/process compositions are treated as more slide-like.
        if layout == PROCESS_DIAGRAM and layout in _recent_layouts(prior_template_ids)[-2:]:
            adjusted -= 1_200
        eligible.append((adjusted, template))

    eligible.sort(
        key=lambda item: (item[0], str(getattr(item[1], "template_id"))),
        reverse=True,
    )
    return eligible[0]


_ORIGINAL_SCORE_WITH_PRIOR = route._score_templates_with_prior
_ORIGINAL_SUGGEST_TEMPLATE = route.suggest_template


def _cinematic_score_templates_with_prior(scene: object, prior: list[str]):
    scored = _ORIGINAL_SCORE_WITH_PRIOR(scene, prior)
    chosen_score, chosen = choose_cinematic_template(scored, prior)
    # Preserve the complete ranked list/API shape while guaranteeing that the
    # quality-gated choice is first.
    return [(chosen_score + 50_000, chosen)] + [
        (score, template)
        for score, template in scored
        if template.template_id != chosen.template_id
    ]


def _cinematic_suggest_template(scene: object):
    prior = route.prior_template_ids(scene)
    selected_score, selected = _cinematic_score_templates_with_prior(scene, prior)[0]
    original, confidence, reason = _ORIGINAL_SUGGEST_TEMPLATE(scene)
    if selected.template_id == original.template_id:
        return original, confidence, reason
    return (
        selected,
        min(0.91, max(0.66, confidence)),
        f"Rerouted to {layout_family(selected.template_id)} to prevent a slide-like or repeated visual sequence.",
    )


route._score_templates_with_prior = _cinematic_score_templates_with_prior
route.score_templates = lambda scene: _cinematic_score_templates_with_prior(
    scene, route.prior_template_ids(scene)
)
route.suggest_template = _cinematic_suggest_template
route.base.score_templates = route.score_templates
route.base.suggest_template = _cinematic_suggest_template
