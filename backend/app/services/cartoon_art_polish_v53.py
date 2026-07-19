from __future__ import annotations

"""Art Polish v53: compact presenter pointer and restrained body-language cue."""

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v19 as v19
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v34 as v34
from . import cartoon_art_polish_v43 as v43
from . import cartoon_art_polish_v52 as v52


# v53 owns the only final pointer. Disable both earlier pointer implementations.
v34.render_planned_frame = v34.v33.render_planned_frame
v43.render_planned_frame = v43.v42.render_planned_frame


def _pointer(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    state, local = v19._beat_state(progress)
    if state == 0:
        return
    right = variant % 4 in (0, 3)
    hand = (1082, 520) if right else (698, 536)
    direction = -1 if right else 1
    reach = round(118 + 36 * local)
    tip = (hand[0] + direction * reach, hand[1] - round(76 + 24 * local))
    handle_end = (hand[0] + direction * 30, hand[1] - 18)
    draw.line((*hand, *handle_end), fill=(74, 55, 38), width=13)
    draw.line((*handle_end, *tip), fill=(49, 62, 76), width=5)
    draw.ellipse((tip[0]-7, tip[1]-7, tip[0]+7, tip[1]+7), fill=cartoon.AMBER, outline=cartoon.INK, width=2)
    # Small shoulder cue creates a pose change without redrawing another body.
    shoulder_x = hand[0] + (18 if right else -18)
    draw.arc((shoulder_x-24, hand[1]-38, shoulder_x+24, hand[1]+10), 195 if right else 345, 315 if right else 105, fill=cartoon.INK, width=4)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v52.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    selected, progress, variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id == "presenter_desk":
        _pointer(ImageDraw.Draw(image), progress, variant)
    return image


cartoon.render_planned_frame = render_planned_frame
