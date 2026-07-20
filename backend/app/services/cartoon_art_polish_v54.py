from __future__ import annotations

"""Art Polish v54: sustained airlock action framing for long habitat beats."""

from PIL import Image

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v19 as v19
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v53 as v53


def _action_crop(image: Image.Image, progress: float) -> Image.Image:
    state, local = v19._beat_state(progress)
    if state != 1:
        return image
    # Ease into a clear door/panel close-up and hold it through the action beat.
    strength = min(1.0, local / 0.22) * min(1.0, (1.0-local) / 0.14)
    strength = max(0.0, min(1.0, strength))
    if strength <= 0.02:
        return image
    width, height = image.size
    zoom = 1.0 + 0.20 * cartoon._ease(strength)
    crop_w = round(width / zoom)
    crop_h = round(height / zoom)
    # Bias toward the airlock door and operating panel.
    center_x = round(width * 0.59)
    center_y = round(height * 0.54)
    left = max(0, min(width-crop_w, center_x-crop_w//2))
    top = max(0, min(height-crop_h, center_y-crop_h//2))
    return image.crop((left, top, left+crop_w, top+crop_h)).resize((width, height), Image.Resampling.LANCZOS)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v53.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    selected, progress, _variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id == "habitat_build":
        image = _action_crop(image, progress)
    return image


cartoon.render_planned_frame = render_planned_frame
