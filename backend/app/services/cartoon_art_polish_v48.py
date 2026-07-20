from __future__ import annotations

"""Art Polish v48: clean-look guard for route, pointer, and doorway layers."""

from PIL import Image
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v47 as v47

# Review correction: chaptering stays cinematic; no lower-third badge replaces the removed path.
v47._chapter_cue = lambda image, progress: None


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v47.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


cartoon.render_planned_frame = render_planned_frame
