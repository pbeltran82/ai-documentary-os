from __future__ import annotations

"""Art Polish v42: enforce doorway safe zones and clean panel occlusion."""

from PIL import Image, ImageDraw
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v19 as v19
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v41 as v41


def _occlude_transport_panels(image: Image.Image, progress: float, variant: int) -> None:
    if variant % 4 != 0:
        return
    state, local = v19._beat_state(progress)
    opening = 0.0 if state == 0 else local if state == 1 else 1.0
    gap = round(24 + 170 * opening)
    center = cartoon.OUTPUT_WIDTH // 2
    top, bottom = 300, 675
    panel_w = 205
    left_inner = center - gap
    right_inner = center + gap
    draw = ImageDraw.Draw(image)
    panel = (82, 94, 104)
    # Redraw panels last so figures cannot leak through the moving-door footprint.
    draw.rounded_rectangle((left_inner - panel_w, top, left_inner, bottom), radius=22, fill=panel, outline=cartoon.INK, width=8)
    draw.rounded_rectangle((right_inner, top, right_inner + panel_w, bottom), radius=22, fill=panel, outline=cartoon.INK, width=8)
    # Deep recess makes the opening read as physical depth rather than flat overlays.
    if gap > 42:
        draw.rectangle((left_inner + 8, top + 20, right_inner - 8, bottom - 18), fill=(38, 49, 60), outline=cartoon.CYAN, width=6)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v41.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    selected, progress, variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id == "transport_scene":
        _occlude_transport_panels(image, progress, variant)
    return image


cartoon.render_planned_frame = render_planned_frame
