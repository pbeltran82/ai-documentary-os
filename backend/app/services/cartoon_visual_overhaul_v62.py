from __future__ import annotations

"""Visual Overhaul v62: clean layered transport and habitat environments.

These two source renderers replace the legacy single-canvas geometry that created
full-height seams and allowed door panels to collide visually with figures.
"""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v61 as v61
from .cartoon_scene_graph import (
    LayerStack,
    draw_airlock,
    draw_cart,
    draw_person,
    phase,
)


TRANSPORT_SKY = (220, 235, 244)
TRANSPORT_WALL = (229, 225, 211)
TRANSPORT_FLOOR = (171, 184, 190)
MARS_SKY = (239, 214, 195)
MARS_GROUND = (174, 92, 61)
MARS_HILL = (143, 72, 51)


def _absolute_progress(duration_seconds: float, time_seconds: float) -> float:
    duration = max(0.001, float(duration_seconds))
    return max(0.0, min(1.0, float(time_seconds) / duration))


def _transport_frame(progress: float, variant: int) -> Image.Image:
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    stack = LayerStack((width, height))
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    # Broad shapes only: no repeated wall divisions or full-height seam lines.
    environment.rectangle((0, 0, width, height), fill=TRANSPORT_SKY)
    environment.rounded_rectangle(
        (110, 100, width - 110, 760),
        radius=62,
        fill=TRANSPORT_WALL,
        outline=cartoon.INK,
        width=10,
    )
    environment.rectangle((0, 760, width, height), fill=TRANSPORT_FLOOR)
    environment.rounded_rectangle(
        (270, 150, width - 270, 270),
        radius=34,
        fill=(58, 73, 88),
        outline=cartoon.INK,
        width=8,
    )
    for index, x in enumerate((465, 730, 1190, 1455)):
        tint = (89, 183, 211) if index % 2 == 0 else (116, 203, 218)
        environment.ellipse((x - 50, 173, x + 50, 253), fill=tint, outline=cartoon.INK, width=6)

    door_open = phase(progress, 0.08, 0.48)
    geometry = draw_airlock(
        stack,
        (690, 250, 1230, 770),
        opening=door_open,
        frame_fill=(47, 61, 76),
        panel_fill=(79, 92, 105),
        interior_fill=(12, 24, 35),
        accent=cartoon.CYAN,
    )
    opening_left, _opening_top, opening_right, opening_bottom = geometry.opening
    environment.polygon(
        (
            (opening_left + 12, opening_bottom - 8),
            (opening_right - 12, opening_bottom - 8),
            (1325, height),
            (595, height),
        ),
        fill=(226, 181, 68),
        outline=cartoon.INK,
    )
    environment.polygon(
        (
            (opening_left + 42, opening_bottom + 10),
            (opening_right - 42, opening_bottom + 10),
            (1195, height),
            (725, height),
        ),
        fill=(244, 214, 118),
    )

    # One operator, one traveler, one cart, and one restrained background worker.
    draw_person(
        actors,
        (430, 765),
        0.82,
        shirt=cartoon.BLUE,
        pants=(52, 63, 79),
        arm_raise=0.7,
    )
    travel = phase(progress, 0.18, 0.82)
    traveler_x = round(650 + 305 * travel)
    traveler_y = round(850 - 188 * travel)
    stride = math.sin(travel * math.pi * 6) * (1.0 - phase(progress, 0.72, 0.88))
    draw_person(
        actors,
        (traveler_x, traveler_y),
        0.76,
        shirt=cartoon.AMBER,
        pants=(53, 62, 79),
        stride=stride,
    )
    draw_person(
        actors,
        (1450, 790),
        0.62,
        shirt=(104, 171, 151),
        pants=(51, 63, 80),
    )
    cart_x = round(1580 - 115 * phase(progress, 0.25, 0.74))
    draw_cart(actors, (cart_x, 820, cart_x + 180, 930), accent=cartoon.CYAN)

    status = cartoon.GREEN if door_open > 0.82 else cartoon.AMBER
    effects.ellipse((950, 205, 970, 225), fill=status)
    effects.ellipse((982, 205, 1002, 225), fill=status)
    return stack.composite(TRANSPORT_SKY)


def _habitat_frame(progress: float, variant: int) -> Image.Image:
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    stack = LayerStack((width, height))
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    environment.rectangle((0, 0, width, height), fill=MARS_SKY)
    environment.polygon(((0, 610), (255, 385), (500, 620)), fill=MARS_HILL)
    environment.polygon(((1310, 610), (1600, 350), (1920, 640)), fill=(157, 77, 52))
    environment.rectangle((0, 610, width, height), fill=MARS_GROUND)

    # Seam-free dome shell with one clean horizon line and no interior ribs.
    environment.pieslice(
        (270, 170, 1650, 930),
        180,
        360,
        fill=(184, 222, 232),
        outline=cartoon.INK,
        width=12,
    )
    environment.rectangle((320, 535, 1600, 655), fill=(64, 92, 104), outline=cartoon.INK, width=8)
    environment.rounded_rectangle((420, 310, 690, 560), radius=38, fill=(150, 204, 174), outline=cartoon.INK, width=8)
    environment.rounded_rectangle((1260, 320, 1510, 560), radius=38, fill=(97, 179, 203), outline=cartoon.INK, width=8)

    # The airlock is attached to the dome and owns the foreground panels.
    opening = phase(progress, 0.12, 0.48)
    if progress > 0.78:
        opening = 1.0 - 0.72 * phase(progress, 0.78, 0.98)
    geometry = draw_airlock(
        stack,
        (770, 350, 1190, 815),
        opening=opening,
        frame_fill=(54, 70, 84),
        panel_fill=(76, 91, 104),
        interior_fill=(12, 23, 31),
        accent=cartoon.CYAN,
    )
    inner_left, _inner_top, inner_right, inner_bottom = geometry.opening
    environment.polygon(
        ((inner_left + 12, inner_bottom), (inner_right - 12, inner_bottom), (1130, 1030), (830, 1030)),
        fill=(110, 90, 78),
        outline=cartoon.INK,
    )

    draw_person(
        actors,
        (520, 805),
        0.78,
        shirt=cartoon.AMBER,
        pants=(53, 62, 79),
        arm_raise=0.55,
    )
    entry = phase(progress, 0.32, 0.82)
    entrant_x = round(680 + 278 * entry)
    entrant_y = round(895 - 190 * entry)
    draw_person(
        actors,
        (entrant_x, entrant_y),
        0.70,
        shirt=cartoon.GREEN,
        pants=(49, 61, 77),
        stride=math.sin(entry * math.pi * 5) * (1.0 - phase(progress, 0.72, 0.9)),
    )
    draw_cart(actors, (1335, 745, 1515, 860), fill=(51, 68, 82), accent=cartoon.GREEN)

    # Small status lights communicate progress without stray wall strokes.
    ready = phase(progress, 0.58, 0.78)
    for index in range(3):
        color = cartoon.GREEN if ready > index / 3 else (75, 84, 91)
        effects.ellipse((890 + index * 55, 300, 914 + index * 55, 324), fill=color, outline=cartoon.INK, width=3)
    return stack.composite(MARS_SKY)


def render_planned_frame(
    scene,
    template_id: str | None,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    plan = dict(getattr(scene, "animation_plan", None) or {})
    forced = str(plan.get("shorts_template_id") or "")
    selected = cartoon.TEMPLATE_BY_ID.get(forced or template_id or "")
    if selected is None:
        selected, _confidence, _reason = cartoon.suggest_template(scene)

    progress = _absolute_progress(duration_seconds, time_seconds)
    scene_number = int(getattr(scene, "scene_number", 1) or 1)
    variant = scene_number % 6
    if selected.template_id == "transport_scene":
        return _transport_frame(progress, variant)
    if selected.template_id == "habitat_build":
        return _habitat_frame(progress, variant)
    return v61.render_planned_frame(
        scene,
        template_id,
        duration_seconds,
        time_seconds,
        style_id,
    )


cartoon.render_planned_frame = render_planned_frame
