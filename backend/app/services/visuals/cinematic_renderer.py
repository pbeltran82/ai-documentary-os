from __future__ import annotations

import math

from PIL import ImageDraw

from .. import finance_motion as engine

WIDTH = 1920
HEIGHT = 1080


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b, strict=True))


def _ambient(
    draw: ImageDraw.ImageDraw,
    palette: dict[str, tuple[int, int, int]],
    progress: float,
    *,
    warmth: float = 0.0,
) -> None:
    """Fast layered lighting without the old grid-and-dashboard background."""
    top = _mix(palette["background"], (3, 7, 14), 0.55)
    bottom_target = (38, 24, 18) if warmth else (8, 21, 38)
    bottom = _mix(palette["background"], bottom_target, 0.72)
    for band in range(18):
        y0 = round(HEIGHT * band / 18)
        y1 = round(HEIGHT * (band + 1) / 18) + 1
        draw.rectangle((0, y0, WIDTH, y1), fill=_mix(top, bottom, band / 17))

    drift = round(90 * math.sin(progress * math.pi * 2))
    glow = _mix(palette["accent"], (255, 255, 255), 0.18)
    draw.ellipse((1050 + drift, -250, 2240 + drift, 940), fill=_mix(bottom, glow, 0.16))
    draw.ellipse((-520 - drift, 430, 780 - drift, 1510), fill=_mix(top, palette["accent_alt"], 0.13))

    # Foreground framing creates depth before any subject is added.
    draw.polygon(((0, 850), (440, 730), (610, 1080), (0, 1080)), fill=_mix(top, (0, 0, 0), 0.45))
    draw.polygon(((1920, 790), (1650, 700), (1490, 1080), (1920, 1080)), fill=_mix(top, (0, 0, 0), 0.38))


def _minimal_common(draw, template, palette, progress: float) -> None:
    """One restrained editorial heading; narration carries the explanation."""
    title = " ".join(str(template.title).split()[:7])
    muted = _mix(palette["muted"], palette["white"], 0.08)
    engine._text(draw, (86, 66), "MIND HORIZON  /  TECH & BEHAVIOR", 18, muted, bold=True)
    engine._text(draw, (86, 105), title, 34, palette["white"], bold=True)
    line_width = 145 + round(215 * max(0.0, min(1.0, progress)))
    draw.rounded_rectangle((86, 160, 86 + line_width, 166), radius=3, fill=palette["accent"])


def _quiet_beat_indicator(draw, template_id, duration_seconds, time_seconds, palette) -> None:
    progress = max(0.0, min(1.0, time_seconds / max(0.001, duration_seconds)))
    x0, y = 1700, 1012
    draw.rounded_rectangle((x0, y, 1840, y + 5), radius=3, fill=_mix(palette["muted"], palette["background"], 0.55))
    draw.rounded_rectangle((x0, y, x0 + round(140 * progress), y + 5), radius=3, fill=palette["accent"])


def _person(
    draw: ImageDraw.ImageDraw,
    x: int,
    ground_y: int,
    scale: float,
    palette: dict[str, tuple[int, int, int]],
    *,
    facing: int = 1,
    digital: bool = False,
) -> None:
    ink = _mix(palette["background"], (0, 0, 0), 0.72)
    rim = palette["accent"] if digital else _mix(palette["white"], palette["accent_alt"], 0.22)
    skin = (196, 154, 124) if not digital else _mix(palette["accent"], palette["white"], 0.24)
    head_r = round(38 * scale)
    head_y = ground_y - round(315 * scale)
    draw.ellipse((x - head_r, head_y - head_r, x + head_r, head_y + head_r), fill=skin, outline=rim, width=max(2, round(3 * scale)))
    torso_top = head_y + head_r - round(2 * scale)
    torso_bottom = ground_y - round(120 * scale)
    shoulder = round(55 * scale)
    waist = round(35 * scale)
    draw.polygon(
        ((x - shoulder, torso_top), (x + shoulder, torso_top), (x + waist, torso_bottom), (x - waist, torso_bottom)),
        fill=ink,
        outline=rim,
    )
    arm_y = torso_top + round(42 * scale)
    phone_x = x + facing * round(105 * scale)
    phone_y = arm_y + round(38 * scale)
    draw.line((x + facing * shoulder, arm_y, phone_x, phone_y), fill=ink, width=max(8, round(18 * scale)))
    draw.line((x - facing * shoulder, arm_y, x - facing * round(72 * scale), torso_bottom - round(5 * scale)), fill=ink, width=max(8, round(17 * scale)))
    hip_y = torso_bottom
    draw.line((x - round(22 * scale), hip_y, x - round(42 * scale), ground_y), fill=ink, width=max(10, round(25 * scale)))
    draw.line((x + round(22 * scale), hip_y, x + round(52 * scale), ground_y), fill=ink, width=max(10, round(25 * scale)))
    if digital:
        for offset in (-22, 0, 22):
            yy = torso_top + round((48 + offset) * scale)
            draw.line((x - round(30 * scale), yy, x + round(30 * scale), yy), fill=palette["accent"], width=max(1, round(2 * scale)))


def _phone(draw, box, palette, progress: float, *, selected: bool = False) -> None:
    left, top, right, bottom = box
    shell = _mix(palette["background"], (0, 0, 0), 0.7)
    draw.rounded_rectangle(box, radius=42, fill=shell, outline=palette["accent"], width=4)
    draw.rounded_rectangle((left + 23, top + 42, right - 23, bottom - 30), radius=25, fill=_mix(palette["panel"], (3, 9, 17), 0.45))
    visible = 3 + round(progress * 3)
    for index in range(visible):
        y = top + 95 + index * 82
        width = right - left - 82 - (index % 2) * 35
        fill = palette["accent"] if selected and index == 2 else _mix(palette["panel_alt"], palette["accent_alt"], 0.16)
        draw.rounded_rectangle((left + 42, y, left + 42 + width, y + 55), radius=14, fill=fill)


def render_algorithm_chose_you(draw, progress, palette) -> None:
    _ambient(draw, palette, progress)
    # A crowded, out-of-focus media field replaces three explanatory panels.
    for index in range(14):
        depth = index / 13
        x = 150 + ((index * 137) % 1120)
        y = 275 + ((index * 83) % 540)
        w = round(120 + 110 * depth)
        h = round(65 + 45 * depth)
        fill = _mix(palette["panel_alt"], palette["background"], 0.42 + depth * 0.28)
        draw.rounded_rectangle((x, y, x + w, y + h), radius=12, fill=fill)
    spotlight = round(420 * progress)
    draw.polygon(((1240, 170), (1880, 320), (1750, 980), (1320 - spotlight // 5, 860)), fill=_mix(palette["background"], palette["accent"], 0.10 + 0.07 * progress))
    _person(draw, 1450, 975, 1.25, palette, facing=1)
    phone_box = (1570, 435, 1800, 845)
    _phone(draw, phone_box, palette, progress, selected=progress > 0.48)
    if progress > 0.56:
        engine._text(draw, (1080, 820), "ONE MOMENT RISES", 28, palette["accent"], bold=True)


def render_behavior_prediction_engine(draw, progress, palette) -> None:
    _ambient(draw, palette, progress)
    _phone(draw, (130, 330, 430, 870), palette, progress)
    # Signals travel through the physical scene instead of a boxed pipeline.
    signal_words = ("PAUSE", "SEARCH", "SCROLL", "DRAFT")
    for index, label in enumerate(signal_words):
        phase = max(0.0, min(1.0, progress * 1.35 - index * 0.16))
        x = round(430 + phase * 690)
        y = 430 + index * 105
        draw.line((430, y, x, 610), fill=_mix(palette["accent_alt"], palette["background"], 0.25), width=3)
        draw.ellipse((x - 11, y - 11, x + 11, y + 11), fill=palette["accent"])
        if phase > 0.45:
            engine._text(draw, (x + 22, y - 8), label, 15, palette["muted"], bold=True)
    # Human profile and a translucent predicted gesture.
    _person(draw, 1270, 965, 1.35, palette, facing=-1)
    ghost_x = 1530 + round(75 * progress)
    _person(draw, ghost_x, 965, 1.35, palette, facing=-1, digital=True)
    probability = round(38 + 58 * progress)
    engine._text(draw, (1130, 310), "THE MODEL ANTICIPATES", 24, palette["muted"], bold=True)
    engine._text(draw, (1130, 350), f"{probability}%", 62, palette["white"], bold=True)


def render_life_event_timeline(draw, progress, palette) -> None:
    _ambient(draw, palette, progress, warmth=0.35)
    horizon_y = 470
    draw.line((0, horizon_y, WIDTH, horizon_y), fill=_mix(palette["muted"], palette["background"], 0.6), width=2)
    # Perspective road turns time into a place the viewer moves through.
    draw.polygon(((850, 1080), (1080, 1080), (1035, horizon_y), (930, horizon_y)), fill=_mix(palette["panel"], (0, 0, 0), 0.22))
    draw.line((960, 1080, 980, horizon_y), fill=palette["warning"], width=5)
    milestones = ((420, "RECORDS"), (760, "WORK"), (1110, "HEALTH"), (1490, "FUTURE"))
    reveal_x = round(250 + 1450 * progress)
    for index, (x, label) in enumerate(milestones):
        y = 620 - index * 48
        active = x <= reveal_x
        color = palette["accent"] if active else _mix(palette["muted"], palette["background"], 0.55)
        draw.line((x, y, x, y - 105), fill=color, width=4)
        draw.ellipse((x - 12, y - 12, x + 12, y + 12), fill=color)
        engine._text(draw, (x - 45, y - 145), label, 18, color, bold=True)
    _person(draw, reveal_x, 970, 0.82, palette, facing=1)
    engine._text(draw, (1220, 850), "ESTIMATE  ≠  CERTAINTY", 28, palette["warning"], bold=True)


def render_digital_footprint_collector(draw, progress, palette) -> None:
    _ambient(draw, palette, progress)
    _person(draw, 1420, 970, 1.25, palette, facing=1)
    # Luminous footprints and fragments show accumulation as a physical trail.
    for index in range(11):
        phase = max(0.0, min(1.0, progress * 1.28 - index * 0.065))
        x = 180 + index * 108
        y = 890 - round(index * 38 + 55 * math.sin(index * 0.8))
        size = 13 + index
        color = _mix(palette["accent_alt"], palette["accent"], phase)
        draw.ellipse((x - size, y - size // 2, x + size, y + size // 2), fill=color)
        if phase > 0.55:
            draw.line((x, y - 20, x + 60, y - 85), fill=_mix(color, palette["background"], 0.42), width=2)
    fragments = round(5 + 28 * progress)
    for index in range(fragments):
        x = 260 + (index * 83) % 1050
        y = 280 + (index * 59) % 480
        draw.rectangle((x, y, x + 5 + index % 9, y + 3), fill=palette["accent"] if index % 2 else palette["accent_alt"])
    engine._text(draw, (120, 760), "EVERY ACTION LEAVES A TRACE", 28, palette["white"], bold=True)


def render_behavioral_twin(draw, progress, palette) -> None:
    _ambient(draw, palette, progress)
    # A mirror relationship communicates modeling more cinematically than two cards.
    mirror = (1010, 245, 1775, 965)
    draw.rounded_rectangle(mirror, radius=28, fill=_mix(palette["panel"], palette["background"], 0.25), outline=_mix(palette["accent"], palette["white"], 0.15), width=4)
    for index in range(8):
        x = 1060 + index * 86
        draw.line((x, 270, x - 80, 940), fill=_mix(palette["accent_alt"], palette["background"], 0.76), width=2)
    _person(draw, 700, 975, 1.45, palette, facing=1)
    twin_x = 1390 + round(45 * math.sin(progress * math.pi))
    _person(draw, twin_x, 975, 1.45, palette, facing=-1, digital=True)
    for index in range(round(14 * progress)):
        x = 860 + (index * 47) % 350
        y = 370 + (index * 73) % 440
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=palette["accent"])
    engine._text(draw, (1080, 890), "A MODEL LEARNS YOUR NEXT MOVE", 25, palette["muted"], bold=True)


def render_machine_choice_explainer(draw, progress, palette) -> None:
    _ambient(draw, palette, progress)
    # Over-the-shoulder observation makes the viewer's action the subject.
    _person(draw, 390, 1080, 1.6, palette, facing=1)
    _phone(draw, (780, 245, 1220, 980), palette, progress, selected=progress > 0.52)
    for index in range(9):
        x = 1330 + (index % 3) * 150
        y = 335 + (index // 3) * 160
        intensity = max(0.0, min(1.0, progress * 1.2 - index * 0.06))
        fill = palette["good"] if index == 4 and progress > 0.58 else _mix(palette["panel_alt"], palette["background"], 0.42)
        draw.rounded_rectangle((x, y, x + 105, y + 78), radius=14, fill=_mix(fill, palette["accent_alt"], 0.12 * intensity))
    if progress > 0.58:
        draw.line((1382, 573, 1220, 610), fill=palette["good"], width=5)
        engine._text(draw, (1340, 705), "RANKED FIRST", 24, palette["good"], bold=True)
    engine._text(draw, (1325, 275), "MANY HIDDEN OPTIONS", 21, palette["muted"], bold=True)


def render_machine_choice_cta(draw, progress, palette) -> None:
    _ambient(draw, palette, progress, warmth=0.45)
    # Finish with a human-scale horizon, then reveal engagement actions.
    draw.rectangle((0, 730, WIDTH, 1080), fill=_mix(palette["background"], (4, 7, 12), 0.55))
    _person(draw, 1460, 1010, 1.05, palette, facing=-1)
    engine._text(draw, (120, 380), "YOUR ACTIONS BECOME PREDICTIONS.", 46, palette["white"], bold=True)
    engine._text(draw, (120, 448), "PREDICTIONS SHAPE WHAT REACHES YOU NEXT.", 27, palette["muted"], bold=True)
    reveal = max(0.0, min(1.0, (progress - 0.48) / 0.32))
    if reveal > 0.02:
        red = _mix(palette["background"], (220, 40, 48), reveal)
        blue = _mix(palette["background"], (45, 105, 220), reveal)
        draw.rounded_rectangle((120, 610, 470, 690), radius=20, fill=red)
        engine._text(draw, (295, 650), "SUBSCRIBE", 27, palette["white"], bold=True, anchor="mm")
        draw.rounded_rectangle((500, 610, 760, 690), radius=40, fill=blue)
        engine._text(draw, (630, 650), "LIKE", 27, palette["white"], bold=True, anchor="mm")


CINEMATIC_RENDERERS = {
    "algorithm_chose_you": render_algorithm_chose_you,
    "behavior_prediction_engine": render_behavior_prediction_engine,
    "life_event_timeline": render_life_event_timeline,
    "digital_footprint_collector": render_digital_footprint_collector,
    "behavioral_twin": render_behavioral_twin,
    "machine_choice_explainer": render_machine_choice_explainer,
    "machine_choice_cta": render_machine_choice_cta,
}

cinematic_common = _minimal_common
cinematic_beat_indicator = _quiet_beat_indicator
