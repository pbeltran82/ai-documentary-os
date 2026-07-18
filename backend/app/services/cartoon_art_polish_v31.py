from __future__ import annotations

"""Art Polish v31: mask legacy doorway geometry before physical door redraws."""

from PIL import Image, ImageDraw
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v19 as v19
from . import cartoon_art_polish_v30 as v30


def _context(scene, template_id, duration_seconds, time_seconds):
    beat = cartoon._beat_for_time(scene, time_seconds)
    selected = cartoon.TEMPLATE_BY_ID.get(template_id or "")
    if selected is None or beat is not None:
        selected, _c, _r = cartoon.suggest_template(scene, str((beat or {}).get("visual_intent", "")))
    start = float((beat or {}).get("relative_start_seconds", 0.0))
    end = float((beat or {}).get("relative_end_seconds", duration_seconds))
    progress = cartoon._ease((time_seconds - start) / max(0.001, end - start))
    scene_number = int(getattr(scene, "scene_number", 1) or 1)
    variant = (scene_number * 7 + {"transport_scene": 0, "habitat_build": 1, "presenter_desk": 2, "crowd_focus": 3, "route_map": 4, "council_scene": 5}.get(selected.template_id, 0)) % 12
    return selected, progress, variant


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v30.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    selected, progress, variant = _context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id == "transport_scene" and variant % 4 == 0:
        draw = ImageDraw.Draw(image)
        state, local = v19._beat_state(progress)
        opening = 0.0 if state == 0 else local if state == 1 else 1.0
        gap = round(24 + 170 * opening)
        center, top, bottom = 960, 300, 675
        draw.rectangle((730, top - 8, 1190, bottom + 8), fill=(55, 67, 76))
        panel_w = 205
        left_inner, right_inner = center - gap, center + gap
        fill = (82, 94, 104)
        draw.rounded_rectangle((left_inner - panel_w, top, left_inner, bottom), radius=22, fill=fill, outline=cartoon.INK, width=8)
        draw.rounded_rectangle((right_inner, top, right_inner + panel_w, bottom), radius=22, fill=fill, outline=cartoon.INK, width=8)
        if opening > 0.15:
            glow = cartoon.GREEN if state == 2 else cartoon.CYAN
            draw.rectangle((left_inner + 8, top + 22, right_inner - 8, bottom - 18), outline=glow, width=8)
    return image


cartoon.render_planned_frame = render_planned_frame
