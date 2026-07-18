from __future__ import annotations

"""Art Polish v36: clean council speaker emphasis on the original seated row."""

from PIL import Image, ImageDraw
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v24 as v24
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v35 as v35


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v35.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    selected, progress, _variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id != "council_scene":
        return image
    speaker, local = v24._speaker_state(progress)
    centers = (650, 960, 1270)
    colors = (cartoon.BLUE, cartoon.PURPLE, cartoon.AMBER)
    cx = centers[speaker]
    draw = ImageDraw.Draw(image)
    nod = round(10 * local)
    draw.arc((cx - 34, 390 - nod, cx + 34, 438 - nod), 205, 335, fill=cartoon.DARK_MUTED, width=6)
    hand_x = round(cx + 52 + 38 * local)
    hand_y = round(500 - 48 * local)
    draw.line((cx + 18, 535, hand_x, hand_y), fill=cartoon.INK, width=13)
    draw.ellipse((hand_x - 10, hand_y - 10, hand_x + 10, hand_y + 10), fill=colors[speaker], outline=cartoon.INK, width=4)
    draw.rounded_rectangle((cx - 72, 686, cx + 72, 700), radius=7, fill=cartoon.CYAN)
    return image


cartoon.render_planned_frame = render_planned_frame
