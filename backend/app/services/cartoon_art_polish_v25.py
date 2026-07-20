from __future__ import annotations

"""Art Polish v25: unmistakable foreground crowd crossing and open-lane staging."""

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v12 as v12
from . import cartoon_art_polish_v24 as v24


def _crowd_crossing(draw: ImageDraw.ImageDraw, progress: float) -> None:
    value = max(0.0, min(1.0, progress))
    floor = round(cartoon.OUTPUT_HEIGHT * 0.76)
    # Clear visual lane.
    draw.rounded_rectangle((260, floor - 16, 1580, floor + 26), radius=16, fill=(187, 197, 204), outline=cartoon.INK, width=4)
    if 0.18 <= value <= 0.82:
        local = cartoon._ease((value - 0.18) / 0.64)
        x = round(330 + 1160 * local)
        y = floor - 205 - round(8 * abs(2 * local - 1))
        v12._human(draw, x, y, 1.20, cartoon.BLUE, "walk")
        draw.rounded_rectangle((x - 95, floor + 10, x + 95, floor + 22), radius=6, fill=cartoon.CYAN)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    beat = cartoon._beat_for_time(scene, time_seconds)
    extra = str((beat or {}).get("visual_intent", ""))
    selected = cartoon.TEMPLATE_BY_ID.get(template_id or "")
    if selected is None or beat is not None:
        selected, _confidence, _reason = cartoon.suggest_template(scene, extra)
    beat_start = float((beat or {}).get("relative_start_seconds", 0.0))
    beat_end = float((beat or {}).get("relative_end_seconds", duration_seconds))
    progress = cartoon._ease((time_seconds - beat_start) / max(0.001, beat_end - beat_start))
    image = v24.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if selected.template_id == "crowd_focus":
        _crowd_crossing(ImageDraw.Draw(image), progress)
    return image


cartoon.render_planned_frame = render_planned_frame
