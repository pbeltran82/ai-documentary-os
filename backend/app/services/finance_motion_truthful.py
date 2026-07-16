from __future__ import annotations

from PIL import ImageDraw

from . import finance_motion as engine
from . import finance_motion_composition as composition
from . import finance_motion_choreography as base


COMPOUND_STATUS_LABEL = "ILLUSTRATIVE GROWTH PATH"


def _compound_truthful(draw: ImageDraw.ImageDraw, t: float) -> None:
    composition._shadowed_round_rect(
        draw,
        (110, 335, 1810, 890),
        fill=(24, 22, 45),
        outline=composition.PURPLE,
    )
    timeline_y = 760
    draw.line((230, timeline_y, 1690, timeline_y), fill=(76, 55, 140), width=6)

    points: list[tuple[int, int]] = []
    for index, value in enumerate((34, 54, 84, 128, 190, 270)):
        progress = engine._progress(t, 0.20 + index * 0.15, 0.72)
        x = 285 + index * 270
        height = round(value * progress)
        y = timeline_y - height - 70
        points.append((x, y))
        composition._coin(
            draw,
            (x, timeline_y),
            radius=28 + round(index * 1.8),
            fill=composition.GOLD,
            label="+",
        )
        if progress > 0.05:
            draw.line((x, timeline_y - 34, x, y + 26), fill=(76, 55, 140), width=5)
            radius = 28 + round(index * 8 * progress)
            draw.ellipse(
                (x - radius, y - radius, x + radius, y + radius),
                fill=composition.PURPLE,
                outline=composition.PURPLE_LIGHT,
                width=4,
            )
            composition._value(draw, (x, y), f"Y{index + 1}", size=22, anchor="mm")

    visible = [
        point
        for index, point in enumerate(points)
        if engine._progress(t, 0.20 + index * 0.15, 0.72) > 0.08
    ]
    if len(visible) > 1:
        draw.line(visible, fill=composition.GREEN, width=9, joint="curve")

    composition._pill(
        draw,
        (960, 415),
        COMPOUND_STATUS_LABEL,
        fill=(57, 41, 108),
        text_fill=composition.PURPLE_LIGHT,
        width=560,
        height=70,
        size=27,
    )
    composition._label(
        draw,
        (960, 500),
        "CONTRIBUTIONS CREATE RETURNS. RETURNS CREATE MORE RETURNS.",
        fill=composition.GREEN_LIGHT,
        size=25,
        anchor="mm",
    )


# Replace only the misleading synthetic percentage. The underlying timing,
# choreography, art direction, project-owned rendering, and template routing stay
# unchanged.
composition.COMPOSITION_RENDERERS["compound_growth"] = _compound_truthful
engine.RENDERERS["compound_growth"] = _compound_truthful

DEFAULT_STYLE_ID = base.DEFAULT_STYLE_ID
OUTPUT_HEIGHT = base.OUTPUT_HEIGHT
OUTPUT_WIDTH = base.OUTPUT_WIDTH
STYLES = base.STYLES
TEMPLATES = base.TEMPLATES
ffmpeg_encoder_command = base.ffmpeg_encoder_command
render_finance_motion = base.render_finance_motion
render_frame = base.render_frame
storyboard_beats = base.storyboard_beats
style_catalog = base.style_catalog
suggest_template = base.suggest_template
template_catalog = base.template_catalog
