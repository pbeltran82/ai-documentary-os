from __future__ import annotations

"""Art Polish v6: strict human/robot language, fixed habitats, and varied shots."""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon


_ACTIVE_VARIANT = 0
_HUMAN_COLORS = (cartoon.BLUE, cartoon.AMBER, cartoon.PURPLE, cartoon.GREEN, cartoon.CYAN, cartoon.RED)
_HAIR_COLORS = ((45, 34, 28), (88, 55, 34), (23, 25, 29), (132, 84, 49))
_ROBOT_LIGHT = (154, 160, 168)
_ROBOT_DARK = (79, 85, 94)


def _line(scale: float) -> int:
    return max(4, round(8 * scale))


def _robot(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0, pose: str = "stand") -> None:
    line = _line(scale)
    head = round(50 * scale)
    torso_w = round(72 * scale)
    torso_h = round(82 * scale)
    neck_h = round(15 * scale)
    torso_top = y + head // 2 + neck_h + round(6 * scale)
    bottom = torso_top + torso_h

    # Robots are always gray and deliberately square.
    draw.rectangle((x - head // 2, y - head // 2, x + head // 2, y + head // 2), fill=_ROBOT_LIGHT, outline=cartoon.INK, width=line)
    draw.rectangle((x - round(9 * scale), y + head // 2, x + round(9 * scale), torso_top), fill=_ROBOT_DARK, outline=cartoon.INK, width=max(2, line // 2))
    draw.rectangle((x - torso_w // 2, torso_top, x + torso_w // 2, bottom), fill=_ROBOT_DARK, outline=cartoon.INK, width=line)
    draw.rounded_rectangle((x - round(18 * scale), y - round(8 * scale), x + round(18 * scale), y + round(7 * scale)), radius=max(2, round(4 * scale)), fill=cartoon.CYAN, outline=cartoon.INK, width=max(2, line // 3))

    shoulder_y = torso_top + round(16 * scale)
    elbow_y = shoulder_y + round(30 * scale)
    hand_y = shoulder_y + round(56 * scale)
    swing = round(10 * scale) if pose == "walk" else 0
    for direction in (-1, 1):
        elbow_x = x + direction * round(48 * scale)
        hand_x = x + direction * (round(42 * scale) + swing)
        draw.line((x + direction * torso_w // 2, shoulder_y, elbow_x, elbow_y, hand_x, hand_y), fill=cartoon.INK, width=line, joint="curve")
        r = max(3, round(6 * scale))
        draw.ellipse((elbow_x - r, elbow_y - r, elbow_x + r, elbow_y + r), fill=_ROBOT_LIGHT, outline=cartoon.INK, width=max(2, line // 3))

    hip_y = bottom
    knee_y = hip_y + round(31 * scale)
    foot_y = hip_y + round(62 * scale)
    for direction in (-1, 1):
        knee_x = x + direction * round(20 * scale)
        foot_x = x + direction * (round(25 * scale) + swing)
        draw.line((x + direction * round(15 * scale), hip_y, knee_x, knee_y, foot_x, foot_y), fill=cartoon.INK, width=line, joint="curve")
        draw.rounded_rectangle((foot_x - round(12 * scale), foot_y - round(5 * scale), foot_x + round(12 * scale), foot_y + round(6 * scale)), radius=max(2, round(4 * scale)), fill=cartoon.INK)


def _human(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int], pose: str = "stand") -> None:
    line = _line(scale)
    skin = (226, 170, 118)
    head_r = round(29 * scale)
    body_w = round(78 * scale)
    body_h = round(92 * scale)
    neck_h = round(22 * scale)
    torso_top = y + head_r + neck_h - round(2 * scale)
    shoulder_y = torso_top + round(15 * scale)
    bottom = torso_top + body_h

    draw.rounded_rectangle((x - round(9 * scale), y + head_r - 3, x + round(9 * scale), torso_top + 2), radius=max(2, round(4 * scale)), fill=skin, outline=cartoon.INK, width=max(2, line // 2))
    draw.polygon(((x - round(20 * scale), torso_top), (x - body_w // 2, shoulder_y), (x - body_w // 2 + round(6 * scale), bottom), (x + body_w // 2 - round(6 * scale), bottom), (x + body_w // 2, shoulder_y), (x + round(20 * scale), torso_top)), fill=color, outline=cartoon.INK)
    draw.line(((x - round(20 * scale), torso_top), (x - body_w // 2, shoulder_y), (x - body_w // 2 + round(6 * scale), bottom), (x + body_w // 2 - round(6 * scale), bottom), (x + body_w // 2, shoulder_y), (x + round(20 * scale), torso_top)), fill=cartoon.INK, width=line, joint="curve")
    draw.ellipse((x - head_r, y - head_r, x + head_r, y + head_r), fill=skin, outline=cartoon.INK, width=line)

    # Large, unmistakable hair silhouettes.
    hair = _HAIR_COLORS[(x // 71 + y // 53) % len(_HAIR_COLORS)]
    style = (x // 97 + y // 41) % 4
    if style == 0:
        draw.pieslice((x - head_r + 2, y - head_r + 2, x + head_r - 2, y + head_r - 2), 180, 360, fill=hair)
    elif style == 1:
        draw.pieslice((x - head_r + 2, y - head_r + 2, x + head_r - 2, y + head_r - 2), 175, 365, fill=hair)
        draw.ellipse((x - head_r - round(8 * scale), y - round(8 * scale), x - head_r + round(10 * scale), y + round(20 * scale)), fill=hair)
    elif style == 2:
        for dx in (-18, -6, 6, 18):
            r = round(10 * scale)
            draw.ellipse((x + round(dx * scale) - r, y - head_r - r // 2, x + round(dx * scale) + r, y - head_r + r * 3 // 2), fill=hair)
    else:
        draw.polygon(((x - head_r + 3, y - round(5 * scale)), (x - round(14 * scale), y - head_r + 2), (x + round(2 * scale), y - round(10 * scale)), (x + round(17 * scale), y - head_r + 3), (x + head_r - 3, y - round(2 * scale))), fill=hair)

    eye = max(2, round(4 * scale))
    for ex in (x - round(10 * scale), x + round(10 * scale)):
        draw.ellipse((ex - eye, y - eye, ex + eye, y + eye), fill=cartoon.INK)
    draw.arc((x - round(14 * scale), y + round(4 * scale), x + round(14 * scale), y + round(23 * scale)), 10, 170, fill=cartoon.INK, width=max(2, round(3 * scale)))

    elbow_y = shoulder_y + round(34 * scale)
    hand_y = shoulder_y + round(62 * scale)
    if pose == "point":
        draw.line((x - body_w // 2, shoulder_y, x - round(58 * scale), elbow_y, x - round(92 * scale), y), fill=cartoon.INK, width=line, joint="curve")
        draw.line((x + body_w // 2, shoulder_y, x + round(50 * scale), elbow_y, x + round(42 * scale), hand_y), fill=cartoon.INK, width=line, joint="curve")
    else:
        for direction in (-1, 1):
            draw.line((x + direction * body_w // 2, shoulder_y, x + direction * round(49 * scale), elbow_y, x + direction * round(38 * scale), hand_y), fill=cartoon.INK, width=line, joint="curve")
    hip_y = bottom
    knee_y = hip_y + round(34 * scale)
    foot_y = hip_y + round(67 * scale)
    for direction in (-1, 1):
        foot_x = x + direction * round(27 * scale)
        draw.line((x + direction * round(17 * scale), hip_y, x + direction * round(22 * scale), knee_y, foot_x, foot_y), fill=cartoon.INK, width=line, joint="curve")
        draw.rounded_rectangle((foot_x - round(12 * scale), foot_y - round(5 * scale), foot_x + round(12 * scale), foot_y + round(6 * scale)), radius=max(2, round(4 * scale)), fill=cartoon.INK)


def _person(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0, *, accent: tuple[int, int, int] | None = None, pose: str = "stand") -> None:
    if accent is None:
        _robot(draw, x, y, scale, pose)
    else:
        color = accent if accent not in (_ROBOT_LIGHT, _ROBOT_DARK, cartoon.MUTED, cartoon.DARK_MUTED) else _HUMAN_COLORS[(x // 83 + y // 67) % len(_HUMAN_COLORS)]
        _human(draw, x, y, scale, color, pose)


def _spacecraft(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, progress: float) -> None:
    w = round(250 * scale)
    h = round(104 * scale)
    line = max(6, round(11 * scale))
    left = x - w // 2
    right = x + w // 2
    draw.rounded_rectangle((left, y - h // 2, right, y + h // 2), radius=round(42 * scale), fill=(205, 210, 216), outline=cartoon.INK, width=line)
    # The blue nose is attached directly to the hull; no floating triangle.
    nose = round(58 * scale)
    draw.polygon(((right - 2, y - h // 2 + line // 2), (right + nose, y), (right - 2, y + h // 2 - line // 2)), fill=cartoon.BLUE, outline=cartoon.INK)
    draw.rectangle((left - round(26 * scale), y - round(25 * scale), left + 3, y + round(25 * scale)), fill=cartoon.DARK_MUTED, outline=cartoon.INK, width=max(4, line // 2))
    for offset in (-0.26, 0.0, 0.26):
        cx = x + round(w * offset)
        r = round(17 * scale)
        draw.ellipse((cx - r, y - r, cx + r, y + r), fill=cartoon.CYAN, outline=cartoon.INK, width=max(3, round(5 * scale)))
    flame = round(44 * scale * (0.8 + 0.2 * math.sin(progress * math.pi * 8)))
    draw.polygon(((left - round(25 * scale), y - round(18 * scale)), (left - round(25 * scale) - flame, y), (left - round(25 * scale), y + round(18 * scale))), fill=cartoon.AMBER, outline=cartoon.INK)


def _rugged_ridges(draw: ImageDraw.ImageDraw, width: int, ground: int, variant: int) -> None:
    layers = (
        ((0, ground), (90, 520), (190, 585), (275, 430), (370, 555), (485, 470), (610, ground), (760, 510), (905, 450), (1045, 560), (1190, 410), (1335, 525), (1510, 455), (1690, 550), (1920, ground)),
        ((0, ground), (120, 610), (240, 565), (360, 650), (505, 535), (660, 625), (825, 545), (980, 630), (1140, 520), (1310, 605), (1480, 535), (1650, 620), (1920, ground)),
        ((0, ground), (160, 560), (300, 485), (430, 590), (600, 500), (760, 565), (900, 460), (1060, 540), (1220, 475), (1400, 590), (1580, 490), (1740, 550), (1920, ground)),
    )
    points = layers[variant % len(layers)]
    draw.polygon(points, fill=(158, 76, 52))
    draw.line(points[1:-1], fill=cartoon.INK, width=8, joint="curve")


def _fixed_habitat(draw: ImageDraw.ImageDraw, cx: int, ground: int, scale: float = 1.0) -> None:
    # Stable geometry: never inflates or deflates with animation progress.
    dome_w = round(330 * scale)
    dome_h = round(215 * scale)
    draw.pieslice((cx - dome_w, ground - dome_h * 2, cx + dome_w, ground), 180, 360, fill=(187, 225, 236), outline=cartoon.INK, width=18)
    for frac in (-0.66, -0.33, 0.0, 0.33, 0.66):
        px = cx + round(dome_w * frac)
        draw.line((px, ground - round(dome_h * (1.75 - abs(frac) * 0.45)), px, ground), fill=cartoon.INK, width=5)
    draw.rounded_rectangle((cx - 58, ground - 148, cx + 58, ground), radius=18, fill=(72, 78, 84), outline=cartoon.INK, width=10)
    draw.line((cx - 38, ground - 112, cx + 38, ground - 112), fill=cartoon.AMBER, width=9)
    draw.ellipse((cx + 28, ground - 76, cx + 43, ground - 61), fill=cartoon.WHITE, outline=cartoon.INK, width=3)


def _draw_habitat(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    ground = round(height * 0.76)
    draw.rectangle((0, 0, width, height), fill=(239, 218, 197))
    _rugged_ridges(draw, width, ground, _ACTIVE_VARIANT)
    draw.rectangle((0, ground, width, height), fill=(190, 105, 70))

    variant = _ACTIVE_VARIANT % 3
    if variant == 0:
        _fixed_habitat(draw, round(width * 0.58), ground, 1.0)
        _human(draw, round(width * 0.25), round(height * 0.48), 1.1, cartoon.AMBER, "point")
        for index in range(3):
            _robot(draw, round(width * (0.76 + index * 0.07)), round(height * (0.48 + 0.025 * (index % 2))), 0.64, "walk")
    elif variant == 1:
        _fixed_habitat(draw, round(width * 0.34), ground, 0.78)
        _spacecraft(draw, round(width * 0.73), round(height * 0.32), 1.0, progress)
        for index in range(4):
            _robot(draw, round(width * (0.50 + index * 0.075)), round(height * 0.58), 0.58, "walk")
        _human(draw, round(width * 0.83), round(height * 0.52), 0.9, cartoon.BLUE, "stand")
    else:
        # Interior maintenance shot for visual variety.
        draw.rounded_rectangle((100, 70, width - 100, height - 65), radius=45, fill=(218, 229, 234), outline=cartoon.INK, width=16)
        for x in (340, 760, 1180, 1600):
            draw.line((x, 70, x, height - 65), fill=(150, 160, 169), width=7)
        draw.rounded_rectangle((round(width * 0.12), round(height * 0.25), round(width * 0.46), round(height * 0.68)), radius=24, fill=(93, 112, 126), outline=cartoon.INK, width=14)
        for index in range(3):
            sx = round(width * (0.17 + index * 0.09))
            draw.rounded_rectangle((sx, round(height * 0.33), sx + 115, round(height * 0.47)), radius=12, fill=_HUMAN_COLORS[index], outline=cartoon.INK, width=7)
        _human(draw, round(width * 0.62), round(height * 0.42), 1.15, cartoon.PURPLE, "point")
        _robot(draw, round(width * 0.80), round(height * 0.44), 0.9, "stand")


def _draw_transport(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    variant = _ACTIVE_VARIANT % 3
    draw.rectangle((0, 0, width, height), fill=(226, 237, 244))
    platform = round(height * 0.78)
    draw.rectangle((0, platform, width, height), fill=(204, 208, 212))
    if variant == 0:
        draw.rounded_rectangle((70, 130, 640, 690), radius=30, fill=(188, 192, 198), outline=cartoon.INK, width=18)
        for index in range(3):
            x1 = 130 + index * 150
            draw.rectangle((x1, 220, x1 + 105, 380), fill=cartoon.CYAN, outline=cartoon.INK, width=8)
        _spacecraft(draw, 1300, 300, 1.55, progress)
        cartoon._crowd(draw, width, height, progress, focal=True)
    elif variant == 1:
        _spacecraft(draw, 960, 270, 1.9, progress)
        draw.polygon(((760, 420), (1160, 420), (1300, platform), (690, platform)), fill=cartoon.AMBER, outline=cartoon.INK)
        for index in range(7):
            accent = _HUMAN_COLORS[index % len(_HUMAN_COLORS)] if index in (2, 5) else None
            _person(draw, 600 + index * 115, 560 + (index % 2) * 18, 0.66, accent=accent, pose="walk")
    else:
        draw.rounded_rectangle((110, 120, 1810, 680), radius=36, fill=(196, 203, 210), outline=cartoon.INK, width=18)
        for index in range(6):
            x1 = 180 + index * 255
            draw.rectangle((x1, 210, x1 + 165, 400), fill=cartoon.CYAN, outline=cartoon.INK, width=9)
        for index in range(8):
            accent = _HUMAN_COLORS[index % len(_HUMAN_COLORS)] if index % 3 == 0 else None
            _person(draw, 350 + index * 160, 560, 0.7, accent=accent)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    """Render edge-to-edge art without the obsolete white storyboard header."""
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
    _ACTIVE_VARIANT = (scene_number + beat_index) % 3

    image = Image.new("RGB", (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT), cartoon.PAPER)
    draw = ImageDraw.Draw(image)
    if selected.template_id == "route_map":
        cartoon._draw_route_map(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "crowd_focus":
        cartoon._crowd(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, focal=True)
    elif selected.template_id == "presenter_desk":
        cartoon._draw_presenter(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "transport_scene":
        _draw_transport(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "habitat_build":
        _draw_habitat(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "council_scene":
        cartoon._draw_council(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    else:
        cartoon._draw_process(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    return image


cartoon._person = _person
cartoon._spacecraft = _spacecraft
cartoon._draw_transport = _draw_transport
cartoon._draw_habitat = _draw_habitat
cartoon.render_planned_frame = render_planned_frame
