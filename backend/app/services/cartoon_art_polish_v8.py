from __future__ import annotations

"""Art Polish v8: calmer crowds, clearer entrances, and richer repeated shots."""

import math

from PIL import ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v6 as v6
from . import cartoon_art_polish_v7 as v7


_HUMAN_COLORS = (cartoon.BLUE, cartoon.AMBER, cartoon.PURPLE, cartoon.GREEN, cartoon.CYAN, cartoon.RED)
_HAIR_COLORS = ((42, 32, 27), (86, 54, 34), (24, 26, 30), (128, 81, 48))


def _human(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    scale: float,
    color: tuple[int, int, int],
    pose: str = "stand",
) -> None:
    """Keep hair unmistakable without oversized helmet-like masses."""
    v6._human(draw, x, y, scale, color, pose)
    head_r = round(29 * scale)
    hair = _HAIR_COLORS[(x // 79 + y // 61) % len(_HAIR_COLORS)]
    style = (x // 113 + y // 47) % 3
    if style == 0:
        draw.pieslice(
            (x - head_r + 3, y - head_r + 2, x + head_r - 3, y + head_r - 2),
            184,
            356,
            fill=hair,
        )
        draw.rectangle(
            (x - head_r + 3, y - round(8 * scale), x - head_r + round(10 * scale), y + round(15 * scale)),
            fill=hair,
        )
    elif style == 1:
        r = max(4, round(8 * scale))
        for dx in (-18, -8, 2, 12, 20):
            cx = x + round(dx * scale)
            cy = y - head_r + round(2 * scale)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=hair)
    else:
        draw.polygon(
            (
                (x - head_r + 3, y - round(4 * scale)),
                (x - round(16 * scale), y - head_r + 3),
                (x + round(2 * scale), y - round(12 * scale)),
                (x + round(18 * scale), y - head_r + round(4 * scale)),
                (x + head_r - 3, y - round(3 * scale)),
            ),
            fill=hair,
        )


def _person(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    scale: float = 1.0,
    *,
    accent: tuple[int, int, int] | None = None,
    pose: str = "stand",
) -> None:
    if accent is None:
        v6._robot(draw, x, y, scale, pose)
    else:
        color = accent if accent not in (cartoon.MUTED, cartoon.DARK_MUTED) else _HUMAN_COLORS[(x // 83 + y // 67) % len(_HUMAN_COLORS)]
        _human(draw, x, y, scale, color, pose)


def _crowd(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, focal: bool = True) -> None:
    """Use fewer, larger, staggered figures so crowds remain readable."""
    rows = ((5, 0.49, 0.76), (6, 0.63, 0.86), (7, 0.78, 0.96))
    for row, (count, y_fraction, scale) in enumerate(rows):
        base_y = round(height * y_fraction)
        for index in range(count):
            offset = 42 if row % 2 else 0
            x = round((index + 0.5) * width / count + offset)
            x = max(80, min(width - 80, x))
            pose = "walk" if (index + row) % 3 == 0 else "stand"
            accent = None
            if focal and row == 1 and index == count // 2:
                accent = cartoon.PURPLE
                y = base_y - round(36 * cartoon._ease(progress))
            elif (index + row * 2) % 5 == 1:
                accent = _HUMAN_COLORS[(index + row) % len(_HUMAN_COLORS)]
                y = base_y
            else:
                y = base_y
            _person(draw, x, y, scale, accent=accent, pose=pose)


def _fixed_habitat(draw: ImageDraw.ImageDraw, cx: int, ground: int, scale: float = 1.0) -> None:
    """Make the airlock read as architecture with tunnel, lights, steps, and path."""
    v7._fixed_habitat_original(draw, cx, ground, scale)
    path_w = round(150 * scale)
    path_top = ground - round(18 * scale)
    draw.polygon(
        (
            (cx - round(44 * scale), path_top),
            (cx + round(44 * scale), path_top),
            (cx + path_w, ground + round(95 * scale)),
            (cx - path_w, ground + round(95 * scale)),
        ),
        fill=(151, 94, 69),
        outline=cartoon.INK,
    )
    for step in range(3):
        sy = ground - round((12 - step * 7) * scale)
        half = round((54 + step * 18) * scale)
        draw.line((cx - half, sy, cx + half, sy), fill=cartoon.AMBER, width=max(4, round(6 * scale)))
    for direction in (-1, 1):
        lx = cx + direction * round(49 * scale)
        draw.ellipse(
            (lx - round(8 * scale), ground - round(118 * scale), lx + round(8 * scale), ground - round(102 * scale)),
            fill=cartoon.CYAN,
            outline=cartoon.INK,
            width=max(2, round(3 * scale)),
        )


def _draw_presenter(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Retain the slim desk while adding a second purposeful visual prop."""
    v7._draw_presenter_original(draw, width, height, progress)
    variant = v7._ACTIVE_VARIANT % 4
    if variant % 2 == 0:
        cx, cy = round(width * 0.15), round(height * 0.48)
        draw.ellipse((cx - 90, cy - 90, cx + 90, cy + 90), fill=cartoon.BLUE, outline=cartoon.INK, width=10)
        draw.polygon(((cx - 55, cy - 10), (cx - 12, cy - 60), (cx + 42, cy - 28), (cx + 28, cy + 34), (cx - 35, cy + 48)), fill=cartoon.GREEN, outline=cartoon.INK)
        draw.arc((cx - 125, cy - 45, cx + 125, cy + 95), 195, 345, fill=cartoon.AMBER, width=10)
    else:
        x1, y1, x2, y2 = round(width * 0.73), round(height * 0.38), round(width * 0.94), round(height * 0.61)
        draw.rounded_rectangle((x1, y1, x2, y2), radius=20, fill=cartoon.WHITE, outline=cartoon.INK, width=9)
        values = (0.38, 0.62, 0.48, 0.78)
        bar_w = (x2 - x1 - 90) // len(values)
        for index, value in enumerate(values):
            bx = x1 + 35 + index * bar_w
            by = y2 - 30
            top = by - round((y2 - y1 - 75) * value)
            draw.rounded_rectangle((bx, top, bx + bar_w - 18, by), radius=7, fill=_HUMAN_COLORS[index], outline=cartoon.INK, width=4)


def _draw_route_map(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Use a larger ship and a clearly curved dotted trajectory."""
    for index in range(30):
        sx = (index * 181) % width
        sy = 24 + (index * 83) % round(height * 0.32)
        r = 2 + index % 3
        draw.ellipse((sx - r, sy - r, sx + r, sy + r), fill=cartoon.MUTED)
    v6._planet(draw, (round(width * 0.22), round(height * 0.58)), round(height * 0.22), cartoon.BLUE, progress)
    v6._planet(draw, (round(width * 0.80), round(height * 0.58)), round(height * 0.19), cartoon.MARS, 1 - progress)

    box = (round(width * 0.31), round(height * 0.20), round(width * 0.73), round(height * 0.71))
    for start in range(205, 336, 18):
        end = min(start + 10, 340)
        draw.arc(box, start, end, fill=cartoon.INK, width=11)
    angle = math.radians(335)
    ex = round((box[0] + box[2]) / 2 + (box[2] - box[0]) / 2 * math.cos(angle))
    ey = round((box[1] + box[3]) / 2 + (box[3] - box[1]) / 2 * math.sin(angle))
    draw.polygon(((ex, ey), (ex - 32, ey - 10), (ex - 18, ey + 28)), fill=cartoon.INK)

    ship_x = round(width * (0.37 + 0.29 * cartoon._ease(progress)))
    ship_y = round(height * (0.34 - 0.06 * math.sin(progress * math.pi)))
    v7._spacecraft(draw, ship_x, ship_y, 1.02, progress)


# Preserve originals before replacing module-local references.
v7._fixed_habitat_original = v7._fixed_habitat
v7._draw_presenter_original = v7._draw_presenter

# Install v8 through both the shared cartoon module and v7's local references.
v7._human = _human
v7._person = _person
v7._fixed_habitat = _fixed_habitat
v7._draw_presenter = _draw_presenter
cartoon._person = _person
cartoon._crowd = _crowd
cartoon._draw_presenter = _draw_presenter
cartoon._draw_route_map = _draw_route_map
