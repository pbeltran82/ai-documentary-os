from __future__ import annotations

"""Art Polish v55: final regular documentary cleanup contract."""

from PIL import Image

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v54 as v54


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v54.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if image.mode != "RGB":
        image = image.convert("RGB")
    target = (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT)
    if image.size != target:
        image = image.resize(target, Image.Resampling.LANCZOS)
    return image


cartoon.render_planned_frame = render_planned_frame
