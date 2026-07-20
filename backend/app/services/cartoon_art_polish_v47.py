from __future__ import annotations

"""Art Polish v47: give long route scenes clear departure, cruise, and arrival chapters."""

from PIL import Image, ImageDraw
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v46 as v46


def _chapter_cue(image: Image.Image, progress: float) -> None:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    if progress < 0.30:
        label = "DEPARTURE"
        color = cartoon.BLUE
    elif progress < 0.72:
        label = "CRUISE"
        color = cartoon.PURPLE
    else:
        label = "ARRIVAL"
        color = cartoon.MARS
    # Small lower-third chapter cue; no route line or UI frame.
    x1, y1 = round(width*0.07), round(height*0.88)
    x2 = x1 + 230
    draw.rounded_rectangle((x1, y1, x2, y1+44), radius=12, fill=(248, 244, 237), outline=cartoon.INK, width=4)
    draw.rounded_rectangle((x1+12, y1+12, x1+48, y1+32), radius=6, fill=color)
    # Deliberately omit text dependency; the color/state change is the cue.


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v46.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    selected, progress, _variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id == "route_map":
        _chapter_cue(image, progress)
    return image


cartoon.render_planned_frame = render_planned_frame
