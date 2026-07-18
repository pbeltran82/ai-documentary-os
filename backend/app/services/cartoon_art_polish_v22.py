from __future__ import annotations

"""Art Polish v22: physical doorway and airlock state changes."""

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v19 as v19
from . import cartoon_art_polish_v21 as v21

_ACTIVE_VARIANT = 0


def _doorway_physics(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    if variant % 4 != 0:
        return
    state, local = v19._beat_state(progress)
    opening = 0.0 if state == 0 else local if state == 1 else 1.0
    gap = round(24 + 170 * opening)
    top, bottom = 300, 675
    center = 960
    panel_w = 205
    left_inner = center - gap
    right_inner = center + gap
    fill = (82, 94, 104)
    draw.rounded_rectangle((left_inner - panel_w, top, left_inner, bottom), radius=22, fill=fill, outline=cartoon.INK, width=8)
    draw.rounded_rectangle((right_inner, top, right_inner + panel_w, bottom), radius=22, fill=fill, outline=cartoon.INK, width=8)
    if opening > 0.15:
        glow = cartoon.GREEN if state == 2 else cartoon.CYAN
        draw.rectangle((left_inner + 8, top + 22, right_inner - 8, bottom - 18), outline=glow, width=8)


def _airlock_physics(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    if variant % 4 != 2:
        return
    state, local = v19._beat_state(progress)
    opening = 0.0 if state == 0 else 0.55 * local if state == 1 else 0.55 + 0.35 * local
    x1, y1, x2, y2 = 885, 340, 1335, 790
    gap = round(18 + 125 * opening)
    center = (x1 + x2) // 2
    draw.rounded_rectangle((x1, y1, center - gap, y2), radius=24, fill=(105, 116, 124), outline=cartoon.INK, width=9)
    draw.rounded_rectangle((center + gap, y1, x2, y2), radius=24, fill=(105, 116, 124), outline=cartoon.INK, width=9)
    if opening > 0.12:
        draw.rectangle((center - gap + 10, y1 + 35, center + gap - 10, y2 - 30), fill=(55, 67, 76), outline=cartoon.CYAN, width=6)


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

    image = v21.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if selected.template_id == "route_map":
        return image
    draw = ImageDraw.Draw(image)
    if selected.template_id == "transport_scene":
        _doorway_physics(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "habitat_build":
        _airlock_physics(draw, progress, _ACTIVE_VARIANT)
    return image


cartoon.render_planned_frame = render_planned_frame
