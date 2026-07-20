from __future__ import annotations

"""Compatibility guard for v18 ambient cues across differing camera layouts."""

from PIL import ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v18 as v18


_original_transport = v18._transport_ambient
_original_habitat = v18._habitat_ambient


def _transport_ambient(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    """Keep actor-attached cues only in the doorway layout; retain safe lights elsewhere."""
    if variant % 4 == 0:
        _original_transport(draw, progress, variant)
        return

    floor = round(cartoon.OUTPUT_HEIGHT * 0.80)
    sweep = round(300 + cartoon._ease(progress) * 1080)
    draw.line((sweep, floor - 12, sweep + 80, floor - 12), fill=cartoon.CYAN, width=6)
    for index, x in enumerate((520, 790, 1080, 1370)):
        pulse = 6 + round(3 * (0.5 + 0.5 * v18._phase(progress, 1.5, index * 0.19)))
        draw.ellipse(
            (x - pulse, 175 - pulse, x + pulse, 175 + pulse),
            fill=cartoon.GREEN if index % 2 else cartoon.CYAN,
            outline=cartoon.INK,
            width=3,
        )


def _habitat_ambient(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    """Render the airlock eye cue only in the close-up layout where it is anchored."""
    ground = round(cartoon.OUTPUT_HEIGHT * 0.77)
    antenna_x = 1450 if variant % 2 else 520
    sweep = round(34 * v18._phase(progress, 0.44))
    draw.line((antenna_x, ground - 220, antenna_x + sweep, ground - 280), fill=cartoon.INK, width=7)
    draw.ellipse(
        (antenna_x + sweep - 9, ground - 289, antenna_x + sweep + 9, ground - 271),
        fill=cartoon.AMBER,
        outline=cartoon.INK,
        width=3,
    )
    for index in range(2):
        drift = round((progress * 95 + index * 125) % 360)
        x = 220 + drift * 4
        y = ground - 30 - index * 22
        draw.arc((x, y, x + 105, y + 38), 190, 340, fill=(151, 94, 69), width=4)
    if variant % 4 == 2:
        v18._blink(draw, 1110, 535, progress, 0.18)


v18._transport_ambient = _transport_ambient
v18._habitat_ambient = _habitat_ambient
