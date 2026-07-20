from __future__ import annotations

"""Visual Overhaul v65: distinct community, arrival, and settlement conclusions.

The fourth Mars export confirmed that the layered renderer solved seams and door
occlusion. This final pass removes late-film visual repetition: only the first
route scene keeps the route map, later route-scored scenes become Mars arrival,
the crowd beat moves inside a greenhouse commons, and the settlement structures
remain physically grounded for the entire shot.
"""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_visual_overhaul_v63 as v63
from . import cartoon_visual_overhaul_v64 as v64
from .cartoon_scene_graph import LayerStack, draw_cart, draw_person, phase


MARS_SKY = (239, 214, 195)
MARS_GROUND = (174, 92, 61)
MARS_HILL = (143, 72, 51)
DOME_FILL = (183, 221, 231)


def _grounded_dome_box(left: int, top: int, right: int, base_y: int) -> tuple[int, int, int, int]:
    return left, top, right, base_y * 2 - top


def _draw_grounded_dome(draw, bounds, *, fill, outline, width: int) -> None:
    left, top, right, base_y = bounds
    draw.pieslice(
        _grounded_dome_box(left, top, right, base_y),
        180,
        360,
        fill=fill,
        outline=outline,
        width=width,
    )
    draw.rectangle((left + 12, base_y - 16, right - 12, base_y + 18), fill=(65, 82, 94), outline=outline, width=max(5, width - 3))


def _community_frame(progress: float, variant: int) -> Image.Image:
    """Interior greenhouse commons so the people beat cannot repeat the exterior."""
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    stack = LayerStack((width, height))
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    environment.rectangle((0, 0, width, height), fill=(218, 234, 240))
    environment.rectangle((0, 780, width, height), fill=(164, 177, 181))
    environment.arc((135, 85, 1785, 1275), 180, 360, fill=(58, 88, 104), width=22)
    environment.rounded_rectangle((105, 245, 500, 720), radius=44, fill=(143, 199, 162), outline=cartoon.INK, width=9)
    environment.rounded_rectangle((1420, 245, 1815, 720), radius=44, fill=(103, 181, 201), outline=cartoon.INK, width=9)
    for x in (170, 250, 330, 410, 1485, 1565, 1645, 1725):
        environment.line((x, 300, x - 35, 660), fill=(55, 91, 75), width=10)

    environment.rounded_rectangle((600, 595, 1320, 805), radius=60, fill=(105, 78, 57), outline=cartoon.INK, width=11)
    environment.ellipse((835, 525, 1085, 735), fill=(226, 181, 68), outline=cartoon.INK, width=8)
    environment.rounded_rectangle((660, 120, 1260, 220), radius=32, fill=(43, 62, 78), outline=cartoon.INK, width=7)
    environment.text((960, 170), "LIFE INSIDE THE HABITAT", font=cartoon._font(36, True), fill=cartoon.WHITE, anchor="mm")

    reveal = phase(progress, 0.05, 0.78)
    residents = (
        (270, 865, cartoon.BLUE, 0.64),
        (590, 925, cartoon.AMBER, 0.58),
        (960, 850, cartoon.GREEN, 0.72),
        (1320, 925, cartoon.PURPLE, 0.58),
        (1650, 865, (88, 172, 159), 0.64),
    )
    visible = max(2, min(len(residents), round(1 + reveal * len(residents))))
    for index, (x, y, color, scale) in enumerate(residents[:visible]):
        draw_person(
            actors,
            (x, y),
            scale,
            shirt=color,
            pants=(48, 59, 76),
            arm_raise=0.50 if index == 2 else 0.10,
        )

    draw_cart(actors, (1485, 770, 1715, 910), fill=(50, 67, 82), accent=cartoon.CYAN)
    effects.rounded_rectangle((650, 930, 1270, 1020), radius=28, fill=(46, 64, 79), outline=cartoon.GREEN, width=6)
    effects.text((960, 975), "A COMMUNITY, NOT JUST A SHELTER", font=cartoon._font(30, True), fill=cartoon.WHITE, anchor="mm")
    return stack.composite((218, 234, 240))


def _draw_ship(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float, descent: float) -> None:
    x, y = center
    s = scale
    body = (
        (round(x - 145 * s), y),
        (round(x - 80 * s), round(y - 45 * s)),
        (round(x + 95 * s), round(y - 34 * s)),
        (round(x + 155 * s), y),
        (round(x + 95 * s), round(y + 34 * s)),
        (round(x - 80 * s), round(y + 45 * s)),
    )
    draw.polygon(body, fill=(232, 239, 244), outline=cartoon.INK)
    draw.ellipse((round(x - 10 * s), round(y - 26 * s), round(x + 48 * s), round(y + 26 * s)), fill=cartoon.CYAN, outline=cartoon.INK, width=max(4, round(6 * s)))
    flame = round((55 + 65 * descent) * s)
    draw.polygon(((round(x - 140 * s), round(y - 20 * s)), (round(x - (140 + flame) * s), y), (round(x - 140 * s), round(y + 20 * s))), fill=cartoon.AMBER, outline=cartoon.INK)


def _arrival_frame(progress: float, variant: int) -> Image.Image:
    """A Mars approach/landing composition, visually separate from the route map."""
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    stack = LayerStack((width, height))
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    environment.rectangle((0, 0, width, height), fill=(16, 34, 52))
    for index, (x, y) in enumerate(((160, 150), (430, 260), (710, 105), (1010, 220), (1320, 120), (1650, 260), (1810, 90))):
        radius = 3 + index % 3
        environment.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(225, 236, 242))

    # Mars fills the lower frame as the ship descends toward a visible landing site.
    environment.ellipse((-170, 420, 2090, 1600), fill=MARS_GROUND, outline=cartoon.INK, width=13)
    environment.polygon(((0, 760), (280, 520), (560, 785)), fill=MARS_HILL)
    environment.polygon(((1280, 790), (1590, 500), (1920, 800)), fill=(154, 77, 52))
    environment.rounded_rectangle((1235, 690, 1740, 890), radius=42, fill=(72, 89, 101), outline=cartoon.CYAN, width=8)
    environment.ellipse((1350, 735, 1625, 860), fill=(46, 62, 74), outline=cartoon.AMBER, width=7)

    descent = phase(progress, 0.08, 0.88)
    ship_x = round(650 + 610 * descent)
    ship_y = round(310 + 390 * descent)
    _draw_ship(actors, (ship_x, ship_y), 0.92 - 0.18 * descent, descent)

    # Ground crew and habitat establish arrival rather than another abstract journey.
    _draw_grounded_dome(environment, (165, 565, 650, 835), fill=DOME_FILL, outline=cartoon.INK, width=9)
    environment.rounded_rectangle((345, 690, 470, 835), radius=24, fill=(52, 69, 82), outline=cartoon.GREEN, width=6)
    draw_person(actors, (790, 880), 0.66, shirt=cartoon.GREEN, pants=(48, 59, 76), arm_raise=0.60)
    draw_person(actors, (1020, 905), 0.60, shirt=cartoon.AMBER, pants=(48, 59, 76))
    draw_cart(actors, (1110, 815, 1320, 940), fill=(50, 67, 82), accent=cartoon.CYAN)

    effects.rounded_rectangle((610, 95, 1310, 205), radius=34, fill=(31, 48, 65), outline=cartoon.AMBER, width=7)
    effects.text((960, 150), "MARS ARRIVAL • LANDING PREP", font=cartoon._font(36, True), fill=cartoon.WHITE, anchor="mm")
    return stack.composite((16, 34, 52))


def _settlement_frame(progress: float, variant: int) -> Image.Image:
    """Grounded exterior resolution; only lights and connections animate."""
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    stack = LayerStack((width, height))
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    base_y = 760
    environment.rectangle((0, 0, width, height), fill=MARS_SKY)
    environment.rectangle((0, base_y, width, height), fill=MARS_GROUND)
    environment.polygon(((0, base_y), (260, 455), (520, base_y)), fill=MARS_HILL)
    environment.polygon(((1390, base_y), (1660, 430), (1920, base_y)), fill=(154, 77, 52))

    domes = (
        (75, 405, 610, base_y, cartoon.CYAN),
        (535, 245, 1315, base_y, cartoon.GREEN),
        (1235, 430, 1845, base_y, cartoon.AMBER),
    )
    readiness = phase(progress, 0.06, 0.80)
    doors: list[tuple[int, int]] = []
    for index, (left, top, right, dome_base, color) in enumerate(domes):
        _draw_grounded_dome(environment, (left, top, right, dome_base), fill=DOME_FILL, outline=cartoon.INK, width=10)
        center = (left + right) // 2
        doors.append((center, dome_base))
        environment.rounded_rectangle((center - 58, dome_base - 180, center + 58, dome_base), radius=22, fill=(50, 68, 81), outline=color, width=7)
        light = color if readiness > 0.18 + index * 0.20 else (72, 82, 92)
        environment.ellipse((center - 14, dome_base - 220, center + 14, dome_base - 192), fill=light, outline=cartoon.INK, width=3)

    hub = (960, 920)
    for index, (x, y) in enumerate(doors):
        active = readiness > 0.24 + index * 0.15
        effects.line((x, y + 10, hub[0], hub[1]), fill=(228, 181, 79) if active else (111, 91, 69), width=34)
    effects.ellipse((910, 870, 1010, 970), fill=cartoon.GREEN if readiness > 0.72 else cartoon.AMBER, outline=cartoon.INK, width=7)

    environment.rounded_rectangle((115, 830, 425, 970), radius=28, fill=(72, 111, 118), outline=cartoon.CYAN, width=7)
    for x in range(150, 405, 52):
        environment.line((x, 850, x - 24, 950), fill=(20, 35, 50), width=5)
    draw_person(actors, (670, 955), 0.58, shirt=cartoon.GREEN, pants=(48, 59, 76))
    draw_person(actors, (1230, 950), 0.58, shirt=cartoon.AMBER, pants=(48, 59, 76), arm_raise=0.42)
    draw_cart(actors, (1465, 850, 1695, 985), fill=(50, 67, 82), accent=cartoon.CYAN)

    effects.rounded_rectangle((530, 75, 1390, 190), radius=36, fill=(42, 60, 76), outline=cartoon.GREEN, width=7)
    effects.text((960, 132), "THE SYSTEMS CONNECT • THE CITY LIVES", font=cartoon._font(36, True), fill=cartoon.WHITE, anchor="mm")
    return stack.composite(MARS_SKY)


def _route_rank(scene) -> tuple[int, int]:
    project = getattr(scene, "project", None)
    scenes = sorted(
        list(getattr(project, "scenes", None) or []),
        key=lambda item: int(getattr(item, "scene_number", 0) or 0),
    )
    route_scenes = [item for item in scenes if v63._selected_template(item, None) == "route_map"]
    number = int(getattr(scene, "scene_number", 0) or 0)
    numbers = [int(getattr(item, "scene_number", 0) or 0) for item in route_scenes]
    try:
        return numbers.index(number), len(numbers)
    except ValueError:
        return 0, max(1, len(numbers))


def render_planned_frame(
    scene,
    template_id: str | None,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    selected = v63._selected_template(scene, template_id)
    progress = v63._absolute_progress(duration_seconds, time_seconds)
    scene_number = int(getattr(scene, "scene_number", 1) or 1)
    variant = scene_number % 6

    if selected == "crowd_focus":
        return _community_frame(progress, variant)
    if selected == "process_diagram":
        return _settlement_frame(progress, variant)
    if selected == "route_map":
        rank, count = _route_rank(scene)
        if v64._is_final_project_scene(scene):
            return _settlement_frame(progress, variant)
        if count > 1 and rank > 0:
            return _arrival_frame(progress, variant)
        return v63._route_frame(progress, variant)

    return v64.render_planned_frame(
        scene,
        template_id,
        duration_seconds,
        time_seconds,
        style_id,
    )


cartoon.render_planned_frame = render_planned_frame
