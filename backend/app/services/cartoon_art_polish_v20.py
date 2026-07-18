from __future__ import annotations

"""Art Polish v20: smooth v19 beat transitions and strengthen environmental response."""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v19 as v19


_ACTIVE_VARIANT = 0


def _smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def _window(progress: float, start: float, end: float, feather: float = 0.08) -> float:
    """Return a softly feathered weight for one time window."""
    if progress <= start - feather or progress >= end + feather:
        return 0.0
    if progress < start:
        return _smoothstep((progress - (start - feather)) / feather)
    if progress > end:
        return 1.0 - _smoothstep((progress - end) / feather)
    return 1.0


def _transport_response(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    floor = round(cartoon.OUTPUT_HEIGHT * 0.80)
    action = _window(progress, 0.27, 0.72, 0.10)
    settle = _window(progress, 0.68, 1.0, 0.08)

    if variant % 4 == 0:
        # Portal illumination breathes into the action beat, then settles green.
        pulse = round(8 + 10 * action + 4 * math.sin(progress * math.tau * 2.0) * action)
        color = cartoon.GREEN if settle > 0.45 else cartoon.CYAN
        for x in (685, 1235):
            draw.rounded_rectangle((x - pulse, 300, x + pulse, 620), radius=8, outline=color, width=5)
    else:
        # A restrained approach marker expands during boarding and contracts after it clears.
        half = round(90 + 240 * action - 130 * settle)
        draw.line((960 - half, floor - 24, 960 + half, floor - 24), fill=cartoon.GREEN, width=6)


def _habitat_response(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    if variant % 4 != 2:
        return
    action = _window(progress, 0.30, 0.70, 0.08)
    settle = _window(progress, 0.67, 1.0, 0.07)
    panel_x, panel_y = 1110, 525

    if action > 0.0:
        radius = round(28 + 18 * action)
        draw.ellipse((panel_x - radius, panel_y - radius, panel_x + radius, panel_y + radius), outline=cartoon.AMBER, width=5)
    if settle > 0.0:
        radius = round(34 + 10 * settle)
        draw.arc((panel_x - radius, panel_y - radius, panel_x + radius, panel_y + radius), 210, 510, fill=cartoon.GREEN, width=7)


def _presenter_response(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    action = _window(progress, 0.28, 0.72, 0.09)
    settle = _window(progress, 0.68, 1.0, 0.07)
    right_side = variant % 4 in (0, 3)
    direction = -1 if right_side else 1
    body_x = 1165 if right_side else 610
    body_y = 500 if right_side else 520
    color = cartoon.BLUE if right_side and variant % 4 == 0 else cartoon.AMBER if right_side else cartoon.GREEN

    # A small shoulder shift bridges the static body and the v19 pointing action.
    shoulder_x = round(body_x + direction * (6 + 12 * action - 5 * settle))
    shoulder_y = round(body_y - 6 * action)
    draw.ellipse((shoulder_x - 20, shoulder_y - 20, shoulder_x + 20, shoulder_y + 20), fill=color, outline=cartoon.INK, width=5)

    if settle > 0.0:
        marker_x = 770 if right_side else 1090
        marker_y = 300
        radius = round(28 + 10 * settle)
        draw.arc((marker_x - radius, marker_y - radius, marker_x + radius, marker_y + radius), 195, 510, fill=cartoon.GREEN, width=6)


def _council_response(draw: ImageDraw.ImageDraw, progress: float) -> None:
    state, local = v19._beat_state(progress)
    centers = (650, 960, 1270)
    cx = centers[state]
    transition = _window(local, 0.0, 0.32, 0.0)

    # A desk light moves to the next speaker before the gesture reaches full extension.
    width = round(65 + 45 * transition)
    draw.rounded_rectangle((cx - width, 675, cx + width, 691), radius=8, fill=cartoon.CYAN, outline=cartoon.INK, width=3)


def _crowd_response(draw: ImageDraw.ImageDraw, progress: float) -> None:
    action = _window(progress, 0.29, 0.71, 0.08)
    if action <= 0.0:
        return
    floor = round(cartoon.OUTPUT_HEIGHT * 0.76)
    center = round(420 + 610 * cartoon._ease((progress - 0.29) / 0.42))
    shadow_w = round(58 + 28 * action)
    draw.ellipse((center - shadow_w, floor - 12, center + shadow_w, floor + 12), fill=(145, 151, 158))


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

    image = v19.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if selected.template_id == "route_map":
        return image

    draw = ImageDraw.Draw(image)
    if selected.template_id == "transport_scene":
        _transport_response(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "habitat_build":
        _habitat_response(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "presenter_desk":
        _presenter_response(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "council_scene":
        _council_response(draw, progress)
    elif selected.template_id == "crowd_focus":
        _crowd_response(draw, progress)
    return image


cartoon.render_planned_frame = render_planned_frame
