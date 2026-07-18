from __future__ import annotations

"""Art Polish v15: character pose cycles and tangent-oriented route travel."""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v6 as v6
from . import cartoon_art_polish_v7 as v7
from . import cartoon_art_polish_v12 as v12
from . import cartoon_art_polish_v13 as v13
from . import cartoon_art_polish_v14 as v14


_ACTIVE_VARIANT = 0


def _phase(progress: float, cycles: float = 2.0) -> float:
    """Smooth repeatable motion phase in the range -1..1."""
    return math.sin(max(0.0, min(1.0, progress)) * math.tau * cycles)


def _motion_lines(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, direction: int = 1) -> None:
    length = round(46 * scale)
    gap = round(18 * scale)
    for index in range(3):
        yy = y + index * gap
        draw.line((x, yy, x - direction * (length - index * 8), yy + index * 2), fill=cartoon.DARK_MUTED, width=max(3, round(5 * scale)))


def _walking_actor(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color, progress: float, robot: bool = False) -> None:
    """Draw a readable actor with alternating stride and gentle vertical weight shift."""
    phase = _phase(progress, 2.25)
    bob = round(abs(phase) * 7 * scale)
    px = x + round(phase * 12 * scale)
    py = y - bob
    pose = "walk"
    if robot:
        v6._robot(draw, px, py, scale, pose)
    else:
        v12._human(draw, px, py, scale, color, pose)
    direction = 1 if phase >= 0 else -1
    _motion_lines(draw, px - direction * round(38 * scale), py + round(120 * scale), scale * 0.72, direction)


def _presenter_gesture(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, variant: int) -> None:
    """Make the presenter visibly teach: pointing hand, head cue, and chart marker."""
    phase = _phase(progress, 1.2)
    if variant % 4 in (0, 3):
        shoulder = (round(width * 0.61), round(height * 0.45))
        target = (round(width * (0.36 + 0.05 * phase)), round(height * (0.31 - 0.03 * phase)))
    else:
        shoulder = (round(width * 0.31), round(height * 0.47))
        target = (round(width * (0.61 + 0.06 * phase)), round(height * (0.34 - 0.04 * phase)))
    elbow = ((shoulder[0] + target[0]) // 2, shoulder[1] - round(45 + 20 * phase))
    draw.line((shoulder, elbow, target), fill=cartoon.INK, width=18, joint="curve")
    draw.ellipse((target[0] - 13, target[1] - 13, target[0] + 13, target[1] + 13), fill=cartoon.AMBER, outline=cartoon.INK, width=4)
    pulse = 24 + round(8 * (0.5 + 0.5 * phase))
    draw.ellipse((target[0] - pulse, target[1] - pulse, target[0] + pulse, target[1] + pulse), outline=cartoon.CYAN, width=5)


def _transport_people(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, variant: int) -> None:
    floor = round(height * 0.80)
    travel = cartoon._ease(progress)
    _walking_actor(draw, round(410 + 330 * travel), floor - 170, 0.92, cartoon.AMBER, progress, robot=False)
    _walking_actor(draw, round(1290 - 250 * travel), floor - 155, 0.82, cartoon.CYAN, 1.0 - progress, robot=True)
    gate_y = 145
    pulse = 13 + round(7 * (0.5 + 0.5 * _phase(progress, 3.0)))
    draw.ellipse((width - 240 - pulse, gate_y - pulse, width - 240 + pulse, gate_y + pulse), fill=cartoon.GREEN, outline=cartoon.INK, width=4)


def _habitat_people(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, variant: int) -> None:
    ground = round(height * 0.77)
    if variant % 4 == 2:
        # Door operator alternates between panel and observer.
        phase = _phase(progress, 1.0)
        hand_x = round(width * 0.58 + 55 * phase)
        hand_y = round(height * 0.49 - 28 * abs(phase))
        draw.line((round(width * 0.54), round(height * 0.58), hand_x, hand_y), fill=cartoon.INK, width=17)
        draw.ellipse((hand_x - 12, hand_y - 12, hand_x + 12, hand_y + 12), fill=cartoon.CYAN, outline=cartoon.INK, width=4)
    else:
        _walking_actor(draw, round(760 + 220 * cartoon._ease(progress)), ground - 175, 0.78, cartoon.GREEN, progress, robot=variant % 2 == 1)


def _council_gesture(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Cycle speaker emphasis with a hand gesture and microphone pulse."""
    eased = cartoon._ease(progress)
    speaker = min(2, int(eased * 3.0))
    centers = (round(width * 0.34), round(width * 0.50), round(width * 0.66))
    cx = centers[speaker]
    cy = round(height * 0.48)
    phase = _phase(progress * 3.0 - speaker, 0.75)
    hand = (cx + round(54 * phase), cy - round(62 + 18 * abs(phase)))
    draw.line((cx, cy + 48, hand[0], hand[1]), fill=cartoon.INK, width=16)
    draw.ellipse((hand[0] - 12, hand[1] - 12, hand[0] + 12, hand[1] + 12), fill=cartoon.AMBER, outline=cartoon.INK, width=4)
    mic_y = round(height * 0.64)
    pulse = 18 + round(7 * (0.5 + 0.5 * _phase(progress, 2.5)))
    draw.ellipse((cx - pulse, mic_y - pulse // 2, cx + pulse, mic_y + pulse // 2), outline=cartoon.CYAN, width=6)


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


def _rotated_spacecraft(image: Image.Image, x: int, y: int, scale: float, progress: float, angle: float) -> None:
    """Render spacecraft on an isolated transparent layer, then rotate to route tangent."""
    pad = 420
    sprite = Image.new("RGBA", (pad * 2, pad * 2), (0, 0, 0, 0))
    sprite_draw = ImageDraw.Draw(sprite)
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
    ship_scale = 0.78 if variant < 2 else 0.72
    safe_start, safe_end = v14._safe_route_interval(earth, mars, control, earth_r, mars_r, ship_scale)
    clearance = 0.018
    safe_start = min(safe_end, safe_start + clearance)
    safe_end = max(safe_start, safe_end - clearance)
    travel_t = safe_start + (safe_end - safe_start) * cartoon._ease(progress)
    ship_x, ship_y = _bezier_point(earth, control, mars, travel_t)
    tangent_x, tangent_y = _bezier_tangent(earth, control, mars, travel_t)
    angle = math.atan2(tangent_y, tangent_x)
    _rotated_spacecraft(image, round(ship_x), round(ship_y), ship_scale, progress, angle)


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
    old14 = v14._ACTIVE_VARIANT
    old13 = v13._ACTIVE_VARIANT
    try:
        v14._ACTIVE_VARIANT = _ACTIVE_VARIANT
        v13._ACTIVE_VARIANT = _ACTIVE_VARIANT
        if selected.template_id == "transport_scene":
            v13._draw_transport(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
            v14._animate_transport(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, _ACTIVE_VARIANT)
            _transport_people(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, _ACTIVE_VARIANT)
        elif selected.template_id == "habitat_build":
            v13._draw_habitat(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
            v14._animate_habitat(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, _ACTIVE_VARIANT)
            _habitat_people(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, _ACTIVE_VARIANT)
        elif selected.template_id == "presenter_desk":
            old10 = v13.v10._ACTIVE_VARIANT
            try:
                v13.v10._ACTIVE_VARIANT = _ACTIVE_VARIANT
                v13.v10._draw_presenter(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
            finally:
                v13.v10._ACTIVE_VARIANT = old10
            v14._animate_presenter(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, _ACTIVE_VARIANT)
            _presenter_gesture(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, _ACTIVE_VARIANT)
        elif selected.template_id == "crowd_focus":
            v13._draw_crowd_scene(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
        elif selected.template_id == "council_scene":
            v7._draw_council(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
            _council_gesture(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
        else:
            cartoon._draw_process(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    finally:
        v14._ACTIVE_VARIANT = old14
        v13._ACTIVE_VARIANT = old13
    return v14._camera_move(image, progress, _ACTIVE_VARIANT, selected.template_id)


cartoon._draw_route_map = lambda draw, width, height, progress: None
cartoon.render_planned_frame = render_planned_frame
