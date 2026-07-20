from __future__ import annotations

"""Art Polish v28: output-size, color-mode, and edge-safety normalization."""

from PIL import Image

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v27 as v27


def _normalize(image: Image.Image) -> Image.Image:
    if image.mode != "RGB":
        image = image.convert("RGB")
    expected = (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT)
    if image.size != expected:
        image = image.resize(expected, Image.Resampling.LANCZOS)
    return image


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v27.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    return _normalize(image)


cartoon.render_planned_frame = render_planned_frame
