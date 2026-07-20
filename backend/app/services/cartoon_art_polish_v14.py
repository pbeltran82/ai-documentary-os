from __future__ import annotations

"""Art Polish v14: controlled camera motion and strict route clearance."""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v6 as v6
from . import cartoon_art_polish_v7 as v7
from . import cartoon_art_polish_v12 as v12
from . import cartoon_art_polish_v13 as v13


_ACTIVE_VARIANT = 0


def _bezier_point(p0, p1, p2, t: float) -> tuple[int, int]:
    one = 1.0 - t
    return (
        round(one * one * p0[0] + 2 * one * t * p1[0] + t * t * p2[0]),
        round(one * one * p0[1] + 2 * one * t * p1[1] + t * t * p2[1]),
    )


def _camera_move(image: Image.Image, progress: float, variant: int, template_id: str) -> Image.Image:
    """Apply a restrained push, pull, or lateral drift without changing shot identity."""
    if template_id == "route_map":
        zoom = 1.0 + 0.012 * math.sin(progress * math.pi)
    else:
        direction = -1.0 if variant % 3 == 1 else 1.0
        zoom = 1.0 + (0.026 + 0.008 * (variant % 2)) * progress * direction
        zoom = max(0.985, zoom)

    width, height = image.size
    scaled_w = max(width, round(width * zoom))
    scaled_h = max(height, round(height * zoom))
    moved = image.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

    max_x = max(0, scaled_w - width)
    max_y = max(0, scaled_h - height)
    drift = cartoon._ease(progress)
    pan_x = round(max_x * ((0.22 + 0.16 * (variant % 4)) if max_x else 0))
    pan_y = round(max_y * ((0.18 + 0.12 * ((variant + 1) % 3)) if max_y else 0))

    if variant % 2:
        pan_x = max_x - pan_x
    if variant % 3 == 2:
        pan_y = max_y - pan_y

    pan_x = round(pan_x * drift)
    pan_y = round(pan_y * drift)
    return moved.crop((pan_x, pan_y, pan_x + width, pan_y + height))


def _animate_transport(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, variant: int) -> None:
    """Add small operational motion while preserving the underlying transport setup."""
    floor = round(height * 0.80)
    travel = cartoon._ease(progress)
    cart_x = round(180 + travel * (width - 520))
    draw.rounded_rectangle((cart_x, floor - 72, cart_x + 180, floor - 18), radius=14, fill=(118, 128, 137), outline=cartoon.INK, width=7)
    for wheel_x in (cart_x + 38, cart_x + 142):
        draw.ellipse((wheel_x - 13, floor - 28, wheel_x + 13, floor - 2), fill=cartoon.INK)
    pulse = 7 + round(5 * (0.5 + 0.5 * math.sin(progress * math.pi * 8)))
    for x in (250, width - 250):
        draw.ellipse((x - pulse, 115 - pulse, x + pulse, 115 + pulse), fill=cartoon.CYAN, outline=cartoon.INK, width=3)


def _animate_habitat(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, variant: int) -> None:
    """Add parallax-friendly activity instead of swapping to a different Mars layout."""
    ground = round(height * 0.77)
    travel = cartoon._ease(progress)
    rover_x = round(260 + travel * 520)
    draw.rounded_rectangle((rover_x, ground - 80, rover_x + 180, ground - 20), radius=18, fill=(111, 121, 130), outline=cartoon.INK, width=8)
    for wheel_x in (rover_x + 35, rover_x + 145):
        draw.ellipse((wheel_x - 18, ground - 38, wheel_x + 18, ground - 2), fill=cartoon.INK)
    draw.line((rover_x + 90, ground - 80, rover_x + 90, ground - 145), fill=cartoon.INK, width=7)
    beacon = 9 + round(4 * (0.5 + 0.5 * math.sin(progress * math.pi * 6)))
    draw.ellipse((rover_x + 90 - beacon, ground - 160 - beacon, rover_x + 90 + beacon, ground - 160 + beacon), fill=cartoon.AMBER, outline=cartoon.INK, width=3)


def _animate_presenter(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, variant: int) -> None:
    """Give presenter graphics a visible reveal without covering the main composition."""
    x1, x2 = round(width * 0.12), round(width * 0.88)
    y = round(height * 0.92)
    draw.rounded_rectangle((x1, y, x2, y + 20), radius=10, fill=(193, 204, 213))
    reveal = round(x1 + (x2 - x1) * cartoon._ease(progress))
    draw.rounded_rectangle((x1, y, reveal, y + 20), radius=10, fill=cartoon.BLUE)


def _animate_council(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, variant: int) -> None:
    """Shift speaker emphasis gently across the council without changing the shot."""
    centers = (round(width * 0.34), round(width * 0.50), round(width * 0.66))
    speaker = min(2, int(cartoon._ease(progress) * 3))
    cx = centers[speaker]
    cy = round(height * 0.56)
    radius = 32 + round(8 * (0.5 + 0.5 * math.sin(progress * math.pi * 5)))
    draw.ellipse((cx - radius, cy - radius // 2, cx + radius, cy + radius // 2), outline=cartoon.CYAN, width=8)


def _safe_route_interval(earth, mars, control, earth_r: int, mars_r: int, ship_scale: float) -> tuple[float, float]:
    """Find a route interval that clears the full capsule, flame, outline, and planet disks."""
    ship_half = 185 * ship_scale
    margin = 26
    safe_start = 0.0
    safe_end = 1.0
    samples = 240

    for index in range(samples + 1):
        t = index / samples
        x, y = _bezier_point(earth, control, mars, t)
        distance = math.hypot(x - earth[0], y - earth[1])
        if distance >= earth_r + ship_half + margin:
            safe_start = t
            break

    for index in range(samples, -1, -1):
        t = index / samples
        x, y = _bezier_point(earth, control, mars, t)
        distance = math.hypot(x - mars[0], y - mars[1])
        if distance >= mars_r + ship_half + margin:
            safe_end = t
            break

    if safe_end <= safe_start:
        return 0.22, 0.74
    return safe_start, safe_end


def _draw_route_map(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Keep the full spacecraft silhouette outside both planet disks."""
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

    points = [_bezier_point(earth, control, mars, step / 48) for step in range(49)]
    for index in range(0, len(points) - 1, 2):
        draw.line((points[index], points[index + 1]), fill=cartoon.INK, width=10)

    ship_scale = 0.82 if variant < 2 else 0.76
    safe_start, safe_end = _safe_route_interval(earth, mars, control, earth_r, mars_r, ship_scale)
    eased = cartoon._ease(progress)
    travel_t = safe_start + (safe_end - safe_start) * eased
    ship_x, ship_y = _bezier_point(earth, control, mars, travel_t)
    v7._spacecraft(draw, ship_x, ship_y, ship_scale, progress)

    tip = _bezier_point(earth, control, mars, safe_end)
    before = _bezier_point(earth, control, mars, max(safe_start, safe_end - 0.03))
    angle = math.atan2(tip[1] - before[1], tip[0] - before[0])
    left = (round(tip[0] - 34 * math.cos(angle - 0.55)), round(tip[1] - 34 * math.sin(angle - 0.55)))
    right = (round(tip[0] - 34 * math.cos(angle + 0.55)), round(tip[1] - 34 * math.sin(angle + 0.55)))
    draw.polygon((tip, left, right), fill=cartoon.INK)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    """Render a stable shot with controlled internal movement and restrained camera motion."""
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
    draw = ImageDraw.Draw(image)

    old = v13._ACTIVE_VARIANT
    try:
        v13._ACTIVE_VARIANT = _ACTIVE_VARIANT
        if selected.template_id == "route_map":
            _draw_route_map(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
        elif selected.template_id == "crowd_focus":
            v13._draw_crowd_scene(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
        elif selected.template_id == "presenter_desk":
            presenter_old = v13.v10._ACTIVE_VARIANT
            try:
                v13.v10._ACTIVE_VARIANT = _ACTIVE_VARIANT
                v13.v10._draw_presenter(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
            finally:
                v13.v10._ACTIVE_VARIANT = presenter_old
            _animate_presenter(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, _ACTIVE_VARIANT)
        elif selected.template_id == "transport_scene":
            v13._draw_transport(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
            _animate_transport(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, _ACTIVE_VARIANT)
        elif selected.template_id == "habitat_build":
            v13._draw_habitat(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
            _animate_habitat(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, _ACTIVE_VARIANT)
        elif selected.template_id == "council_scene":
            v13.v7._draw_council(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
            _animate_council(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, _ACTIVE_VARIANT)
        else:
            cartoon._draw_process(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    finally:
        v13._ACTIVE_VARIANT = old

    return _camera_move(image, progress, _ACTIVE_VARIANT, selected.template_id)


cartoon._draw_route_map = _draw_route_map
cartoon.render_planned_frame = render_planned_frame
