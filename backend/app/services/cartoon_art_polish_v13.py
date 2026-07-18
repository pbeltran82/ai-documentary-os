from __future__ import annotations

"""Art Polish v13: final repeat, depth, crowd, and route endpoint cleanup."""

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v6 as v6
from . import cartoon_art_polish_v7 as v7
from . import cartoon_art_polish_v10 as v10
from . import cartoon_art_polish_v11 as v11
from . import cartoon_art_polish_v12 as v12


_ACTIVE_VARIANT = 0
_COLORS = (cartoon.BLUE, cartoon.AMBER, cartoon.PURPLE, cartoon.GREEN, cartoon.CYAN, cartoon.RED)


def _person(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0, *, accent=None, pose: str = "stand") -> None:
    if accent is None:
        v6._robot(draw, x, y, scale, pose)
    else:
        v12._human(draw, x, y, scale, accent, pose)


def _draw_transport(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Use a stable scene-level setup and reduce doorway dominance."""
    variant = _ACTIVE_VARIANT % 4
    platform = round(height * 0.80)

    if variant != 0:
        old = v10._ACTIVE_VARIANT
        try:
            v10._ACTIVE_VARIANT = variant
            v10._draw_transport(draw, width, height, progress)
        finally:
            v10._ACTIVE_VARIANT = old
        return

    draw.rectangle((0, 0, width, height), fill=(226, 237, 244))
    draw.rectangle((0, platform, width, height), fill=(193, 198, 203))

    # Smaller portal with visible terminal architecture and ship exterior context.
    draw.rounded_rectangle((120, 95, width - 120, 735), radius=44, fill=(198, 205, 212), outline=cartoon.INK, width=18)
    for x in (215, 1675):
        draw.rounded_rectangle((x - 70, 135, x + 70, 715), radius=24, fill=(128, 141, 152), outline=cartoon.INK, width=10)
    for y in (150, 245):
        draw.line((285, y, 1635, y), fill=(151, 163, 173), width=20)

    portal = (650, 225, 1270, 680)
    draw.rounded_rectangle(portal, radius=34, fill=(57, 65, 75), outline=cartoon.INK, width=15)
    draw.rounded_rectangle((715, 285, 1205, 680), radius=26, fill=(93, 109, 120), outline=cartoon.INK, width=9)
    for lx in (685, 1235):
        draw.rounded_rectangle((lx - 15, 285, lx + 15, 620), radius=9, fill=cartoon.CYAN, outline=cartoon.INK, width=4)
    draw.rounded_rectangle((790, 245, 1130, 295), radius=12, fill=cartoon.AMBER, outline=cartoon.INK, width=5)

    # Partial ship exterior at frame right makes the portal relationship explicit.
    v7._spacecraft(draw, 1585, 360, 1.18, progress)
    draw.polygon(((745, 620), (1175, 620), (1390, platform), (530, platform)), fill=(224, 177, 67), outline=cartoon.INK)

    figures = (
        (500, 590, 0.92, cartoon.AMBER),
        (770, 620, 0.78, None),
        (1030, 590, 0.88, cartoon.PURPLE),
        (1300, 625, 0.74, None),
    )
    for x, y, scale, accent in figures:
        _person(draw, x, y, scale, accent=accent, pose="walk")


def _draw_habitat(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Vary foreground anchors and stagger workers in depth."""
    variant = _ACTIVE_VARIANT % 4
    ground = round(height * 0.77)

    if variant in (0, 1, 2):
        old = v10._ACTIVE_VARIANT
        try:
            v10._ACTIVE_VARIANT = variant
            v10._draw_habitat(draw, width, height, progress)
        finally:
            v10._ACTIVE_VARIANT = old

        if variant == 0:
            # Equipment crate foreground instead of another shoulder silhouette.
            draw.rounded_rectangle((80, 765, 390, 1040), radius=24, fill=(118, 128, 137), outline=cartoon.INK, width=12)
            draw.line((120, 850, 350, 850), fill=cartoon.AMBER, width=10)
        elif variant == 1:
            # Stagger settlement workers by scale and vertical placement.
            v6._robot(draw, 930, 610, 0.82, "walk")
            v6._robot(draw, 1110, 565, 0.66, "walk")
            v6._robot(draw, 1265, 630, 0.54, "walk")
        else:
            # Larger operator at the door, smaller observer deeper in frame.
            v6._robot(draw, 1110, 515, 1.22, "stand")
            _person(draw, 1510, 610, 0.66, accent=cartoon.CYAN, pose="stand")
        return

    # Alternate over-the-shoulder setup using a robot silhouette, not the blue human shoulder.
    draw.rectangle((0, 0, width, height), fill=(239, 218, 197))
    v6._rugged_ridges(draw, width, ground, variant)
    draw.rectangle((0, ground, width, height), fill=(190, 105, 70))
    v10.v8._fixed_habitat(draw, 1260, ground, 0.80)
    draw.rounded_rectangle((-150, 560, 510, 1190), radius=70, fill=(79, 85, 94), outline=cartoon.INK, width=18)
    draw.rectangle((55, 455, 325, 690), fill=(154, 160, 168), outline=cartoon.INK, width=16)
    draw.rounded_rectangle((115, 515, 265, 570), radius=12, fill=cartoon.CYAN, outline=cartoon.INK, width=5)
    v6._robot(draw, 835, 590, 0.78, "walk")
    _person(draw, 1040, 555, 0.82, accent=cartoon.GREEN, pose="point")


def _draw_crowd_scene(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Ground the crowd with asymmetric clusters and a readable foreground focal figure."""
    draw.rectangle((0, 0, width, height), fill=(231, 237, 241))
    floor = round(height * 0.76)
    draw.rectangle((0, floor, width, height), fill=(202, 207, 212))
    draw.line((0, floor, width, floor), fill=cartoon.INK, width=10)
    for x, w in ((95, 260), (480, 330), (970, 235), (1375, 360)):
        draw.rounded_rectangle((x, 90, x + w, 300), radius=22, fill=cartoon.CYAN, outline=cartoon.INK, width=8)
    draw.rounded_rectangle((690, 335, 1250, 465), radius=24, fill=(121, 132, 143), outline=cartoon.INK, width=10)

    # Irregular clusters rather than a grid.
    figures = (
        (165, 555, 0.76, None), (335, 620, 0.92, cartoon.BLUE),
        (565, 560, 0.68, None), (720, 650, 0.84, None),
        (925, 555, 0.74, cartoon.PURPLE), (1115, 625, 0.96, None),
        (1360, 570, 0.70, cartoon.AMBER), (1515, 645, 0.86, None),
        (1740, 585, 0.72, None),
    )
    for index, (x, y, scale, accent) in enumerate(figures):
        _person(draw, x, y, scale, accent=accent, pose="walk" if index % 3 == 0 else "stand")
    _person(draw, 980, 500 - round(30 * cartoon._ease(progress)), 1.18, accent=cartoon.GREEN, pose="point")


def _bezier_point(p0, p1, p2, t: float) -> tuple[int, int]:
    one = 1.0 - t
    return (
        round(one * one * p0[0] + 2 * one * t * p1[0] + t * t * p2[0]),
        round(one * one * p0[1] + 2 * one * t * p1[1] + t * t * p2[1]),
    )


def _draw_route_map(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    """Stop the ship before either planet silhouette while keeping it on the route."""
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

    points = [_bezier_point(earth, control, mars, step / 40) for step in range(41)]
    for index in range(0, len(points) - 1, 2):
        draw.line((points[index], points[index + 1]), fill=cartoon.INK, width=10)
    arrow = points[-4]
    tip = points[-3]
    draw.polygon((tip, (arrow[0] - 26, arrow[1] - 16), (arrow[0] - 16, arrow[1] + 25)), fill=cartoon.INK)

    eased = cartoon._ease(progress)
    # Keep the capsule clear of both planet disks; the route itself may continue to the centers.
    travel_t = 0.11 + eased * 0.75
    ship_x, ship_y = _bezier_point(earth, control, mars, travel_t)
    endpoint_distance = min(travel_t - 0.11, 0.86 - travel_t)
    proximity = max(0.0, min(1.0, endpoint_distance / 0.20))
    ship_scale = 0.70 + 0.36 * proximity
    v7._spacecraft(draw, ship_x, ship_y, ship_scale, progress)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    """Use stable per-scene variants so adjacent shots cannot repeat within a scene."""
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

    offsets = {"transport_scene": 0, "habitat_build": 1, "presenter_desk": 2, "crowd_focus": 3, "route_map": 4}
    _ACTIVE_VARIANT = (scene_number * 5 + offsets.get(selected.template_id, 0)) % 12

    image = Image.new("RGB", (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT), cartoon.PAPER)
    draw = ImageDraw.Draw(image)
    if selected.template_id == "route_map":
        _draw_route_map(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
    elif selected.template_id == "crowd_focus":
        _draw_crowd_scene(draw, cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT, progress)
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


cartoon._person = _person
cartoon._draw_transport = _draw_transport
cartoon._draw_habitat = _draw_habitat
cartoon._draw_route_map = _draw_route_map
cartoon.render_planned_frame = render_planned_frame
