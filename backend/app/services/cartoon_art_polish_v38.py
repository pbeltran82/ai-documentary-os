from __future__ import annotations

"""Art Polish v38: keep one clear crowd crossing and suppress competing crowd overlays."""

from PIL import Image
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v18 as v18
from . import cartoon_art_polish_v19 as v19
from . import cartoon_art_polish_v37 as v37

# v25 supplies the deliberate crossing. Remove older ambient/focal crowd layers.
v18._crowd_ambient = lambda draw, progress: None
v19._crowd_beat = lambda draw, progress: None


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    return v37.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)


cartoon.render_planned_frame = render_planned_frame
