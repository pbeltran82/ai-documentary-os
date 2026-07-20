from __future__ import annotations

"""Cinematic anti-slide pass for the remaining weak 16:9 Tech & Behavior scenes.

Only drawing registries are changed. Story text, narration, timing, audio, captions,
project data, API contracts, timeline assembly, and FFmpeg behavior are untouched.
"""

import math

from PIL import ImageDraw

from . import documentary_variety_expansion as expansion
from . import tech_behavior_motion as base
from . import tech_behavior_truthful as truthful


UPGRADED_TEMPLATES = (
    "attention_auction",
    "life_event_timeline",
    "machine_choice_explainer",
)


def _depth_field(
    draw: ImageDraw.ImageDraw,
    palette: dict[str, tuple[int, int, int]],
    progress: float,
    *,
    horizon_y: int = 690,
) -> None:
    """Create deterministic depth without a bordered presentation panel."""
    drift = round(26 * math.sin(progress * math.pi * 2))
    draw.ellipse((-260 + drift, 250, 910 + drift, 1130), fill=palette["panel"])
    draw.ellipse((1180 - drift, 150, 2210 - drift, 980), fill=palette["panel_alt"])
    draw.polygon(
        ((0, horizon_y), (420, horizon_y - 115), (1050, horizon_y + 95), (1920, horizon_y - 70), (1920, 1080), (0, 1080)),
        fill=(4, 8, 18),
    )
    for index in range(7):
        x = 150 + index * 285 + drift // 2
        height = 65 + (index % 3) * 35
        draw.rounded_rectangle(
            (x, horizon_y - height, x + 120, horizon_y + 220),
            radius=18,
            fill=palette["panel_alt"],
        )


def _attention_auction(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    """Stage attention as a physical auction instead of a score dashboard."""
    q = base._phase(progress, 0.04, 0.92)
    _depth_field(draw, palette, progress, horizon_y=735)

    draw.ellipse((835, 360, 1055, 580), fill=palette["muted"])
    draw.rounded_rectangle((790, 555, 1100, 1015), radius=105, fill=palette["panel"])
    draw.ellipse((760, 960, 1130, 1085), fill=(2, 5, 13))

    bidders = (
        (250, 455, "NEWS", 0.62, palette["accent_alt"]),
        (470, 680, "SHOP", 0.71, palette["warning"]),
        (1430, 430, "SOCIAL", 0.79, palette["accent"]),
        (1580, 720, "VIDEO", 0.88, palette["good"]),
    )
    target = (950, 620)
    for index, (x, y, label, score, color) in enumerate(bidders):
        local = base._phase(q, index * 0.11, min(1.0, index * 0.11 + 0.48))
        radius = 58 + round(24 * local)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
        if local > 0.08:
            draw.line((x, y, *target), fill=color, width=4 + index)
        base.engine._text(draw, (x, y + radius + 38), label, 21, palette["white"], bold=True, anchor="mm")
        if local > 0.38:
            base.engine._text(draw, (x, y), str(round(score * local * 100)), 28, palette["ink"], bold=True, anchor="mm")

    if q > 0.68:
        draw.arc((1325, 555, 1835, 965), 200, 340, fill=palette["good"], width=18)
        base.engine._text(draw, (1590, 930), "WINS THE NEXT MOMENT", 26, palette["good"], bold=True, anchor="mm")


def _life_event_timeline(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    """Turn the timeline into a traveled landscape rather than a chart card."""
    q = base._phase(progress, 0.04, 0.92)
    _depth_field(draw, palette, progress, horizon_y=690)

    draw.polygon(((690, 1080), (875, 530), (1035, 530), (1325, 1080)), fill=palette["panel"])
    draw.line((875, 530, 690, 1080), fill=palette["accent_alt"], width=7)
    draw.line((1035, 530, 1325, 1080), fill=palette["accent_alt"], width=7)

    milestones = (
        (770, 925, "RECORDS", palette["accent_alt"]),
        (875, 760, "JOB", palette["accent"]),
        (1000, 650, "HEALTH", palette["warning"]),
        (1125, 585, "MORTALITY", palette["bad"]),
    )
    for index, (x, y, label, color) in enumerate(milestones):
        local = base._phase(q, index * 0.14, min(1.0, index * 0.14 + 0.45))
        if local <= 0.02:
            continue
        radius = 25 + index * 7
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
        draw.line((x, y + radius, x, y + 105), fill=color, width=5)
        base.engine._text(draw, (x, y + 135), label, 19, palette["white"], bold=True, anchor="mm")

    fork = (1040, 610)
    futures = (
        (1490, 400, "LIKELY", palette["good"]),
        (1580, 620, "POSSIBLE", palette["accent"]),
        (1450, 845, "UNCERTAIN", palette["muted"]),
    )
    for index, (x, y, label, color) in enumerate(futures):
        local = base._phase(q, 0.42 + index * 0.10, min(1.0, 0.82 + index * 0.05))
        if local <= 0.02:
            continue
        end_x = round(fork[0] + (x - fork[0]) * local)
        end_y = round(fork[1] + (y - fork[1]) * local)
        draw.line((*fork, end_x, end_y), fill=color, width=8 - index)
        draw.ellipse((end_x - 34, end_y - 34, end_x + 34, end_y + 34), fill=color)
        base.engine._text(draw, (end_x, end_y + 68), label, 20, palette["white"], bold=True, anchor="mm")


def _machine_choice_explainer(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    """Reveal hidden ranking around one viewer action without side-by-side panels."""
    q = base._phase(progress, 0.04, 0.92)
    _depth_field(draw, palette, progress, horizon_y=745)

    draw.rounded_rectangle((75, 330, 720, 1060), radius=72, fill=(3, 7, 18), outline=palette["accent"], width=8)
    draw.rounded_rectangle((125, 390, 670, 985), radius=46, fill=palette["panel"])
    draw.ellipse((300, 560, 505, 765), fill=palette["accent"])
    draw.polygon(((375, 615), (375, 710), (455, 662)), fill=palette["ink"])
    base.engine._text(draw, (400, 865), "VISIBLE ACTION", 25, palette["white"], bold=True, anchor="mm")

    candidates = (
        (910, 400, 0.42),
        (1190, 330, 0.66),
        (1510, 430, 0.81),
        (1010, 680, 0.54),
        (1320, 720, 0.73),
        (1640, 690, 0.91),
        (1110, 930, 0.38),
        (1500, 940, 0.59),
    )
    winner = 5
    for index, (x, y, score) in enumerate(candidates):
        local = base._phase(q, index * 0.065, min(1.0, index * 0.065 + 0.42))
        radius = 30 + round(score * 24)
        color = palette["good"] if index == winner and q > 0.68 else palette["accent_alt"]
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color if local > 0.15 else palette["panel_alt"])
        if local > 0.22:
            draw.line((x, y, 720, 665), fill=color, width=2 + round(score * 5))
        if local > 0.46:
            base.engine._text(draw, (x, y), str(round(score * 100)), 17, palette["ink"], bold=True, anchor="mm")

    if q > 0.68:
        draw.arc((1440, 585, 1840, 985), 210, 345, fill=palette["good"], width=16)
        base.engine._text(draw, (1640, 1020), "RANKED OPPORTUNITY", 24, palette["good"], bold=True, anchor="mm")


def install_cinematic_anti_slide_pass() -> None:
    base.RENDERERS["attention_auction"] = _attention_auction
    base.RENDERERS["life_event_timeline"] = _life_event_timeline
    base.RENDERERS["machine_choice_explainer"] = _machine_choice_explainer
    expansion.base.RENDERERS["attention_auction"] = _attention_auction
    truthful.base.RENDERERS["life_event_timeline"] = _life_event_timeline
    truthful.base.RENDERERS["machine_choice_explainer"] = _machine_choice_explainer


install_cinematic_anti_slide_pass()
