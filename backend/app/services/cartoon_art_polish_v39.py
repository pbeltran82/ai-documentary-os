from __future__ import annotations

"""Art Polish v39: final overdraw, compatibility, and output safety guard."""

from PIL import Image
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v19 as v19
from . import cartoon_art_polish_v20 as v20
from . import cartoon_art_polish_v21 as v21
from . import cartoon_art_polish_v38 as v38

# The v31-v38 stack supplies the final focal actions. Disable stale overlays
# from the staged-beat stack so no duplicate torso, arm, council, or trail leaks.
v19._presenter_beat = lambda draw, progress, variant: None
v19._council_beat = lambda draw, progress: None
v20._presenter_response = lambda draw, progress, variant: None
v20._council_response = lambda draw, progress: None
v20._crowd_response = lambda draw, progress: None
v21._presenter_confirmation = lambda draw, progress, variant: None
v21._council_confirmation = lambda draw, progress: None
v21._crowd_response = lambda draw, progress: None


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v38.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if image.mode != "RGB":
        image = image.convert("RGB")
    target = (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT)
    if image.size != target:
        image = image.resize(target, Image.Resampling.LANCZOS)
    return image


cartoon.render_planned_frame = render_planned_frame
