from __future__ import annotations

"""Art Polish v37: controlled airlock action close-up with wide-shot return."""

from PIL import Image
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v19 as v19
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v36 as v36


def _focus_crop(image: Image.Image, center_x: int, center_y: int, zoom: float) -> Image.Image:
    width, height = image.size
    crop_w = round(width / zoom)
    crop_h = round(height / zoom)
    left = max(0, min(width - crop_w, center_x - crop_w // 2))
    top = max(0, min(height - crop_h, center_y - crop_h // 2))
    return image.crop((left, top, left + crop_w, top + crop_h)).resize((width, height), Image.Resampling.LANCZOS)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v36.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    selected, progress, variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id != "habitat_build" or variant % 4 != 2:
        return image
    state, local = v19._beat_state(progress)
    if state != 1:
        return image
    # Ease into a modest panel/door close-up, then ease back before confirmation.
    envelope = 1.0 - abs(2.0 * local - 1.0)
    zoom = 1.0 + 0.11 * cartoon._ease(envelope)
    return _focus_crop(image, 1110, 535, zoom)


cartoon.render_planned_frame = render_planned_frame
