from __future__ import annotations

"""Art Polish v49: regression guard for the clean-look stack."""

from PIL import Image
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v15 as v15
from . import cartoon_art_polish_v17 as v17
from . import cartoon_art_polish_v34 as v34
from . import cartoon_art_polish_v48 as v48

# The v45 route renderer is authoritative. Prevent legacy public hooks from being
# reintroduced by direct previews after the final service import order completes.
cartoon._draw_route_map = lambda draw, width, height, progress: None

# v43 already replaces v34.render_planned_frame with the single-pointer version.
# Keep legacy helper animation layers from re-adding presentation lines.
if hasattr(v15, "_animate_presenter"):
    v15._animate_presenter = lambda draw, width, height, progress, variant: None
if hasattr(v17, "_animate_presenter"):
    v17._animate_presenter = lambda draw, width, height, progress, variant: None


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v48.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    target = (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT)
    if image.mode != "RGB":
        image = image.convert("RGB")
    if image.size != target:
        image = image.resize(target, Image.Resampling.LANCZOS)
    return image


cartoon.render_planned_frame = render_planned_frame
