from __future__ import annotations

"""Art Polish v35: suppress duplicate council replacement bodies."""

from PIL import Image
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v24 as v24
from . import cartoon_art_polish_v34 as v34

# Preserve the original council row and remove the pasted-over replacement row.
v24._council_pose = lambda draw, progress: None


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    return v34.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)


cartoon.render_planned_frame = render_planned_frame
