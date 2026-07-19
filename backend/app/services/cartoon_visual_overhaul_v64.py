from __future__ import annotations

"""Visual Overhaul v64: finish Mars on the settlement, never a second departure."""

from PIL import Image

from . import cartoon_documentary as cartoon
from . import cartoon_visual_overhaul_v63 as v63


def _context(scene) -> str:
    return " ".join(
        [
            str(getattr(scene, "narration", "") or ""),
            str(getattr(scene, "visual_intent", "") or ""),
            *[str(value) for value in (getattr(scene, "search_keywords", None) or [])],
        ]
    ).lower()


def _is_final_project_scene(scene) -> bool:
    project = getattr(scene, "project", None)
    scenes = list(getattr(project, "scenes", None) or [])
    if not scenes:
        return False
    numbers = [int(getattr(item, "scene_number", 0) or 0) for item in scenes]
    return int(getattr(scene, "scene_number", 0) or 0) == max(numbers, default=-1)


def _is_mars_story(scene) -> bool:
    context = _context(scene)
    return any(
        signal in context
        for signal in (
            "mars",
            "martian",
            "interplanetary",
            "off-planet",
            "spacecraft",
            "habitat",
        )
    )


def render_planned_frame(
    scene,
    template_id: str | None,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    selected = v63._selected_template(scene, template_id)
    progress = v63._absolute_progress(duration_seconds, time_seconds)
    scene_number = int(getattr(scene, "scene_number", 1) or 1)
    variant = scene_number % 6

    # A full documentary may use a route scene before the conclusion, but its final
    # visual must resolve the journey. This also prevents two adjacent route assets
    # from each restarting at Earth when broad Mars language scores both scenes.
    if selected == "route_map" and _is_final_project_scene(scene) and _is_mars_story(scene):
        return v63._process_frame(progress, variant)

    return v63.render_planned_frame(
        scene,
        template_id,
        duration_seconds,
        time_seconds,
        style_id,
    )


cartoon.render_planned_frame = render_planned_frame
