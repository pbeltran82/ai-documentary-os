from __future__ import annotations

"""Visual Overhaul v66: adjacent transport scenes must not restart boarding.

Frame-level QA of the fifth Mars export found two consecutive opening scenes
that both resolved to ``transport_scene``. The first remains the authored
boarding/airlock action. A consecutive transport scene now becomes a distinct
cargo-and-logistics control beat so the documentary advances instead of
replaying the doorway animation.
"""

from PIL import Image

from . import cartoon_documentary as cartoon
from . import cartoon_visual_overhaul_v63 as v63
from . import cartoon_visual_overhaul_v65 as v65
from .cartoon_scene_graph import LayerStack, draw_cart, draw_person, phase

ROOM = (219, 233, 240)
FLOOR = (163, 177, 184)
INK = cartoon.INK

# Preserve the complete v65 route/community/settlement behavior before extending
# its public renderer contract. Existing callers that import v65 continue to see
# the final installed renderer, while this module can safely delegate downward.
_previous_render_planned_frame = v65.render_planned_frame


def _ordered_scenes(scene) -> list:
    project = getattr(scene, "project", None)
    return sorted(
        list(getattr(project, "scenes", None) or []),
        key=lambda item: int(getattr(item, "scene_number", 0) or 0),
    )


def _previous_scene(scene):
    scenes = _ordered_scenes(scene)
    number = int(getattr(scene, "scene_number", 0) or 0)
    for index, item in enumerate(scenes):
        if int(getattr(item, "scene_number", 0) or 0) == number:
            return scenes[index - 1] if index > 0 else None
    return None


def _is_consecutive_transport(scene, selected: str) -> bool:
    if selected != "transport_scene":
        return False
    previous = _previous_scene(scene)
    if previous is None:
        return False
    return v63._selected_template(previous, None) == "transport_scene"


def _logistics_frame(progress: float, variant: int) -> Image.Image:
    """Cargo staging and dispatch control, visually separate from boarding."""
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    stack = LayerStack((width, height))
    environment = stack.draw("environment")
    actors = stack.draw("actors")
    foreground = stack.draw("foreground")
    effects = stack.draw("effects")

    environment.rectangle((0, 0, width, height), fill=ROOM)
    environment.rectangle((0, 760, width, height), fill=FLOOR)
    environment.rounded_rectangle(
        (95, 80, width - 95, 735),
        radius=58,
        fill=(235, 238, 234),
        outline=INK,
        width=10,
    )

    # Dispatch wall: manifests, route readiness, and cargo allocation.
    environment.rounded_rectangle(
        (720, 135, 1740, 610),
        radius=42,
        fill=(43, 61, 78),
        outline=INK,
        width=9,
    )
    reveal = phase(progress, 0.04, 0.78)
    columns = (
        (815, "CREW", cartoon.CYAN),
        (1085, "CARGO", cartoon.AMBER),
        (1355, "POWER", cartoon.GREEN),
        (1625, "CLEAR", cartoon.PURPLE),
    )
    for index, (x, label, color) in enumerate(columns):
        active = reveal > 0.12 + index * 0.18
        resolved = color if active else (82, 94, 106)
        environment.rounded_rectangle(
            (x - 105, 245, x + 105, 500),
            radius=30,
            fill=(61, 78, 94),
            outline=resolved,
            width=7,
        )
        environment.text(
            (x, 205),
            label,
            font=cartoon._font(27, True),
            fill=cartoon.WHITE,
            anchor="mm",
        )
        for row in range(3):
            y = 300 + row * 66
            status = active or reveal > 0.2 + index * 0.16 + row * 0.05
            environment.ellipse(
                (x - 62, y - 11, x - 40, y + 11),
                fill=resolved if status else (92, 102, 112),
                outline=INK,
                width=3,
            )
            environment.rounded_rectangle(
                (x - 22, y - 10, x + 68, y + 10),
                radius=8,
                fill=(190, 202, 208) if status else (121, 132, 140),
            )

    # Foreground logistics lane: one supervisor and moving cargo, no doorway reset.
    draw_person(
        actors,
        (420, 790),
        0.92,
        shirt=cartoon.BLUE,
        pants=(48, 59, 76),
        arm_raise=0.62,
    )
    cargo_move = phase(progress, 0.18, 0.84)
    cart_x = round(520 + 520 * cargo_move)
    draw_cart(
        actors,
        (cart_x, 790, cart_x + 235, 935),
        fill=(49, 68, 84),
        accent=cartoon.AMBER,
    )
    draw_person(
        actors,
        (1320, 850),
        0.68,
        shirt=cartoon.GREEN,
        pants=(48, 59, 76),
        arm_raise=0.28,
    )

    foreground.rounded_rectangle(
        (135, 110, 610, 225),
        radius=34,
        fill=(46, 64, 80),
        outline=INK,
        width=7,
    )
    foreground.text(
        (372, 168),
        "MISSION LOGISTICS",
        font=cartoon._font(36, True),
        fill=cartoon.WHITE,
        anchor="mm",
    )

    ready = phase(progress, 0.68, 0.92)
    effects.rounded_rectangle(
        (700, 650, 1220, 730),
        radius=26,
        fill=(39, 58, 73),
        outline=cartoon.GREEN if ready > 0.7 else cartoon.AMBER,
        width=7,
    )
    effects.text(
        (960, 690),
        "CREW + CARGO CLEARED",
        font=cartoon._font(31, True),
        fill=cartoon.WHITE,
        anchor="mm",
    )
    return stack.composite(ROOM)


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

    if _is_consecutive_transport(scene, selected):
        return _logistics_frame(progress, variant)

    return _previous_render_planned_frame(
        scene,
        template_id,
        duration_seconds,
        time_seconds,
        style_id,
    )


# Keep v65 as the public compatibility surface while installing the v66 extension.
v65.render_planned_frame = render_planned_frame
cartoon.render_planned_frame = v65.render_planned_frame
