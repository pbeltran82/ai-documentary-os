from __future__ import annotations

"""Art Polish v7: cinematic shot variety and connected visual objects.

This pass preserves the established visual language while improving physical
relationships: spacecraft parts overlap into one silhouette, habitat airlocks
connect to the dome, transport scenes show boarding infrastructure, and desks
no longer dominate presenter/council compositions.
"""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v6 as v6


_ACTIVE_VARIANT = 0
_HUMAN_COLORS = (cartoon.BLUE, cartoon.AMBER, cartoon.PURPLE, cartoon.GREEN, cartoon.CYAN, cartoon.RED)


def _human(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    scale: float,
    color: tuple[int, int, int],
    pose: str = "stand",
) -> None:
    """Use the v6 human rig with larger hair that survives crowd-scale renders."""
    v6._human(draw, x, y, scale, color, pose)
    hair = ((45, 34, 28), (88, 55, 34), (23, 25, 29), (132, 84, 49))[(x // 71 + y // 53) % 4]
    head_r = round(29 * scale)
    tuft = max(4, round(10 * scale))
    style = (x // 97 + y // 41) % 3
    if style == 0:
        # Full cap with visible sideburns.
        draw.arc(
            (x - head_r - 2, y - head_r - 2, x + head_r + 2, y + head_r + 2),
            185,
            355,
            fill=hair,
            width=max(5, round(11 * scale)),
        )
        draw.ellipse((x - head_r - tuft // 2, y - round(10 * scale), x - head_r + tuft, y + round(19 * scale)), fill=hair)
    elif style == 1:
        # Curly crown.
        for dx in (-20, -10, 0, 10, 20):
            r = max(4, round(9 * scale))
            cx = x + round(dx * scale)
            cy = y - head_r - round(2 * scale)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=hair)
    else:
        # Side-part with a larger readable sweep.
        draw.polygon(
            (
                (x - head_r, y - round(2 * scale)),
                (x - round(17 * scale), y - head_r - round(7 * scale)),
                (x + round(4 * scale), y - round(13 * scale)),
                (x + round(20 * scale), y - head_r - round(3 * scale)),
                (x + head_r, y - round(2 * scale)),
            ),
            fill=hair,
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
        color = accent if accent not in (cartoon.MUTED, cartoon.DARK_MUTED) else _HUMAN_COLORS[(x // 83 + y // 67) % len(_HUMAN_COLORS)]
        _human(draw, x, y, scale, color, pose)


def _spacecraft(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, progress: float) -> None:
    """Draw one continuous capsule silhouette with overlapping nose and engine."""
    w = round(252 * scale)
    h = round(106 * scale)
    line = max(6, round(11 * scale))
    left = x - w // 2
    right = x + w // 2
    overlap = round(18 * scale)

    draw.rounded_rectangle(
        (left, y - h // 2, right, y + h // 2),
        radius=round(42 * scale),
        fill=(205, 210, 216),
        outline=cartoon.INK,
        width=line,
    )
    # Nose begins inside the hull, eliminating the outlined seam/gap.
    nose = round(66 * scale)
    draw.polygon(
        (
            (right - overlap, y - h // 2 + line // 2),
            (right + nose, y),
            (right - overlap, y + h // 2 - line // 2),
        ),
        fill=cartoon.BLUE,
        outline=cartoon.INK,
    )
    # Redraw hull/nose join as one uninterrupted contour.
    draw.line((right - overlap, y - h // 2 + line // 2, right + nose, y, right - overlap, y + h // 2 - line // 2), fill=cartoon.INK, width=max(4, line // 2), joint="curve")

    bell_w = round(34 * scale)
    draw.polygon(
        (
            (left + overlap, y - round(25 * scale)),
            (left - bell_w, y - round(34 * scale)),
            (left - bell_w, y + round(34 * scale)),
            (left + overlap, y + round(25 * scale)),
        ),
        fill=cartoon.DARK_MUTED,
        outline=cartoon.INK,
    )
    for offset in (-0.25, 0.0, 0.25):
        cx = x + round(w * offset)
        r = round(17 * scale)
        draw.ellipse((cx - r, y - r, cx + r, y + r), fill=cartoon.CYAN, outline=cartoon.INK, width=max(3, round(5 * scale)))
    flame = round(48 * scale * (0.86 + 0.14 * math.sin(progress * math.pi * 8)))
    draw.polygon(
        (
            (left - bell_w + 3, y - round(19 * scale)),
            (left - bell_w - flame, y),
            (left - bell_w + 3, y + round(19 * scale)),
        ),
        fill=cartoon.AMBER,
        outline=cartoon.INK,
    )


def _fixed_habitat(draw: ImageDraw.ImageDraw, cx: int, ground: int, scale: float = 1.0) -> None:
    """Stable dome with a visibly connected entrance tunnel and airlock bay."""
    dome_w = round(330 * scale)
    dome_h = round(215 * scale)
    draw.pieslice((cx - dome_w, ground - dome_h * 2, cx + dome_w, ground), 180, 360, fill=(187, 225, 236), outline=cartoon.INK, width=18)
    for frac in (-0.66, -0.33, 0.0, 0.33, 0.66):
        px = cx + round(dome_w * frac)
        draw.line((px, ground - round(dome_h * (1.75 - abs(frac) * 0.45)), px, ground), fill=cartoon.INK, width=5)

    # Entrance tunnel overlaps the dome and terminates in a clear airlock bay.
    tunnel_w = round(150 * scale)
    tunnel_h = round(82 * scale)
    tunnel_left = cx - tunnel_w // 2
    tunnel_top = ground - round(106 * scale)
    draw.rounded_rectangle(
        (tunnel_left, tunnel_top, tunnel_left + tunnel_w, tunnel_top + tunnel_h),
        radius=round(22 * scale),
        fill=(136, 163, 176),
        outline=cartoon.INK,
        width=10,
    )
    bay_w = round(112 * scale)
    bay_h = round(150 * scale)
    draw.rounded_rectangle(
        (cx - bay_w // 2, ground - bay_h, cx + bay_w // 2, ground),
        radius=round(18 * scale),
        fill=(72, 78, 84),
        outline=cartoon.INK,
        width=10,
    )
    draw.line((cx - round(36 * scale), ground - round(112 * scale), cx + round(36 * scale), ground - round(112 * scale)), fill=cartoon.AMBER, width=9)
    draw.ellipse((cx + round(26 * scale), ground - round(77 * scale), cx + round(42 * scale), ground - round(61 * scale)), fill=cartoon.WHITE, outline=cartoon.INK, width=3)


def _draw_presenter(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    variant = _ACTIVE_VARIANT % 3
    draw.rectangle((0, 0, width, height), fill=(228, 239, 245))
    for x in range(0, width, 96):
        draw.line((x, 0, x, height), fill=(201, 222, 234), width=3)
    for y in range(0, height, 96):
        draw.line((0, y, width, y), fill=(201, 222, 234), width=3)

    # Upper screens use the full frame and vary by shot.
    if variant == 0:
        screen = (90, 70, 590, 320)
        presenter_x, presenter_y = round(width * 0.64), round(height * 0.28)
    elif variant == 1:
        screen = (width - 620, 70, width - 90, 330)
        presenter_x, presenter_y = round(width * 0.34), round(height * 0.28)
    else:
        screen = (round(width * 0.27), 55, round(width * 0.73), 285)
        presenter_x, presenter_y = round(width * 0.50), round(height * 0.31)
    draw.rounded_rectangle(screen, radius=24, fill=cartoon.CYAN, outline=cartoon.INK, width=11)
    draw.line((screen[0] + 55, screen[1] + 80, screen[2] - 55, screen[1] + 80), fill=cartoon.BLUE, width=10)
    draw.line((screen[0] + 55, screen[1] + 145, screen[2] - 150, screen[1] + 145), fill=cartoon.DARK_MUTED, width=8)

    _human(draw, presenter_x, presenter_y, 1.72, _HUMAN_COLORS[variant], "point")
    # Slim console instead of a giant slab.
    desk_y = round(height * 0.72)
    desk_left = round(width * 0.23)
    desk_right = round(width * 0.77)
    draw.rounded_rectangle((desk_left, desk_y, desk_right, desk_y + 105), radius=26, fill=(78, 81, 87), outline=cartoon.INK, width=15)
    draw.line((desk_left + 90, desk_y + 105, desk_left + 55, height), fill=cartoon.INK, width=18)
    draw.line((desk_right - 90, desk_y + 105, desk_right - 55, height), fill=cartoon.INK, width=18)
    draw.rounded_rectangle((desk_left + 65, desk_y - 105, desk_left + 250, desk_y), radius=14, fill=cartoon.WHITE, outline=cartoon.INK, width=9)


def _draw_council(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    variant = _ACTIVE_VARIANT % 3
    draw.rectangle((0, 0, width, height), fill=(224, 232, 237))
    draw.rounded_rectangle((55, 45, width - 55, height - 45), radius=40, fill=(234, 239, 242), outline=cartoon.INK, width=15)
    # Wall displays and civic crest.
    draw.rounded_rectangle((105, 80, 510, 250), radius=22, fill=cartoon.CYAN, outline=cartoon.INK, width=9)
    draw.rounded_rectangle((width - 510, 80, width - 105, 250), radius=22, fill=cartoon.AMBER, outline=cartoon.INK, width=9)
    draw.ellipse((width // 2 - 70, 70, width // 2 + 70, 210), fill=cartoon.BLUE, outline=cartoon.INK, width=9)

    # Curved, shallower council desk rather than a full-width brown slab.
    table_y = round(height * 0.58)
    draw.arc((round(width * 0.17), table_y - 170, round(width * 0.83), table_y + 260), 190, 350, fill=cartoon.INK, width=70)
    draw.arc((round(width * 0.17), table_y - 170, round(width * 0.83), table_y + 260), 190, 350, fill=(112, 85, 65), width=48)

    positions = (0.34, 0.50, 0.66)
    for index, frac in enumerate(positions):
        pose = "point" if index == variant else "stand"
        _human(draw, round(width * frac), round(height * 0.31), 1.08, _HUMAN_COLORS[(index + variant) % len(_HUMAN_COLORS)], pose)
        # Individual microphone and monitor.
        px = round(width * frac)
        draw.line((px, table_y - 8, px + 18, table_y - 60), fill=cartoon.INK, width=6)
        draw.ellipse((px + 11, table_y - 69, px + 25, table_y - 55), fill=cartoon.RED, outline=cartoon.INK, width=3)
        draw.rounded_rectangle((px - 48, table_y + 20, px + 48, table_y + 75), radius=9, fill=cartoon.CYAN, outline=cartoon.INK, width=6)

    for index in range(6):
        accent = _HUMAN_COLORS[index % len(_HUMAN_COLORS)] if index in (1, 4) else None
        _person(draw, round(width * (0.24 + index * 0.105)), round(height * 0.78), 0.56, accent=accent)


def _draw_transport(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    variant = _ACTIVE_VARIANT % 4
    draw.rectangle((0, 0, width, height), fill=(226, 237, 244))
    platform = round(height * 0.80)
    draw.rectangle((0, platform, width, height), fill=(193, 198, 203))

    if variant == 0:
        # Wide terminal establishing shot.
        draw.rounded_rectangle((60, 95, 640, 690), radius=30, fill=(188, 192, 198), outline=cartoon.INK, width=18)
        for index in range(3):
            x1 = 125 + index * 155
            draw.rectangle((x1, 205, x1 + 110, 380), fill=cartoon.CYAN, outline=cartoon.INK, width=8)
        _spacecraft(draw, 1320, 285, 1.52, progress)
        ramp = ((1130, 390), (1410, 390), (1535, platform), (1030, platform))
        draw.polygon(ramp, fill=cartoon.AMBER, outline=cartoon.INK)
        cartoon._crowd(draw, width, height, progress, focal=True)
    elif variant == 1:
        # Medium boarding-ramp action shot.
        _spacecraft(draw, 1040, 250, 1.92, progress)
        draw.polygon(((805, 405), (1215, 405), (1370, platform), (680, platform)), fill=cartoon.AMBER, outline=cartoon.INK)
        for index in range(8):
            accent = _HUMAN_COLORS[index % len(_HUMAN_COLORS)] if index in (1, 4, 7) else None
            _person(draw, 610 + index * 105, 555 + (index % 2) * 20, 0.68, accent=accent, pose="walk")
    elif variant == 2:
        # Close-up doorway and loading detail.
        draw.rounded_rectangle((160, 110, 1760, 700), radius=42, fill=(198, 205, 212), outline=cartoon.INK, width=18)
        draw.rounded_rectangle((690, 170, 1230, 640), radius=35, fill=(66, 73, 82), outline=cartoon.INK, width=15)
        draw.polygon(((720, 570), (1200, 570), (1410, platform), (530, platform)), fill=cartoon.AMBER, outline=cartoon.INK)
        for index in range(6):
            accent = _HUMAN_COLORS[index] if index % 2 else None
            _person(draw, 590 + index * 145, 560, 0.75, accent=accent, pose="walk")
    else:
        # Side-profile departure shot.
        _spacecraft(draw, 1090, 300, 2.05, progress)
        draw.line((250, platform - 25, 1650, platform - 25), fill=cartoon.INK, width=18)
        draw.line((340, platform - 25, 340, platform), fill=cartoon.INK, width=14)
        draw.line((1570, platform - 25, 1570, platform), fill=cartoon.INK, width=14)
        for index in range(5):
            accent = _HUMAN_COLORS[index] if index in (0, 3) else None
            _person(draw, 390 + index * 180, 585, 0.72, accent=accent)


def _draw_habitat(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    ground = round(height * 0.77)
    variant = _ACTIVE_VARIANT % 4
    draw.rectangle((0, 0, width, height), fill=(239, 218, 197))
    v6._rugged_ridges(draw, width, ground, variant)
    draw.rectangle((0, ground, width, height), fill=(190, 105, 70))

    if variant == 0:
        _fixed_habitat(draw, round(width * 0.60), ground, 1.0)
        _human(draw, round(width * 0.24), round(height * 0.49), 1.12, cartoon.AMBER, "point")
        for index in range(3):
            v6._robot(draw, round(width * (0.78 + index * 0.065)), round(height * (0.50 + 0.025 * (index % 2))), 0.62, "walk")
    elif variant == 1:
        _fixed_habitat(draw, round(width * 0.31), ground, 0.72)
        _spacecraft(draw, round(width * 0.73), round(height * 0.30), 1.05, progress)
        for index in range(4):
            _person(draw, round(width * (0.49 + index * 0.08)), round(height * 0.58), 0.60, accent=_HUMAN_COLORS[index] if index == 2 else None, pose="walk")
    elif variant == 2:
        # Interior maintenance shot.
        draw.rounded_rectangle((85, 55, width - 85, height - 55), radius=45, fill=(218, 229, 234), outline=cartoon.INK, width=16)
        for x in (330, 750, 1170, 1590):
            draw.line((x, 55, x, height - 55), fill=(150, 160, 169), width=7)
        draw.rounded_rectangle((180, 235, 760, 720), radius=28, fill=(93, 112, 126), outline=cartoon.INK, width=14)
        for index in range(3):
            sx = 250 + index * 155
            draw.rounded_rectangle((sx, 330, sx + 120, 480), radius=12, fill=_HUMAN_COLORS[index], outline=cartoon.INK, width=7)
        _human(draw, 1190, 425, 1.18, cartoon.PURPLE, "point")
        v6._robot(draw, 1510, 450, 0.92, "stand")
    else:
        # Close-up cargo and airlock activity.
        _fixed_habitat(draw, round(width * 0.68), ground, 0.88)
        for index in range(3):
            x1 = 150 + index * 190
            draw.rounded_rectangle((x1, ground - 165, x1 + 145, ground), radius=12, fill=(132, 139, 147), outline=cartoon.INK, width=9)
            draw.line((x1 + 20, ground - 105, x1 + 125, ground - 105), fill=cartoon.AMBER, width=7)
        _human(draw, 660, 530, 1.02, cartoon.GREEN, "point")
        v6._robot(draw, 910, 560, 0.76, "walk")


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    """Render edge-to-edge art with deterministic four-way shot variation."""
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
    _ACTIVE_VARIANT = (scene_number * 2 + beat_index) % 4

    image = Image.new("RGB", (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT), cartoon.PAPER)
    draw = ImageDraw.Draw(image)
    if selected.template_id == "route_map":
        cartoon._draw_route_map(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "crowd_focus":
        cartoon._crowd(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, focal=True)
    elif selected.template_id == "presenter_desk":
        _draw_presenter(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "transport_scene":
        _draw_transport(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "habitat_build":
        _draw_habitat(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "council_scene":
        _draw_council(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    else:
        cartoon._draw_process(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    return image


# Install v7 after all earlier polish modules.
cartoon._person = _person
cartoon._spacecraft = _spacecraft
cartoon._draw_presenter = _draw_presenter
cartoon._draw_council = _draw_council
cartoon._draw_transport = _draw_transport
cartoon._draw_habitat = _draw_habitat
cartoon.render_planned_frame = render_planned_frame

# Earlier scene modules call v3._spacecraft directly; redirect those calls too.
from . import cartoon_art_polish_v3 as v3  # noqa: E402
v3._spacecraft = _spacecraft
