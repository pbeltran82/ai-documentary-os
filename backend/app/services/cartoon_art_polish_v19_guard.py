from __future__ import annotations

"""Safety guard for v19: keep staged beats without duplicating existing actors."""

from PIL import ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v12 as v12
from . import cartoon_art_polish_v19 as v19


def _transport_beat(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    """Use portal/ramp state changes only; v18 already supplies moving actors."""
    state, local = v19._beat_state(progress)
    floor = round(cartoon.OUTPUT_HEIGHT * 0.80)
    colors = (cartoon.CYAN, cartoon.GREEN, cartoon.AMBER)

    if variant % 4 == 0:
        portal = (715, 285, 1205, 680)
        inset = 44 if state == 0 else round(44 - 28 * local) if state == 1 else 16
        draw.rounded_rectangle(
            (portal[0] + inset, portal[1] + inset, portal[2] - inset, portal[3]),
            radius=22,
            outline=colors[state],
            width=9,
        )
        ramp_progress = 0.0 if state == 0 else local if state == 1 else 1.0
        ramp_width = round(150 + 420 * ramp_progress)
        draw.line((960 - ramp_width // 2, floor - 8, 960 + ramp_width // 2, floor - 8), fill=colors[state], width=12)
    else:
        lengths = (260, 610, 180)
        center = round(960 + (local - 0.5) * 90)
        draw.line((center - lengths[state] // 2, floor - 10, center + lengths[state] // 2, floor - 10), fill=colors[state], width=10)


def _habitat_beat(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    """Animate the airlock operation only; wide Mars scenes already contain workers."""
    if variant % 4 != 2:
        return

    state, local = v19._beat_state(progress)
    panel_x, panel_y = 1110, 525
    if state == 0:
        light = cartoon.CYAN
        radius = 16
    elif state == 1:
        light = cartoon.AMBER
        radius = 18 + round(10 * local)
    else:
        light = cartoon.GREEN
        radius = 24
    draw.ellipse((panel_x - radius, panel_y - radius, panel_x + radius, panel_y + radius), fill=light, outline=cartoon.INK, width=5)

    if state == 1:
        hand_x = round(1030 + 72 * local)
        hand_y = round(615 - 86 * local)
        draw.line((1030, 615, hand_x, hand_y), fill=cartoon.INK, width=16)
        draw.ellipse((hand_x - 12, hand_y - 12, hand_x + 12, hand_y + 12), fill=(120, 153, 169), outline=cartoon.INK, width=4)


def _crowd_beat(draw: ImageDraw.ImageDraw, progress: float) -> None:
    """Use one focal crossing only during the middle beat, then clear the frame."""
    state, local = v19._beat_state(progress)
    if state != 1:
        return
    floor = round(cartoon.OUTPUT_HEIGHT * 0.76)
    x = round(420 + 610 * local)
    v12._human(draw, x, floor - 190, 1.02, cartoon.BLUE, "walk")


v19._transport_beat = _transport_beat
v19._habitat_beat = _habitat_beat
v19._crowd_beat = _crowd_beat
