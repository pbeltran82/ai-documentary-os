from __future__ import annotations

"""Art Polish v18: ambient motion hierarchy without compounding camera crops."""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v17 as v17


_ACTIVE_VARIANT = 0


def _phase(progress: float, cycles: float = 1.0, offset: float = 0.0) -> float:
    value = max(0.0, min(1.0, progress))
    return math.sin((value * cycles + offset) * math.tau)


def _blink(draw: ImageDraw.ImageDraw, x: int, y: int, progress: float, offset: float = 0.0) -> None:
    pulse = _phase(progress, 2.2, offset)
    if pulse < -0.74:
        draw.arc((x - 13, y - 5, x + 13, y + 7), 10, 170, fill=cartoon.INK, width=4)
    else:
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=cartoon.INK)


def _head_cue(draw: ImageDraw.ImageDraw, x: int, y: int, progress: float, offset: float = 0.0) -> None:
    shift = round(5 * _phase(progress, 0.48, offset))
    draw.arc((x - 18 + shift, y - 12, x + 18 + shift, y + 13), 205, 330, fill=cartoon.DARK_MUTED, width=4)


def _transport_ambient(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    floor = round(cartoon.OUTPUT_HEIGHT * 0.80)
    sweep = round(260 + cartoon._ease(progress) * 1180)
    draw.line((sweep, floor - 12, sweep + 90, floor - 12), fill=cartoon.CYAN, width=6)
    for index, x in enumerate((520, 790, 1080, 1370)):
        pulse = 6 + round(3 * (0.5 + 0.5 * _phase(progress, 1.5, index * 0.19)))
        draw.ellipse((x - pulse, 175 - pulse, x + pulse, 175 + pulse), fill=cartoon.GREEN if index % 2 else cartoon.CYAN, outline=cartoon.INK, width=3)
    _head_cue(draw, 770, 600, progress, 0.12)
    _head_cue(draw, 1285, 610, progress, 0.47)


def _habitat_ambient(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    ground = round(cartoon.OUTPUT_HEIGHT * 0.77)
    antenna_x = 1450 if variant % 2 else 520
    sweep = round(34 * _phase(progress, 0.44))
    draw.line((antenna_x, ground - 220, antenna_x + sweep, ground - 280), fill=cartoon.INK, width=7)
    draw.ellipse((antenna_x + sweep - 9, ground - 289, antenna_x + sweep + 9, ground - 271), fill=cartoon.AMBER, outline=cartoon.INK, width=3)
    for index in range(2):
        drift = round((progress * 95 + index * 125) % 360)
        x = 220 + drift * 4
        y = ground - 30 - index * 22
        draw.arc((x, y, x + 105, y + 38), 190, 340, fill=(151, 94, 69), width=4)
    _blink(draw, 1110, 535, progress, 0.18)


def _presenter_ambient(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    if variant % 4 in (0, 3):
        eye = (1160, 365)
        screen_x = 770
    else:
        eye = (605, 385)
        screen_x = 1090
    _blink(draw, eye[0], eye[1], progress, 0.23)
    marker_y = round(275 + 42 * (0.5 + 0.5 * _phase(progress, 0.55)))
    draw.ellipse((screen_x - 8, marker_y - 8, screen_x + 8, marker_y + 8), fill=cartoon.AMBER, outline=cartoon.INK, width=3)


def _council_ambient(draw: ImageDraw.ImageDraw, progress: float) -> None:
    speaker = min(2, int(cartoon._ease(progress) * 3.0))
    centers = (650, 960, 1270)
    for index, cx in enumerate(centers):
        offset = index * 0.21
        _blink(draw, cx, 420, progress, offset)
        if index != speaker:
            nod = round(4 * _phase(progress, 0.38, offset))
            draw.arc((cx - 20, 455 + nod, cx + 20, 475 + nod), 20, 160, fill=cartoon.DARK_MUTED, width=3)


def _crowd_ambient(draw: ImageDraw.ImageDraw, progress: float) -> None:
    heads = ((335, 590), (720, 620), (1115, 590), (1515, 615))
    for index, (x, y) in enumerate(heads):
        _head_cue(draw, x, y, progress, index * 0.17)
    sign_x = round(790 + 130 * (0.5 + 0.5 * _phase(progress, 0.28)))
    draw.rounded_rectangle((sign_x, 380, sign_x + 70, 399), radius=7, fill=cartoon.AMBER)


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

    image = v17.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if selected.template_id == "route_map":
        return image

    draw = ImageDraw.Draw(image)
    if selected.template_id == "transport_scene":
        _transport_ambient(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "habitat_build":
        _habitat_ambient(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "presenter_desk":
        _presenter_ambient(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "council_scene":
        _council_ambient(draw, progress)
    elif selected.template_id == "crowd_focus":
        _crowd_ambient(draw, progress)
    return image


cartoon.render_planned_frame = render_planned_frame
