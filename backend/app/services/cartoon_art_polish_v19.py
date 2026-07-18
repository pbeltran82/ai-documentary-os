from __future__ import annotations

"""Art Polish v19: staged mid-scene beats and stronger focal motion hierarchy."""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v6 as v6
from . import cartoon_art_polish_v12 as v12
from . import cartoon_art_polish_v18 as v18


_ACTIVE_VARIANT = 0


def _phase(progress: float, cycles: float = 1.0, offset: float = 0.0) -> float:
    value = max(0.0, min(1.0, progress))
    return math.sin((value * cycles + offset) * math.tau)


def _beat_state(progress: float) -> tuple[int, float]:
    """Return opening, action, or settle state plus local eased progress."""
    value = max(0.0, min(0.999999, progress))
    state = min(2, int(value * 3.0))
    local = value * 3.0 - state
    return state, cartoon._ease(local)


def _transport_beat(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    state, local = _beat_state(progress)
    floor = round(cartoon.OUTPUT_HEIGHT * 0.80)
    colors = (cartoon.CYAN, cartoon.GREEN, cartoon.AMBER)

    if variant % 4 == 0:
        portal = (715, 285, 1205, 680)
        inset = 44 if state == 0 else round(44 - 28 * local) if state == 1 else 16
        draw.rounded_rectangle(
            (portal[0] + inset, portal[1] + inset, portal[2] - inset, portal[3]),
            radius=22,
            outline=colors[state],
            width=9,
        )
        ramp_progress = 0.0 if state == 0 else local if state == 1 else 1.0
        ramp_width = round(150 + 420 * ramp_progress)
        draw.line((960 - ramp_width // 2, floor - 8, 960 + ramp_width // 2, floor - 8), fill=colors[state], width=12)
    else:
        lengths = (260, 610, 180)
        center = round(960 + (local - 0.5) * 90)
        draw.line((center - lengths[state] // 2, floor - 10, center + lengths[state] // 2, floor - 10), fill=colors[state], width=10)

    if state == 1:
        actor_x = round(250 + 920 * local)
        actor_y = floor - 170 - round(8 * abs(_phase(local, 1.5)))
        v12._human(draw, actor_x, actor_y, 0.94, cartoon.AMBER, "walk")
    elif state == 2:
        v6._robot(draw, 1280, floor - 150, 0.82, "stand")


def _habitat_beat(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    state, local = _beat_state(progress)
    ground = round(cartoon.OUTPUT_HEIGHT * 0.77)

    if variant % 4 == 2:
        # Panel close-up: idle, operate, confirm.
        panel_x, panel_y = 1110, 525
        if state == 0:
            light = cartoon.CYAN
            radius = 16
        elif state == 1:
            light = cartoon.AMBER
            radius = 18 + round(10 * local)
        else:
            light = cartoon.GREEN
            radius = 24
        draw.ellipse((panel_x - radius, panel_y - radius, panel_x + radius, panel_y + radius), fill=light, outline=cartoon.INK, width=5)
        if state == 1:
            hand_x = round(1030 + 72 * local)
            hand_y = round(615 - 86 * local)
            draw.line((1030, 615, hand_x, hand_y), fill=cartoon.INK, width=16)
            draw.ellipse((hand_x - 12, hand_y - 12, hand_x + 12, hand_y + 12), fill=(120, 153, 169), outline=cartoon.INK, width=4)
    else:
        # Wide habitat: arrival, crossing, destination pause.
        if state == 0:
            x = 740
        elif state == 1:
            x = round(740 + 430 * local)
        else:
            x = 1170
        v6._robot(draw, x, ground - 160, 0.76, "walk" if state == 1 else "stand")
        if state == 2:
            draw.line((x + 25, ground - 210, x + 110, ground - 260), fill=cartoon.INK, width=11)


def _presenter_beat(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    state, local = _beat_state(progress)
    right_side = variant % 4 in (0, 3)
    body_x = 1165 if right_side else 610
    body_y = 500 if right_side else 520
    direction = -1 if right_side else 1

    # Compact torso lean makes the pointing gesture feel motivated.
    lean = 0 if state == 0 else round(direction * (10 + 16 * local)) if state == 1 else round(direction * 18)
    draw.rounded_rectangle(
        (body_x - 34 + lean, body_y - 45, body_x + 34 + lean, body_y + 50),
        radius=18,
        fill=cartoon.BLUE if right_side and variant % 4 == 0 else cartoon.AMBER if right_side else cartoon.GREEN,
        outline=cartoon.INK,
        width=6,
    )
    head_shift = 0 if state == 0 else round(direction * 12 * local) if state == 1 else round(direction * 12)
    draw.arc((body_x - 30 + head_shift, body_y - 145, body_x + 30 + head_shift, body_y - 95), 200, 340, fill=cartoon.DARK_MUTED, width=5)

    if state == 2:
        marker_x = 770 if right_side else 1090
        marker_y = 300
        draw.ellipse((marker_x - 24, marker_y - 24, marker_x + 24, marker_y + 24), outline=cartoon.GREEN, width=7)


def _council_beat(draw: ImageDraw.ImageDraw, progress: float) -> None:
    state, local = _beat_state(progress)
    centers = (650, 960, 1270)
    speaker = state
    cx = centers[speaker]
    lean = round((local if state == 1 else 1.0 if state == 2 else 0.35) * 18)

    draw.rounded_rectangle((cx - 42, 470 - lean, cx + 42, 565 - lean), radius=18, outline=cartoon.CYAN, width=7)
    hand_x = round(cx + 55 + 45 * _phase(local, 0.65, speaker * 0.17))
    hand_y = round(435 - 28 * abs(_phase(local, 0.65, speaker * 0.17)))
    draw.line((cx, 525 - lean, hand_x, hand_y), fill=cartoon.INK, width=15)
    draw.ellipse((hand_x - 11, hand_y - 11, hand_x + 11, hand_y + 11), fill=cartoon.AMBER, outline=cartoon.INK, width=4)


def _crowd_beat(draw: ImageDraw.ImageDraw, progress: float) -> None:
    state, local = _beat_state(progress)
    floor = round(cartoon.OUTPUT_HEIGHT * 0.76)
    if state == 0:
        x = 360
    elif state == 1:
        x = round(360 + 690 * local)
    else:
        x = 1050
    color = cartoon.GREEN if state == 2 else cartoon.BLUE
    v12._human(draw, x, floor - 190, 1.05, color, "walk" if state == 1 else "stand")


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

    image = v18.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if selected.template_id == "route_map":
        return image

    draw = ImageDraw.Draw(image)
    if selected.template_id == "transport_scene":
        _transport_beat(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "habitat_build":
        _habitat_beat(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "presenter_desk":
        _presenter_beat(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "council_scene":
        _council_beat(draw, progress)
    elif selected.template_id == "crowd_focus":
        _crowd_beat(draw, progress)
    return image


cartoon.render_planned_frame = render_planned_frame
