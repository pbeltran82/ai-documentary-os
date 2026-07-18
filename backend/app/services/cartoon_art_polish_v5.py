from __future__ import annotations

"""Art Polish v5: distinct robots/humans, cleaner spacecraft, and rugged Mars."""

import math

from PIL import ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v3 as v3
from . import cartoon_art_polish_v4 as v4


def _line(scale: float) -> int:
    return max(4, round(8 * scale))


def _human(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    scale: float,
    accent: tuple[int, int, int],
    pose: str,
) -> None:
    line = _line(scale)
    head_r = round(28 * scale)
    neck_w = round(17 * scale)
    neck_h = round(24 * scale)
    body_w = round(80 * scale)
    body_h = round(94 * scale)
    torso_top = y + head_r + round(15 * scale)
    shoulder_y = torso_top + round(14 * scale)
    left = x - body_w // 2
    right = x + body_w // 2
    bottom = torso_top + body_h

    # Visible skin neck below the head.
    draw.rounded_rectangle(
        (x - neck_w // 2, y + head_r - 2, x + neck_w // 2, y + head_r + neck_h),
        radius=max(2, round(5 * scale)),
        fill=accent,
        outline=cartoon.INK,
        width=max(2, line // 2),
    )
    draw.polygon(
        (
            (x - round(20 * scale), torso_top),
            (left, shoulder_y),
            (left + round(6 * scale), bottom),
            (right - round(6 * scale), bottom),
            (right, shoulder_y),
            (x + round(20 * scale), torso_top),
        ),
        fill=accent,
        outline=cartoon.INK,
    )
    draw.line(
        (
            (x - round(20 * scale), torso_top),
            (left, shoulder_y),
            (left + round(6 * scale), bottom),
            (right - round(6 * scale), bottom),
            (right, shoulder_y),
            (x + round(20 * scale), torso_top),
        ),
        fill=cartoon.INK,
        width=line,
        joint="curve",
    )
    draw.ellipse(
        (x - head_r, y - head_r, x + head_r, y + head_r),
        fill=accent,
        outline=cartoon.INK,
        width=line,
    )

    # Simple, high-contrast hair cap makes humans distinct from robots.
    hair_h = round(17 * scale)
    draw.pieslice(
        (x - head_r + line // 2, y - head_r + line // 2, x + head_r - line // 2, y + head_r - line // 2),
        180,
        360,
        fill=(49, 39, 34),
    )
    draw.polygon(
        (
            (x - head_r + round(4 * scale), y - round(5 * scale)),
            (x - round(10 * scale), y - hair_h),
            (x + round(3 * scale), y - round(7 * scale)),
            (x + round(14 * scale), y - hair_h),
            (x + head_r - round(4 * scale), y - round(3 * scale)),
        ),
        fill=(49, 39, 34),
    )

    eye = max(2, round(4 * scale))
    for eye_x in (x - round(10 * scale), x + round(10 * scale)):
        draw.ellipse((eye_x - eye, y - eye, eye_x + eye, y + eye), fill=cartoon.INK)
    draw.arc(
        (x - round(14 * scale), y + round(3 * scale), x + round(14 * scale), y + round(22 * scale)),
        10,
        170,
        fill=cartoon.INK,
        width=max(2, round(3 * scale)),
    )

    elbow_y = shoulder_y + round(34 * scale)
    hand_y = shoulder_y + round(62 * scale)

    def limb(points: tuple[tuple[int, int], ...]) -> None:
        draw.line(points, fill=cartoon.INK, width=line, joint="curve")

    if pose == "point":
        limb(((left, shoulder_y), (x - round(58 * scale), elbow_y), (x - round(94 * scale), y)))
        limb(((right, shoulder_y), (x + round(54 * scale), elbow_y), (x + round(45 * scale), hand_y)))
    elif pose == "carry":
        limb(((left, shoulder_y), (x - round(50 * scale), elbow_y), (x - round(29 * scale), hand_y)))
        limb(((right, shoulder_y), (x + round(50 * scale), elbow_y), (x + round(29 * scale), hand_y)))
        box_y = hand_y - round(8 * scale)
        draw.rounded_rectangle(
            (x - round(38 * scale), box_y, x + round(38 * scale), box_y + round(38 * scale)),
            radius=max(3, round(6 * scale)),
            fill=cartoon.AMBER,
            outline=cartoon.INK,
            width=max(3, line // 2),
        )
    else:
        limb(((left, shoulder_y), (x - round(49 * scale), elbow_y), (x - round(38 * scale), hand_y)))
        limb(((right, shoulder_y), (x + round(49 * scale), elbow_y), (x + round(38 * scale), hand_y)))

    hip_y = bottom - round(3 * scale)
    knee_y = hip_y + round(35 * scale)
    foot_y = hip_y + round(69 * scale)
    stride = round(16 * scale) if pose == "walk" else 0
    limb(((x - round(18 * scale), hip_y), (x - round(23 * scale) - stride, knee_y), (x - round(29 * scale) - stride, foot_y)))
    limb(((x + round(18 * scale), hip_y), (x + round(23 * scale) + stride, knee_y), (x + round(29 * scale) + stride, foot_y)))
    for foot_x in (x - round(29 * scale) - stride, x + round(29 * scale) + stride):
        draw.rounded_rectangle(
            (foot_x - round(13 * scale), foot_y - round(5 * scale), foot_x + round(13 * scale), foot_y + round(6 * scale)),
            radius=max(2, round(5 * scale)),
            fill=cartoon.INK,
        )


def _robot(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, pose: str) -> None:
    line = _line(scale)
    gray = (135, 142, 151)
    dark = (79, 86, 96)
    head_w = round(53 * scale)
    head_h = round(45 * scale)
    torso_w = round(70 * scale)
    torso_h = round(82 * scale)
    neck_h = round(13 * scale)
    torso_top = y + head_h // 2 + neck_h + round(8 * scale)
    shoulder_y = torso_top + round(15 * scale)
    left = x - torso_w // 2
    right = x + torso_w // 2
    bottom = torso_top + torso_h

    draw.rounded_rectangle(
        (x - head_w // 2, y - head_h // 2, x + head_w // 2, y + head_h // 2),
        radius=max(3, round(7 * scale)),
        fill=gray,
        outline=cartoon.INK,
        width=line,
    )
    draw.rectangle(
        (x - round(9 * scale), y + head_h // 2, x + round(9 * scale), torso_top),
        fill=dark,
        outline=cartoon.INK,
        width=max(2, line // 2),
    )
    draw.rounded_rectangle(
        (left, torso_top, right, bottom),
        radius=max(4, round(10 * scale)),
        fill=dark,
        outline=cartoon.INK,
        width=line,
    )
    # Visor and machine status light.
    draw.rounded_rectangle(
        (x - round(18 * scale), y - round(8 * scale), x + round(18 * scale), y + round(6 * scale)),
        radius=max(2, round(5 * scale)),
        fill=(177, 224, 235),
        outline=cartoon.INK,
        width=max(2, line // 3),
    )
    draw.ellipse(
        (x - round(4 * scale), torso_top + round(13 * scale), x + round(4 * scale), torso_top + round(21 * scale)),
        fill=cartoon.AMBER,
    )

    elbow_y = shoulder_y + round(31 * scale)
    hand_y = shoulder_y + round(55 * scale)

    def joint(px: int, py: int) -> None:
        r = max(3, round(6 * scale))
        draw.ellipse((px - r, py - r, px + r, py + r), fill=gray, outline=cartoon.INK, width=max(2, line // 3))

    for direction in (-1, 1):
        ex = x + direction * round(48 * scale)
        hx = x + direction * round(42 * scale)
        draw.line((x + direction * torso_w // 2, shoulder_y, ex, elbow_y, hx, hand_y), fill=cartoon.INK, width=line, joint="curve")
        joint(ex, elbow_y)
    hip_y = bottom
    knee_y = hip_y + round(31 * scale)
    foot_y = hip_y + round(62 * scale)
    for direction in (-1, 1):
        kx = x + direction * round(21 * scale)
        fx = x + direction * round(25 * scale)
        draw.line((x + direction * round(15 * scale), hip_y, kx, knee_y, fx, foot_y), fill=cartoon.INK, width=line, joint="curve")
        joint(kx, knee_y)
        draw.rounded_rectangle((fx - round(12 * scale), foot_y - round(5 * scale), fx + round(12 * scale), foot_y + round(5 * scale)), radius=max(2, round(4 * scale)), fill=cartoon.INK)


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
        _robot(draw, x, y, scale, pose)
    else:
        _human(draw, x, y, scale, accent, pose)


def _planet(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int, color: tuple[int, int, int], progress: float) -> None:
    """Draw Earth or Mars without Saturn-like rings."""
    x, y = center
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color, outline=cartoon.INK, width=max(10, radius // 9))
    if color == cartoon.BLUE:
        draw.polygon(
            (
                (x - radius * 3 // 5, y - radius // 4),
                (x - radius // 5, y - radius * 2 // 3),
                (x + radius // 6, y - radius // 4),
                (x, y + radius // 7),
                (x - radius // 2, y + radius // 4),
            ),
            fill=cartoon.GREEN,
            outline=cartoon.INK,
        )
        draw.polygon(
            (
                (x + radius // 4, y + radius // 8),
                (x + radius * 2 // 3, y - radius // 8),
                (x + radius * 3 // 5, y + radius // 3),
                (x + radius // 3, y + radius // 2),
            ),
            fill=cartoon.GREEN,
            outline=cartoon.INK,
        )
    else:
        for dx, dy, rr in ((-0.34, -0.18, 0.15), (0.25, 0.17, 0.12), (0.05, -0.40, 0.08), (-0.12, 0.37, 0.10)):
            cx = x + round(radius * dx)
            cy = y + round(radius * dy)
            r = round(radius * rr)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(154, 67, 43), outline=cartoon.INK, width=max(4, radius // 30))


def _spacecraft(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, progress: float) -> None:
    """Readable capsule silhouette without decorative triangle fins."""
    w = round(245 * scale)
    h = round(104 * scale)
    line = max(6, round(11 * scale))
    body_left = x - w // 2
    body_right = x + w // 2
    draw.rounded_rectangle(
        (body_left, y - h // 2, body_right, y + h // 2),
        radius=round(43 * scale),
        fill=(205, 210, 216),
        outline=cartoon.INK,
        width=line,
    )
    # Rounded cockpit nose and conventional rear engine bell.
    draw.pieslice(
        (body_right - round(35 * scale), y - h // 2, body_right + round(65 * scale), y + h // 2),
        270,
        90,
        fill=cartoon.BLUE,
        outline=cartoon.INK,
        width=line,
    )
    draw.rounded_rectangle(
        (body_left - round(25 * scale), y - round(29 * scale), body_left + round(4 * scale), y + round(29 * scale)),
        radius=max(3, round(8 * scale)),
        fill=(91, 98, 107),
        outline=cartoon.INK,
        width=max(4, line // 2),
    )
    for offset in (-0.22, 0.05, 0.28):
        cx = x + round(w * offset)
        r = round(17 * scale)
        draw.ellipse((cx - r, y - r, cx + r, y + r), fill=cartoon.CYAN, outline=cartoon.INK, width=max(3, round(6 * scale)))
    flame = round(48 * scale * (0.72 + 0.28 * math.sin(progress * math.pi * 8)))
    draw.polygon(
        (
            (body_left - round(20 * scale), y - round(18 * scale)),
            (body_left - round(20 * scale) - flame, y),
            (body_left - round(20 * scale), y + round(18 * scale)),
        ),
        fill=cartoon.AMBER,
        outline=cartoon.INK,
    )


def _rugged_ridge(draw: ImageDraw.ImageDraw, width: int, ground: int) -> None:
    points = [
        (0, ground),
        (0, ground - 90),
        (round(width * 0.06), ground - 210),
        (round(width * 0.11), ground - 155),
        (round(width * 0.17), ground - 320),
        (round(width * 0.23), ground - 235),
        (round(width * 0.29), ground - 285),
        (round(width * 0.36), ground - 135),
        (round(width * 0.43), ground - 250),
        (round(width * 0.49), ground - 175),
        (round(width * 0.56), ground - 305),
        (round(width * 0.62), ground - 220),
        (round(width * 0.70), ground - 270),
        (round(width * 0.77), ground - 145),
        (round(width * 0.84), ground - 300),
        (round(width * 0.91), ground - 205),
        (width, ground - 260),
        (width, ground),
    ]
    draw.polygon(points, fill=(160, 77, 53))
    # Secondary ridge creates natural depth instead of pyramid silhouettes.
    draw.line(points[2:-1], fill=(117, 58, 43), width=10, joint="curve")


def _draw_habitat(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    ground = round(height * 0.75)
    draw.rectangle((0, 0, width, ground), fill=(241, 211, 190))
    _rugged_ridge(draw, width, ground)
    draw.rectangle((0, ground, width, height), fill=(190, 105, 70))

    cx = round(width * 0.57)
    dome_w = round(width * (0.22 + 0.16 * cartoon._ease(progress)))
    dome_h = round(height * (0.17 + 0.13 * cartoon._ease(progress)))
    draw.pieslice((cx - dome_w, ground - dome_h * 2, cx + dome_w, ground), 180, 360, fill=(187, 225, 236), outline=cartoon.INK, width=18)
    for frac in (-0.5, 0.0, 0.5):
        px = cx + round(dome_w * frac)
        draw.line((px, ground - dome_h * 1.88, px, ground), fill=cartoon.INK, width=5)

    # Airlock and labeled visual cues are now physically distinct objects.
    draw.rounded_rectangle((cx - 62, ground - 145, cx + 62, ground), radius=18, fill=(72, 78, 84), outline=cartoon.INK, width=10)
    draw.line((cx - 42, ground - 112, cx + 42, ground - 112), fill=cartoon.AMBER, width=9)
    draw.ellipse((cx + 30, ground - 75, cx + 45, ground - 60), fill=cartoon.WHITE, outline=cartoon.INK, width=3)
    v4._solar_array(draw, round(width * 0.17), round(height * 0.48), 0.95)
    for index in range(3):
        v4._drone(draw, round(width * (0.73 + index * 0.09)), round(height * (0.24 + 0.07 * (index % 2))), 0.78, progress + index * 0.13)
    for index in range(3):
        bx = round(width * (0.75 + index * 0.073))
        by = ground - 104
        draw.rounded_rectangle((bx, by, bx + 72, ground), radius=8, fill=(116, 124, 134), outline=cartoon.INK, width=7)
        draw.line((bx + 12, by + 31, bx + 60, by + 31), fill=cartoon.AMBER, width=5)
        draw.arc((bx + 20, by + 5, bx + 52, by + 34), 180, 360, fill=cartoon.INK, width=4)
    _human(draw, round(width * 0.27), round(height * 0.47), 1.08, cartoon.AMBER, "carry")


def _draw_route_map(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    for index in range(26):
        sx = (index * 173) % width
        sy = 35 + (index * 79) % round(height * 0.28)
        r = 3 + index % 3
        draw.ellipse((sx - r, sy - r, sx + r, sy + r), fill=cartoon.MUTED)
    _planet(draw, (round(width * 0.22), round(height * 0.55)), round(height * 0.22), cartoon.BLUE, progress)
    _planet(draw, (round(width * 0.79), round(height * 0.55)), round(height * 0.19), cartoon.MARS, 1 - progress)
    v3._arrow(draw, (round(width * 0.39), round(height * 0.47)), (round(width * 0.65), round(height * 0.47)), progress)
    ship_x = round(width * (0.38 + 0.28 * cartoon._ease(progress)))
    _spacecraft(draw, ship_x, round(height * 0.30), 0.78, progress)


cartoon._person = _person
cartoon._planet = _planet
cartoon._draw_route_map = _draw_route_map
cartoon._draw_habitat = _draw_habitat
# v4 scene functions resolve cartoon._person at render time, so council,
# presenter, transport, and crowds now automatically use the human/robot split.
