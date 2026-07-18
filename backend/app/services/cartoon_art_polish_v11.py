from __future__ import annotations

"""Art Polish v11: final focal-scale, anatomy, and repeat-control refinement."""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v6 as v6
from . import cartoon_art_polish_v7 as v7
from . import cartoon_art_polish_v8 as v8
from . import cartoon_art_polish_v10 as v10


_ACTIVE_VARIANT = 0
_COLORS = (cartoon.BLUE, cartoon.AMBER, cartoon.PURPLE, cartoon.GREEN, cartoon.CYAN, cartoon.RED)


def _human(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    scale: float,
    color: tuple[int, int, int],
    pose: str = "stand",
) -> None:
    """Keep the established human design while strengthening thin limbs."""
    v8._human(draw, x, y, scale, color, pose)
    line = max(7, round(11 * scale))
    head_r = round(29 * scale)
    neck_h = round(22 * scale)
    body_w = round(78 * scale)
    body_h = round(92 * scale)
    torso_top = y + head_r + neck_h - round(2 * scale)
    shoulder_y = torso_top + round(15 * scale)
    bottom = torso_top + body_h
    elbow_y = shoulder_y + round(34 * scale)
    hand_y = shoulder_y + round(62 * scale)

    if pose == "point":
        draw.line(
            (x - body_w // 2, shoulder_y, x - round(58 * scale), elbow_y, x - round(92 * scale), y),
            fill=cartoon.INK,
            width=line,
            joint="curve",
        )
        draw.line(
            (x + body_w // 2, shoulder_y, x + round(50 * scale), elbow_y, x + round(42 * scale), hand_y),
            fill=cartoon.INK,
            width=line,
            joint="curve",
        )
    else:
        for direction in (-1, 1):
            draw.line(
                (
                    x + direction * body_w // 2,
                    shoulder_y,
                    x + direction * round(49 * scale),
                    elbow_y,
                    x + direction * round(38 * scale),
                    hand_y,
                ),
                fill=cartoon.INK,
                width=line,
                joint="curve",
            )

    hip_y = bottom
    knee_y = hip_y + round(34 * scale)
    foot_y = hip_y + round(67 * scale)
    for direction in (-1, 1):
        foot_x = x + direction * round(27 * scale)
        draw.line(
            (x + direction * round(17 * scale), hip_y, x + direction * round(22 * scale), knee_y, foot_x, foot_y),
            fill=cartoon.INK,
            width=line,
            joint="curve",
        )


def _person(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    scale: float = 1.0,
    *,
    accent: tuple[int, int, int] | None = None,
    pose: str = "stand",
) -> None:
    if accent is None:
        v6._robot(draw, x, y, scale, pose)
    else:
        color = accent if accent not in (cartoon.MUTED, cartoon.DARK_MUTED) else _COLORS[(x // 83 + y // 67) % len(_COLORS)]
        _human(draw, x, y, scale, color, pose)


def _draw_transport(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Use fewer, larger focal figures in wide transport compositions."""
    variant = _ACTIVE_VARIANT % 4
    old = v10._ACTIVE_VARIANT
    try:
        v10._ACTIVE_VARIANT = variant
        v10._draw_transport(draw, width, height, progress)
    finally:
        v10._ACTIVE_VARIANT = old

    if variant == 0:
        _human(draw, 520, 560, 0.96, cartoon.AMBER, "walk")
        v6._robot(draw, 1280, 585, 0.88, "walk")
    elif variant == 1:
        _human(draw, 430, 650, 0.86, cartoon.BLUE, "walk")
        v6._robot(draw, 930, 655, 0.82, "walk")
    elif variant == 2:
        _human(draw, 520, 555, 0.98, cartoon.PURPLE, "walk")
        v6._robot(draw, 1390, 590, 0.90, "walk")
    else:
        _human(draw, 540, 560, 0.94, cartoon.GREEN, "walk")
        v6._robot(draw, 1325, 585, 0.84, "walk")


def _draw_habitat(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Increase focal action scale, especially inside the airlock close-up."""
    variant = _ACTIVE_VARIANT % 4
    old = v10._ACTIVE_VARIANT
    try:
        v10._ACTIVE_VARIANT = variant
        v10._draw_habitat(draw, width, height, progress)
    finally:
        v10._ACTIVE_VARIANT = old

    if variant == 0:
        _human(draw, 470, 500, 1.32, cartoon.AMBER, "point")
    elif variant == 1:
        _human(draw, 880, 565, 0.96, cartoon.CYAN, "stand")
    elif variant == 2:
        # Large operator inside the doorway makes the action and scale obvious.
        v6._robot(draw, 1120, 520, 1.18, "stand")
        _human(draw, 635, 500, 1.42, cartoon.GREEN, "point")
    else:
        v6._robot(draw, 920, 565, 0.84, "walk")


def _bezier_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    t: float,
) -> tuple[int, int]:
    one = 1.0 - t
    return (
        round(one * one * p0[0] + 2 * one * t * p1[0] + t * t * p2[0]),
        round(one * one * p0[1] + 2 * one * t * p1[1] + t * t * p2[1]),
    )


def _draw_route_map(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Keep the ship on-path while reducing its size near either planet."""
    variant = _ACTIVE_VARIANT % 3
    draw.rectangle((0, 0, width, height), fill=cartoon.PAPER)
    for index in range(30):
        sx = (index * 181) % width
        sy = 24 + (index * 83) % round(height * 0.38)
        radius = 2 + index % 3
        draw.ellipse((sx - radius, sy - radius, sx + radius, sy + radius), fill=cartoon.MUTED)

    if variant == 0:
        earth, mars, control = (360, 690), (1540, 410), (960, 130)
        earth_r, mars_r = 225, 190
    elif variant == 1:
        earth, mars, control = (300, 760), (1580, 300), (930, 100)
        earth_r, mars_r = 180, 235
    else:
        earth, mars, control = (270, 760), (1480, 560), (850, 180)
        earth_r, mars_r = 135, 285

    cartoon._planet(draw, earth, earth_r, cartoon.BLUE, progress)
    cartoon._planet(draw, mars, mars_r, cartoon.MARS, 1 - progress)
    points = [_bezier_point(earth, control, mars, step / 36) for step in range(37)]
    for index in range(0, len(points) - 1, 2):
        draw.line((points[index], points[index + 1]), fill=cartoon.INK, width=10)
    arrow = points[-2]
    draw.polygon((points[-1], (arrow[0] - 30, arrow[1] - 18), (arrow[0] - 18, arrow[1] + 28)), fill=cartoon.INK)

    eased = cartoon._ease(progress)
    ship_x, ship_y = _bezier_point(earth, control, mars, eased)
    # Full size at mid-flight; smoothly capped as the ship approaches either planet.
    endpoint_distance = min(eased, 1.0 - eased)
    proximity = min(1.0, endpoint_distance / 0.22)
    ship_scale = (0.72 + 0.38 * proximity) if variant < 2 else (0.68 + 0.36 * proximity)
    v7._spacecraft(draw, ship_x, ship_y, ship_scale, progress)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    """Choose stable variants with a longer repeat period across nearby scenes."""
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
    beat_index = int(max(0.0, time_seconds) // max(1.0, duration_seconds / 3.0))

    # The quotient term breaks the short modulo cycle that caused nearby scenes
    # separated by one template-family period to reuse the same camera setup.
    _ACTIVE_VARIANT = (scene_number + scene_number // 4 + beat_index * 2) % 12

    image = Image.new("RGB", (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT), cartoon.PAPER)
    draw = ImageDraw.Draw(image)
    if selected.template_id == "route_map":
        _draw_route_map(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "crowd_focus":
        v10._draw_crowd_scene(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "presenter_desk":
        old = v10._ACTIVE_VARIANT
        try:
            v10._ACTIVE_VARIANT = _ACTIVE_VARIANT
            v10._draw_presenter(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
        finally:
            v10._ACTIVE_VARIANT = old
    elif selected.template_id == "transport_scene":
        _draw_transport(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "habitat_build":
        _draw_habitat(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "council_scene":
        v7._draw_council(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    else:
        cartoon._draw_process(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    return image


# Install v11 last so all render paths use the refined anatomy and staging.
v8._human = _human
v8._person = _person
cartoon._person = _person
cartoon._draw_transport = _draw_transport
cartoon._draw_habitat = _draw_habitat
cartoon._draw_route_map = _draw_route_map
cartoon.render_planned_frame = render_planned_frame
