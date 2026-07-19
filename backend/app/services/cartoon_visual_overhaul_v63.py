from __future__ import annotations

"""Visual Overhaul v63: one layered art direction for every regular template.

The first overhaul replaced transport and habitat at their source. This release
finishes the job so presenter, council, crowd, process, and route scenes cannot
fall back to the older crowded diagram renderers.
"""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v52 as v52
from . import cartoon_visual_overhaul_v62 as v62
from .cartoon_scene_graph import LayerStack, draw_cart, draw_person, phase

SKY = (219, 235, 245)
WALL = (236, 234, 224)
FLOOR = (177, 188, 194)
MARS_SKY = (239, 214, 195)
MARS_GROUND = (174, 92, 61)
MARS_HILL = (143, 72, 51)
ROOM = (224, 235, 241)
DARK_ROOM = (30, 47, 64)


def _absolute_progress(duration_seconds: float, time_seconds: float) -> float:
    duration = max(0.001, float(duration_seconds))
    return max(0.0, min(1.0, float(time_seconds) / duration))


def _selected_template(scene, template_id: str | None) -> str:
    plan = dict(getattr(scene, "animation_plan", None) or {})
    forced = str(plan.get("shorts_template_id") or "")
    if forced in cartoon.TEMPLATE_BY_ID:
        return forced
    if template_id in cartoon.TEMPLATE_BY_ID:
        return str(template_id)
    selected, _confidence, _reason = cartoon.suggest_template(scene)
    return selected.template_id


def _presenter_frame(progress: float, variant: int) -> Image.Image:
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    stack = LayerStack((width, height))
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    foreground = stack.draw("foreground")
    effects = stack.draw("effects")

    environment.rectangle((0, 0, width, height), fill=ROOM)
    environment.rectangle((0, 790, width, height), fill=FLOOR)
    environment.rounded_rectangle((735, 125, 1705, 735), radius=42, fill=(250, 250, 247), outline=cartoon.INK, width=10)
    environment.rounded_rectangle((165, 720, 660, 875), radius=28, fill=(66, 75, 83), outline=cartoon.INK, width=9)

    draw_person(
        actors,
        (420, 735),
        1.05,
        shirt=cartoon.GREEN,
        pants=(48, 59, 76),
        arm_raise=0.64,
    )

    chart_left, chart_top, chart_right, chart_bottom = 850, 235, 1585, 625
    environment.line((chart_left, chart_bottom, chart_right, chart_bottom), fill=(82, 94, 106), width=5)
    environment.line((chart_left, chart_top, chart_left, chart_bottom), fill=(82, 94, 106), width=5)
    values = (0.16, 0.31, 0.28, 0.53, 0.47, 0.72, 0.82)
    reveal = phase(progress, 0.05, 0.84)
    points: list[tuple[int, int]] = []
    for index, value in enumerate(values):
        x = round(chart_left + index * (chart_right - chart_left) / (len(values) - 1))
        y = round(chart_bottom - value * (chart_bottom - chart_top))
        points.append((x, y))
    visible_count = max(2, min(len(points), round(1 + reveal * (len(points) - 1))))
    visible = points[:visible_count]
    effects.line(visible, fill=cartoon.BLUE, width=13, joint="curve")
    for x, y in visible:
        effects.ellipse((x - 10, y - 10, x + 10, y + 10), fill=cartoon.AMBER, outline=cartoon.INK, width=3)

    target_index = min(len(visible) - 1, max(1, round(reveal * (len(points) - 1))))
    target_x, target_y = visible[target_index]
    foreground.line((560, 500, target_x - 20, target_y + 15), fill=(64, 74, 84), width=8)
    foreground.ellipse((target_x - 27, target_y + 8, target_x - 13, target_y + 22), fill=cartoon.AMBER)

    environment.rounded_rectangle((114, 105, 580, 205), radius=30, fill=(52, 70, 88), outline=cartoon.INK, width=7)
    environment.text((347, 155), "EVIDENCE", font=cartoon._font(38, True), fill=cartoon.WHITE, anchor="mm")
    return stack.composite(ROOM)


def _council_frame(progress: float, variant: int) -> Image.Image:
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    stack = LayerStack((width, height))
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    foreground = stack.draw("foreground")
    effects = stack.draw("effects")

    environment.rectangle((0, 0, width, height), fill=(214, 231, 239))
    environment.rounded_rectangle((90, 70, width - 90, height - 70), radius=55, fill=(232, 241, 245), outline=cartoon.INK, width=10)
    environment.rectangle((0, 820, width, height), fill=(172, 184, 190))

    # One readable council table, three speakers, and only four audience members.
    foreground.arc((330, 520, 1590, 1050), 195, 345, fill=(93, 67, 49), width=70)
    active = min(2, int(max(0.0, min(0.999, progress)) * 3))
    positions = ((610, 610), (960, 560), (1310, 610))
    colors = (cartoon.BLUE, cartoon.AMBER, cartoon.PURPLE)
    for index, ((x, y), color) in enumerate(zip(positions, colors)):
        lift = 32 if index == active else 0
        draw_person(
            actors,
            (x, y - lift),
            0.86,
            shirt=color,
            pants=(48, 59, 76),
            arm_raise=0.72 if index == active else 0.18,
        )
        effects.rounded_rectangle(
            (x - 105, 770, x + 105, 845),
            radius=20,
            fill=(51, 61, 74),
            outline=color if index == active else (92, 103, 115),
            width=6,
        )

    for index, x in enumerate((420, 760, 1160, 1500)):
        draw_person(
            actors,
            (x, 935),
            0.48,
            shirt=(93, 112, 129) if index % 2 == 0 else (108, 145, 153),
            pants=(50, 61, 78),
        )

    environment.rounded_rectangle((650, 105, 1270, 210), radius=32, fill=DARK_ROOM, outline=cartoon.INK, width=7)
    environment.text((960, 158), "WHO SETS THE RULES?", font=cartoon._font(36, True), fill=cartoon.WHITE, anchor="mm")
    return stack.composite((214, 231, 239))


def _crowd_frame(progress: float, variant: int) -> Image.Image:
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    stack = LayerStack((width, height))
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    environment.rectangle((0, 0, width, height), fill=MARS_SKY)
    environment.polygon(((0, 660), (280, 390), (560, 670)), fill=MARS_HILL)
    environment.polygon(((1330, 670), (1640, 360), (1920, 690)), fill=(154, 77, 52))
    environment.rectangle((0, 650, width, height), fill=MARS_GROUND)
    environment.pieslice((470, 225, 1450, 820), 180, 360, fill=(183, 221, 231), outline=cartoon.INK, width=11)
    environment.rounded_rectangle((865, 470, 1055, 765), radius=35, fill=(53, 70, 84), outline=cartoon.CYAN, width=7)

    # Five foreground residents, not a repeated grid of miniature bodies.
    colors = (cartoon.BLUE, cartoon.AMBER, cartoon.GREEN, cartoon.PURPLE, (88, 172, 159))
    bases = ((310, 865), (620, 920), (960, 870), (1290, 925), (1600, 865))
    focal = min(4, int(max(0.0, min(0.999, progress)) * 5))
    for index, ((x, y), color) in enumerate(zip(bases, colors)):
        lift = 34 if index == focal else 0
        draw_person(
            actors,
            (x, y - lift),
            0.72 if index == focal else 0.62,
            shirt=color,
            pants=(48, 59, 76),
            arm_raise=0.55 if index == focal else 0.12,
        )

    draw_cart(actors, (1500, 760, 1710, 885), fill=(50, 67, 82), accent=cartoon.CYAN)
    effects.rounded_rectangle((625, 90, 1295, 195), radius=32, fill=(49, 66, 82), outline=cartoon.INK, width=7)
    effects.text((960, 143), "PEOPLE MAKE THE CITY", font=cartoon._font(36, True), fill=cartoon.WHITE, anchor="mm")
    return stack.composite(MARS_SKY)


def _process_frame(progress: float, variant: int) -> Image.Image:
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    stack = LayerStack((width, height))
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    effects = stack.draw("effects")

    environment.rectangle((0, 0, width, height), fill=(215, 231, 240))
    environment.rectangle((0, 760, width, height), fill=(174, 92, 61))
    environment.polygon(((0, 760), (230, 500), (470, 765)), fill=MARS_HILL)
    environment.polygon(((1450, 765), (1690, 485), (1920, 760)), fill=(154, 77, 52))

    modules = (
        (150, 230, 610, 670, "TRANSPORT", cartoon.CYAN),
        (730, 155, 1190, 670, "HABITAT", cartoon.GREEN),
        (1310, 230, 1770, 670, "GOVERNANCE", cartoon.AMBER),
    )
    reveal = phase(progress, 0.04, 0.80)
    for index, (left, top, right, bottom, label, color) in enumerate(modules):
        active = reveal >= index / 3
        outline = color if active else (100, 112, 122)
        environment.rounded_rectangle((left, top, right, bottom), radius=48, fill=(238, 244, 246), outline=outline, width=10)
        environment.rounded_rectangle((left + 45, top + 50, right - 45, top + 135), radius=24, fill=(52, 68, 83), outline=cartoon.INK, width=5)
        environment.text(((left + right) // 2, top + 92), label, font=cartoon._font(30, True), fill=cartoon.WHITE, anchor="mm")

    # Semantic contents inside each module.
    environment.polygon(((260, 510), (365, 405), (470, 510), (365, 575)), fill=(221, 229, 234), outline=cartoon.INK)
    environment.rectangle((325, 410, 405, 545), fill=(66, 82, 96), outline=cartoon.CYAN, width=6)
    environment.pieslice((805, 300, 1115, 605), 180, 360, fill=(183, 221, 231), outline=cartoon.INK, width=8)
    environment.rounded_rectangle((925, 420, 995, 600), radius=17, fill=(53, 70, 84), outline=cartoon.GREEN, width=6)
    for x in (1415, 1540, 1665):
        environment.rounded_rectangle((x, 380, x + 80, 540), radius=20, fill=(68, 82, 96), outline=cartoon.AMBER, width=5)

    if reveal > 0.28:
        effects.line((610, 450, 730, 450), fill=cartoon.INK, width=12)
        effects.polygon(((730, 450), (700, 428), (700, 472)), fill=cartoon.INK)
    if reveal > 0.62:
        effects.line((1190, 450, 1310, 450), fill=cartoon.INK, width=12)
        effects.polygon(((1310, 450), (1280, 428), (1280, 472)), fill=cartoon.INK)

    draw_person(actors, (880, 925), 0.62, shirt=cartoon.GREEN, pants=(48, 59, 76))
    draw_person(actors, (1050, 925), 0.62, shirt=cartoon.AMBER, pants=(48, 59, 76), arm_raise=0.45)
    draw_cart(actors, (1440, 825, 1650, 950), fill=(50, 67, 82), accent=cartoon.CYAN)
    return stack.composite((215, 231, 240))


def _route_frame(progress: float, variant: int) -> Image.Image:
    """Keep travel monotonic while adding distinct departure, cruise, and arrival beats."""
    image = v52._route(progress, variant)
    draw = ImageDraw.Draw(image)

    if 0.22 <= progress < 0.62:
        local = phase(progress, 0.22, 0.62)
        panel_alpha = round(220 * min(1.0, local / 0.18) * min(1.0, (1.0 - local) / 0.18))
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rounded_rectangle((570, 105, 1350, 315), radius=42, fill=(24, 38, 57, panel_alpha), outline=(118, 194, 214, panel_alpha), width=7)
        od.text((960, 160), "DEEP-SPACE CRUISE", font=cartoon._font(38, True), fill=(*cartoon.WHITE, panel_alpha), anchor="mm")
        labels = (("POWER", cartoon.AMBER), ("AIR", cartoon.CYAN), ("NAV", cartoon.GREEN))
        for index, (label, color) in enumerate(labels):
            x = 700 + index * 260
            ready = local > 0.18 + index * 0.18
            fill = color if ready else (86, 96, 108)
            od.rounded_rectangle((x - 88, 205, x + 88, 275), radius=22, fill=(*fill, panel_alpha), outline=(*cartoon.INK, panel_alpha), width=5)
            od.text((x, 240), label, font=cartoon._font(25, True), fill=(*cartoon.WHITE, panel_alpha), anchor="mm")
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(image)

    if progress >= 0.86:
        arrival = phase(progress, 0.86, 0.98)
        base_y = 885
        for index, x in enumerate((1320, 1485, 1640)):
            rise = round((1.0 - arrival) * (80 + index * 18))
            draw.pieslice((x - 92, base_y - 112 + rise, x + 92, base_y + 55 + rise), 180, 360, fill=(183, 221, 231), outline=cartoon.INK, width=6)
            draw.rectangle((x - 24, base_y - 18 + rise, x + 24, base_y + 55 + rise), fill=(53, 70, 84), outline=cartoon.GREEN, width=4)
    return image


def render_planned_frame(
    scene,
    template_id: str | None,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    selected = _selected_template(scene, template_id)
    progress = _absolute_progress(duration_seconds, time_seconds)
    scene_number = int(getattr(scene, "scene_number", 1) or 1)
    variant = scene_number % 6

    if selected == "transport_scene":
        return v62._transport_frame(progress, variant)
    if selected == "habitat_build":
        return v62._habitat_frame(progress, variant)
    if selected == "presenter_desk":
        return _presenter_frame(progress, variant)
    if selected == "council_scene":
        return _council_frame(progress, variant)
    if selected == "crowd_focus":
        return _crowd_frame(progress, variant)
    if selected == "process_diagram":
        return _process_frame(progress, variant)
    if selected == "route_map":
        return _route_frame(progress, variant)
    return v62.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)


cartoon.render_planned_frame = render_planned_frame
