from __future__ import annotations

"""Art Polish v24: full council speaker pose states and clearer focus changes."""

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v12 as v12
from . import cartoon_art_polish_v23 as v23

_ACTIVE_VARIANT = 0


def _speaker_state(progress: float) -> tuple[int, float]:
    value = max(0.0, min(0.999999, progress))
    speaker = min(2, int(value * 3.0))
    local = cartoon._ease(value * 3.0 - speaker)
    return speaker, local


def _council_pose(draw: ImageDraw.ImageDraw, progress: float) -> None:
    speaker, local = _speaker_state(progress)
    centers = (650, 960, 1270)
    colors = (cartoon.BLUE, cartoon.PURPLE, cartoon.AMBER)
    for index, cx in enumerate(centers):
        if index == speaker:
            lean = round(18 + 12 * local)
            v12._human(draw, cx, 430 - lean, 0.86, colors[index], "point")
            draw.rounded_rectangle((cx - 82, 680, cx + 82, 696), radius=8, fill=cartoon.CYAN)
        else:
            v12._human(draw, cx, 448, 0.78, colors[index], "stand")


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
    image = v23.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if selected.template_id == "council_scene":
        _council_pose(ImageDraw.Draw(image), progress)
    return image


cartoon.render_planned_frame = render_planned_frame
