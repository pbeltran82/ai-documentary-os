from __future__ import annotations

"""Art Polish v23: complete presenter pose states without torso overlays."""

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v12 as v12
from . import cartoon_art_polish_v22 as v22

_ACTIVE_VARIANT = 0


def _state(progress: float) -> tuple[int, float]:
    value = max(0.0, min(0.999999, progress))
    state = min(2, int(value * 3.0))
    return state, cartoon._ease(value * 3.0 - state)


def _presenter_pose(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    state, local = _state(progress)
    right = variant % 4 in (0, 3)
    x = 1185 if right else 590
    y = 475
    color = cartoon.BLUE if right and variant % 4 == 0 else cartoon.AMBER if right else cartoon.GREEN
    pose = "stand" if state == 0 else "point"
    shift = round((1 if right else -1) * (8 + 14 * local)) if state == 1 else round((1 if right else -1) * 18) if state == 2 else 0
    v12._human(draw, x + shift, y, 1.05, color, pose)
    if state == 2:
        marker_x = 785 if right else 1110
        draw.rounded_rectangle((marker_x - 95, 330, marker_x + 95, 342), radius=6, fill=cartoon.GREEN)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    global _ACTIVE_VARIANT
    beat = cartoon._beat_for_time(scene, time_seconds)
    extra = str((beat or {}).get("visual_intent", ""))
    selected = cartoon.TEMPLATE_BY_ID.get(template_id or "")
    if selected is None or beat is not None:
        selected, _confidence, _reason = cartoon.suggest_template(scene, extra)
    beat_start = float((beat or {}).get("relative_start_seconds", 0.0))
    beat_end = float((beat or {}).get("relative_end_seconds", duration_seconds))
    progress = cartoon._ease((time_seconds - beat_start) / max(0.001, beat_end - beat_start))
    scene_number = int(getattr(scene, "scene_number", 1) or 1)
    offsets = {"transport_scene": 0, "habitat_build": 1, "presenter_desk": 2, "crowd_focus": 3, "route_map": 4, "council_scene": 5}
    _ACTIVE_VARIANT = (scene_number * 7 + offsets.get(selected.template_id, 0)) % 12
    image = v22.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if selected.template_id == "presenter_desk":
        _presenter_pose(ImageDraw.Draw(image), progress, _ACTIVE_VARIANT)
    return image


cartoon.render_planned_frame = render_planned_frame
