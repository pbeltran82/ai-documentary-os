from __future__ import annotations

"""Art Polish v16: integrate gestures, reduce duplicate actors, and soften motion overlays."""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v6 as v6
from . import cartoon_art_polish_v7 as v7
from . import cartoon_art_polish_v12 as v12
from . import cartoon_art_polish_v13 as v13
from . import cartoon_art_polish_v14 as v14
from . import cartoon_art_polish_v15 as v15


_ACTIVE_VARIANT = 0


def _phase(progress: float, cycles: float = 1.0) -> float:
    return math.sin(max(0.0, min(1.0, progress)) * math.tau * cycles)


def _shoulder_cap(draw: ImageDraw.ImageDraw, x: int, y: int, radius: int, color) -> None:
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color, outline=cartoon.INK, width=max(4, radius // 3))


def _integrated_arm(
    draw: ImageDraw.ImageDraw,
    shoulder: tuple[int, int],
    target: tuple[int, int],
    color,
    *,
    elbow_bias: int = -40,
    width: int = 18,
) -> None:
    sx, sy = shoulder
    tx, ty = target
    elbow = ((sx + tx) // 2, (sy + ty) // 2 + elbow_bias)
    # Torso patch and shoulder cap visually attach the animated limb to the body.
    draw.rounded_rectangle((sx - 30, sy - 38, sx + 30, sy + 44), radius=18, fill=color, outline=cartoon.INK, width=6)
    _shoulder_cap(draw, sx, sy, 23, color)
    draw.line((shoulder, elbow, target), fill=cartoon.INK, width=width, joint="curve")
    draw.ellipse((tx - 12, ty - 12, tx + 12, ty + 12), fill=color, outline=cartoon.INK, width=4)


def _single_walker(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, progress: float, *, robot: bool, color) -> None:
    phase = _phase(progress, 1.5)
    px = x + round(phase * 18 * scale)
    py = y - round(abs(phase) * 6 * scale)
    if robot:
        v6._robot(draw, px, py, scale, "walk")
    else:
        v12._human(draw, px, py, scale, color, "walk")


def _render_presenter(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    old10 = v13.v10._ACTIVE_VARIANT
    try:
        v13.v10._ACTIVE_VARIANT = variant
        v13.v10._draw_presenter(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    finally:
        v13.v10._ACTIVE_VARIANT = old10

    phase = _phase(progress, 0.9)
    if variant % 4 in (0, 3):
        shoulder = (1165, 500)
        target = (720 + round(70 * phase), 330 - round(30 * abs(phase)))
        color = cartoon.BLUE if variant % 4 == 0 else cartoon.AMBER
    else:
        shoulder = (610, 520)
        target = (1220 + round(85 * phase), 350 - round(28 * abs(phase)))
        color = cartoon.GREEN
    _integrated_arm(draw, shoulder, target, color, elbow_bias=-55, width=17)
    pulse = 24 + round(7 * (0.5 + 0.5 * phase))
    draw.ellipse((target[0] - pulse, target[1] - pulse, target[0] + pulse, target[1] + pulse), outline=cartoon.CYAN, width=5)
    v14._animate_presenter(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, variant)


def _render_council(draw: ImageDraw.ImageDraw, progress: float) -> None:
    v7._draw_council(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    eased = cartoon._ease(progress)
    speaker = min(2, int(eased * 3.0))
    centers = (650, 960, 1270)
    colors = (cartoon.BLUE, cartoon.PURPLE, cartoon.AMBER)
    cx = centers[speaker]
    phase = _phase(progress + speaker * 0.17, 1.25)
    shoulder = (cx, 520)
    target = (cx + round(75 * phase), 410 - round(22 * abs(phase)))
    _integrated_arm(draw, shoulder, target, colors[speaker], elbow_bias=-32, width=15)
    mic_y = 690
    pulse = 16 + round(5 * (0.5 + 0.5 * phase))
    draw.ellipse((cx - pulse, mic_y - pulse // 2, cx + pulse, mic_y + pulse // 2), outline=cartoon.CYAN, width=5)


def _render_transport(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    old13 = v13._ACTIVE_VARIANT
    try:
        v13._ACTIVE_VARIANT = variant
        v13._draw_transport(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    finally:
        v13._ACTIVE_VARIANT = old13
    v14._animate_transport(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, variant)
    # One focal walker only: avoids doubling the already populated v13 layouts.
    floor = round(cartoon.OUTPUT_HEIGHT * 0.80)
    if variant % 2:
        _single_walker(draw, 430, floor - 170, 0.90, progress, robot=False, color=cartoon.AMBER)
    else:
        _single_walker(draw, 1320, floor - 155, 0.82, 1.0 - progress, robot=True, color=cartoon.CYAN)


def _render_habitat(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    old13 = v13._ACTIVE_VARIANT
    try:
        v13._ACTIVE_VARIANT = variant
        v13._draw_habitat(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    finally:
        v13._ACTIVE_VARIANT = old13
    v14._animate_habitat(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, variant)

    if variant % 4 == 2:
        phase = _phase(progress, 0.85)
        shoulder = (1035, 600)
        target = (1115 + round(48 * phase), 505 - round(25 * abs(phase)))
        _integrated_arm(draw, shoulder, target, (120, 153, 169), elbow_bias=-28, width=16)
        draw.ellipse((target[0] - 16, target[1] - 16, target[0] + 16, target[1] + 16), fill=cartoon.CYAN, outline=cartoon.INK, width=4)
    elif variant % 4 == 1:
        ground = round(cartoon.OUTPUT_HEIGHT * 0.77)
        _single_walker(draw, 980, ground - 165, 0.70, progress, robot=True, color=cartoon.GREEN)


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

    # Keep the proven rotated-route renderer from v15 intact.
    if selected.template_id == "route_map":
        return v15.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)

    image = Image.new("RGB", (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT), cartoon.PAPER)
    draw = ImageDraw.Draw(image)

    if selected.template_id == "presenter_desk":
        _render_presenter(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "council_scene":
        _render_council(draw, progress)
    elif selected.template_id == "transport_scene":
        _render_transport(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "habitat_build":
        _render_habitat(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "crowd_focus":
        old13 = v13._ACTIVE_VARIANT
        try:
            v13._ACTIVE_VARIANT = _ACTIVE_VARIANT
            v13._draw_crowd_scene(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
        finally:
            v13._ACTIVE_VARIANT = old13
    else:
        cartoon._draw_process(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)

    return v14._camera_move(image, progress, _ACTIVE_VARIANT, selected.template_id)


cartoon.render_planned_frame = render_planned_frame
