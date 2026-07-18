from __future__ import annotations

"""Art Polish v30: final director integration for the v21-v30 documentary stack."""

from PIL import Image

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v28 as v28
from . import cartoon_art_polish_v29 as v29  # noqa: F401


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    """Render through the reviewed stack with a stable final contract."""
    image = v28.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if image.mode != "RGB":
        image = image.convert("RGB")
    if image.size != (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT):
        image = image.resize((cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT), Image.Resampling.LANCZOS)
    return image


cartoon.render_planned_frame = render_planned_frame
