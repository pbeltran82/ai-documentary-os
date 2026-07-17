from __future__ import annotations

"""Editorial polish shared by Shorts and landscape tech visuals.

This module deliberately patches the existing render registries at runtime. That
keeps the approved native-Shorts foundation intact while letting both delivery
formats share the better clothed human design and stronger decision metaphors.
"""

import math
from typing import Any

from PIL import Image, ImageDraw

from . import native_shorts as shorts

_PATCHED = False


def _landscape_person(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    palette: dict[str, tuple[int, int, int]],
    *,
    digital: bool = False,
) -> None:
    """Draw a finished, clothed person instead of the old wireframe stick rig."""
    x, ground_y = center
    accent = palette["accent"] if digital else palette["accent_alt"]
    shirt = accent
    denim = (43, 79, 126) if not digital else (35, 88, 132)
    skin = (239, 190, 145)
    ink = palette.get("ink", (5, 10, 20))
    hair = (38, 29, 26)

    # Body proportions intentionally match the approved Shorts character:
    # narrow waist, full clothes, natural forearms, grounded feet.
    head_y = ground_y - 335
    draw.ellipse((x - 62, head_y - 66, x + 62, head_y + 58), fill=skin, outline=ink, width=6)
    draw.pieslice((x - 66, head_y - 75, x + 66, head_y + 28), 180, 356, fill=hair)
    draw.polygon(
        (
            (x - 60, head_y - 20),
            (x - 44, head_y - 58),
            (x - 17, head_y - 48),
            (x + 2, head_y - 67),
            (x + 28, head_y - 47),
            (x + 55, head_y - 55),
            (x + 63, head_y - 17),
        ),
        fill=hair,
    )
    draw.ellipse((x - 27, head_y - 8, x - 15, head_y + 4), fill=ink)
    draw.ellipse((x + 15, head_y - 8, x + 27, head_y + 4), fill=ink)
    draw.arc((x - 25, head_y + 8, x + 25, head_y + 42), 20, 160, fill=ink, width=4)

    neck_top = head_y + 48
    draw.rounded_rectangle((x - 15, neck_top, x + 15, neck_top + 35), radius=8, fill=skin)
    torso_top = neck_top + 25
    torso_bottom = ground_y - 132
    shirt_points = (
        (x - 62, torso_top),
        (x + 62, torso_top),
        (x + 43, torso_bottom),
        (x - 43, torso_bottom),
    )
    draw.polygon(tuple((px + 5, py + 6) for px, py in shirt_points), fill=ink)
    draw.polygon(shirt_points, fill=shirt, outline=ink)

    # Relaxed, slightly bent arms prevent the rigid T-pose/stick-figure look.
    for side in (-1, 1):
        shoulder = (x + side * 57, torso_top + 20)
        elbow = (x + side * 91, torso_top + 92)
        hand = (x + side * 82, torso_bottom + 40)
        draw.line((shoulder, elbow), fill=ink, width=24)
        draw.line((shoulder, elbow), fill=shirt, width=17)
        draw.line((elbow, hand), fill=ink, width=21)
        draw.line((elbow, hand), fill=skin, width=14)
        draw.ellipse((hand[0] - 13, hand[1] - 13, hand[0] + 13, hand[1] + 13), fill=skin, outline=ink, width=3)

    waist_y = torso_bottom - 4
    draw.rounded_rectangle((x - 45, waist_y, x + 45, waist_y + 32), radius=7, fill=denim, outline=ink, width=4)
    left_leg = ((x - 42, waist_y + 20), (x - 3, waist_y + 20), (x - 16, ground_y - 12), (x - 70, ground_y - 12))
    right_leg = ((x + 3, waist_y + 20), (x + 42, waist_y + 20), (x + 70, ground_y - 12), (x + 16, ground_y - 12))
    draw.polygon(left_leg, fill=denim, outline=ink)
    draw.polygon(right_leg, fill=denim, outline=ink)
    draw.rounded_rectangle((x - 83, ground_y - 22, x - 12, ground_y + 7), radius=11, fill=(22, 29, 40))
    draw.rounded_rectangle((x + 12, ground_y - 22, x + 83, ground_y + 7), radius=11, fill=(22, 29, 40))

    if digital:
        # A few contained signal marks communicate the modeled counterpart
        # without turning the body back into a wireframe.
        for offset in (-35, 0, 35):
            draw.line((x - 36, torso_top + 70 + offset, x + 36, torso_top + 70 + offset), fill=palette["accent"], width=3)


def install_landscape_character_patch() -> None:
    """Install the finished character after the tech renderer finishes importing."""
    global _PATCHED
    if _PATCHED:
        return
    from . import tech_behavior_motion

    tech_behavior_motion._person_wireframe = _landscape_person
    _PATCHED = True


def _decision_field(canvas: Image.Image, progress: float, accent: shorts.RGB) -> None:
    """Full-height ranked field; no generic video play-button metaphor."""
    draw = ImageDraw.Draw(canvas)
    reveal = shorts._phase(progress, 0.02, 0.62)
    select = shorts._phase(progress, 0.48, 0.92)
    center_x = 540

    shorts._text(draw, (center_x, 465), "THOUSANDS OF POSSIBLE MOMENTS", 25, shorts.MUTED, bold=True, anchor="mm")
    candidates = (
        (190, 610), (410, 555), (680, 610), (875, 560),
        (225, 805), (515, 760), (825, 825),
        (330, 1040), (700, 1030), (875, 1160),
    )
    target = (540, 1020)
    for index, point in enumerate(candidates):
        active = reveal > index * 0.055
        radius = 22 + (index % 3) * 7
        color = accent if active else (37, 54, 78)
        draw.ellipse((point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius), fill=color)
        if active:
            shorts._arrow(draw, point, target, accent, min(1.0, reveal + index * 0.035), 4)

    # The winning outcome rises as a ranked card rather than a UI play control.
    lift = round(55 * select)
    winner = (260, 925 - lift, 820, 1185 - lift)
    draw.rounded_rectangle(winner, radius=46, fill=(16, 58, 82), outline=shorts.GREEN, width=7)
    shorts._text(draw, (540, winner[1] + 65), "RANKED OUTCOME", 27, shorts.GREEN, bold=True, anchor="mm")
    shorts._text(draw, (540, winner[1] + 140), "#1", 96, shorts.WHITE, bold=True, anchor="mm")
    shorts._text(draw, (540, winner[1] + 215), "PLACED IN FRONT OF YOU", 25, shorts.MUTED, bold=True, anchor="mm")


def _choice_funnel(canvas: Image.Image, progress: float, accent: shorts.RGB) -> None:
    """A selection funnel replaces the repeated phone/play icon composition."""
    draw = ImageDraw.Draw(canvas)
    q = shorts._phase(progress, 0.03, 0.9)
    shorts._text(draw, (540, 470), "THE VISIBLE ACTION", 24, shorts.MUTED, bold=True, anchor="mm")
    shorts._chip(draw, (540, 555), "YOU KEPT WATCHING", shorts.CYAN)

    widths = (760, 600, 440, 280)
    labels = ("WATCH TIME", "RELEVANCE", "TIMING", "HISTORY")
    colors = (shorts.PURPLE, shorts.CYAN, shorts.GREEN, shorts.AMBER)
    top = 690
    for index, (width, label, color) in enumerate(zip(widths, labels, colors, strict=True)):
        local = shorts._phase(q, index * 0.14, min(1.0, index * 0.14 + 0.42))
        y = top + index * 145
        left = round(540 - width * local / 2)
        right = round(540 + width * local / 2)
        if right > left:
            draw.rounded_rectangle((left, y, right, y + 74), radius=30, fill=(18, 38, 66), outline=color, width=4)
            shorts._text(draw, (540, y + 37), label, 25, color, bold=True, anchor="mm")
        if index < len(widths) - 1:
            shorts._arrow(draw, (540, y + 80), (540, y + 135), color, local, 6)

    if q > 0.68:
        shorts._chip(draw, (540, 1325), "ONE OPPORTUNITY RANKED FIRST", shorts.GREEN, scale=1.08)


def _behavior_path(canvas: Image.Image, progress: float, accent: shorts.RGB) -> None:
    """Full-bleed action-to-profile pathway for stronger layout variety."""
    draw = ImageDraw.Draw(canvas)
    q = shorts._phase(progress, 0.02, 0.9)
    labels = ("SCROLL", "PAUSE", "SEARCH", "DRAFT", "WATCH")
    path = ((160, 560), (350, 710), (190, 885), (420, 1050), (300, 1240))
    for index, (label, point) in enumerate(zip(labels, path, strict=True)):
        active = q > index * 0.13
        color = shorts.PURPLE if index % 2 == 0 else shorts.CYAN
        if index:
            previous = path[index - 1]
            shorts._arrow(draw, previous, point, color, max(0.0, q - index * 0.08), 7)
        draw.ellipse((point[0] - 42, point[1] - 42, point[0] + 42, point[1] + 42), fill=color if active else (39, 52, 74))
        shorts._text(draw, (point[0] + 68, point[1]), label, 25, shorts.WHITE if active else shorts.MUTED, bold=True, anchor="lm")

    profile_left = 585
    draw.rounded_rectangle((profile_left, 580, 935, 1280), radius=46, fill=(15, 42, 72), outline=accent, width=5)
    shorts._text(draw, (760, 650), "BEHAVIORAL PROFILE", 25, accent, bold=True, anchor="mm")
    for index in range(round(10 * q)):
        width = 120 + (index * 39) % 150
        color = shorts.CYAN if index % 2 == 0 else shorts.PURPLE
        draw.rounded_rectangle((635, 745 + index * 43, 635 + width, 770 + index * 43), radius=12, fill=color)
    shorts._text(draw, (760, 1225), f"{round(10000 * q):,} SIGNALS", 34, shorts.WHITE, bold=True, anchor="mm")


def _story_cta(canvas: Image.Image, progress: float) -> None:
    """Land the thesis before asking for engagement."""
    draw = ImageDraw.Draw(canvas)
    shorts._text(draw, (shorts.SAFE_LEFT, 1285), "YOUR ACTIONS BECOME PREDICTIONS.", 31, shorts.WHITE, bold=True)
    shorts._text(draw, (shorts.SAFE_LEFT, 1332), "THOSE PREDICTIONS SHAPE WHAT COMES NEXT.", 25, shorts.MUTED, bold=True)
    y = 1450
    draw.rounded_rectangle((shorts.SAFE_LEFT, y, 650, y + 92), radius=22, fill=shorts.RED)
    draw.polygon(((118, y + 26), (118, y + 66), (151, y + 46)), fill=shorts.WHITE)
    shorts._text(draw, (390, y + 46), "SUBSCRIBE", 36, shorts.WHITE, bold=True, anchor="mm")
    draw.rounded_rectangle((680, y, shorts.SAFE_RIGHT, y + 92), radius=46, fill=shorts.BLUE)
    shorts._text(draw, (845, y + 46), "LIKE  👍", 32, shorts.WHITE, bold=True, anchor="mm")
    shorts._text(draw, (shorts.SAFE_LEFT, 1590), "KEEP QUESTIONING THE SYSTEM", 23, (122, 138, 162), bold=True)


def compose_documentary_shorts(
    source: Image.Image,
    *,
    family_id: str | None,
    template_id: str | None,
    progress: float = 0.5,
    title: str | None = None,
    subtitle: str | None = None,
) -> Image.Image:
    """Compose the approved Shorts system with the next editorial polish pass."""
    install_landscape_character_patch()
    shorts.RENDERERS[("tech_behavior_motion", "algorithm_chose_you")] = _decision_field
    shorts.RENDERERS[("tech_behavior_motion", "machine_choice_explainer")] = _choice_funnel
    shorts.RENDERERS[("tech_behavior_motion", "machine_choice_cta")] = _choice_funnel
    shorts.RENDERERS[("tech_behavior_motion", "digital_footprint_collector")] = _behavior_path
    shorts._cta = _story_cta

    # Remove the empty opening beat while retaining the existing controlled exit.
    resolved_progress = max(0.04, min(1.0, float(progress)))
    return shorts.compose_native_shorts(
        source,
        family_id=family_id,
        template_id=template_id,
        progress=resolved_progress,
        title=title,
        subtitle=subtitle,
    )
