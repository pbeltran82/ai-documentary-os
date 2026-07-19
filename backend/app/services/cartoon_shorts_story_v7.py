from __future__ import annotations

"""Shorts Story v7: layered transport, habitat, and settlement conclusion."""

import math

from PIL import Image, ImageDraw

from . import exact_visuals as exact
from . import native_shorts as shorts
from .cartoon_scene_graph import LayerStack, draw_airlock, draw_cart, draw_person, phase


def _apply(canvas: Image.Image, stack: LayerStack) -> None:
    rendered = stack.composite(canvas)
    canvas.paste(rendered)


def _transport(canvas: Image.Image, progress: float, accent) -> None:
    stack = LayerStack(canvas.size)
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    environment.rounded_rectangle(
        (80, 430, 1000, 1370),
        radius=56,
        fill=(28, 44, 61),
        outline=(8, 14, 24),
        width=10,
    )
    environment.polygon(((225, 1260), (855, 1260), (960, 1430), (120, 1430)), fill=(226, 181, 68))
    environment.rounded_rectangle((285, 485, 795, 615), radius=42, fill=(67, 83, 99), outline=(8, 14, 24), width=7)
    for x in (390, 540, 690):
        environment.ellipse((x - 42, 510, x + 42, 582), fill=shorts.CYAN, outline=(8, 14, 24), width=5)

    opening = phase(progress, 0.08, 0.50)
    draw_airlock(
        stack,
        (250, 625, 830, 1240),
        opening=opening,
        frame_fill=(51, 65, 79),
        panel_fill=(82, 96, 108),
        interior_fill=(7, 18, 29),
        accent=shorts.CYAN,
    )

    draw_person(
        actors,
        (175, 1275),
        0.48,
        shirt=shorts.BLUE,
        pants=(48, 60, 79),
        arm_raise=0.7,
    )
    travel = phase(progress, 0.20, 0.84)
    traveler_x = round(320 + 225 * travel)
    traveler_y = round(1360 - 300 * travel)
    draw_person(
        actors,
        (traveler_x, traveler_y),
        0.52,
        shirt=shorts.AMBER,
        pants=(47, 59, 78),
        stride=math.sin(travel * math.pi * 6) * (1.0 - phase(progress, 0.72, 0.88)),
    )
    draw_cart(actors, (820, 1210, 990, 1320), fill=(49, 68, 84), accent=shorts.GREEN)
    effects.ellipse((525, 585, 548, 608), fill=shorts.GREEN if opening > 0.8 else shorts.AMBER)
    shorts._chip(effects, (540, 1490), "BOARD ONE SAFE CORRIDOR", shorts.CYAN)
    _apply(canvas, stack)


def _habitat(canvas: Image.Image, progress: float, accent) -> None:
    stack = LayerStack(canvas.size)
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    environment.rectangle((0, 1120, 1080, 1510), fill=(171, 91, 61))
    environment.polygon(((0, 1115), (180, 860), (350, 1120)), fill=(132, 68, 51))
    environment.polygon(((760, 1120), (930, 840), (1080, 1120)), fill=(145, 72, 51))
    environment.pieslice(
        (85, 470, 995, 1260),
        180,
        360,
        fill=(185, 222, 232),
        outline=(8, 14, 24),
        width=11,
    )
    environment.rounded_rectangle((145, 690, 345, 990), radius=36, fill=(138, 198, 164), outline=(8, 14, 24), width=7)
    environment.rounded_rectangle((765, 690, 940, 990), radius=36, fill=(93, 174, 201), outline=(8, 14, 24), width=7)

    opening = phase(progress, 0.10, 0.48)
    if progress > 0.80:
        opening = 1.0 - 0.68 * phase(progress, 0.80, 0.98)
    draw_airlock(
        stack,
        (365, 620, 715, 1205),
        opening=opening,
        frame_fill=(49, 66, 80),
        panel_fill=(78, 93, 107),
        interior_fill=(8, 20, 30),
        accent=shorts.CYAN,
    )

    draw_person(
        actors,
        (215, 1305),
        0.45,
        shirt=shorts.AMBER,
        pants=(48, 60, 78),
        arm_raise=0.55,
    )
    entry = phase(progress, 0.30, 0.82)
    entrant_x = round(330 + 210 * entry)
    entrant_y = round(1375 - 315 * entry)
    draw_person(
        actors,
        (entrant_x, entrant_y),
        0.48,
        shirt=shorts.GREEN,
        pants=(47, 59, 77),
        stride=math.sin(entry * math.pi * 5) * (1.0 - phase(progress, 0.72, 0.9)),
    )
    draw_cart(actors, (820, 1210, 990, 1320), fill=(48, 67, 82), accent=shorts.GREEN)
    for index in range(3):
        ready = phase(progress, 0.55 + index * 0.08, 0.68 + index * 0.08)
        color = shorts.GREEN if ready > 0.65 else (61, 72, 86)
        effects.ellipse((475 + index * 52, 570, 499 + index * 52, 594), fill=color, outline=(8, 14, 24), width=3)
    shorts._chip(effects, (540, 1490), "AIR • POWER • SHELTER", shorts.GREEN)
    _apply(canvas, stack)


def _settlement(canvas: Image.Image, progress: float, accent) -> None:
    """Final Mars beat: show an inhabited system rather than another route."""
    stack = LayerStack(canvas.size)
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    environment.rectangle((0, 1170, 1080, 1510), fill=(171, 91, 61))
    environment.polygon(((0, 1170), (190, 875), (360, 1170)), fill=(132, 68, 51))
    environment.polygon(((720, 1170), (910, 830), (1080, 1170)), fill=(143, 72, 51))

    growth = phase(progress, 0.04, 0.74)
    domes = (
        (65, 650, 435, 1185, shorts.CYAN),
        (350, 520, 760, 1185, shorts.GREEN),
        (665, 690, 1015, 1185, shorts.AMBER),
    )
    for index, (left, top, right, bottom, color) in enumerate(domes):
        local = phase(growth, index * 0.16, 0.48 + index * 0.16)
        rise = round((1.0 - local) * 145)
        environment.pieslice(
            (left, top + rise, right, bottom + rise),
            180,
            360,
            fill=(178, 218, 229),
            outline=(8, 14, 24),
            width=9,
        )
        environment.rounded_rectangle(
            (round((left + right) / 2 - 48), bottom - 190 + rise, round((left + right) / 2 + 48), bottom + rise),
            radius=18,
            fill=(46, 64, 78),
            outline=color,
            width=6,
        )

    # A connected settlement: paths, greenhouse, solar power, and people.
    environment.line((220, 1195, 540, 1075, 850, 1195), fill=(228, 181, 79), width=34, joint="curve")
    environment.rounded_rectangle((90, 1260, 330, 1370), radius=24, fill=(72, 111, 118), outline=shorts.CYAN, width=6)
    for x in range(115, 315, 45):
        environment.line((x, 1275, x - 18, 1355), fill=(20, 35, 50), width=4)
    draw_person(actors, (415, 1335), 0.40, shirt=shorts.GREEN, pants=(47, 59, 77))
    draw_person(actors, (665, 1325), 0.40, shirt=shorts.AMBER, pants=(47, 59, 77), arm_raise=0.45)
    draw_cart(actors, (820, 1270, 985, 1375), fill=(48, 67, 82), accent=shorts.CYAN)

    status = phase(progress, 0.58, 0.88)
    for index, (label, color) in enumerate((("TRANSPORT", shorts.CYAN), ("HABITAT", shorts.GREEN), ("GOVERNANCE", shorts.AMBER))):
        x = 200 + index * 340
        resolved = color if status > index * 0.25 else (55, 67, 82)
        effects.rounded_rectangle((x - 135, 1430, x + 135, 1515), radius=22, fill=(13, 29, 47), outline=resolved, width=5)
        shorts._text(effects, (x, 1472), label, 23, shorts.WHITE, bold=True, anchor="mm")
    _apply(canvas, stack)


shorts.RENDERERS[(exact.TECH_FAMILY_ID, "transport_scene")] = _transport
shorts.RENDERERS[(exact.TECH_FAMILY_ID, "habitat_build")] = _habitat
shorts.RENDERERS[(exact.TECH_FAMILY_ID, "process_diagram")] = _settlement
shorts.COMPOSITIONS[(exact.TECH_FAMILY_ID, "process_diagram")] = shorts.ShortsComposition(
    "A CITY ONLY WORKS WHEN THE SYSTEMS CONNECT"
)
