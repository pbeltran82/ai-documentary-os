from __future__ import annotations

import math

from PIL import ImageDraw

from . import finance_motion as text_engine


WHITE = (248, 250, 252)
INK = (9, 14, 27)
RED_LIGHT = (254, 202, 202)
SUBSCRIBE_RED = (220, 53, 69)
SUBSCRIBE_RED_DARK = (151, 30, 43)
LIKE_BLUE = (48, 126, 218)
LIKE_BLUE_LIGHT = (160, 211, 255)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def draw_like_icon(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    *,
    scale: float = 1.0,
    fill: tuple[int, int, int] = WHITE,
) -> None:
    """Draw the original, rights-clean thumbs-up mark used by every CTA family."""
    x, y = center
    outline = INK
    cuff = (
        x - round(35 * scale),
        y - round(12 * scale),
        x - round(17 * scale),
        y + round(27 * scale),
    )
    draw.rounded_rectangle(
        (cuff[0] + 3, cuff[1] + 4, cuff[2] + 3, cuff[3] + 4),
        radius=max(3, round(5 * scale)),
        fill=outline,
    )
    draw.rounded_rectangle(cuff, radius=max(3, round(5 * scale)), fill=fill)
    hand = (
        (x - round(12 * scale), y + round(24 * scale)),
        (x + round(20 * scale), y + round(24 * scale)),
        (x + round(29 * scale), y + round(15 * scale)),
        (x + round(31 * scale), y - round(5 * scale)),
        (x + round(25 * scale), y - round(12 * scale)),
        (x + round(8 * scale), y - round(12 * scale)),
        (x + round(14 * scale), y - round(30 * scale)),
        (x + round(10 * scale), y - round(39 * scale)),
        (x + round(2 * scale), y - round(40 * scale)),
        (x - round(8 * scale), y - round(19 * scale)),
        (x - round(14 * scale), y - round(10 * scale)),
    )
    draw.polygon(tuple((px + 3, py + 4) for px, py in hand), fill=outline)
    draw.polygon(hand, fill=fill)


def draw_subscribe_button(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    reveal: float,
    *,
    pulse: float = 0.5,
    scale: float = 1.0,
) -> tuple[int, int, int, int] | None:
    reveal = _clamp(reveal)
    if reveal <= 0.14:
        return None

    center_x, center_y = center
    width = round(520 * scale * (0.88 + 0.12 * reveal))
    height = round(108 * scale * (0.90 + 0.10 * reveal))
    left = center_x - width // 2
    top = round(center_y - height // 2 + (1 - reveal) * 24 * scale)
    right = left + width
    bottom = top + height
    radius = max(14, round(28 * scale))

    halo = round((8 + 8 * _clamp(pulse)) * scale * reveal)
    draw.rounded_rectangle(
        (left - halo, top - halo // 2, right + halo, bottom + halo // 2),
        radius=radius + 4,
        outline=SUBSCRIBE_RED_DARK,
        width=max(2, round(3 * scale)),
    )
    shadow = max(4, round(8 * scale))
    draw.rounded_rectangle(
        (left + shadow, top + shadow, right + shadow, bottom + shadow),
        radius=radius,
        fill=(3, 6, 14),
    )
    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=radius,
        fill=SUBSCRIBE_RED,
        outline=RED_LIGHT,
        width=max(2, round(2 * scale)),
    )

    play_x = left + round(62 * scale * (0.86 + 0.14 * reveal))
    play_half = round(20 * scale * (0.76 + 0.24 * reveal))
    draw.polygon(
        (
            (play_x - play_half // 2, center_y - play_half),
            (play_x - play_half // 2, center_y + play_half),
            (play_x + play_half, center_y),
        ),
        fill=WHITE,
    )
    text_engine._text(
        draw,
        (left + round(width * 0.60), center_y),
        "SUBSCRIBE",
        max(25, round(47 * scale)),
        WHITE,
        bold=True,
        anchor="mm",
    )
    return left, top, right, bottom


def draw_like_button(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    reveal: float,
    *,
    scale: float = 1.0,
) -> tuple[int, int, int, int] | None:
    reveal = _clamp(reveal)
    if reveal <= 0.16:
        return None

    center_x, center_y = center
    width = round(270 * scale * (0.72 + 0.28 * reveal))
    height = round(78 * scale)
    rendered_y = round(center_y + (1 - reveal) * 24 * scale)
    left = center_x - width // 2
    right = center_x + width // 2
    top = rendered_y - height // 2
    bottom = rendered_y + height // 2
    radius = height // 2
    shadow = max(4, round(6 * scale))

    draw.rounded_rectangle(
        (left + shadow, top + shadow, right + shadow, bottom + shadow),
        radius=radius,
        fill=(3, 6, 14),
    )
    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=radius,
        fill=LIKE_BLUE,
        outline=LIKE_BLUE_LIGHT,
        width=max(2, round(2 * scale)),
    )
    draw_like_icon(
        draw,
        (left + round(61 * scale), rendered_y + 1),
        scale=0.63 * scale * (0.82 + 0.18 * reveal),
        fill=WHITE,
    )
    text_engine._text(
        draw,
        (left + round(width * 0.67), rendered_y),
        "LIKE",
        max(22, round(35 * scale)),
        WHITE,
        bold=True,
        anchor="mm",
    )
    return left, top, right, bottom


def draw_subscribe_like(
    draw: ImageDraw.ImageDraw,
    *,
    subscribe_center: tuple[int, int],
    like_center: tuple[int, int],
    subscribe_reveal: float,
    like_reveal: float,
    pulse: float | None = None,
    subscribe_scale: float = 1.0,
    like_scale: float = 1.0,
) -> dict[str, tuple[int, int, int, int] | None]:
    resolved_pulse = (
        (math.sin(_clamp(subscribe_reveal) * math.pi * 4) + 1) / 2
        if pulse is None
        else pulse
    )
    return {
        "subscribe": draw_subscribe_button(
            draw,
            subscribe_center,
            subscribe_reveal,
            pulse=resolved_pulse,
            scale=subscribe_scale,
        ),
        "like": draw_like_button(
            draw,
            like_center,
            like_reveal,
            scale=like_scale,
        ),
    }
