from __future__ import annotations

"""Art Polish v27: normalize motion intensity and focal emphasis across scene families."""

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v26 as v26


def _focus_frame(draw: ImageDraw.ImageDraw, progress: float, template_id: str) -> None:
    value = max(0.0, min(1.0, progress))
    pulse = 0.5 - 0.5 * abs(2.0 * value - 1.0)
    if pulse <= 0.05:
        return
    boxes = {
        "transport_scene": (580, 210, 1340, 780),
        "habitat_build": (760, 250, 1450, 830),
        "presenter_desk": (420, 175, 1510, 760),
        "council_scene": (470, 300, 1450, 760),
        "crowd_focus": (260, 290, 1640, 880),
    }
    box = boxes.get(template_id)
    if box is None:
        return
    inset = round(14 + 18 * pulse)
    draw.rounded_rectangle((box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset), radius=28, outline=cartoon.CYAN, width=3)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    beat = cartoon._beat_for_time(scene, time_seconds)
    extra = str((beat or {}).get("visual_intent", ""))
    selected = cartoon.TEMPLATE_BY_ID.get(template_id or "")
    if selected is None or beat is not None:
        selected, _confidence, _reason = cartoon.suggest_template(scene, extra)
    beat_start = float((beat or {}).get("relative_start_seconds", 0.0))
    beat_end = float((beat or {}).get("relative_end_seconds", duration_seconds))
    progress = cartoon._ease((time_seconds - beat_start) / max(0.001, beat_end - beat_start))
    image = v26.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if selected.template_id != "route_map":
        _focus_frame(ImageDraw.Draw(image), progress, selected.template_id)
    return image


cartoon.render_planned_frame = render_planned_frame
