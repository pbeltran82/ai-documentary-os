from __future__ import annotations

"""Shorts Story v8: grounded settlement geometry and distinct late-story beats.

The fourth Mars export proved the story structure was correct, but exposed three
small visual defects: the final domes used a vertically translated construction
animation, the community and settlement beats both read as exterior dome shots,
and an entering figure could brush a closing panel. This release fixes those
issues at their source.
"""

import math

from PIL import Image

from . import exact_visuals as exact
from . import native_shorts as shorts
from .cartoon_scene_graph import LayerStack, draw_airlock, draw_cart, draw_person, phase


INK = (8, 14, 24)
MARS_GROUND = (174, 92, 61)
MARS_HILL = (139, 70, 50)
DOME_FILL = (180, 220, 231)


def _apply(canvas: Image.Image, stack: LayerStack) -> None:
    canvas.paste(stack.composite(canvas))


def _grounded_dome_box(left: int, top: int, right: int, base_y: int) -> tuple[int, int, int, int]:
    """Return an ellipse box whose upper semicircle ends exactly at ``base_y``."""
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
    draw.rectangle((left + 8, base_y - 12, right - 8, base_y + 14), fill=(66, 82, 94), outline=outline, width=max(4, width - 3))


def _transport(canvas: Image.Image, progress: float, accent) -> None:
    stack = LayerStack(canvas.size)
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    environment.rounded_rectangle((70, 420, 1010, 1380), radius=58, fill=(28, 44, 61), outline=INK, width=10)
    environment.polygon(((205, 1265), (875, 1265), (990, 1435), (90, 1435)), fill=(226, 181, 68))
    environment.rounded_rectangle((260, 480, 820, 610), radius=42, fill=(67, 83, 99), outline=INK, width=7)
    for x in (385, 540, 695):
        environment.ellipse((x - 42, 510, x + 42, 582), fill=shorts.CYAN, outline=INK, width=5)

    # The door reaches its safe open state before the traveler begins moving.
    opening = phase(progress, 0.04, 0.32)
    draw_airlock(
        stack,
        (215, 605, 865, 1245),
        opening=opening,
        frame_fill=(51, 65, 79),
        panel_fill=(82, 96, 108),
        interior_fill=(7, 18, 29),
        accent=shorts.CYAN,
    )

    draw_person(actors, (155, 1285), 0.46, shirt=shorts.BLUE, pants=(48, 60, 79), arm_raise=0.62)
    travel = phase(progress, 0.36, 0.86)
    traveler_x = round(350 + 190 * travel)
    traveler_y = round(1360 - 270 * travel)
    traveler_scale = 0.48 - 0.08 * phase(travel, 0.62, 1.0)
    draw_person(
        actors,
        (traveler_x, traveler_y),
        traveler_scale,
        shirt=shorts.AMBER,
        pants=(47, 59, 78),
        stride=math.sin(travel * math.pi * 5) * (1.0 - phase(travel, 0.68, 0.92)),
    )
    draw_cart(actors, (820, 1215, 995, 1325), fill=(49, 68, 84), accent=shorts.GREEN)
    effects.ellipse((528, 570, 552, 594), fill=shorts.GREEN if opening > 0.82 else shorts.AMBER)
    shorts._chip(effects, (540, 1490), "BOARD ONE SAFE CORRIDOR", shorts.CYAN)
    _apply(canvas, stack)


def _habitat(canvas: Image.Image, progress: float, accent) -> None:
    stack = LayerStack(canvas.size)
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    ground_y = 1110
    environment.rectangle((0, ground_y, 1080, 1510), fill=MARS_GROUND)
    environment.polygon(((0, ground_y), (185, 850), (360, ground_y)), fill=MARS_HILL)
    environment.polygon(((745, ground_y), (930, 825), (1080, ground_y)), fill=(148, 74, 51))
    _draw_grounded_dome(environment, (75, 475, 1005, ground_y), fill=(185, 222, 232), outline=INK, width=11)
    environment.rounded_rectangle((135, 720, 325, 995), radius=34, fill=(138, 198, 164), outline=INK, width=7)
    environment.rounded_rectangle((775, 720, 950, 995), radius=34, fill=(93, 174, 201), outline=INK, width=7)

    opening = phase(progress, 0.05, 0.30)
    # Closing begins only after the entrant is fully behind the foreground panels.
    if progress > 0.90:
        opening = 1.0 - 0.45 * phase(progress, 0.90, 1.0)
    draw_airlock(
        stack,
        (325, 610, 755, 1205),
        opening=opening,
        frame_fill=(49, 66, 80),
        panel_fill=(78, 93, 107),
        interior_fill=(8, 20, 30),
        accent=shorts.CYAN,
    )

    draw_person(actors, (190, 1310), 0.43, shirt=shorts.AMBER, pants=(48, 60, 78), arm_raise=0.50)
    entry = phase(progress, 0.38, 0.84)
    entrant_x = round(330 + 210 * entry)
    entrant_y = round(1370 - 285 * entry)
    entrant_scale = 0.46 - 0.08 * phase(entry, 0.62, 1.0)
    draw_person(
        actors,
        (entrant_x, entrant_y),
        entrant_scale,
        shirt=shorts.GREEN,
        pants=(47, 59, 77),
        stride=math.sin(entry * math.pi * 5) * (1.0 - phase(entry, 0.68, 0.92)),
    )
    draw_cart(actors, (825, 1215, 995, 1325), fill=(48, 67, 82), accent=shorts.GREEN)
    for index in range(3):
        ready = phase(progress, 0.52 + index * 0.08, 0.65 + index * 0.08)
        color = shorts.GREEN if ready > 0.65 else (61, 72, 86)
        effects.ellipse((474 + index * 52, 560, 500 + index * 52, 586), fill=color, outline=INK, width=3)
    shorts._chip(effects, (540, 1490), "AIR • POWER • SHELTER", shorts.GREEN)
    _apply(canvas, stack)


def _community(canvas: Image.Image, progress: float, accent) -> None:
    """A distinct interior community beat, not another exterior dome shot."""
    stack = LayerStack(canvas.size)
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    environment.rounded_rectangle((65, 430, 1015, 1390), radius=60, fill=(219, 235, 241), outline=INK, width=11)
    environment.rectangle((80, 1110, 1000, 1390), fill=(155, 169, 174))
    environment.arc((105, 465, 975, 1160), 180, 360, fill=(62, 92, 107), width=18)
    environment.rounded_rectangle((105, 570, 340, 1015), radius=34, fill=(146, 201, 164), outline=INK, width=7)
    environment.rounded_rectangle((740, 570, 975, 1015), radius=34, fill=(108, 184, 202), outline=INK, width=7)
    for x in (145, 205, 265, 780, 840, 900):
        environment.line((x, 625, x - 25, 960), fill=(54, 91, 75), width=8)

    environment.rounded_rectangle((315, 910, 765, 1080), radius=46, fill=(105, 78, 57), outline=INK, width=9)
    environment.ellipse((465, 860, 615, 985), fill=(226, 181, 68), outline=INK, width=6)

    reveal = phase(progress, 0.08, 0.76)
    residents = (
        (205, 1190, shorts.BLUE, 0.40),
        (390, 1245, shorts.AMBER, 0.38),
        (565, 1175, shorts.GREEN, 0.44),
        (750, 1240, shorts.PURPLE, 0.38),
        (900, 1185, shorts.CYAN, 0.40),
    )
    visible = max(2, min(len(residents), round(1 + reveal * len(residents))))
    for index, (x, y, color, scale) in enumerate(residents[:visible]):
        draw_person(actors, (x, y), scale, shirt=color, pants=(47, 59, 77), arm_raise=0.45 if index == 2 else 0.10)

    shorts._chip(effects, (540, 1488), "A COMMUNITY, NOT JUST A SHELTER", shorts.PURPLE)
    _apply(canvas, stack)


def _settlement(canvas: Image.Image, progress: float, accent) -> None:
    """A fixed, grounded exterior settlement; readiness animates, buildings do not."""
    stack = LayerStack(canvas.size)
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    base_y = 1085
    environment.rectangle((0, base_y, 1080, 1510), fill=MARS_GROUND)
    environment.polygon(((0, base_y), (170, 820), (355, base_y)), fill=MARS_HILL)
    environment.polygon(((720, base_y), (920, 790), (1080, base_y)), fill=(146, 72, 50))

    domes = (
        (35, 625, 390, base_y, shorts.CYAN),
        (325, 500, 755, base_y, shorts.GREEN),
        (690, 655, 1045, base_y, shorts.AMBER),
    )
    readiness = phase(progress, 0.08, 0.78)
    door_centers: list[tuple[int, int]] = []
    for index, (left, top, right, dome_base, color) in enumerate(domes):
        _draw_grounded_dome(environment, (left, top, right, dome_base), fill=DOME_FILL, outline=INK, width=9)
        center = (left + right) // 2
        door_centers.append((center, dome_base))
        door_fill = (46, 64, 78)
        environment.rounded_rectangle((center - 50, dome_base - 180, center + 50, dome_base), radius=18, fill=door_fill, outline=color, width=6)
        light = color if readiness > index * 0.22 else (60, 72, 84)
        environment.ellipse((center - 12, dome_base - 215, center + 12, dome_base - 191), fill=light, outline=INK, width=3)

    # Connections illuminate in sequence while every structure remains planted.
    hub = (540, 1210)
    for index, (center, dome_base) in enumerate(door_centers):
        active = readiness > 0.24 + index * 0.16
        effects.line((center, dome_base + 8, hub[0], hub[1]), fill=(228, 181, 79) if active else (111, 91, 69), width=30)
    effects.ellipse((505, 1175, 575, 1245), fill=shorts.GREEN if readiness > 0.72 else shorts.AMBER, outline=INK, width=6)

    environment.rounded_rectangle((70, 1240, 315, 1360), radius=24, fill=(72, 111, 118), outline=shorts.CYAN, width=6)
    for x in range(100, 300, 46):
        environment.line((x, 1257, x - 18, 1342), fill=(20, 35, 50), width=4)
    draw_person(actors, (400, 1360), 0.38, shirt=shorts.GREEN, pants=(47, 59, 77))
    draw_person(actors, (660, 1350), 0.38, shirt=shorts.AMBER, pants=(47, 59, 77), arm_raise=0.40)
    draw_cart(actors, (820, 1265, 995, 1375), fill=(48, 67, 82), accent=shorts.CYAN)

    for index, (label, color) in enumerate((
        ("TRANSPORT", shorts.CYAN),
        ("HABITAT", shorts.GREEN),
        ("GOVERNANCE", shorts.AMBER),
    )):
        x = 200 + index * 340
        resolved = color if readiness > 0.26 + index * 0.18 else (55, 67, 82)
        effects.rounded_rectangle((x - 135, 1430, x + 135, 1515), radius=22, fill=(13, 29, 47), outline=resolved, width=5)
        shorts._text(effects, (x, 1472), label, 23, shorts.WHITE, bold=True, anchor="mm")
    _apply(canvas, stack)


shorts.RENDERERS[(exact.TECH_FAMILY_ID, "transport_scene")] = _transport
shorts.RENDERERS[(exact.TECH_FAMILY_ID, "habitat_build")] = _habitat
shorts.RENDERERS[(exact.TECH_FAMILY_ID, "crowd_focus")] = _community
shorts.RENDERERS[(exact.TECH_FAMILY_ID, "process_diagram")] = _settlement
shorts.COMPOSITIONS[(exact.TECH_FAMILY_ID, "crowd_focus")] = shorts.ShortsComposition(
    "PEOPLE TURN A HABITAT INTO A COMMUNITY"
)
shorts.COMPOSITIONS[(exact.TECH_FAMILY_ID, "process_diagram")] = shorts.ShortsComposition(
    "A CITY ONLY WORKS WHEN THE SYSTEMS CONNECT"
)
