from __future__ import annotations

"""Art Polish v3 for the general cartoon documentary renderer.

This pass keeps the existing routing and timing contract while improving the
silhouette quality of characters and the definition of recurring documentary
objects: planets, route arrows, spacecraft, habitats, buildings, control rooms,
drones, cargo, and council/process compositions.
"""

import math

from PIL import ImageDraw

from . import cartoon_documentary as cartoon


def _line(scale: float) -> int:
    return max(4, round(9 * scale))


def _person(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    scale: float = 1.0,
    *,
    accent: tuple[int, int, int] | None = None,
    pose: str = "stand",
) -> None:
    line = _line(scale)
    head_r = round(31 * scale)
    neck_w = round(20 * scale)
    neck_h = round(20 * scale)
    body_w = round(74 * scale)
    body_h = round(92 * scale)
    fill = accent or cartoon.MUTED
    body_fill = fill if accent else cartoon.DARK_MUTED

    # Draw neck first so the head and torso overlap into one continuous silhouette.
    neck_top = y + head_r - round(4 * scale)
    draw.rounded_rectangle(
        (x - neck_w // 2, neck_top, x + neck_w // 2, neck_top + neck_h),
        radius=max(2, round(6 * scale)),
        fill=fill,
        outline=cartoon.INK,
        width=max(2, line // 2),
    )

    torso_top = neck_top + round(8 * scale)
    shoulder = round(15 * scale)
    torso = (
        x - body_w // 2,
        torso_top,
        x + body_w // 2,
        torso_top + body_h,
    )
    draw.rounded_rectangle(
        torso,
        radius=round(24 * scale),
        fill=body_fill,
        outline=cartoon.INK,
        width=line,
    )

    # Head overlaps the neck and torso top, removing the previous floating gap.
    draw.ellipse(
        (x - head_r, y - head_r, x + head_r, y + head_r),
        fill=fill,
        outline=cartoon.INK,
        width=line,
    )

    shoulder_y = torso_top + shoulder
    elbow_y = shoulder_y + round(34 * scale)
    hand_y = shoulder_y + round(62 * scale)
    hand_r = max(4, round(7 * scale))

    def limb(points: tuple[tuple[int, int], ...]) -> None:
        draw.line(points, fill=cartoon.INK, width=line, joint="curve")

    if pose == "point":
        limb(((x - body_w // 2, shoulder_y), (x - round(56 * scale), elbow_y), (x - round(92 * scale), y - round(2 * scale))))
        draw.ellipse((x - round(99 * scale), y - round(9 * scale), x - round(85 * scale), y + round(5 * scale)), fill=fill, outline=cartoon.INK, width=max(2, line // 2))
        limb(((x + body_w // 2, shoulder_y), (x + round(54 * scale), elbow_y), (x + round(47 * scale), hand_y)))
        draw.ellipse((x + round(40 * scale), hand_y - hand_r, x + round(54 * scale), hand_y + hand_r), fill=fill, outline=cartoon.INK, width=max(2, line // 2))
    elif pose == "carry":
        limb(((x - body_w // 2, shoulder_y), (x - round(50 * scale), elbow_y), (x - round(28 * scale), hand_y)))
        limb(((x + body_w // 2, shoulder_y), (x + round(50 * scale), elbow_y), (x + round(28 * scale), hand_y)))
        box_y = hand_y - round(8 * scale)
        draw.rounded_rectangle((x - round(34 * scale), box_y, x + round(34 * scale), box_y + round(34 * scale)), radius=round(5 * scale), fill=cartoon.AMBER, outline=cartoon.INK, width=max(3, line // 2))
    else:
        swing = round(10 * scale) if pose == "walk" else 0
        limb(((x - body_w // 2, shoulder_y), (x - round(48 * scale), elbow_y), (x - round(38 * scale) - swing, hand_y)))
        limb(((x + body_w // 2, shoulder_y), (x + round(48 * scale), elbow_y), (x + round(38 * scale) + swing, hand_y)))
        for hx in (x - round(38 * scale) - swing, x + round(38 * scale) + swing):
            draw.ellipse((hx - hand_r, hand_y - hand_r, hx + hand_r, hand_y + hand_r), fill=fill, outline=cartoon.INK, width=max(2, line // 2))

    hip_y = torso_top + body_h - round(4 * scale)
    knee_y = hip_y + round(34 * scale)
    foot_y = hip_y + round(67 * scale)
    stride = round(16 * scale) if pose == "walk" else 0
    limb(((x - round(18 * scale), hip_y), (x - round(22 * scale) - stride, knee_y), (x - round(28 * scale) - stride, foot_y)))
    limb(((x + round(18 * scale), hip_y), (x + round(22 * scale) + stride, knee_y), (x + round(28 * scale) + stride, foot_y)))
    shoe_w = round(22 * scale)
    shoe_h = max(5, round(9 * scale))
    draw.rounded_rectangle((x - round(28 * scale) - stride - shoe_w // 2, foot_y - shoe_h // 2, x - round(28 * scale) - stride + shoe_w // 2, foot_y + shoe_h // 2), radius=shoe_h // 2, fill=cartoon.INK)
    draw.rounded_rectangle((x + round(28 * scale) + stride - shoe_w // 2, foot_y - shoe_h // 2, x + round(28 * scale) + stride + shoe_w // 2, foot_y + shoe_h // 2), radius=shoe_h // 2, fill=cartoon.INK)

    if accent:
        eye = max(2, round(4 * scale))
        draw.ellipse((x - round(10 * scale) - eye, y - eye, x - round(10 * scale) + eye, y + eye), fill=cartoon.INK)
        draw.ellipse((x + round(10 * scale) - eye, y - eye, x + round(10 * scale) + eye, y + eye), fill=cartoon.INK)
        draw.arc((x - round(14 * scale), y + round(3 * scale), x + round(14 * scale), y + round(23 * scale)), 10, 170, fill=cartoon.INK, width=max(2, round(3 * scale)))


def _planet(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int, color: tuple[int, int, int], progress: float) -> None:
    x, y = center
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color, outline=cartoon.INK, width=18)
    if color == cartoon.BLUE:
        land = cartoon.GREEN
        draw.polygon(((x - radius * 3 // 5, y - radius // 4), (x - radius // 5, y - radius * 2 // 3), (x + radius // 6, y - radius // 4), (x, y + radius // 7), (x - radius // 2, y + radius // 4)), fill=land, outline=cartoon.INK)
        draw.polygon(((x + radius // 4, y + radius // 8), (x + radius * 2 // 3, y - radius // 8), (x + radius * 3 // 5, y + radius // 3), (x + radius // 3, y + radius // 2)), fill=land, outline=cartoon.INK)
        draw.arc((x - radius - 26, y - radius // 3, x + radius + 26, y + radius // 3), 190, 350, fill=cartoon.WHITE, width=8)
    else:
        for dx, dy, rr in ((-0.34, -0.18, 0.15), (0.25, 0.17, 0.12), (0.05, -0.40, 0.08), (-0.12, 0.37, 0.10)):
            cx, cy, r = x + round(radius * dx), y + round(radius * dy), round(radius * rr)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(154, 67, 43), outline=cartoon.INK, width=max(4, radius // 30))
        draw.arc((x - radius - 24, y - radius // 5, x + radius + 24, y + radius // 5), 175, 355, fill=cartoon.AMBER, width=7)


def _arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], progress: float) -> None:
    p = cartoon._ease(progress)
    x2 = round(start[0] + (end[0] - start[0]) * p)
    y2 = round(start[1] + (end[1] - start[1]) * p)
    draw.line((start[0], start[1], x2, y2), fill=cartoon.WHITE, width=34)
    draw.line((start[0], start[1], x2, y2), fill=cartoon.INK, width=18)
    for fraction in (0.28, 0.52, 0.76):
        if p > fraction:
            px = round(start[0] + (end[0] - start[0]) * fraction)
            py = round(start[1] + (end[1] - start[1]) * fraction)
            draw.ellipse((px - 9, py - 9, px + 9, py + 9), fill=cartoon.AMBER, outline=cartoon.INK, width=4)
    if p > 0.72:
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        length, wing = 54, 34
        points = [
            end,
            (round(end[0] - length * math.cos(angle) + wing * math.sin(angle)), round(end[1] - length * math.sin(angle) - wing * math.cos(angle))),
            (round(end[0] - length * math.cos(angle) - wing * math.sin(angle)), round(end[1] - length * math.sin(angle) + wing * math.cos(angle))),
        ]
        draw.polygon(points, fill=cartoon.INK)


def _spacecraft(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, progress: float) -> None:
    w, h = round(250 * scale), round(105 * scale)
    draw.rounded_rectangle((x - w // 2, y - h // 2, x + w // 2, y + h // 2), radius=round(45 * scale), fill=(205, 210, 216), outline=cartoon.INK, width=max(6, round(12 * scale)))
    draw.polygon(((x + w // 2, y), (x + round(w * 0.72), y - round(h * 0.24)), (x + round(w * 0.72), y + round(h * 0.24))), fill=cartoon.BLUE, outline=cartoon.INK)
    draw.polygon(((x - round(w * 0.12), y + h // 2), (x - round(w * 0.42), y + round(h * 0.82)), (x + round(w * 0.08), y + h // 2)), fill=cartoon.MUTED, outline=cartoon.INK)
    for offset in (-0.23, 0.05, 0.30):
        cx = x + round(w * offset)
        r = round(18 * scale)
        draw.ellipse((cx - r, y - r, cx + r, y + r), fill=cartoon.CYAN, outline=cartoon.INK, width=max(3, round(6 * scale)))
    flame = round(55 * scale * (0.65 + 0.35 * math.sin(progress * math.pi * 8)))
    draw.polygon(((x - w // 2, y - round(22 * scale)), (x - w // 2 - flame, y), (x - w // 2, y + round(22 * scale))), fill=cartoon.AMBER, outline=cartoon.INK)


def _draw_route_map(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    _planet(draw, (round(width * 0.23), round(height * 0.56)), round(height * 0.20), cartoon.BLUE, progress)
    _planet(draw, (round(width * 0.78), round(height * 0.56)), round(height * 0.17), cartoon.MARS, 1 - progress)
    _arrow(draw, (round(width * 0.39), round(height * 0.49)), (round(width * 0.64), round(height * 0.49)), progress)
    ship_x = round(width * (0.39 + 0.25 * cartoon._ease(progress)))
    _spacecraft(draw, ship_x, round(height * 0.39), 0.62, progress)


def _draw_presenter(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    for x in range(0, width, 86):
        draw.line((x, 0, x, height), fill=(205, 228, 241), width=4)
    for y in range(0, height, 86):
        draw.line((0, y, width, y), fill=(205, 228, 241), width=4)
    desk_y = round(height * 0.72)
    draw.rounded_rectangle((80, desk_y, width - 80, height + 40), radius=28, fill=(70, 72, 78), outline=cartoon.INK, width=18)
    _person(draw, round(width * 0.48), round(height * 0.30), 1.55, accent=cartoon.BLUE, pose="point")
    draw.rounded_rectangle((round(width * 0.10), desk_y - 120, round(width * 0.25), desk_y), radius=12, fill=cartoon.WHITE, outline=cartoon.INK, width=10)
    draw.line((round(width * 0.125), desk_y - 85, round(width * 0.225), desk_y - 85), fill=cartoon.BLUE, width=7)
    draw.line((round(width * 0.125), desk_y - 55, round(width * 0.205), desk_y - 55), fill=cartoon.DARK_MUTED, width=6)
    draw.rounded_rectangle((round(width * 0.74), desk_y - 135, round(width * 0.88), desk_y - 10), radius=18, fill=cartoon.CYAN, outline=cartoon.INK, width=10)
    draw.line((round(width * 0.77), desk_y - 42, round(width * 0.85), desk_y - 105), fill=cartoon.INK, width=8)


def _draw_transport(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    platform = round(height * 0.77)
    draw.rectangle((0, platform, width, height), fill=(204, 208, 212))
    ship_y = round(height * 0.28)
    _spacecraft(draw, round(width * 0.66), ship_y, 1.45, progress)
    draw.rounded_rectangle((round(width * 0.08), round(height * 0.22), round(width * 0.43), round(height * 0.63)), radius=30, fill=(188, 192, 198), outline=cartoon.INK, width=18)
    draw.rectangle((round(width * 0.27), round(height * 0.31), round(width * 0.39), round(height * 0.63)), fill=(48, 52, 58), outline=cartoon.INK, width=10)
    draw.line((round(width * 0.43), round(height * 0.57), round(width * 0.57), platform), fill=cartoon.INK, width=18)
    draw.line((round(width * 0.43), round(height * 0.57), round(width * 0.57), platform), fill=cartoon.AMBER, width=8)
    cartoon._crowd(draw, width, height, progress, focal=True)


def _draw_habitat(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    ground = round(height * 0.73)
    draw.rectangle((0, ground, width, height), fill=(190, 105, 70))
    draw.polygon(((0, ground), (round(width * 0.18), round(height * 0.58)), (round(width * 0.34), ground), (round(width * 0.55), round(height * 0.62)), (round(width * 0.74), ground), (width, round(height * 0.57)), (width, ground)), fill=(167, 82, 55))
    cx = round(width * 0.58)
    dome_w = round(width * (0.20 + 0.17 * cartoon._ease(progress)))
    dome_h = round(height * (0.15 + 0.14 * cartoon._ease(progress)))
    draw.pieslice((cx - dome_w, ground - dome_h * 2, cx + dome_w, ground), 180, 360, fill=(187, 225, 236), outline=cartoon.INK, width=18)
    for frac in (-0.5, 0.0, 0.5):
        x = cx + round(dome_w * frac)
        draw.line((x, ground - dome_h * 1.9, x, ground), fill=cartoon.INK, width=5)
    draw.rectangle((cx - 45, ground - 120, cx + 45, ground), fill=(72, 78, 84), outline=cartoon.INK, width=8)
    for index in range(4):
        drone_x = round(width * (0.68 + index * 0.065))
        drone_y = round(height * (0.28 + (index % 2) * 0.08 - 0.04 * math.sin(progress * math.pi * 6 + index)))
        draw.ellipse((drone_x - 24, drone_y - 14, drone_x + 24, drone_y + 14), fill=cartoon.BLUE, outline=cartoon.INK, width=6)
        draw.line((drone_x - 38, drone_y, drone_x + 38, drone_y), fill=cartoon.INK, width=5)
    for index in range(3):
        bx = round(width * (0.77 + index * 0.07))
        draw.rounded_rectangle((bx, ground - 90, bx + 58, ground), radius=8, fill=cartoon.AMBER if index == 1 else cartoon.BLUE, outline=cartoon.INK, width=7)
    _person(draw, round(width * 0.24), round(height * 0.48), 1.05, accent=cartoon.AMBER, pose="carry")


def _draw_council(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    draw.rounded_rectangle((80, 80, width - 80, height - 70), radius=38, fill=(226, 232, 236), outline=cartoon.INK, width=16)
    for x in (220, width - 220):
        draw.rectangle((x - 55, 80, x + 55, height - 70), fill=(195, 202, 208), outline=cartoon.INK, width=8)
    table_y = round(height * 0.53)
    draw.rounded_rectangle((round(width * 0.18), table_y, round(width * 0.82), table_y + 130), radius=34, fill=(96, 76, 62), outline=cartoon.INK, width=16)
    _person(draw, round(width * 0.36), round(height * 0.30), 1.02, accent=cartoon.PURPLE, pose="point")
    _person(draw, round(width * 0.52), round(height * 0.30), 1.02, accent=cartoon.AMBER)
    _person(draw, round(width * 0.68), round(height * 0.30), 1.02, accent=cartoon.BLUE)
    for index in range(5):
        _person(draw, round(width * (0.27 + index * 0.115)), round(height * 0.76), 0.58, accent=None)


def _draw_process(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    left = (round(width * 0.24), round(height * 0.55))
    right = (round(width * 0.76), round(height * 0.55))
    draw.rounded_rectangle((left[0] - 210, left[1] - 175, left[0] + 210, left[1] + 175), radius=44, fill=cartoon.CYAN, outline=cartoon.INK, width=18)
    draw.rounded_rectangle((right[0] - 210, right[1] - 175, right[0] + 210, right[1] + 175), radius=44, fill=cartoon.AMBER, outline=cartoon.INK, width=18)
    # Left: cargo/supply system. Right: finished habitat/community outcome.
    for row in range(2):
        for col in range(2):
            bx = left[0] - 120 + col * 130
            by = left[1] - 90 + row * 105
            draw.rounded_rectangle((bx, by, bx + 92, by + 70), radius=10, fill=cartoon.WHITE, outline=cartoon.INK, width=7)
    dome_y = right[1] + 75
    draw.pieslice((right[0] - 130, right[1] - 115, right[0] + 130, dome_y), 180, 360, fill=(186, 222, 234), outline=cartoon.INK, width=11)
    _arrow(draw, (left[0] + 230, left[1] - 50), (right[0] - 230, right[1] - 50), progress)
    _arrow(draw, (right[0] - 230, right[1] + 90), (left[0] + 230, left[1] + 90), progress)


cartoon._person = _person
cartoon._planet = _planet
cartoon._arrow = _arrow
cartoon._draw_route_map = _draw_route_map
cartoon._draw_presenter = _draw_presenter
cartoon._draw_transport = _draw_transport
cartoon._draw_habitat = _draw_habitat
cartoon._draw_council = _draw_council
cartoon._draw_process = _draw_process
