from __future__ import annotations

"""Final editorial pass for PR #40.

This module intentionally changes only two things:

1. project-level Tech & Behavior template variety, and
2. the terminal Shorts thesis/CTA layout.

Everything else in the approved visual-polish layer remains untouched.
"""

from collections import Counter

from PIL import Image, ImageDraw

from . import documentary_visual_polish as polish
from . import tech_behavior_route_patch as route


# Strongly discourage the three concepts that were visibly repeating in the
# reviewed Short. They remain available when narration makes them necessary,
# but unused visual ideas win before a repeated one does.
_REPEAT_SENSITIVE = {
    "digital_footprint_collector",
    "machine_choice_explainer",
    "algorithm_chose_you",
    "behavioral_twin",
}

PROJECT_REUSE_LIMIT = 1
PRIOR_USE_PENALTY = 70
RECENT_USE_PENALTY = 320
IMMEDIATE_REPEAT_PENALTY = 900
PROJECT_OVERUSE_PENALTY = 1_600
SENSITIVE_REPEAT_PENALTY = 1_050
SEMANTIC_GROUP_REPEAT_PENALTY = 520
RECENT_WINDOW = 5


def _score_templates_with_prior(
    scene: object,
    prior: list[str],
) -> list[tuple[int, route.base.TechTemplate]]:
    """Prefer a complete set of distinct visual ideas before any reuse."""
    scored = route.truthful.score_templates(scene)
    decisive = route._decisive_match(scene)
    decisive_template_id = decisive[0] if decisive is not None else None
    raw_template_id = route._raw_template_id(scene)
    variant_group = next(
        (
            members
            for members in route.SEMANTIC_VARIANT_GROUPS.values()
            if raw_template_id in members
        ),
        None,
    )

    counts = Counter(prior)
    recent = set(prior[-RECENT_WINDOW:])
    all_non_cta = {
        template.template_id
        for _score, template in scored
        if template.template_id != route.CTA_TEMPLATE_ID
    }
    unused_project_templates = {
        template_id for template_id in all_non_cta if counts[template_id] == 0
    }
    unused_group_templates = (
        {template_id for template_id in variant_group if counts[template_id] == 0}
        if variant_group is not None
        else set()
    )

    adjusted: list[tuple[int, route.base.TechTemplate]] = []
    for score, template in scored:
        template_id = template.template_id
        value = score

        if template_id == decisive_template_id:
            value += route.DECISIVE_BOOST
        if (
            decisive_template_id == route.CTA_TEMPLATE_ID
            and not route.is_terminal_scene(scene)
            and template_id == route.EARLY_CTA_FALLBACK_TEMPLATE_ID
        ):
            value += route.EARLY_CTA_FALLBACK_BOOST

        if template_id == route.CTA_TEMPLATE_ID and not route.is_terminal_scene(scene):
            value -= 10_000
        elif template_id == route.CTA_TEMPLATE_ID and decisive_template_id != route.CTA_TEMPLATE_ID:
            value -= 12

        # Stay semantically close when an unused option exists inside the same
        # visual family, but do not force a repeat after that family is exhausted.
        if variant_group is not None and template_id not in variant_group and unused_group_templates:
            value -= 95

        use_count = counts[template_id]
        value -= use_count * PRIOR_USE_PENALTY

        if use_count >= PROJECT_REUSE_LIMIT and unused_project_templates:
            value -= PROJECT_OVERUSE_PENALTY
        if template_id in _REPEAT_SENSITIVE and use_count:
            value -= SENSITIVE_REPEAT_PENALTY * use_count
        if template_id in recent:
            value -= RECENT_USE_PENALTY
        if prior and template_id == prior[-1]:
            value -= IMMEDIATE_REPEAT_PENALTY

        # Ranking and behavioral-signal scenes can look repetitive even when
        # their exact template IDs differ, so penalize recently used semantic
        # siblings as well as exact duplicates.
        for members in route.SEMANTIC_VARIANT_GROUPS.values():
            if template_id in members and any(item in members for item in prior[-3:]):
                value -= SEMANTIC_GROUP_REPEAT_PENALTY
                break

        adjusted.append((value, template))

    adjusted.sort(key=lambda pair: (pair[0], pair[1].template_id), reverse=True)
    return adjusted


def _blend(
    muted: tuple[int, int, int],
    vivid: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(round(a + (b - a) * amount) for a, b in zip(muted, vivid, strict=True))


def _clean_story_cta(canvas: Image.Image, progress: float) -> None:
    """Give the thesis its own quiet field before engagement controls appear."""
    shorts = polish.shorts
    draw = ImageDraw.Draw(canvas)

    thesis_reveal = shorts._phase(progress, 0.02, 0.24)
    cta_reveal = shorts._phase(progress, 0.48, 0.74)

    # Cover the lower ranking/funnel graphics so the conclusion never competes
    # with a green score chip or other underlying renderer detail.
    panel = (48, 1080, 1032, 1665)
    draw.rounded_rectangle(
        panel,
        radius=42,
        fill=(5, 12, 24),
        outline=(27, 48, 74),
        width=3,
    )

    label_color = _blend((55, 68, 89), shorts.CYAN, thesis_reveal)
    thesis_color = _blend((66, 76, 94), shorts.WHITE, thesis_reveal)
    support_color = _blend((50, 61, 78), shorts.MUTED, thesis_reveal)

    shorts._text(draw, (shorts.SAFE_LEFT, 1135), "THE FINAL IDEA", 21, label_color, bold=True)
    shorts._text(
        draw,
        (shorts.SAFE_LEFT, 1190),
        "YOUR ACTIONS BECOME PREDICTIONS.",
        39,
        thesis_color,
        bold=True,
    )
    shorts._text(
        draw,
        (shorts.SAFE_LEFT, 1260),
        "THOSE PREDICTIONS SHAPE",
        27,
        support_color,
        bold=True,
    )
    shorts._text(
        draw,
        (shorts.SAFE_LEFT, 1302),
        "WHAT REACHES YOU NEXT.",
        27,
        support_color,
        bold=True,
    )

    if cta_reveal <= 0.01:
        shorts._text(
            draw,
            (shorts.SAFE_LEFT, 1515),
            "AI DOCUMENTARY OS",
            19,
            (78, 91, 112),
            bold=True,
        )
        return

    red = _blend((46, 31, 42), shorts.RED, cta_reveal)
    blue = _blend((24, 42, 66), shorts.BLUE, cta_reveal)
    button_text = _blend((92, 100, 115), shorts.WHITE, cta_reveal)
    y = 1435

    draw.rounded_rectangle((shorts.SAFE_LEFT, y, 650, y + 92), radius=22, fill=red)
    draw.polygon(((118, y + 26), (118, y + 66), (151, y + 46)), fill=button_text)
    shorts._text(draw, (390, y + 46), "SUBSCRIBE", 36, button_text, bold=True, anchor="mm")

    draw.rounded_rectangle((680, y, shorts.SAFE_RIGHT, y + 92), radius=46, fill=blue)
    shorts._text(draw, (845, y + 46), "LIKE  👍", 32, button_text, bold=True, anchor="mm")
    shorts._text(
        draw,
        (shorts.SAFE_LEFT, 1585),
        "KEEP QUESTIONING THE SYSTEM",
        22,
        _blend((52, 62, 78), (122, 138, 162), cta_reveal),
        bold=True,
    )


def install_final_pass() -> None:
    """Install the narrowly scoped routing and CTA fixes."""
    route.PROJECT_REUSE_LIMIT = PROJECT_REUSE_LIMIT
    route.PRIOR_USE_PENALTY = PRIOR_USE_PENALTY
    route.RECENT_USE_PENALTY = RECENT_USE_PENALTY
    route.IMMEDIATE_REPEAT_PENALTY = IMMEDIATE_REPEAT_PENALTY
    route.PROJECT_OVERUSE_PENALTY = PROJECT_OVERUSE_PENALTY
    route._score_templates_with_prior = _score_templates_with_prior
    polish._story_cta = _clean_story_cta


install_final_pass()
