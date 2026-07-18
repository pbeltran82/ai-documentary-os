from __future__ import annotations

"""Art Polish v9: direct repeated templates with six distinct camera setups."""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v6 as v6
from . import cartoon_art_polish_v7 as v7
from . import cartoon_art_polish_v8 as v8


_ACTIVE_VARIANT = 0
_COLORS = (cartoon.BLUE, cartoon.AMBER, cartoon.PURPLE, cartoon.GREEN, cartoon.CYAN, cartoon.RED)


def _draw_presenter(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    variant = _ACTIVE_VARIANT % 6
    draw.rectangle((0, 0, width, height), fill=(228, 239, 245))
    for x in range(0, width, 112):
        draw.line((x, 0, x, height), fill=(202, 222, 234), width=3)
    for y in range(0, height, 112):
        draw.line((0, y, width, y), fill=(202, 222, 234), width=3)

    if variant in (0, 3):
        # Medium close-up: presenter dominates the frame.
        px = round(width * (0.60 if variant == 0 else 0.40))
        v8._human(draw, px, round(height * 0.31), 2.05, _COLORS[variant], "point")
        sx1 = 90 if variant == 0 else width - 760
        sx2 = sx1 + 650
        draw.rounded_rectangle((sx1, 90, sx2, 455), radius=28, fill=cartoon.CYAN, outline=cartoon.INK, width=12)
        draw.line((sx1 + 60, 190, sx2 - 60, 190), fill=cartoon.BLUE, width=12)
        draw.line((sx1 + 60, 275, sx2 - 170, 275), fill=cartoon.DARK_MUTED, width=9)
        draw.line((sx1 + 60, 350, sx2 - 240, 350), fill=cartoon.AMBER, width=9)
        desk_y = round(height * 0.80)
        draw.rounded_rectangle((round(width * 0.28), desk_y, round(width * 0.72), desk_y + 90), radius=24, fill=(77, 80, 86), outline=cartoon.INK, width=14)
    elif variant in (1, 4):
        # Over-the-shoulder analysis shot.
        screen = (round(width * 0.38), 90, width - 90, round(height * 0.72))
        draw.rounded_rectangle(screen, radius=34, fill=cartoon.WHITE, outline=cartoon.INK, width=14)
        for i, value in enumerate((0.35, 0.58, 0.46, 0.78, 0.64)):
            bx = screen[0] + 90 + i * 180
            by = screen[3] - 70
            top = by - round(360 * value)
            draw.rounded_rectangle((bx, top, bx + 105, by), radius=10, fill=_COLORS[i], outline=cartoon.INK, width=6)
        v8._human(draw, round(width * 0.18), round(height * 0.47), 1.65, _COLORS[variant], "point")
    else:
        # Side-profile studio with planet model and shallow console.
        v8._human(draw, round(width * 0.34), round(height * 0.35), 1.82, _COLORS[variant], "point")
        cx, cy = round(width * 0.74), round(height * 0.40)
        draw.ellipse((cx - 180, cy - 180, cx + 180, cy + 180), fill=cartoon.BLUE, outline=cartoon.INK, width=14)
        draw.polygon(((cx - 110, cy - 20), (cx - 35, cy - 110), (cx + 70, cy - 50), (cx + 48, cy + 70), (cx - 65, cy + 95)), fill=cartoon.GREEN, outline=cartoon.INK)
        draw.arc((cx - 235, cy - 90, cx + 235, cy + 165), 195, 345, fill=cartoon.AMBER, width=13)
        draw.rounded_rectangle((250, 815, 1080, 900), radius=22, fill=(77, 80, 86), outline=cartoon.INK, width=14)


def _draw_transport(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    variant = _ACTIVE_VARIANT % 6
    draw.rectangle((0, 0, width, height), fill=(226, 237, 244))
    platform = round(height * 0.80)
    draw.rectangle((0, platform, width, height), fill=(193, 198, 203))

    if variant == 0:
        v7._draw_transport(draw, width, height, progress)
    elif variant == 1:
        # Low-angle ramp close-up.
        v7._spacecraft(draw, 1110, 235, 2.10, progress)
        draw.polygon(((720, 420), (1280, 420), (1560, platform), (430, platform)), fill=cartoon.AMBER, outline=cartoon.INK)
        for i in range(5):
            accent = _COLORS[i] if i in (1, 4) else None
            v8._person(draw, 585 + i * 185, 585 + (i % 2) * 24, 0.80, accent=accent, pose="walk")
    elif variant == 2:
        # Overhead terminal plan view.
        draw.rounded_rectangle((110, 110, width - 110, height - 105), radius=42, fill=(207, 214, 220), outline=cartoon.INK, width=16)
        draw.rounded_rectangle((180, 190, 720, 470), radius=30, fill=(74, 82, 92), outline=cartoon.INK, width=12)
        draw.polygon(((720, 285), (1290, 285), (1490, 590), (720, 590)), fill=cartoon.AMBER, outline=cartoon.INK)
        v7._spacecraft(draw, 1370, 440, 1.35, progress)
        for i in range(7):
            accent = _COLORS[i % len(_COLORS)] if i % 3 == 0 else None
            v8._person(draw, 430 + i * 165, 650 + (i % 2) * 35, 0.58, accent=accent, pose="walk")
    elif variant == 3:
        # Ship doorway close-up.
        draw.rounded_rectangle((120, 95, width - 120, 735), radius=48, fill=(198, 205, 212), outline=cartoon.INK, width=18)
        draw.rounded_rectangle((610, 155, 1310, 665), radius=38, fill=(57, 65, 75), outline=cartoon.INK, width=16)
        for lx in (730, 1190):
            draw.ellipse((lx - 18, 215, lx + 18, 251), fill=cartoon.CYAN, outline=cartoon.INK, width=4)
        draw.polygon(((655, 590), (1265, 590), (1510, platform), (410, platform)), fill=cartoon.AMBER, outline=cartoon.INK)
        for i in range(4):
            accent = _COLORS[i] if i % 2 else None
            v8._person(draw, 650 + i * 205, 600, 0.86, accent=accent, pose="walk")
    elif variant == 4:
        # Departure silhouette.
        draw.rectangle((0, 0, width, round(height * 0.55)), fill=(182, 211, 229))
        v7._spacecraft(draw, 1010, 330, 2.25, progress)
        draw.line((180, platform - 22, 1740, platform - 22), fill=cartoon.INK, width=18)
        for i in range(4):
            v8._person(draw, 470 + i * 260, 605, 0.78, accent=_COLORS[i] if i in (0, 3) else None)
    else:
        # Interior boarding corridor.
        draw.rounded_rectangle((80, 70, width - 80, height - 70), radius=46, fill=(217, 226, 232), outline=cartoon.INK, width=16)
        draw.rounded_rectangle((680, 115, 1240, 680), radius=38, fill=(61, 69, 79), outline=cartoon.INK, width=14)
        for i in range(5):
            draw.line((180 + i * 365, 70, 180 + i * 365, height - 70), fill=(151, 160, 169), width=7)
        for i in range(5):
            v8._person(draw, 520 + i * 190, 585 + (i % 2) * 20, 0.76, accent=_COLORS[i] if i in (1, 4) else None, pose="walk")


def _draw_habitat(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    variant = _ACTIVE_VARIANT % 6
    ground = round(height * 0.77)
    draw.rectangle((0, 0, width, height), fill=(239, 218, 197))
    v6._rugged_ridges(draw, width, ground, variant)
    draw.rectangle((0, ground, width, height), fill=(190, 105, 70))

    if variant in (0, 1, 2, 3):
        # Reuse the four proven v7 layouts.
        old = v7._ACTIVE_VARIANT
        try:
            v7._ACTIVE_VARIANT = variant
            v7._draw_habitat(draw, width, height, progress)
        finally:
            v7._ACTIVE_VARIANT = old
    elif variant == 4:
        # Side-angle habitat cluster.
        v8._fixed_habitat(draw, round(width * 0.40), ground, 0.78)
        v8._fixed_habitat(draw, round(width * 0.73), ground, 0.52)
        draw.line((845, ground - 85, 1260, ground - 65), fill=(122, 151, 164), width=56)
        draw.line((845, ground - 85, 1260, ground - 65), fill=cartoon.INK, width=8)
        for i in range(3):
            v6._robot(draw, 1030 + i * 125, 600 + i * 10, 0.66, "walk")
    else:
        # Tight airlock operation close-up.
        draw.rounded_rectangle((150, 85, width - 150, height - 75), radius=48, fill=(213, 224, 230), outline=cartoon.INK, width=16)
        draw.rounded_rectangle((650, 135, 1270, 760), radius=42, fill=(70, 78, 88), outline=cartoon.INK, width=16)
        draw.rounded_rectangle((770, 245, 1150, 670), radius=30, fill=(120, 153, 169), outline=cartoon.INK, width=12)
        for lx in (715, 1205):
            draw.ellipse((lx - 20, 250, lx + 20, 290), fill=cartoon.CYAN, outline=cartoon.INK, width=5)
        v8._human(draw, 430, 455, 1.35, cartoon.GREEN, "point")
        v6._robot(draw, 1480, 490, 1.05, "stand")


def _draw_route_map(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    variant = _ACTIVE_VARIANT % 3
    if variant == 0:
        v8._draw_route_map(draw, width, height, progress)
        return

    draw.rectangle((0, 0, width, height), fill=cartoon.PAPER)
    for index in range(30):
        sx = (index * 181) % width
        sy = 24 + (index * 83) % round(height * 0.38)
        r = 2 + index % 3
        draw.ellipse((sx - r, sy - r, sx + r, sy + r), fill=cartoon.MUTED)

    if variant == 1:
        # Diagonal travel composition.
        cartoon._planet(draw, (360, 760), 225, cartoon.BLUE, progress)
        cartoon._planet(draw, (1560, 310), 190, cartoon.MARS, 1 - progress)
        path = (430, 145, 1590, 865)
        for start in range(205, 336, 18):
            draw.arc(path, start, min(start + 10, 340), fill=cartoon.INK, width=11)
        ship_x = round(650 + 640 * cartoon._ease(progress))
        ship_y = round(620 - 290 * cartoon._ease(progress))
        v7._spacecraft(draw, ship_x, ship_y, 1.08, progress)
    else:
        # Close destination approach.
        cartoon._planet(draw, (1510, 590), 265, cartoon.MARS, 1 - progress)
        draw.arc((280, 140, 1510, 900), 210, 338, fill=cartoon.INK, width=12)
        ship_x = round(560 + 590 * cartoon._ease(progress))
        ship_y = round(500 - 120 * math.sin(progress * math.pi))
        v7._spacecraft(draw, ship_x, ship_y, 1.30, progress)
        draw.ellipse((260, 700, 500, 940), fill=cartoon.BLUE, outline=cartoon.INK, width=14)


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
    beat_index = int(max(0.0, time_seconds) // max(1.0, duration_seconds / 3.0))
    _ACTIVE_VARIANT = (scene_number * 3 + beat_index * 2) % 6

    image = Image.new("RGB", (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT), cartoon.PAPER)
    draw = ImageDraw.Draw(image)
    if selected.template_id == "route_map":
        _draw_route_map(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "crowd_focus":
        v8._crowd(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress, focal=True)
    elif selected.template_id == "presenter_desk":
        _draw_presenter(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "transport_scene":
        _draw_transport(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "habitat_build":
        _draw_habitat(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "council_scene":
        v7._draw_council(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    else:
        cartoon._draw_process(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    return image


cartoon._draw_presenter = _draw_presenter
cartoon._draw_transport = _draw_transport
cartoon._draw_habitat = _draw_habitat
cartoon._draw_route_map = _draw_route_map
cartoon.render_planned_frame = render_planned_frame
