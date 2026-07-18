from __future__ import annotations

"""Art Polish v33: remove the duplicate replacement presenter actor."""

from PIL import Image
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v23 as v23
from . import cartoon_art_polish_v32 as v32

# The base presenter is already present in the composition. Disable the later
# full-actor overlay that caused the visible second green/blue body.
v23._presenter_pose = lambda draw, progress, variant: None


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    return v32.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)


cartoon.render_planned_frame = render_planned_frame
