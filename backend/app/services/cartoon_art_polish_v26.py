from __future__ import annotations

"""Art Polish v26: smooth physical scene transitions with anticipations and settles."""

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v25 as v25


def _window(value: float, start: float, end: float) -> float:
    if value <= start or value >= end:
        return 0.0
    local = (value - start) / max(0.001, end - start)
    return 4.0 * local * (1.0 - local)


def _transition_cue(draw: ImageDraw.ImageDraw, progress: float, template_id: str) -> None:
    anticipation = _window(progress, 0.18, 0.42)
    settle = _window(progress, 0.66, 0.94)
    if template_id == "transport_scene":
        floor = round(cartoon.OUTPUT_HEIGHT * 0.80)
        width = round(90 + 330 * anticipation + 180 * settle)
        draw.line((960 - width, floor - 58, 960 + width, floor - 58), fill=cartoon.GREEN, width=5)
    elif template_id == "habitat_build":
        radius = round(18 + 20 * anticipation + 12 * settle)
        draw.arc((1110 - radius, 525 - radius, 1110 + radius, 525 + radius), 205, 515, fill=cartoon.GREEN, width=5)
    elif template_id == "presenter_desk":
        x = 785 if anticipation >= settle else 1110
        width = round(35 + 85 * max(anticipation, settle))
        draw.rounded_rectangle((x - width, 365, x + width, 374), radius=5, fill=cartoon.CYAN)
    elif template_id == "council_scene":
        center = (650, 960, 1270)[min(2, int(max(0.0, min(0.999, progress)) * 3.0))]
        half = round(45 + 45 * max(anticipation, settle))
        draw.rounded_rectangle((center - half, 720, center + half, 730), radius=5, fill=cartoon.CYAN)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    beat = cartoon._beat_for_time(scene, time_seconds)
    extra = str((beat or {}).get("visual_intent", ""))
    selected = cartoon.TEMPLATE_BY_ID.get(template_id or "")
    if selected is None or beat is not None:
        selected, _confidence, _reason = cartoon.suggest_template(scene, extra)
    beat_start = float((beat or {}).get("relative_start_seconds", 0.0))
    beat_end = float((beat or {}).get("relative_end_seconds", duration_seconds))
    progress = cartoon._ease((time_seconds - beat_start) / max(0.001, beat_end - beat_start))
    image = v25.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if selected.template_id != "route_map":
        _transition_cue(ImageDraw.Draw(image), progress, selected.template_id)
    return image


cartoon.render_planned_frame = render_planned_frame
