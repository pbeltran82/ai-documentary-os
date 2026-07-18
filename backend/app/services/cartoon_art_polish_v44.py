from __future__ import annotations

"""Art Polish v44: distinct Earth palettes without tinting focal artwork."""

from PIL import Image, ImageChops
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v43 as v43


def _earth_background(image: Image.Image, variant: int) -> Image.Image:
    palettes = ((222, 239, 247), (232, 242, 232), (236, 232, 247), (244, 236, 218))
    target = Image.new("RGB", image.size, palettes[variant % len(palettes)])
    paper = Image.new("RGB", image.size, cartoon.PAPER)
    diff = ImageChops.difference(image.convert("RGB"), paper).convert("L")
    mask = diff.point(lambda value: 255 if value < 24 else 0)
    result = image.convert("RGB")
    result.paste(target, (0, 0), mask)
    return result


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v43.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    selected, _progress, variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id in {"transport_scene", "presenter_desk", "council_scene", "crowd_focus"}:
        image = _earth_background(image, variant)
    return image


cartoon.render_planned_frame = render_planned_frame
