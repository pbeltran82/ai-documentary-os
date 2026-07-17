from __future__ import annotations

"""Routing guards for the expanded Tech & Behavior composition family."""

from . import tech_behavior_route_patch as route


_ORIGINAL_DECISIVE_MATCH = route._decisive_match
_ORIGINAL_SCORE_WITH_PRIOR = route._score_templates_with_prior
_ORIGINAL_SUGGEST_TEMPLATE = route.suggest_template

_NEW_DECISIVE_ROUTES = (
    (
        "attention_auction",
        (
            "highest bidder",
            "compete for your attention",
            "attention market",
        ),
    ),
    (
        "signal_feedback_loop",
        (
            "feedback loop",
            "next signal",
            "output becomes the next input",
        ),
    ),
    (
        "profile_forecast",
        (
            "profile becomes a forecast",
            "profile becomes a prediction",
            "forecast of future events",
        ),
    ),
    (
        "consequence_map",
        (
            "shapes what reaches you",
            "ranking shapes what",
            "changes the path in front of you",
            "next path in front of you",
            "shapes the next choice",
        ),
    ),
)


def _expanded_decisive_match(scene: object) -> tuple[str, str] | None:
    context = route._context(scene)
    for template_id, phrases in _NEW_DECISIVE_ROUTES:
        for phrase in phrases:
            if phrase in context:
                return template_id, phrase
    return _ORIGINAL_DECISIVE_MATCH(scene)


def _guarded_score_templates_with_prior(scene: object, prior: list[str]):
    scored = _ORIGINAL_SCORE_WITH_PRIOR(scene, prior)
    decisive = _expanded_decisive_match(scene)
    decisive_id = decisive[0] if decisive is not None else None
    guarded = [
        (
            score - 10_000
            if template.template_id == route.CTA_TEMPLATE_ID
            and decisive_id != route.CTA_TEMPLATE_ID
            else score,
            template,
        )
        for score, template in scored
    ]
    guarded.sort(key=lambda pair: (pair[0], pair[1].template_id), reverse=True)
    return guarded


def _guarded_suggest_template(scene: object):
    template, confidence, reason = _ORIGINAL_SUGGEST_TEMPLATE(scene)
    decisive = _expanded_decisive_match(scene)
    decisive_id = decisive[0] if decisive is not None else None
    if template.template_id != route.CTA_TEMPLATE_ID or decisive_id == route.CTA_TEMPLATE_ID:
        return template, confidence, reason

    selected_score, selected = _guarded_score_templates_with_prior(
        scene,
        route.prior_template_ids(scene),
    )[0]
    resolved_confidence = min(0.92, max(0.58, 0.58 + max(0, selected_score) * 0.025))
    return (
        selected,
        round(resolved_confidence, 2),
        "Selected a non-terminal composition; engagement CTA is reserved for explicit closing narration.",
    )


route._decisive_match = _expanded_decisive_match
route._score_templates_with_prior = _guarded_score_templates_with_prior
route.suggest_template = _guarded_suggest_template
route.base.suggest_template = _guarded_suggest_template

# Install only after the routing and renderer registries are fully initialized.
from . import documentary_cross_format_polish as _documentary_cross_format_polish  # noqa: E402,F401
