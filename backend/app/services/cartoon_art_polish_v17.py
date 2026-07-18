from __future__ import annotations

"""Art Polish v17: tighten gestures, add restrained background life, and align route exhaust."""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v6 as v6
from . import cartoon_art_polish_v7 as v7
from . import cartoon_art_polish_v12 as v12
from . import cartoon_art_polish_v13 as v13
from . import cartoon_art_polish_v14 as v14
from . import cartoon_art_polish_v15 as v15
from . import cartoon_art_polish_v16 as v16


_ACTIVE_VARIANT = 0


def _phase(progress: float, cycles: float = 1.0) -> float:
    return math.sin(max(0.0, min(1.0, progress)) * math.tau * cycles)


def _integrated_arm(
    draw: ImageDraw.ImageDraw,
    shoulder: tuple[int, int],
    target: tuple[int, int],
    color,
    *,
    elbow_bias: int,
    width: int,
) -> None:
    """Attach a compact gesture to the existing torso without an oversized reach."""
    sx, sy = shoulder
    tx, ty = target
    elbow = ((sx + tx) // 2, (sy + ty) // 2 + elbow_bias)
    draw.rounded_rectangle((sx - 25, sy - 32, sx + 25, sy + 38), radius=15, fill=color, outline=cartoon.INK, width=5)
    draw.ellipse((sx - 19, sy - 19, sx + 19, sy + 19), fill=color, outline=cartoon.INK, width=5)
    draw.line((shoulder, elbow, target), fill=cartoon.INK, width=width, joint="curve")
    draw.ellipse((tx - 10, ty - 10, tx + 10, ty + 10), fill=color, outline=cartoon.INK, width=4)


def _single_walker(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, progress: float, *, robot: bool, color) -> None:
    phase = _phase(progress, 1.35)
    px = x + round(phase * 14 * scale)
    py = y - round(abs(phase) * 5 * scale)
    if robot:
        v6._robot(draw, px, py, scale, "walk")
    else:
        v12._human(draw, px, py, scale, color, "walk")


def _background_life(draw: ImageDraw.ImageDraw, progress: float, variant: int, *, habitat: bool = False) -> None:
    """Use two small distant workers with tiny offsets, avoiding foreground duplication."""
    phase = _phase(progress, 0.65)
    if habitat:
        ground = round(cartoon.OUTPUT_HEIGHT * 0.77)
        positions = ((1390, ground - 118, 0.43), (1540, ground - 105, 0.36))
    else:
        floor = round(cartoon.OUTPUT_HEIGHT * 0.80)
        positions = ((1550, floor - 122, 0.40), (1690, floor - 108, 0.34))
    for index, (x, y, scale) in enumerate(positions):
        dx = round((phase if index == 0 else -phase) * 8)
        v6._robot(draw, x + dx, y, scale, "walk")


def _render_presenter(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    old10 = v13.v10._ACTIVE_VARIANT
    try:
        v13.v10._ACTIVE_VARIANT = variant
        v13.v10._draw_presenter(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    finally:
        v13.v10._ACTIVE_VARIANT = old10

    phase = _phase(progress, 0.85)
    if variant % 4 in (0, 3):
        shoulder = (1165, 500)
        target = (825 + round(48 * phase), 350 - round(22 * abs(phase)))
        color = cartoon.BLUE if variant % 4 == 0 else cartoon.AMBER
    else:
        shoulder = (610, 520)
        target = (1085 + round(55 * phase), 370 - round(20 * abs(phase)))
        color = cartoon.GREEN
    _integrated_arm(draw, shoulder, target, color, elbow_bias=-42, width=15)
    pulse = 19 + round(5 * (0.5 + 0.5 * phase))
    draw.ellipse((target[0] - pulse, target[1] - pulse, target[0] + pulse, target[1] + pulse), outline=cartoon.CYAN, width=4)
    v14._animate_presenter(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, variant)


def _render_council(draw: ImageDraw.ImageDraw, progress: float) -> None:
    v7._draw_council(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    eased = cartoon._ease(progress)
    speaker = min(2, int(eased * 3.0))
    centers = (650, 960, 1270)
    colors = (cartoon.BLUE, cartoon.PURPLE, cartoon.AMBER)
    cx = centers[speaker]
    phase = _phase(progress + speaker * 0.19, 1.15)
    shoulder = (cx, 520)
    target = (cx + round(92 * phase), 392 - round(30 * abs(phase)))
    _integrated_arm(draw, shoulder, target, colors[speaker], elbow_bias=-38, width=16)
    mic_y = 690
    pulse = 18 + round(7 * (0.5 + 0.5 * phase))
    draw.ellipse((cx - pulse, mic_y - pulse // 2, cx + pulse, mic_y + pulse // 2), outline=cartoon.CYAN, width=6)


def _render_transport(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    old13 = v13._ACTIVE_VARIANT
    try:
        v13._ACTIVE_VARIANT = variant
        v13._draw_transport(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    finally:
        v13._ACTIVE_VARIANT = old13
    v14._animate_transport(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, variant)
    floor = round(cartoon.OUTPUT_HEIGHT * 0.80)
    if variant % 2:
        _single_walker(draw, 430, floor - 170, 0.88, progress, robot=False, color=cartoon.AMBER)
    else:
        _single_walker(draw, 1320, floor - 155, 0.80, 1.0 - progress, robot=True, color=cartoon.CYAN)
    _background_life(draw, progress, variant)


def _render_habitat(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    old13 = v13._ACTIVE_VARIANT
    try:
        v13._ACTIVE_VARIANT = variant
        v13._draw_habitat(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    finally:
        v13._ACTIVE_VARIANT = old13
    v14._animate_habitat(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, variant)
    if variant % 4 == 2:
        phase = _phase(progress, 0.82)
        shoulder = (1035, 600)
        target = (1095 + round(38 * phase), 515 - round(20 * abs(phase)))
        _integrated_arm(draw, shoulder, target, (120, 153, 169), elbow_bias=-24, width=15)
        draw.ellipse((target[0] - 14, target[1] - 14, target[0] + 14, target[1] + 14), fill=cartoon.CYAN, outline=cartoon.INK, width=4)
    _background_life(draw, progress, variant, habitat=True)


def _bezier_point(p0, p1, p2, t: float) -> tuple[float, float]:
    one = 1.0 - t
    return (
        one * one * p0[0] + 2 * one * t * p1[0] + t * t * p2[0],
        one * one * p0[1] + 2 * one * t * p1[1] + t * t * p2[1],
    )


def _bezier_tangent(p0, p1, p2, t: float) -> tuple[float, float]:
    return (
        2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0]),
        2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1]),
    )


def _rotated_spacecraft_with_exhaust(image: Image.Image, x: int, y: int, scale: float, progress: float, angle: float) -> None:
    """Draw the plume on the spacecraft layer so body and exhaust rotate together."""
    pad = 440
    sprite = Image.new("RGBA", (pad * 2, pad * 2), (0, 0, 0, 0))
    sprite_draw = ImageDraw.Draw(sprite)
    plume = 70 + round(22 * (0.5 + 0.5 * math.sin(progress * math.pi * 8)))
    sprite_draw.polygon(
        ((pad - round(145 * scale), pad), (pad - round((145 + plume) * scale), pad - round(28 * scale)), (pad - round((145 + plume) * scale), pad + round(28 * scale))),
        fill=cartoon.AMBER,
        outline=cartoon.INK,
    )
    v7._spacecraft(sprite_draw, pad, pad, scale, progress)
    rotated = sprite.rotate(-math.degrees(angle), resample=Image.Resampling.BICUBIC, expand=True)
    image.paste(rotated, (round(x - rotated.width / 2), round(y - rotated.height / 2)), rotated)


def _draw_route_map(image: Image.Image, progress: float) -> None:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    variant = _ACTIVE_VARIANT % 3
    draw.rectangle((0, 0, width, height), fill=cartoon.PAPER)
    for index in range(30):
        sx = (index * 181) % width
        sy = 24 + (index * 83) % round(height * 0.38)
        radius = 2 + index % 3
        draw.ellipse((sx - radius, sy - radius, sx + radius, sy + radius), fill=cartoon.MUTED)
    layouts = (
        ((360, 690), (1540, 410), (960, 130), 225, 190),
        ((300, 760), (1580, 300), (930, 100), 180, 235),
        ((270, 760), (1480, 560), (850, 180), 135, 285),
    )
    earth, mars, control, earth_r, mars_r = layouts[variant]
    cartoon._planet(draw, earth, earth_r, cartoon.BLUE, progress)
    cartoon._planet(draw, mars, mars_r, cartoon.MARS, 1 - progress)
    points = [_bezier_point(earth, control, mars, step / 64) for step in range(65)]
    for index in range(0, len(points) - 1, 2):
        draw.line((points[index], points[index + 1]), fill=cartoon.INK, width=10)
    ship_scale = 0.76 if variant < 2 else 0.70
    safe_start, safe_end = v14._safe_route_interval(earth, mars, control, earth_r, mars_r, ship_scale)
    safe_start = min(safe_end, safe_start + 0.022)
    safe_end = max(safe_start, safe_end - 0.025)
    travel_t = safe_start + (safe_end - safe_start) * cartoon._ease(progress)
    ship_x, ship_y = _bezier_point(earth, control, mars, travel_t)
    tangent_x, tangent_y = _bezier_tangent(earth, control, mars, travel_t)
    angle = math.atan2(tangent_y, tangent_x)
    _rotated_spacecraft_with_exhaust(image, round(ship_x), round(ship_y), ship_scale, progress, angle)


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

    image = Image.new("RGB", (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT), cartoon.PAPER)
    if selected.template_id == "route_map":
        _draw_route_map(image, progress)
        return v14._camera_move(image, progress, _ACTIVE_VARIANT, selected.template_id)

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
