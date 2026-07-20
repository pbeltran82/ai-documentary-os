from __future__ import annotations

"""Art Polish v34: compact presenter pointer and chart-led emphasis."""

from PIL import Image, ImageDraw
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v19 as v19
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v33 as v33


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v33.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    selected, progress, variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id != "presenter_desk":
        return image
    state, local = v19._beat_state(progress)
    if state == 0:
        return image
    draw = ImageDraw.Draw(image)
    right = variant % 4 in (0, 3)
    hand = (1095, 515) if right else (685, 535)
    tip_x = round((930 if right else 855) + (-55 if right else 55) * local)
    tip_y = round(410 - 40 * local)
    draw.line((hand[0], hand[1], tip_x, tip_y), fill=cartoon.INK, width=9)
    draw.ellipse((tip_x - 8, tip_y - 8, tip_x + 8, tip_y + 8), fill=cartoon.AMBER, outline=cartoon.INK, width=3)
    if state == 2:
        marker_x = 785 if right else 1110
        draw.rounded_rectangle((marker_x - 80, 338, marker_x + 80, 349), radius=5, fill=cartoon.GREEN)
    return image


cartoon.render_planned_frame = render_planned_frame
