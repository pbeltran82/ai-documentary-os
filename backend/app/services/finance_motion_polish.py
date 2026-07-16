from __future__ import annotations

import math

from PIL import Image, ImageDraw

from . import finance_motion as base

# Editorial styling layer over the portable Pillow/FFmpeg engine. Importing this
# module installs clean-export renderers while preserving scene selection, local
# file generation, rights records, and the established encoder workflow.

TEMPLATES = base.TEMPLATES
OUTPUT_WIDTH = base.OUTPUT_WIDTH
OUTPUT_HEIGHT = base.OUTPUT_HEIGHT
template_catalog = base.template_catalog
suggest_template = base.suggest_template
ffmpeg_encoder_command = base.ffmpeg_encoder_command
_background = base._background

WHITE = base.WHITE
MUTED = base.MUTED
PURPLE = base.PURPLE
PURPLE_LIGHT = base.PURPLE_LIGHT
GREEN = base.GREEN
GREEN_LIGHT = base.GREEN_LIGHT
RED_LIGHT = base.RED_LIGHT
PANEL_LIGHT = base.PANEL_LIGHT
SLATE = (71, 85, 105)
PURPLE_DARK = (76, 55, 140)


def _chip(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    label: str,
    *,
    fill: tuple[int, int, int] = PURPLE,
    text_fill: tuple[int, int, int] = WHITE,
    width: int = 150,
    height: int = 64,
    size: int = 28,
) -> None:
    x, y = center
    draw.rounded_rectangle(
        (x - width // 2, y - height // 2, x + width // 2, y + height // 2),
        radius=height // 2,
        fill=fill,
    )
    base._text(draw, (x, y), label, size, text_fill, bold=True, anchor="mm")


def _arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    fill: tuple[int, int, int] = PURPLE_LIGHT,
    width: int = 8,
) -> None:
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=fill, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    length = 26
    spread = 0.55
    draw.polygon(
        (
            (x2, y2),
            (
                round(x2 - length * math.cos(angle - spread)),
                round(y2 - length * math.sin(angle - spread)),
            ),
            (
                round(x2 - length * math.cos(angle + spread)),
                round(y2 - length * math.sin(angle + spread)),
            ),
        ),
        fill=fill,
    )


def _common_clean(image: Image.Image, template: base.MotionTemplate) -> ImageDraw.ImageDraw:
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((110, 100, 118, 250), radius=4, fill=PURPLE)
    base._text(draw, (150, 105), template.title, 68, bold=True)
    base._text(draw, (150, 195), template.subtitle, 31, PURPLE_LIGHT)
    # No product watermark or internal footer in exported footage. Provenance
    # remains in the asset metadata, manifest, and selected-asset rights record.
    return draw


def _paycheck_polished(draw: ImageDraw.ImageDraw, t: float) -> None:
    life = base._progress(t, 0.35, 0.85)
    future = base._progress(t, 0.80, 0.75)
    transfer = base._progress(t, 0.75, 1.15)
    confirmation = base._progress(t, 1.70, 0.45)

    base._panel(draw, (150, 340, 1770, 860))
    base._text(draw, (220, 405), "PAYCHECK ARRIVES", 36, MUTED, bold=True)
    draw.rounded_rectangle((220, 535, 1700, 635), radius=22, fill=PANEL_LIGHT)

    if life > 0:
        draw.rounded_rectangle(
            (220, 535, 220 + round(1240 * life), 635),
            radius=22,
            fill=SLATE,
        )
    if future > 0:
        draw.rounded_rectangle(
            (1480, 535, 1480 + round(220 * future), 635),
            radius=22,
            fill=PURPLE,
        )

    base._text(draw, (250, 565), "90%  LIFESTYLE", 32, bold=True)
    base._text(draw, (1590, 585), "10%", 34, bold=True, anchor="mm")
    base._text(draw, (1590, 720), "FUTURE", 28, PURPLE_LIGHT, bold=True, anchor="mm")

    token_x = round(base._lerp(560, 1585, transfer))
    token_y = round(465 - 55 * math.sin(math.pi * transfer))
    _chip(draw, (token_x, token_y), "10%", width=136)

    if transfer < 0.98:
        _arrow(draw, (token_x + 76, token_y), (min(1510, token_x + 165), token_y))
    elif confirmation > 0:
        ring = round(70 + 18 * confirmation)
        draw.ellipse(
            (1590 - ring, 585 - ring, 1590 + ring, 585 + ring),
            outline=GREEN,
            width=5,
        )
        _chip(
            draw,
            (1275, 790),
            "AUTO-TRANSFERRED",
            fill=(15, 47, 42),
            text_fill=GREEN_LIGHT,
            width=310,
            height=58,
            size=24,
        )


def _transfer_polished(draw: ImageDraw.ImageDraw, t: float) -> None:
    transfer = base._progress(t, 0.40, 1.35)
    confirmation = base._progress(t, 1.55, 0.45)

    base._panel(draw, (160, 360, 760, 760))
    base._panel(draw, (1160, 360, 1760, 760), outline=PURPLE_DARK)
    base._text(draw, (230, 425), "CHECKING", 34, MUTED, bold=True)
    base._text(draw, (1230, 425), "INDEX FUND", 34, PURPLE_LIGHT, bold=True)
    base._text(
        draw,
        (460, 570),
        f"{100 - round(10 * transfer)}%",
        78,
        bold=True,
        anchor="mm",
    )
    base._text(
        draw,
        (1460, 570),
        f"+{round(10 * transfer)}%",
        78,
        GREEN_LIGHT,
        bold=True,
        anchor="mm",
    )

    _arrow(draw, (780, 575), (1140, 575), fill=PURPLE_DARK, width=10)
    x = round(base._lerp(805, 1115, transfer))
    y = round(575 - 70 * math.sin(math.pi * transfer))
    _chip(draw, (x, y), "10%", width=120, height=58, size=26)

    _chip(
        draw,
        (960, 825),
        "✓ SCHEDULED" if confirmation > 0.2 else "EVERY PAYDAY",
        fill=(15, 47, 42) if confirmation > 0 else PANEL_LIGHT,
        text_fill=GREEN_LIGHT if confirmation > 0 else PURPLE_LIGHT,
        width=280,
        height=62,
        size=26,
    )


def _index_polished(draw: ImageDraw.ImageDraw, t: float) -> None:
    base._panel(draw, (150, 320, 1770, 885))
    baseline = 805
    points: list[tuple[int, int]] = []

    for index, height in enumerate((100, 165, 245, 340, 460, 610)):
        progress = base._progress(t, 0.25 + index * 0.11, 0.90)
        actual = round(height * progress)
        x = 250 + index * 235
        draw.rounded_rectangle(
            (x, baseline - actual, x + 145, baseline),
            radius=15,
            fill=PURPLE,
        )
        point = (x + 72, baseline - actual - 22)
        points.append(point)
        if progress > 0.1:
            draw.ellipse(
                (point[0] - 9, point[1] - 9, point[0] + 9, point[1] + 9),
                fill=GREEN,
            )

    visible = [
        point
        for index, point in enumerate(points)
        if base._progress(t, 0.25 + index * 0.11, 0.90) > 0.1
    ]
    if len(visible) > 1:
        draw.line(visible, fill=GREEN, width=7, joint="curve")

    draw.line((220, baseline, 1680, baseline), fill=SLATE, width=3)
    _chip(
        draw,
        (430, 850),
        "REGULAR DEPOSITS",
        fill=PANEL_LIGHT,
        text_fill=PURPLE_LIGHT,
        width=340,
    )
    _chip(draw, (1485, 850), "TIME →", fill=PANEL_LIGHT, width=190)


def _compound_polished(draw: ImageDraw.ImageDraw, t: float) -> None:
    base._panel(draw, (150, 320, 1770, 885))
    points: list[tuple[int, int]] = []

    for index, size in enumerate((34, 46, 62, 84, 116, 160)):
        progress = base._progress(t, 0.24 + index * 0.13, 0.70)
        actual = max(8, round(size * progress))
        x = 280 + index * 255
        y = 775 - actual
        center = (x + actual // 2, y + actual // 2)
        points.append(center)

        if progress > 0.3:
            glow = actual + 28
            draw.ellipse(
                (
                    center[0] - glow // 2,
                    center[1] - glow // 2,
                    center[0] + glow // 2,
                    center[1] + glow // 2,
                ),
                outline=PURPLE_DARK,
                width=5,
            )
        draw.ellipse((x, y, x + actual, y + actual), fill=PURPLE)
        base._text(
            draw,
            (center[0], 825),
            f"Y{index + 1}",
            23,
            PURPLE_LIGHT,
            bold=True,
            anchor="mm",
        )

    visible = [
        point
        for index, point in enumerate(points)
        if base._progress(t, 0.24 + index * 0.13, 0.70) > 0.08
    ]
    if len(visible) > 1:
        draw.line(visible, fill=GREEN, width=8, joint="curve")

    momentum = round(100 + 240 * base._progress(t, 0.65, 1.45))
    _chip(
        draw,
        (960, 405),
        f"CONSISTENCY × TIME  =  {momentum}% MOMENTUM",
        fill=PANEL_LIGHT,
        text_fill=GREEN_LIGHT,
        width=730,
        height=66,
        size=28,
    )


def _comparison_polished(draw: ImageDraw.ImageDraw, t: float) -> None:
    progress = base._progress(t, 0.35, 0.95)
    base._panel(draw, (160, 360, 880, 815), (63, 23, 32), (127, 29, 29))
    base._panel(draw, (1040, 360, 1760, 815), (15, 47, 42), (6, 95, 70))

    base._text(draw, (520, 425), "SPEND FIRST", 44, RED_LIGHT, bold=True, anchor="mm")
    base._text(
        draw,
        (1400, 425),
        "PAY SELF FIRST",
        44,
        GREEN_LIGHT,
        bold=True,
        anchor="mm",
    )
    base._text(draw, (520, 585), "$0 LEFT", 74, bold=True, anchor="mm")
    base._text(
        draw,
        (1400, 585),
        f"{round(10 * progress)}% INVESTED",
        74,
        bold=True,
        anchor="mm",
    )

    draw.rounded_rectangle((270, 700, 770, 726), radius=13, fill=(89, 35, 43))
    draw.rounded_rectangle((1150, 700, 1650, 726), radius=13, fill=(20, 73, 63))
    draw.rounded_rectangle(
        (1150, 700, 1150 + round(500 * progress), 726),
        radius=13,
        fill=GREEN,
    )
    _chip(
        draw,
        (520, 765),
        "✕ REACTIVE",
        fill=(89, 35, 43),
        text_fill=RED_LIGHT,
        width=250,
        size=24,
    )
    _chip(
        draw,
        (1400, 765),
        "✓ AUTOMATIC",
        fill=(20, 73, 63),
        text_fill=GREEN_LIGHT,
        width=260,
        size=24,
    )


def _subscribe_polished(draw: ImageDraw.ImageDraw, t: float) -> None:
    pulse = 1 + 0.025 * math.sin(t * 4)
    width, height = round(1000 * pulse), round(260 * pulse)
    left, top = (OUTPUT_WIDTH - width) // 2, 420 - (height - 260) // 2

    ring_progress = base._progress(t, 0.30, 1.15)
    for offset, color in ((100, PURPLE_DARK), (170, (44, 32, 82))):
        radius_x = round((width // 2 + offset) * ring_progress)
        radius_y = round((height // 2 + offset // 2) * ring_progress)
        if radius_x > 0:
            draw.ellipse(
                (
                    960 - radius_x,
                    top + height // 2 - radius_y,
                    960 + radius_x,
                    top + height // 2 + radius_y,
                ),
                outline=color,
                width=5,
            )

    draw.rounded_rectangle(
        (left, top, left + width, top + height),
        radius=46,
        fill=PURPLE,
    )
    base._text(draw, (960, top + 90), "SUBSCRIBE", 82, bold=True, anchor="mm")
    base._text(
        draw,
        (960, top + 190),
        "BUILD THE NEXT STEP",
        35,
        (237, 233, 254),
        bold=True,
        anchor="mm",
    )
    draw.rounded_rectangle(
        (700, 735, 700 + round(520 * base._progress(t, 0.70, 1.0)), 745),
        radius=5,
        fill=GREEN,
    )


def install_clean_motion_style() -> None:
    base._common = _common_clean
    base.RENDERERS.update(
        {
            "paycheck_split": _paycheck_polished,
            "recurring_transfer": _transfer_polished,
            "index_growth": _index_polished,
            "compound_growth": _compound_polished,
            "pay_self_comparison": _comparison_polished,
            "subscribe_cta": _subscribe_polished,
        }
    )


install_clean_motion_style()

render_frame = base.render_frame
render_finance_motion = base.render_finance_motion
