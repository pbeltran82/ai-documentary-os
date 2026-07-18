from __future__ import annotations

"""Art Polish v32: mask legacy airlock geometry before physical panel redraws."""

from PIL import Image, ImageDraw
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v19 as v19
from . import cartoon_art_polish_v31 as v31


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v31.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    selected, progress, variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id == "habitat_build" and variant % 4 == 2:
        draw = ImageDraw.Draw(image)
        state, local = v19._beat_state(progress)
        opening = 0.0 if state == 0 else 0.55 * local if state == 1 else 0.55 + 0.35 * local
        x1, y1, x2, y2 = 885, 340, 1335, 790
        draw.rectangle((x1 - 8, y1 - 8, x2 + 8, y2 + 8), fill=(55, 67, 76))
        gap = round(18 + 125 * opening)
        center = (x1 + x2) // 2
        fill = (105, 116, 124)
        draw.rounded_rectangle((x1, y1, center - gap, y2), radius=24, fill=fill, outline=cartoon.INK, width=9)
        draw.rounded_rectangle((center + gap, y1, x2, y2), radius=24, fill=fill, outline=cartoon.INK, width=9)
        if opening > 0.12:
            draw.rectangle((center - gap + 10, y1 + 35, center + gap - 10, y2 - 30), fill=(44, 57, 66), outline=cartoon.CYAN, width=6)
    return image


cartoon.render_planned_frame = render_planned_frame
