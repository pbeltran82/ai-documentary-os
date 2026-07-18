from __future__ import annotations

"""Art Polish v4: visible necks, fuller compositions, and literal objects."""

import math

from PIL import ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v3 as v3


def _person(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    scale: float = 1.0,
    *,
    accent: tuple[int, int, int] | None = None,
    pose: str = "stand",
) -> None:
    line = max(4, round(8 * scale))
    head_r = round(28 * scale)
    neck_w = round(17 * scale)
    neck_h = round(25 * scale)
    body_w = round(82 * scale)
    body_h = round(96 * scale)
    fill = accent or cartoon.MUTED
    body_fill = fill if accent else cartoon.DARK_MUTED

    neck_top = y + head_r - round(1 * scale)
    draw.rounded_rectangle(
        (x - neck_w // 2, neck_top, x + neck_w // 2, neck_top + neck_h),
        radius=max(2, round(5 * scale)),
        fill=fill,
    )

    torso_top = neck_top + round(18 * scale)
    shoulder_y = torso_top + round(15 * scale)
    left = x - body_w // 2
    right = x + body_w // 2
    bottom = torso_top + body_h
    draw.polygon(
        (
            (x - round(20 * scale), torso_top),
            (left, shoulder_y),
            (left + round(6 * scale), bottom),
            (right - round(6 * scale), bottom),
            (right, shoulder_y),
            (x + round(20 * scale), torso_top),
        ),
        fill=body_fill,
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

    # Redraw the neck above the torso so it remains visibly distinct.
    draw.rounded_rectangle(
        (x - neck_w // 2, neck_top, x + neck_w // 2, neck_top + neck_h),
        radius=max(2, round(5 * scale)),
        fill=fill,
        outline=cartoon.INK,
        width=max(2, line // 2),
    )
    draw.ellipse(
        (x - head_r, y - head_r, x + head_r, y + head_r),
        fill=fill,
        outline=cartoon.INK,
        width=line,
    )

    elbow_y = shoulder_y + round(34 * scale)
    hand_y = shoulder_y + round(62 * scale)
    hand_r = max(4, round(7 * scale))

    def limb(points: tuple[tuple[int, int], ...]) -> None:
        draw.line(points, fill=cartoon.INK, width=line, joint="curve")

    if pose == "point":
        limb(((left, shoulder_y), (x - round(58 * scale), elbow_y), (x - round(94 * scale), y)))
        draw.ellipse((x - round(101 * scale), y - hand_r, x - round(87 * scale), y + hand_r), fill=fill, outline=cartoon.INK, width=max(2, line // 2))
        limb(((right, shoulder_y), (x + round(54 * scale), elbow_y), (x + round(45 * scale), hand_y)))
    elif pose == "carry":
        limb(((left, shoulder_y), (x - round(50 * scale), elbow_y), (x - round(28 * scale), hand_y)))
        limb(((right, shoulder_y), (x + round(50 * scale), elbow_y), (x + round(28 * scale), hand_y)))
        box_y = hand_y - round(8 * scale)
        draw.rounded_rectangle((x - round(38 * scale), box_y, x + round(38 * scale), box_y + round(38 * scale)), radius=round(6 * scale), fill=cartoon.AMBER, outline=cartoon.INK, width=max(3, line // 2))
        draw.line((x, box_y, x, box_y + round(38 * scale)), fill=cartoon.INK, width=max(2, line // 3))
    else:
        swing = round(11 * scale) if pose == "walk" else 0
        limb(((left, shoulder_y), (x - round(49 * scale), elbow_y), (x - round(38 * scale) - swing, hand_y)))
        limb(((right, shoulder_y), (x + round(49 * scale), elbow_y), (x + round(38 * scale) + swing, hand_y)))

    hip_y = bottom - round(3 * scale)
    knee_y = hip_y + round(35 * scale)
    foot_y = hip_y + round(69 * scale)
    stride = round(16 * scale) if pose == "walk" else 0
    limb(((x - round(18 * scale), hip_y), (x - round(23 * scale) - stride, knee_y), (x - round(29 * scale) - stride, foot_y)))
    limb(((x + round(18 * scale), hip_y), (x + round(23 * scale) + stride, knee_y), (x + round(29 * scale) + stride, foot_y)))
    for foot_x in (x - round(29 * scale) - stride, x + round(29 * scale) + stride):
        draw.rounded_rectangle((foot_x - round(13 * scale), foot_y - round(5 * scale), foot_x + round(13 * scale), foot_y + round(6 * scale)), radius=max(2, round(5 * scale)), fill=cartoon.INK)

    if accent:
        eye = max(2, round(4 * scale))
        draw.ellipse((x - round(10 * scale) - eye, y - eye, x - round(10 * scale) + eye, y + eye), fill=cartoon.INK)
        draw.ellipse((x + round(10 * scale) - eye, y - eye, x + round(10 * scale) + eye, y + eye), fill=cartoon.INK)
        draw.arc((x - round(14 * scale), y + round(3 * scale), x + round(14 * scale), y + round(22 * scale)), 10, 170, fill=cartoon.INK, width=max(2, round(3 * scale)))


def _drone(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, progress: float) -> None:
    bob = round(8 * scale * math.sin(progress * math.pi * 6 + x * 0.01))
    y += bob
    body_w = round(55 * scale)
    body_h = round(24 * scale)
    arm = round(36 * scale)
    rotor = round(18 * scale)
    draw.rounded_rectangle((x - body_w // 2, y - body_h // 2, x + body_w // 2, y + body_h // 2), radius=round(10 * scale), fill=cartoon.BLUE, outline=cartoon.INK, width=max(4, round(6 * scale)))
    for direction in (-1, 1):
        draw.line((x + direction * body_w // 2, y, x + direction * (body_w // 2 + arm), y - round(12 * scale)), fill=cartoon.INK, width=max(3, round(5 * scale)))
        rx = x + direction * (body_w // 2 + arm)
        ry = y - round(12 * scale)
        draw.ellipse((rx - rotor, ry - round(5 * scale), rx + rotor, ry + round(5 * scale)), fill=cartoon.CYAN, outline=cartoon.INK, width=max(2, round(3 * scale)))
    draw.line((x, y + body_h // 2, x, y + round(30 * scale)), fill=cartoon.INK, width=max(3, round(4 * scale)))
    draw.ellipse((x - round(7 * scale), y + round(25 * scale), x + round(7 * scale), y + round(39 * scale)), fill=cartoon.AMBER, outline=cartoon.INK, width=max(2, round(3 * scale)))


def _solar_array(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float) -> None:
    panel_w = round(160 * scale)
    panel_h = round(78 * scale)
    draw.line((x, y, x, y + round(80 * scale)), fill=cartoon.INK, width=max(5, round(8 * scale)))
    draw.rounded_rectangle((x - panel_w // 2, y - panel_h // 2, x + panel_w // 2, y + panel_h // 2), radius=8, fill=(47, 91, 151), outline=cartoon.INK, width=max(5, round(8 * scale)))
    for col in range(1, 4):
        px = x - panel_w // 2 + panel_w * col // 4
        draw.line((px, y - panel_h // 2, px, y + panel_h // 2), fill=cartoon.CYAN, width=max(2, round(3 * scale)))
    draw.line((x - panel_w // 2, y, x + panel_w // 2, y), fill=cartoon.CYAN, width=max(2, round(3 * scale)))


def _draw_route_map(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    # Fill the former blank top strip with stars, orbit paths, and the spacecraft.
    for index in range(26):
        sx = (index * 173) % width
        sy = 35 + (index * 79) % round(height * 0.28)
        r = 3 + index % 3
        draw.ellipse((sx - r, sy - r, sx + r, sy + r), fill=cartoon.MUTED)
    v3._planet(draw, (round(width * 0.22), round(height * 0.55)), round(height * 0.22), cartoon.BLUE, progress)
    v3._planet(draw, (round(width * 0.79), round(height * 0.55)), round(height * 0.19), cartoon.MARS, 1 - progress)
    v3._arrow(draw, (round(width * 0.39), round(height * 0.47)), (round(width * 0.65), round(height * 0.47)), progress)
    ship_x = round(width * (0.38 + 0.28 * cartoon._ease(progress)))
    v3._spacecraft(draw, ship_x, round(height * 0.30), 0.78, progress)


def _draw_presenter(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    for x in range(0, width, 86):
        draw.line((x, 0, x, height), fill=(205, 228, 241), width=4)
    for y in range(0, height, 86):
        draw.line((0, y, width, y), fill=(205, 228, 241), width=4)
    # Upper wall screens intentionally occupy the old white band.
    for index, fill in enumerate((cartoon.CYAN, cartoon.AMBER, cartoon.PURPLE)):
        x1 = 105 + index * 285
        draw.rounded_rectangle((x1, 50, x1 + 235, 190), radius=18, fill=fill, outline=cartoon.INK, width=9)
        draw.line((x1 + 35, 105, x1 + 190, 105), fill=cartoon.INK, width=6)
        draw.line((x1 + 35, 145, x1 + 145, 145), fill=cartoon.INK, width=6)
    desk_y = round(height * 0.70)
    draw.rounded_rectangle((70, desk_y, width - 70, height + 40), radius=28, fill=(70, 72, 78), outline=cartoon.INK, width=18)
    _person(draw, round(width * 0.52), round(height * 0.27), 1.62, accent=cartoon.BLUE, pose="point")
    draw.rounded_rectangle((round(width * 0.10), desk_y - 120, round(width * 0.25), desk_y), radius=12, fill=cartoon.WHITE, outline=cartoon.INK, width=10)
    draw.line((round(width * 0.125), desk_y - 84, round(width * 0.225), desk_y - 84), fill=cartoon.BLUE, width=7)
    draw.line((round(width * 0.125), desk_y - 53, round(width * 0.205), desk_y - 53), fill=cartoon.DARK_MUTED, width=6)


def _draw_transport(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    sky = round(height * 0.36)
    draw.rectangle((0, 0, width, sky), fill=(226, 237, 244))
    for index in range(5):
        tower_x = index * round(width * 0.22)
        tower_h = round(height * (0.12 + 0.03 * (index % 3)))
        draw.rectangle((tower_x, sky - tower_h, tower_x + round(width * 0.15), sky), fill=(188, 198, 207), outline=cartoon.INK, width=7)
    platform = round(height * 0.78)
    draw.rectangle((0, platform, width, height), fill=(204, 208, 212))
    v3._spacecraft(draw, round(width * 0.69), round(height * 0.26), 1.62, progress)
    # Clearly defined terminal with windows, door, and boarding ramp.
    draw.rounded_rectangle((round(width * 0.05), round(height * 0.22), round(width * 0.39), round(height * 0.64)), radius=30, fill=(188, 192, 198), outline=cartoon.INK, width=18)
    for index in range(3):
        x1 = round(width * (0.085 + index * 0.09))
        draw.rectangle((x1, round(height * 0.29), x1 + round(width * 0.065), round(height * 0.43)), fill=cartoon.CYAN, outline=cartoon.INK, width=8)
    door = (round(width * 0.25), round(height * 0.43), round(width * 0.35), round(height * 0.64))
    draw.rectangle(door, fill=(49, 54, 61), outline=cartoon.INK, width=10)
    draw.polygon(((door[2], door[3] - 18), (round(width * 0.55), platform), (round(width * 0.48), platform), (door[2], door[3] - 65)), fill=cartoon.AMBER, outline=cartoon.INK)
    cartoon._crowd(draw, width, height, progress, focal=True)


def _draw_habitat(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    # Mountain silhouettes use the top of frame rather than leaving it blank.
    ground = round(height * 0.75)
    draw.rectangle((0, ground, width, height), fill=(190, 105, 70))
    draw.polygon(((0, ground), (round(width * 0.13), round(height * 0.30)), (round(width * 0.28), ground), (round(width * 0.43), round(height * 0.38)), (round(width * 0.59), ground), (round(width * 0.77), round(height * 0.28)), (width, ground)), fill=(160, 77, 53))
    cx = round(width * 0.56)
    dome_w = round(width * (0.22 + 0.16 * cartoon._ease(progress)))
    dome_h = round(height * (0.17 + 0.13 * cartoon._ease(progress)))
    draw.pieslice((cx - dome_w, ground - dome_h * 2, cx + dome_w, ground), 180, 360, fill=(187, 225, 236), outline=cartoon.INK, width=18)
    for frac in (-0.5, 0.0, 0.5):
        px = cx + round(dome_w * frac)
        draw.line((px, ground - dome_h * 1.88, px, ground), fill=cartoon.INK, width=5)
    # Readable airlock with warning stripe and handle.
    draw.rounded_rectangle((cx - 62, ground - 145, cx + 62, ground), radius=18, fill=(72, 78, 84), outline=cartoon.INK, width=10)
    draw.line((cx - 42, ground - 112, cx + 42, ground - 112), fill=cartoon.AMBER, width=9)
    draw.ellipse((cx + 30, ground - 75, cx + 45, ground - 60), fill=cartoon.WHITE, outline=cartoon.INK, width=3)
    _solar_array(draw, round(width * 0.18), round(height * 0.47), 0.95)
    for index in range(3):
        _drone(draw, round(width * (0.72 + index * 0.09)), round(height * (0.25 + 0.07 * (index % 2))), 0.78, progress + index * 0.13)
    for index in range(3):
        bx = round(width * (0.74 + index * 0.075))
        by = ground - 105
        draw.rounded_rectangle((bx, by, bx + 74, ground), radius=8, fill=cartoon.AMBER if index == 1 else cartoon.BLUE, outline=cartoon.INK, width=7)
        draw.line((bx + 12, by + 32, bx + 62, by + 32), fill=cartoon.INK, width=5)
        draw.arc((bx + 20, by + 5, bx + 54, by + 35), 180, 360, fill=cartoon.INK, width=4)
    _person(draw, round(width * 0.27), round(height * 0.47), 1.08, accent=cartoon.AMBER, pose="carry")


def _draw_council(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    draw.rounded_rectangle((60, 35, width - 60, height - 55), radius=38, fill=(226, 232, 236), outline=cartoon.INK, width=16)
    # Crest and public information screens fill the upper wall.
    draw.ellipse((round(width * 0.44), 55, round(width * 0.56), 185), fill=cartoon.BLUE, outline=cartoon.INK, width=9)
    draw.polygon(((round(width * 0.50), 75), (round(width * 0.54), 145), (round(width * 0.46), 145)), fill=cartoon.WHITE)
    for x1 in (110, width - 420):
        draw.rounded_rectangle((x1, 60, x1 + 310, 180), radius=16, fill=cartoon.CYAN, outline=cartoon.INK, width=8)
        draw.line((x1 + 35, 105, x1 + 270, 105), fill=cartoon.INK, width=6)
        draw.line((x1 + 35, 140, x1 + 210, 140), fill=cartoon.INK, width=6)
    table_y = round(height * 0.53)
    draw.rounded_rectangle((round(width * 0.16), table_y, round(width * 0.84), table_y + 135), radius=34, fill=(96, 76, 62), outline=cartoon.INK, width=16)
    _person(draw, round(width * 0.35), round(height * 0.28), 1.03, accent=cartoon.PURPLE, pose="point")
    _person(draw, round(width * 0.52), round(height * 0.28), 1.03, accent=cartoon.AMBER)
    _person(draw, round(width * 0.69), round(height * 0.28), 1.03, accent=cartoon.BLUE)
    for index in range(5):
        _person(draw, round(width * (0.27 + index * 0.115)), round(height * 0.76), 0.58)


def _draw_process(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    # Header icons make the relationship readable without text labels.
    draw.rounded_rectangle((100, 45, width - 100, 205), radius=30, fill=(231, 236, 239), outline=cartoon.INK, width=10)
    for index, fill in enumerate((cartoon.BLUE, cartoon.AMBER, cartoon.GREEN)):
        cx = round(width * (0.30 + index * 0.20))
        draw.ellipse((cx - 42, 82, cx + 42, 166), fill=fill, outline=cartoon.INK, width=7)
    left = (round(width * 0.24), round(height * 0.58))
    right = (round(width * 0.76), round(height * 0.58))
    draw.rounded_rectangle((left[0] - 220, left[1] - 170, left[0] + 220, left[1] + 170), radius=44, fill=cartoon.CYAN, outline=cartoon.INK, width=18)
    draw.rounded_rectangle((right[0] - 220, right[1] - 170, right[0] + 220, right[1] + 170), radius=44, fill=cartoon.AMBER, outline=cartoon.INK, width=18)
    # Literal supply crates with handles and straps.
    for row in range(2):
        for col in range(2):
            bx = left[0] - 135 + col * 145
            by = left[1] - 105 + row * 115
            draw.rounded_rectangle((bx, by, bx + 105, by + 78), radius=10, fill=cartoon.WHITE, outline=cartoon.INK, width=7)
            draw.line((bx + 15, by + 39, bx + 90, by + 39), fill=cartoon.BLUE, width=5)
            draw.arc((bx + 34, by - 8, bx + 72, by + 25), 180, 360, fill=cartoon.INK, width=4)
    dome_y = right[1] + 75
    draw.pieslice((right[0] - 145, right[1] - 125, right[0] + 145, dome_y), 180, 360, fill=(186, 222, 234), outline=cartoon.INK, width=11)
    draw.rectangle((right[0] - 34, right[1] - 18, right[0] + 34, dome_y), fill=cartoon.DARK_MUTED, outline=cartoon.INK, width=6)
    _solar_array(draw, right[0] + 150, right[1] - 55, 0.52)
    v3._arrow(draw, (left[0] + 235, left[1] - 52), (right[0] - 235, right[1] - 52), progress)
    v3._arrow(draw, (right[0] - 235, right[1] + 92), (left[0] + 235, left[1] + 92), progress)


cartoon._person = _person
cartoon._draw_route_map = _draw_route_map
cartoon._draw_presenter = _draw_presenter
cartoon._draw_transport = _draw_transport
cartoon._draw_habitat = _draw_habitat
cartoon._draw_council = _draw_council
cartoon._draw_process = _draw_process
