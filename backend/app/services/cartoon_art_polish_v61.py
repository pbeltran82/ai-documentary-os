from __future__ import annotations

"""Art Polish v61: deterministic route continuity across visual beats."""

from PIL import Image

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v52 as v52
from . import cartoon_art_polish_v55 as v55


def render_planned_frame(
    scene,
    template_id: str | None,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    selected, _beat_progress, variant = v31._context(
        scene,
        template_id,
        duration_seconds,
        time_seconds,
    )
    if selected.template_id == "route_map":
        # Route motion belongs to the whole scene, never to an individual visual
        # beat. Absolute scene progress remains deterministic when frames render
        # out of order and cannot reset when the beat planner advances.
        duration = max(0.001, float(duration_seconds))
        scene_progress = max(0.0, min(1.0, float(time_seconds) / duration))
        return v52._route(cartoon._ease(scene_progress), variant)
    return v55.render_planned_frame(
        scene,
        template_id,
        duration_seconds,
        time_seconds,
        style_id,
    )


cartoon.render_planned_frame = render_planned_frame
