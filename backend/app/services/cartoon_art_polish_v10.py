from __future__ import annotations

"""Art Polish v10: unify camera variants with coherent staging and depth."""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v6 as v6
from . import cartoon_art_polish_v7 as v7
from . import cartoon_art_polish_v8 as v8
from . import cartoon_art_polish_v9 as v9


_ACTIVE_VARIANT = 0
_COLORS = (cartoon.BLUE, cartoon.AMBER, cartoon.PURPLE, cartoon.GREEN, cartoon.CYAN, cartoon.RED)


def _studio_grid(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    draw.rectangle((0, 0, width, height), fill=(228, 239, 245))
    for x in range(0, width, 112):
        draw.line((x, 0, x, height), fill=(202, 222, 234), width=3)
    for y in range(0, height, 112):
        draw.line((0, y, width, y), fill=(202, 222, 234), width=3)


def _screen_chart(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], variant: int) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=30, fill=cartoon.WHITE, outline=cartoon.INK, width=13)
    if variant % 2 == 0:
        points = []
        values = (0.72, 0.58, 0.64, 0.42, 0.50, 0.27)
        for index, value in enumerate(values):
            px = x1 + 70 + index * (x2 - x1 - 140) // (len(values) - 1)
            py = y1 + 65 + round((y2 - y1 - 125) * value)
            points.append((px, py))
        draw.line(points, fill=cartoon.BLUE, width=13, joint="curve")
        for px, py in points:
            draw.ellipse((px - 11, py - 11, px + 11, py + 11), fill=cartoon.AMBER, outline=cartoon.INK, width=4)
    else:
        values = (0.35, 0.62, 0.46, 0.78)
        bar_w = (x2 - x1 - 120) // len(values)
        for index, value in enumerate(values):
            bx = x1 + 45 + index * bar_w
            by = y2 - 45
            top = by - round((y2 - y1 - 110) * value)
            draw.rounded_rectangle((bx, top, bx + bar_w - 18, by), radius=9, fill=_COLORS[index], outline=cartoon.INK, width=5)


def _draw_presenter(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Make the presenter visibly engage with the graphic instead of facing front."""
    variant = _ACTIVE_VARIANT % 4
    _studio_grid(draw, width, height)

    if variant == 0:
        screen = (90, 90, 820, 610)
        _screen_chart(draw, screen, variant)
        v8._human(draw, 1260, 370, 1.92, cartoon.BLUE, "point")
        draw.rounded_rectangle((1010, 815, 1610, 900), radius=24, fill=(77, 80, 86), outline=cartoon.INK, width=14)
    elif variant == 1:
        # Over-the-shoulder composition: foreground shoulder anchors depth.
        screen = (540, 80, 1810, 735)
        _screen_chart(draw, screen, variant)
        draw.ellipse((40, 520, 610, 1090), fill=cartoon.PURPLE, outline=cartoon.INK, width=18)
        draw.pieslice((110, 320, 430, 640), 180, 360, fill=(42, 32, 27))
        draw.line((430, 570, 760, 410), fill=cartoon.INK, width=22)
    elif variant == 2:
        # Side-profile teaching shot with the screen dominant.
        screen = (870, 115, 1810, 690)
        _screen_chart(draw, screen, variant)
        v8._human(draw, 500, 400, 1.95, cartoon.GREEN, "point")
        draw.rounded_rectangle((250, 820, 960, 905), radius=24, fill=(77, 80, 86), outline=cartoon.INK, width=14)
    else:
        # Tight editorial close-up with a planet diagram.
        v8._human(draw, 620, 390, 2.20, cartoon.AMBER, "point")
        cx, cy = 1450, 410
        draw.ellipse((cx - 220, cy - 220, cx + 220, cy + 220), fill=cartoon.BLUE, outline=cartoon.INK, width=15)
        draw.polygon(((cx - 135, cy - 18), (cx - 42, cy - 132), (cx + 88, cy - 62), (cx + 56, cy + 82), (cx - 82, cy + 105)), fill=cartoon.GREEN, outline=cartoon.INK)
        draw.arc((cx - 290, cy - 120, cx + 290, cy + 190), 195, 345, fill=cartoon.AMBER, width=14)


def _doorway_environment(draw: ImageDraw.ImageDraw, width: int, height: int, platform: int) -> None:
    """A terminal/ship doorway with structure, lighting, interior floor, and signage."""
    draw.rounded_rectangle((120, 85, width - 120, 745), radius=48, fill=(198, 205, 212), outline=cartoon.INK, width=18)
    draw.rounded_rectangle((570, 145, 1350, 675), radius=42, fill=(57, 65, 75), outline=cartoon.INK, width=16)
    draw.rounded_rectangle((650, 215, 1270, 675), radius=30, fill=(92, 108, 119), outline=cartoon.INK, width=10)
    # Lit portal frame.
    for lx in (625, 1295):
        draw.rounded_rectangle((lx - 18, 215, lx + 18, 610), radius=10, fill=cartoon.CYAN, outline=cartoon.INK, width=4)
    draw.rounded_rectangle((760, 165, 1160, 220), radius=12, fill=cartoon.AMBER, outline=cartoon.INK, width=5)
    # Interior perspective floor and cargo silhouettes.
    draw.polygon(((700, 610), (1220, 610), (1410, platform), (510, platform)), fill=(143, 151, 159), outline=cartoon.INK)
    for x in (790, 1070):
        draw.rounded_rectangle((x, 470, x + 95, 590), radius=10, fill=(119, 126, 134), outline=cartoon.INK, width=6)


def _draw_transport(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    variant = _ACTIVE_VARIANT % 4
    draw.rectangle((0, 0, width, height), fill=(226, 237, 244))
    platform = round(height * 0.80)
    draw.rectangle((0, platform, width, height), fill=(193, 198, 203))

    if variant == 0:
        _doorway_environment(draw, width, height, platform)
        for index in range(5):
            accent = _COLORS[index] if index in (1, 4) else None
            v8._person(draw, 610 + index * 175, 610 + (index % 2) * 22, 0.78, accent=accent, pose="walk")
    elif variant == 1:
        # Grounded overhead view with terminal walls, bay markings, and shadows.
        draw.rounded_rectangle((90, 80, width - 90, height - 70), radius=44, fill=(210, 217, 223), outline=cartoon.INK, width=16)
        draw.rounded_rectangle((135, 130, 670, 490), radius=28, fill=(118, 130, 141), outline=cartoon.INK, width=12)
        for x in (205, 375, 545):
            draw.rectangle((x, 205, x + 105, 365), fill=cartoon.CYAN, outline=cartoon.INK, width=7)
        draw.polygon(((680, 250), (1370, 250), (1570, 650), (680, 650)), fill=(224, 177, 67), outline=cartoon.INK)
        for y in (335, 455, 575):
            draw.line((740, y, 1440, y), fill=cartoon.WHITE, width=8)
        # Soft shadow under ship, then ship itself.
        draw.ellipse((1110, 380, 1730, 615), fill=(151, 158, 165))
        v7._spacecraft(draw, 1400, 455, 1.42, progress)
        for index in range(5):
            v8._person(draw, 500 + index * 190, 700, 0.55, accent=_COLORS[index] if index in (0, 3) else None, pose="walk")
    elif variant == 2:
        # Low-angle ramp with a visibly attached boarding relationship.
        v7._spacecraft(draw, 1110, 235, 2.10, progress)
        draw.polygon(((720, 420), (1280, 420), (1560, platform), (430, platform)), fill=cartoon.AMBER, outline=cartoon.INK)
        draw.line((720, 420, 1280, 420), fill=cartoon.CYAN, width=10)
        for index in range(5):
            accent = _COLORS[index] if index in (1, 4) else None
            v8._person(draw, 585 + index * 185, 585 + (index % 2) * 24, 0.80, accent=accent, pose="walk")
    else:
        # Interior corridor with destination portal and floor perspective.
        draw.rounded_rectangle((80, 70, width - 80, height - 70), radius=46, fill=(217, 226, 232), outline=cartoon.INK, width=16)
        draw.rounded_rectangle((680, 115, 1240, 680), radius=38, fill=(61, 69, 79), outline=cartoon.INK, width=14)
        for x in (180, 545, 910, 1275, 1640):
            draw.line((x, 70, x, height - 70), fill=(151, 160, 169), width=7)
        draw.line((500, height - 70, 790, 680), fill=cartoon.AMBER, width=10)
        draw.line((1420, height - 70, 1130, 680), fill=cartoon.AMBER, width=10)
        for index in range(5):
            v8._person(draw, 520 + index * 190, 585 + (index % 2) * 20, 0.76, accent=_COLORS[index] if index in (1, 4) else None, pose="walk")


def _foreground_rocks(draw: ImageDraw.ImageDraw, width: int, height: int, variant: int) -> None:
    rocks = (
        ((-70, 885), (220, 760), (420, 1080), (-70, 1080)),
        ((1510, 810), (1900, 730), (1990, 1080), (1420, 1080)),
    )
    draw.polygon(rocks[variant % 2], fill=(131, 66, 48), outline=cartoon.INK)


def _draw_habitat(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    variant = _ACTIVE_VARIANT % 4
    ground = round(height * 0.77)
    draw.rectangle((0, 0, width, height), fill=(239, 218, 197))
    v6._rugged_ridges(draw, width, ground, variant)
    draw.rectangle((0, ground, width, height), fill=(190, 105, 70))

    if variant == 0:
        # Low-angle partial crop with foreground rock depth.
        v8._fixed_habitat(draw, 1320, ground, 1.02)
        _foreground_rocks(draw, width, height, 0)
        v8._human(draw, 500, 520, 1.20, cartoon.AMBER, "point")
        v6._robot(draw, 820, 590, 0.76, "walk")
    elif variant == 1:
        # Side-angle connected settlement.
        v8._fixed_habitat(draw, 700, ground, 0.80)
        v8._fixed_habitat(draw, 1320, ground, 0.58)
        draw.line((955, ground - 88, 1125, ground - 72), fill=(122, 151, 164), width=62)
        draw.line((955, ground - 88, 1125, ground - 72), fill=cartoon.INK, width=8)
        _foreground_rocks(draw, width, height, 1)
        for index in range(3):
            v6._robot(draw, 980 + index * 120, 610 + index * 8, 0.65, "walk")
    elif variant == 2:
        # Tight three-quarter airlock interaction instead of symmetrical staging.
        draw.rounded_rectangle((180, 80, width - 120, height - 70), radius=48, fill=(213, 224, 230), outline=cartoon.INK, width=16)
        draw.rounded_rectangle((760, 115, 1450, 790), radius=44, fill=(70, 78, 88), outline=cartoon.INK, width=16)
        draw.rounded_rectangle((870, 230, 1325, 710), radius=32, fill=(120, 153, 169), outline=cartoon.INK, width=12)
        for lx in (815, 1395):
            draw.ellipse((lx - 20, 250, lx + 20, 290), fill=cartoon.CYAN, outline=cartoon.INK, width=5)
        draw.polygon(((870, 710), (1325, 710), (1510, 960), (690, 960)), fill=(151, 94, 69), outline=cartoon.INK)
        v8._human(draw, 650, 520, 1.32, cartoon.GREEN, "point")
        v6._robot(draw, 1120, 565, 0.92, "stand")
    else:
        # Over-the-shoulder colony view from behind a foreground worker.
        v8._fixed_habitat(draw, 1240, ground, 0.78)
        draw.ellipse((-120, 565, 570, 1255), fill=cartoon.BLUE, outline=cartoon.INK, width=18)
        draw.pieslice((40, 410, 360, 730), 180, 360, fill=(42, 32, 27))
        v6._robot(draw, 860, 600, 0.68, "walk")
        v6._robot(draw, 1040, 620, 0.58, "walk")


def _draw_crowd_scene(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Ground the crowd in a civic/transit environment instead of blank paper."""
    draw.rectangle((0, 0, width, height), fill=(231, 237, 241))
    draw.rectangle((0, round(height * 0.76), width, height), fill=(202, 207, 212))
    draw.line((0, round(height * 0.76), width, round(height * 0.76)), fill=cartoon.INK, width=10)
    for x in (120, 520, 920, 1320, 1720):
        draw.rounded_rectangle((x, 95, x + 250, 315), radius=22, fill=cartoon.CYAN, outline=cartoon.INK, width=8)
    draw.rounded_rectangle((650, 350, 1270, 485), radius=25, fill=(121, 132, 143), outline=cartoon.INK, width=10)
    v8._crowd(draw, width, height, progress, focal=True)


def _bezier_point(p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float], t: float) -> tuple[int, int]:
    one = 1.0 - t
    x = one * one * p0[0] + 2 * one * t * p1[0] + t * t * p2[0]
    y = one * one * p0[1] + 2 * one * t * p1[1] + t * t * p2[1]
    return round(x), round(y)


def _draw_route_map(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Keep the ship centered on the exact same curve used for the route."""
    variant = _ACTIVE_VARIANT % 3
    draw.rectangle((0, 0, width, height), fill=cartoon.PAPER)
    for index in range(30):
        sx = (index * 181) % width
        sy = 24 + (index * 83) % round(height * 0.38)
        r = 2 + index % 3
        draw.ellipse((sx - r, sy - r, sx + r, sy + r), fill=cartoon.MUTED)

    if variant == 0:
        earth = (360, 690)
        mars = (1540, 410)
        control = (960, 130)
        cartoon._planet(draw, earth, 225, cartoon.BLUE, progress)
        cartoon._planet(draw, mars, 190, cartoon.MARS, 1 - progress)
    elif variant == 1:
        earth = (300, 760)
        mars = (1580, 300)
        control = (930, 100)
        cartoon._planet(draw, earth, 180, cartoon.BLUE, progress)
        cartoon._planet(draw, mars, 235, cartoon.MARS, 1 - progress)
    else:
        earth = (270, 760)
        mars = (1480, 560)
        control = (850, 180)
        cartoon._planet(draw, earth, 135, cartoon.BLUE, progress)
        cartoon._planet(draw, mars, 285, cartoon.MARS, 1 - progress)

    points = [_bezier_point(earth, control, mars, step / 30) for step in range(31)]
    for index in range(0, len(points) - 1, 2):
        draw.line((points[index], points[index + 1]), fill=cartoon.INK, width=10)
    arrow = points[-2]
    draw.polygon((points[-1], (arrow[0] - 30, arrow[1] - 18), (arrow[0] - 18, arrow[1] + 28)), fill=cartoon.INK)
    ship_x, ship_y = _bezier_point(earth, control, mars, cartoon._ease(progress))
    v7._spacecraft(draw, ship_x, ship_y, 1.14 if variant < 2 else 1.28, progress)


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
    _ACTIVE_VARIANT = (scene_number * 5 + beat_index * 3) % 12

    image = Image.new("RGB", (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT), cartoon.PAPER)
    draw = ImageDraw.Draw(image)
    if selected.template_id == "route_map":
        _draw_route_map(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "crowd_focus":
        _draw_crowd_scene(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
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
