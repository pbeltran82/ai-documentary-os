from __future__ import annotations

"""Art Polish v41: remove unintended dome/grid seams while preserving the habitat shell."""

from PIL import Image, ImageDraw
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v40 as v40


def _clean_dome_seams(image: Image.Image) -> None:
    width, height = image.size
    sample = image.getpixel((width // 2, max(40, round(height * 0.18))))
    if not (isinstance(sample, tuple) and len(sample) >= 3 and sample[2] >= sample[0]):
        return
    draw = ImageDraw.Draw(image)
    # Mask only the thin internal rails visible in the dome family. Keep the shell,
    # lower wall divisions, characters, and machinery untouched.
    for ratio in (0.138, 0.270, 0.402, 0.533, 0.665):
        x = round(width * ratio)
        draw.rectangle((x - 5, round(height * 0.145), x + 5, round(height * 0.465)), fill=sample)
    # Three restrained supports communicate structure without a cage/grid effect.
    support = tuple(max(0, c - 38) for c in sample[:3])
    for ratio in (0.27, 0.50, 0.73):
        x = round(width * ratio)
        draw.line((x, round(height * 0.24), x, round(height * 0.46)), fill=support, width=4)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v40.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    selected, _progress, _variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id == "habitat_build":
        _clean_dome_seams(image)
    return image


cartoon.render_planned_frame = render_planned_frame
