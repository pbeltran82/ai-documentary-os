from __future__ import annotations

"""Art Polish v40: stable final renderer for the v31-v40 cleanup stack."""

from PIL import Image
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v39 as v39


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    return v39.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)


cartoon.render_planned_frame = render_planned_frame
