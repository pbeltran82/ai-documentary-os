from __future__ import annotations

import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageDraw

from ..models import Scene
from . import finance_motion as engine
from . import finance_motion_art as art
from . import engagement_cta as engagement
from .media_library import MEDIA_ROOT, project_directory, public_media_url, safe_component
from .video_format import (
    format_exact_visual_frame,
    project_video_format,
    video_format_profile,
)


@dataclass(frozen=True)
class TechTemplate:
    template_id: str
    label: str
    description: str
    keywords: tuple[str, ...]
    title: str
    subtitle: str


@dataclass(frozen=True)
class TechDirectedMotion:
    template: TechTemplate
    style: art.MotionStyle
    media_path: Path
    preview_path: Path
    media_relative_path: str
    preview_relative_path: str
    media_url: str
    preview_url: str
    content_type: str
    size_bytes: int
    checksum_sha256: str
    duration_seconds: float
    width: int
    height: int
    video_format: str


TEMPLATES = (
    TechTemplate(
        "algorithm_chose_you",
        "Algorithm Chose You",
        "Show a recommendation system ranking one viewer and one video into the same moment.",
        tuple("algorithm recommendation recommended feed ranked ranking watch video choice choose today viewer".split()),
        "THE ALGORITHM CHOSE THE MOMENT",
        "Thousands of possibilities. One ranked outcome.",
    ),
    TechTemplate(
        "behavior_prediction_engine",
        "Behavior Prediction Engine",
        "Turn scrolls, pauses, clicks, and drafts into a visible prediction pipeline.",
        tuple("predict predicting prediction behavior scroll pause click draft signal model artificial intelligence ai".split()),
        "BEHAVIOR BECOMES A PREDICTION",
        "Signals enter. Probabilities come out.",
    ),
    TechTemplate(
        "life_event_timeline",
        "Life-Event Timeline",
        "Visualize a model estimating future life events from accumulated records.",
        tuple("job jobs sick sickness health die death mortality life event timeline records researchers 2018".split()),
        "A MODEL OF WHAT HAPPENS NEXT",
        "Past records become estimates of future events.",
    ),
    TechTemplate(
        "digital_footprint_collector",
        "Digital Footprint Collector",
        "Collect everyday interactions into an expanding behavioral data trail.",
        tuple("digital footprint every scroll pause click deleted abandoned draft track tracking data signal".split()),
        "YOUR FOOTPRINT NEVER STOPS GROWING",
        "Every interaction leaves another behavioral signal.",
    ),
    TechTemplate(
        "behavioral_twin",
        "Behavioral Twin",
        "Build a predictive digital counterpart from a person's repeated signals.",
        tuple("digital twin behavioral version profile identity model targeting bidder sold anticipate next".split()),
        "THE MODEL BESIDE YOU",
        "A behavioral twin estimates what you may do next.",
    ),
    TechTemplate(
        "machine_choice_explainer",
        "Machine Choice Explainer",
        "Contrast one visible viewer action with the hidden ranking field behind it.",
        tuple("choose choice machine ranked ranking opportunity invisible decision recommendation click play".split()),
        "THE RANKING BEHIND THE CHOICE",
        "One visible action. A field of hidden scores.",
    ),
    TechTemplate(
        "machine_choice_cta",
        "Machine Choice CTA",
        "End on the unresolved question, then land on clear Like and Subscribe actions.",
        tuple("choose choice machine subscribe like support awake watch moment final question".split()),
        "WHO CHOSE THIS MOMENT?",
        "You pressed play. The machine ranked the opportunity.",
    ),
)
TEMPLATE_BY_ID = {template.template_id: template for template in TEMPLATES}

DEFAULT_STYLE_ID = art.DEFAULT_STYLE_ID
STYLES = art.STYLES
OUTPUT_WIDTH = engine.OUTPUT_WIDTH
OUTPUT_HEIGHT = engine.OUTPUT_HEIGHT
OUTPUT_FPS = engine.OUTPUT_FPS
ffmpeg_encoder_command = art.ffmpeg_encoder_command
style_catalog = art.style_catalog


BEATS_BY_TEMPLATE = {
    "algorithm_chose_you": (
        ("POSSIBILITIES", "Establish the crowded recommendation field.", 0.16),
        ("RANKING", "Score and narrow the feed around one viewer.", 0.52),
        ("SELECTED", "Land on the exact video placed in front of the viewer.", 0.86),
    ),
    "behavior_prediction_engine": (
        ("SIGNALS", "Introduce the behavioral inputs.", 0.16),
        ("MODEL", "Combine the inputs inside the prediction engine.", 0.52),
        ("PROBABILITY", "Output the predicted next action.", 0.86),
    ),
    "life_event_timeline": (
        ("RECORDS", "Establish the accumulated life records.", 0.16),
        ("ESTIMATES", "Place model estimates along the timeline.", 0.53),
        ("FUTURE", "Reveal the uncertainty attached to future events.", 0.86),
    ),
    "digital_footprint_collector": (
        ("INTERACTIONS", "Show ordinary digital behavior.", 0.16),
        ("COLLECTION", "Stream every signal into the profile.", 0.52),
        ("FOOTPRINT", "Reveal the growing behavioral record.", 0.86),
    ),
    "behavioral_twin": (
        ("PERSON", "Establish the human source.", 0.16),
        ("MODELING", "Transfer repeated signals into the twin.", 0.52),
        ("ANTICIPATION", "Show the twin estimating the next action.", 0.86),
    ),
    "machine_choice_explainer": (
        ("ACTION", "Establish the viewer's visible play decision.", 0.16),
        ("RANKING FIELD", "Reveal the hidden alternatives and model scores.", 0.52),
        ("SELECTED", "Connect the visible action to the ranked opportunity.", 0.86),
    ),
    "machine_choice_cta": (
        ("YOUR CHOICE", "Begin with the viewer's visible action.", 0.16),
        ("MACHINE RANK", "Reveal the ranking system behind the opportunity.", 0.52),
        ("LIKE + SUBSCRIBE", "Finish on two clear engagement actions.", 0.86),
    ),
}


CAMERA_PROFILES = {
    "algorithm_chose_you": ((0.30, 0.52), (0.70, 0.52), 0.014),
    "behavior_prediction_engine": ((0.28, 0.54), (0.72, 0.50), 0.012),
    "life_event_timeline": ((0.24, 0.55), (0.76, 0.50), 0.012),
    "digital_footprint_collector": ((0.30, 0.58), (0.70, 0.48), 0.014),
    "behavioral_twin": ((0.30, 0.54), (0.70, 0.52), 0.014),
    "machine_choice_explainer": ((0.34, 0.52), (0.66, 0.50), 0.014),
    "machine_choice_cta": ((0.42, 0.52), (0.58, 0.50), 0.018),
}


def _words(value: str) -> set[str]:
    return {
        "".join(character for character in token.lower() if character.isalnum())
        for token in value.split()
    } - {""}


def template_catalog() -> list[dict[str, object]]:
    return [
        {
            "template_id": template.template_id,
            "label": template.label,
            "description": template.description,
        }
        for template in TEMPLATES
    ]


def score_templates(scene: Scene) -> list[tuple[int, TechTemplate]]:
    context = " ".join([scene.narration, scene.visual_intent, *scene.search_keywords])
    words = _words(context)
    scored = [(len(words & set(template.keywords)), template) for template in TEMPLATES]
    scored.sort(key=lambda pair: (pair[0], pair[1].template_id), reverse=True)
    return scored


def suggest_template(scene: Scene) -> tuple[TechTemplate, float, str]:
    matched, template = score_templates(scene)[0]
    confidence = min(0.98, 0.52 + matched * 0.075)
    reason = (
        f"Matched {matched} technology and behavior signal"
        f"{'s' if matched != 1 else ''} in the scene brief."
        if matched
        else "Selected as the safest general algorithmic-behavior composition."
    )
    return template, round(confidence, 2), reason


def storyboard_beats(template_id: str, duration_seconds: float) -> list[dict[str, object]]:
    if template_id not in TEMPLATE_BY_ID:
        raise HTTPException(status_code=422, detail="Unknown tech and behavior template")
    duration = max(1.0, float(duration_seconds))
    return [
        {
            "label": label,
            "description": description,
            "time_seconds": round(min(duration - 0.04, max(0.08, duration * fraction)), 3),
        }
        for label, description, fraction in BEATS_BY_TEMPLATE[template_id]
    ]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _ease(value: float) -> float:
    value = _clamp(value)
    return value * value * (3 - 2 * value)


def _phase(progress: float, start: float, end: float) -> float:
    return _ease((progress - start) / max(0.001, end - start))


def _palette(style_id: str) -> dict[str, tuple[int, int, int]]:
    if style_id == "clean_infographic":
        return {
            "background": (7, 20, 35),
            "panel": (12, 31, 50),
            "panel_alt": (17, 42, 63),
            "accent": (56, 189, 248),
            "accent_alt": (45, 212, 191),
            "good": (52, 211, 153),
            "warning": (245, 158, 11),
            "bad": (248, 113, 113),
            "white": (248, 250, 252),
            "muted": (148, 163, 184),
            "ink": (6, 20, 31),
        }
    if style_id == "editorial_documentary":
        return {
            "background": (10, 15, 25),
            "panel": (20, 27, 39),
            "panel_alt": (34, 42, 54),
            "accent": (214, 168, 95),
            "accent_alt": (129, 140, 158),
            "good": (112, 169, 148),
            "warning": (214, 168, 95),
            "bad": (190, 104, 104),
            "white": (232, 236, 242),
            "muted": (156, 164, 177),
            "ink": (13, 18, 26),
        }
    return {
        "background": (7, 10, 28),
        "panel": (15, 20, 48),
        "panel_alt": (24, 31, 70),
        "accent": (34, 211, 238),
        "accent_alt": (139, 92, 246),
        "good": (52, 211, 153),
        "warning": (245, 190, 73),
        "bad": (251, 113, 133),
        "white": (248, 250, 252),
        "muted": (159, 171, 193),
        "ink": (7, 12, 27),
    }


def _base_frame(style_id: str, time_seconds: float) -> Image.Image:
    palette = _palette(style_id)
    image = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), palette["background"])
    draw = ImageDraw.Draw(image)
    offset = round((time_seconds * 18) % 120)
    for x in range(-120 + offset, OUTPUT_WIDTH + 120, 120):
        draw.line((x, 0, x, OUTPUT_HEIGHT), fill=palette["panel_alt"], width=1)
    for y in range(0, OUTPUT_HEIGHT, 120):
        draw.line((0, y, OUTPUT_WIDTH, y), fill=palette["panel_alt"], width=1)
    for index in range(14):
        x = (index * 173 + offset * 2) % OUTPUT_WIDTH
        y = 300 + (index * 89) % 650
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=palette["accent_alt"])
    return image


def _panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    palette: dict[str, tuple[int, int, int]],
    *,
    outline: tuple[int, int, int] | None = None,
    radius: int = 26,
) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(
        (left + 12, top + 14, right + 12, bottom + 14),
        radius=radius,
        fill=(2, 5, 14),
    )
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=palette["panel"],
        outline=outline or palette["panel_alt"],
        width=3,
    )


def _pill(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    value: str,
    palette: dict[str, tuple[int, int, int]],
    *,
    fill: tuple[int, int, int] | None = None,
    width: int = 250,
    text_fill: tuple[int, int, int] | None = None,
) -> None:
    x, y = center
    draw.rounded_rectangle(
        (x - width // 2, y - 29, x + width // 2, y + 29),
        radius=29,
        fill=fill or palette["panel_alt"],
    )
    engine._text(
        draw,
        center,
        value,
        22,
        text_fill or palette["white"],
        bold=True,
        anchor="mm",
    )


def _node(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
    *,
    label: str = "",
) -> None:
    x, y = center
    draw.ellipse((x - radius - 8, y - radius - 8, x + radius + 8, y + radius + 8), outline=color, width=2)
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    if label:
        engine._text(draw, center, label, max(15, radius // 2), (5, 12, 24), bold=True, anchor="mm")


def _phone(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], palette: dict[str, tuple[int, int, int]]) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(box, radius=42, fill=(4, 8, 19), outline=palette["accent"], width=4)
    draw.rounded_rectangle((left + 24, top + 55, right - 24, bottom - 38), radius=22, fill=palette["panel"])
    draw.rounded_rectangle(((left + right) // 2 - 50, top + 18, (left + right) // 2 + 50, top + 30), radius=6, fill=palette["muted"])


def _person_wireframe(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    palette: dict[str, tuple[int, int, int]],
    *,
    digital: bool = False,
) -> None:
    x, y = center
    color = palette["accent"] if digital else palette["white"]
    draw.ellipse((x - 58, y - 210, x + 58, y - 94), outline=color, width=8)
    draw.line((x, y - 92, x, y + 100), fill=color, width=10)
    draw.line((x, y - 45, x - 95, y + 15), fill=color, width=9)
    draw.line((x, y - 45, x + 95, y + 15), fill=color, width=9)
    draw.line((x, y + 98, x - 70, y + 210), fill=color, width=10)
    draw.line((x, y + 98, x + 70, y + 210), fill=color, width=10)
    if digital:
        for offset in (-35, 0, 35):
            draw.line((x - 45, y + offset, x + 45, y + offset), fill=palette["accent_alt"], width=2)


def _common(
    draw: ImageDraw.ImageDraw,
    template: TechTemplate,
    palette: dict[str, tuple[int, int, int]],
    progress: float,
) -> None:
    _pill(draw, (220, 105), "TECH & BEHAVIOR", palette, fill=palette["panel_alt"], width=260, text_fill=palette["accent"])
    engine._text(draw, (110, 155), template.title, 58, palette["white"], bold=True)
    engine._text(draw, (112, 225), template.subtitle, 28, palette["muted"])
    draw.rounded_rectangle((112, 278, 620, 286), radius=4, fill=palette["panel_alt"])
    draw.rounded_rectangle((112, 278, 112 + round(508 * progress), 286), radius=4, fill=palette["accent"])


def _algorithm_chose_you(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    rank = _phase(progress, 0.12, 0.62)
    selection = _phase(progress, 0.55, 0.90)
    _panel(draw, (100, 350, 610, 930), palette, outline=palette["accent_alt"])
    _phone(draw, (210, 390, 500, 885), palette)
    for index in range(5):
        y = 485 + index * 72
        active = index == 2
        draw.rounded_rectangle(
            (245, y, 465, y + 48),
            radius=13,
            fill=palette["accent"] if active and selection > 0.35 else palette["panel_alt"],
        )
        engine._text(draw, (270, y + 13), f"VIDEO {index + 1}", 16, palette["ink"] if active and selection > 0.35 else palette["muted"], bold=True)

    _panel(draw, (690, 350, 1220, 930), palette, outline=palette["accent"])
    engine._text(draw, (955, 395), "RANKING ENGINE", 27, palette["accent"], bold=True, anchor="mm")
    candidates = 12 - round(rank * 11)
    for row in range(4):
        for column in range(3):
            index = row * 3 + column
            x = 790 + column * 160
            y = 500 + row * 105
            visible = index < candidates or index == 0
            _node(draw, (x, y), 18 if visible else 10, palette["accent_alt"] if visible else palette["panel_alt"])
    for y in (500, 605, 710, 815):
        draw.line((815, y, 1090, 650), fill=palette["accent"], width=2)
    _node(draw, (1110, 650), 42, palette["good"], label="1")

    _panel(draw, (1300, 350, 1820, 930), palette, outline=palette["good"])
    engine._text(draw, (1560, 395), "PLACED IN YOUR FEED", 25, palette["good"], bold=True, anchor="mm")
    draw.rounded_rectangle((1390, 485, 1730, 690), radius=24, fill=palette["panel_alt"], outline=palette["accent"], width=3)
    play_radius = 45 + round(10 * math.sin(progress * math.pi * 8))
    draw.ellipse((1560 - play_radius, 588 - play_radius, 1560 + play_radius, 588 + play_radius), fill=palette["accent"])
    draw.polygon(((1548, 560), (1548, 616), (1592, 588)), fill=palette["ink"])
    confidence = round(51 + 48 * selection)
    _pill(draw, (1560, 770), f"MATCH {confidence}%", palette, fill=palette["good"], width=260, text_fill=palette["ink"])
    if selection > 0.72:
        engine._text(draw, (1560, 850), "YOU + THIS VIDEO + THIS MOMENT", 20, palette["white"], bold=True, anchor="mm")


def _behavior_prediction_engine(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    collect = _phase(progress, 0.08, 0.48)
    infer = _phase(progress, 0.42, 0.86)
    signals = (("SCROLL", "1.8s"), ("PAUSE", "4.2s"), ("CLICK", "YES"), ("DRAFT", "DELETED"))
    for index, (label, value) in enumerate(signals):
        y = 405 + index * 126
        _panel(draw, (110, y, 520, y + 94), palette, outline=palette["accent_alt"])
        engine._text(draw, (145, y + 20), label, 20, palette["muted"], bold=True)
        engine._text(draw, (470, y + 47), value, 26, palette["accent"], bold=True, anchor="rm")
        local = _phase(collect, index * 0.16, min(1.0, index * 0.16 + 0.45))
        x = round(520 + (765 - 520) * local)
        _node(draw, (x, y + 47), 14, palette["accent"])
        draw.line((520, y + 47, 765, 610), fill=palette["accent_alt"], width=3)

    _panel(draw, (760, 385, 1210, 850), palette, outline=palette["accent"])
    engine._text(draw, (985, 425), "PREDICTION MODEL", 27, palette["accent"], bold=True, anchor="mm")
    nodes = ((875, 525), (1095, 525), (820, 650), (985, 690), (1150, 650))
    for index, center in enumerate(nodes):
        pulse = 22 + round(8 * math.sin(progress * 10 + index))
        _node(draw, center, pulse, palette["accent_alt"] if index % 2 else palette["accent"])
    links = ((0, 3), (1, 3), (2, 3), (4, 3), (0, 1), (2, 4))
    for start, end in links:
        draw.line((*nodes[start], *nodes[end]), fill=palette["muted"], width=3)

    _panel(draw, (1290, 385, 1810, 850), palette, outline=palette["good"])
    engine._text(draw, (1550, 425), "NEXT ACTION", 25, palette["good"], bold=True, anchor="mm")
    probability = round(34 + 63 * infer)
    engine._text(draw, (1550, 590), f"{probability}%", 105, palette["white"], bold=True, anchor="mm")
    engine._text(draw, (1550, 680), "WATCH TO THE END", 25, palette["accent"], bold=True, anchor="mm")
    draw.rounded_rectangle((1370, 755, 1730, 775), radius=10, fill=palette["panel_alt"])
    draw.rounded_rectangle((1370, 755, 1370 + round(360 * infer), 775), radius=10, fill=palette["good"])


def _life_event_timeline(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    reveal = _phase(progress, 0.12, 0.82)
    _panel(draw, (100, 365, 1820, 900), palette, outline=palette["accent_alt"])
    baseline_y = 660
    draw.line((200, baseline_y, 1720, baseline_y), fill=palette["muted"], width=5)
    events = (
        (300, "DIGITAL RECORDS", "PAST", palette["accent"]),
        (700, "JOB CHANGE", "ESTIMATE", palette["warning"]),
        (1110, "HEALTH EVENT", "ESTIMATE", palette["bad"]),
        (1530, "LONGEVITY", "ESTIMATE", palette["good"]),
    )
    for index, (x, label, category, color) in enumerate(events):
        local = _phase(reveal, index * 0.18, min(1.0, index * 0.18 + 0.42))
        draw.line((x, baseline_y, x, baseline_y - round(130 * local)), fill=color, width=5)
        _node(draw, (x, baseline_y), 19, color)
        if local > 0.25:
            _panel(draw, (x - 145, 430, x + 145, 565), palette, outline=color, radius=18)
            engine._text(draw, (x, 465), category, 16, palette["muted"], bold=True, anchor="mm")
            engine._text(draw, (x, 515), label, 21, color, bold=True, anchor="mm")
    cursor_x = round(200 + 1520 * reveal)
    draw.line((cursor_x, 405, cursor_x, 825), fill=palette["accent"], width=3)
    _pill(draw, (cursor_x, 825), "MODEL TIME", palette, fill=palette["panel_alt"], width=180, text_fill=palette["accent"])
    engine._text(draw, (960, 855), "ESTIMATE ≠ CERTAINTY", 24, palette["warning"], bold=True, anchor="mm")


def _digital_footprint_collector(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    stream = _phase(progress, 0.08, 0.76)
    _phone(draw, (120, 365, 530, 910), palette)
    interactions = ("SCROLL", "PAUSE", "CLICK", "DELETE")
    for index, label in enumerate(interactions):
        y = 475 + index * 92
        draw.rounded_rectangle((185, y, 465, y + 58), radius=14, fill=palette["panel_alt"])
        engine._text(draw, (325, y + 29), label, 20, palette["accent"], bold=True, anchor="mm")
        local = _phase(stream, index * 0.16, min(1.0, index * 0.16 + 0.42))
        x = round(530 + 500 * local)
        _node(draw, (x, y + 29), 13, palette["accent_alt"])
        draw.line((530, y + 29, 1050, 640), fill=palette["accent_alt"], width=3)

    _panel(draw, (1040, 365, 1810, 910), palette, outline=palette["accent"])
    engine._text(draw, (1425, 405), "BEHAVIORAL RECORD", 27, palette["accent"], bold=True, anchor="mm")
    layers = 3 + round(11 * stream)
    for index in range(layers):
        y = 500 + index * 25
        width = 300 + (index % 4) * 80
        draw.rounded_rectangle((1180, y, 1180 + width, y + 14), radius=7, fill=palette["accent_alt"] if index % 2 else palette["accent"])
    signal_count = round(127 + 9873 * stream)
    engine._text(draw, (1425, 805), f"{signal_count:,}", 72, palette["white"], bold=True, anchor="mm")
    engine._text(draw, (1425, 865), "ACCUMULATED SIGNALS", 20, palette["muted"], bold=True, anchor="mm")


def _behavioral_twin(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    transfer = _phase(progress, 0.12, 0.68)
    anticipate = _phase(progress, 0.62, 0.90)
    _panel(draw, (100, 360, 700, 920), palette, outline=palette["white"])
    _person_wireframe(draw, (400, 645), palette)
    engine._text(draw, (400, 865), "YOU", 26, palette["white"], bold=True, anchor="mm")

    _panel(draw, (1220, 360, 1820, 920), palette, outline=palette["accent"])
    _person_wireframe(draw, (1520, 645), palette, digital=True)
    engine._text(draw, (1520, 865), "BEHAVIORAL TWIN", 26, palette["accent"], bold=True, anchor="mm")

    signals = ("SEARCH", "PAUSE", "PURCHASE", "DRAFT")
    for index, label in enumerate(signals):
        y = 450 + index * 115
        local = _phase(transfer, index * 0.14, min(1.0, index * 0.14 + 0.42))
        x = round(700 + 520 * local)
        draw.line((700, y, 1220, y), fill=palette["panel_alt"], width=3)
        _pill(draw, (x, y), label, palette, fill=palette["accent_alt"], width=150, text_fill=palette["white"])

    if anticipate > 0.15:
        _pill(draw, (960, 810), f"NEXT ACTION {round(41 + 55 * anticipate)}%", palette, fill=palette["good"], width=340, text_fill=palette["ink"])
    engine._text(draw, (960, 405), "SIGNALS BECOME A PREDICTIVE COUNTERPART", 22, palette["muted"], bold=True, anchor="mm")


MACHINE_CHOICE_BAR_START_Y = 490
MACHINE_CHOICE_BAR_STEP_Y = 31
MACHINE_CHOICE_BAR_HEIGHT = 16
MACHINE_CHOICE_LABEL_Y = 735


def _machine_choice_cta(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    reveal = _phase(progress, 0.12, 0.72)
    subscribe_reveal = _phase(progress, 0.42, 0.72)
    like_reveal = _phase(progress, 0.66, 0.90)
    _panel(draw, (130, 365, 860, 790), palette, outline=palette["white"])
    engine._text(draw, (495, 430), "YOU CHOSE", 31, palette["white"], bold=True, anchor="mm")
    _node(draw, (495, 570), 72, palette["white"], label="PLAY")
    engine._text(draw, (495, 710), "VISIBLE ACTION", 24, palette["muted"], bold=True, anchor="mm")

    _panel(draw, (1060, 365, 1790, 790), palette, outline=palette["accent"])
    engine._text(draw, (1425, 430), "MACHINE RANKED", 31, palette["accent"], bold=True, anchor="mm")
    for index in range(7):
        width = round((110 + index * 33) * reveal)
        y = MACHINE_CHOICE_BAR_START_Y + index * MACHINE_CHOICE_BAR_STEP_Y
        draw.rounded_rectangle((1190, y, 1190 + width, y + 16), radius=8, fill=palette["accent_alt"] if index < 6 else palette["good"])
    engine._text(draw, (1425, MACHINE_CHOICE_LABEL_Y), "INVISIBLE OPPORTUNITY", 24, palette["muted"], bold=True, anchor="mm")

    engine._text(draw, (960, 820), "SUPPORT THE NEXT STORY", 24, palette["muted"], bold=True, anchor="mm")
    engagement.draw_subscribe_like(
        draw,
        subscribe_center=(790, 910),
        like_center=(1215, 910),
        subscribe_reveal=subscribe_reveal,
        like_reveal=like_reveal,
        pulse=(math.sin(progress * math.pi * 6) + 1) / 2,
        subscribe_scale=0.78,
        like_scale=0.88,
    )


def _machine_choice_explainer(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    reveal = _phase(progress, 0.10, 0.74)
    selection = _phase(progress, 0.58, 0.90)

    _panel(draw, (110, 375, 660, 865), palette, outline=palette["white"])
    engine._text(draw, (385, 430), "VISIBLE ACTION", 29, palette["white"], bold=True, anchor="mm")
    _node(draw, (385, 610), 72, palette["white"], label="PLAY")
    _pill(
        draw,
        (385, 770),
        "ONE DECISION",
        palette,
        fill=palette["panel_alt"],
        width=270,
        text_fill=palette["muted"],
    )

    _panel(draw, (820, 350, 1810, 885), palette, outline=palette["accent"])
    engine._text(draw, (1315, 405), "HIDDEN RANKING FIELD", 29, palette["accent"], bold=True, anchor="mm")
    candidate_y = (500, 565, 630, 695, 760)
    for index, y in enumerate(candidate_y):
        local = _phase(reveal, index * 0.10, min(1.0, index * 0.10 + 0.42))
        bar_width = round((160 + index * 75) * local)
        color = palette["good"] if index == 3 and selection > 0.35 else palette["accent_alt"]
        _node(draw, (930, y), 13, color)
        draw.rounded_rectangle(
            (980, y - 10, 980 + bar_width, y + 10),
            radius=10,
            fill=color,
        )
        engine._text(
            draw,
            (1690, y),
            f"{round((0.54 + index * 0.08) * 100)}",
            22,
            palette["muted"],
            bold=True,
            anchor="mm",
        )
    cursor_x = round(980 + 520 * selection)
    draw.line((cursor_x, 465, cursor_x, 810), fill=palette["good"], width=4)
    _pill(
        draw,
        (1315, 830),
        "OPPORTUNITY SELECTED" if selection > 0.55 else "SCORING OPPORTUNITIES",
        palette,
        fill=palette["good"] if selection > 0.55 else palette["panel_alt"],
        width=390,
        text_fill=palette["ink"] if selection > 0.55 else palette["muted"],
    )

    draw.line((680, 610, 790, 610), fill=palette["accent"], width=7)
    draw.polygon(((790, 610), (760, 590), (760, 630)), fill=palette["accent"])
    engine._text(
        draw,
        (960, 940),
        "ONE CLICK • MANY HIDDEN SCORES",
        27,
        palette["warning"],
        bold=True,
        anchor="mm",
    )


RENDERERS = {
    "algorithm_chose_you": _algorithm_chose_you,
    "behavior_prediction_engine": _behavior_prediction_engine,
    "life_event_timeline": _life_event_timeline,
    "digital_footprint_collector": _digital_footprint_collector,
    "behavioral_twin": _behavioral_twin,
    "machine_choice_explainer": _machine_choice_explainer,
    "machine_choice_cta": _machine_choice_cta,
}


def _camera_move(image: Image.Image, template_id: str, progress: float) -> Image.Image:
    start, end, zoom_amount = CAMERA_PROFILES[template_id]
    eased = _ease(progress)
    zoom = 1 + zoom_amount * eased
    width, height = image.size
    scaled_width = max(width, round(width * zoom))
    scaled_height = max(height, round(height * zoom))
    scaled = image.resize((scaled_width, scaled_height), Image.Resampling.BILINEAR)
    focus_x = start[0] + (end[0] - start[0]) * eased
    focus_y = start[1] + (end[1] - start[1]) * eased
    left = round((scaled_width - width) * _clamp(focus_x))
    top = round((scaled_height - height) * _clamp(focus_y))
    return scaled.crop((left, top, left + width, top + height))


def _beat_indicator(
    draw: ImageDraw.ImageDraw,
    template_id: str,
    duration_seconds: float,
    time_seconds: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    beats = storyboard_beats(template_id, duration_seconds)
    active = 0
    for index, beat in enumerate(beats):
        if time_seconds >= float(beat["time_seconds"]):
            active = index
    start_x = 1490
    y = 116
    draw.line((start_x, y, start_x + 250, y), fill=palette["muted"], width=3)
    for index, _beat in enumerate(beats):
        x = start_x + index * 125
        radius = 11 if index == active else 7
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=palette["good"] if index == active else palette["muted"])
    engine._text(draw, (1770, 142), str(beats[active]["label"]), 20, palette["good"], bold=True, anchor="ra")


def render_frame(
    template_id: str,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    template = TEMPLATE_BY_ID.get(template_id)
    if template is None:
        raise HTTPException(status_code=422, detail="Unknown tech and behavior template")
    style = art.STYLE_BY_ID.get(style_id or DEFAULT_STYLE_ID)
    if style is None:
        raise HTTPException(status_code=422, detail="Unknown exact visual style")
    duration = max(1.0, float(duration_seconds))
    time_value = max(0.0, min(float(time_seconds), duration))
    progress = time_value / duration
    palette = _palette(style.style_id)
    image = _base_frame(style.style_id, time_value)
    draw = ImageDraw.Draw(image)
    _common(draw, template, palette, progress)
    RENDERERS[template_id](draw, progress, palette)
    _beat_indicator(draw, template_id, duration, time_value, palette)
    frame = _camera_move(image, template_id, progress)
    styled = art.STYLE_RENDERERS[style.style_id](frame, time_value)
    fade_seconds = max(0.15, min(0.35, duration / 6))
    visibility = min(
        engine._clamp(time_value / fade_seconds),
        engine._clamp((duration - time_value) / fade_seconds),
    )
    if visibility < 1:
        return Image.blend(Image.new("RGB", styled.size, palette["background"]), styled, visibility)
    return styled


def _encode_frames(
    ffmpeg: str,
    template: TechTemplate,
    style: art.MotionStyle,
    duration_seconds: float,
    output_path: Path,
    video_format: str = "youtube",
) -> None:
    profile = video_format_profile(video_format)
    process = subprocess.Popen(
        ffmpeg_encoder_command(ffmpeg, output_path, profile.width, profile.height),
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    frame_count = max(1, math.ceil(duration_seconds * OUTPUT_FPS))
    code = -1
    try:
        assert process.stdin is not None
        for index in range(frame_count):
            frame = render_frame(
                template.template_id,
                duration_seconds,
                min(duration_seconds, index / OUTPUT_FPS),
                style.style_id,
            )
            process.stdin.write(
                format_exact_visual_frame(
                    frame,
                    video_format,
                    "tech_behavior_motion",
                    template.template_id,
                ).tobytes()
            )
        process.stdin.close()
        code = process.wait(timeout=engine.RENDER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        raise HTTPException(status_code=504, detail="Tech and behavior motion render timed out") from exc
    except BrokenPipeError as exc:
        process.kill()
        process.wait()
        error = engine._compact_error(process.stderr.read() if process.stderr else None)
        raise HTTPException(status_code=500, detail=f"Tech motion encoder stopped unexpectedly: {error}") from exc
    finally:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
    if code != 0:
        error = engine._compact_error(process.stderr.read() if process.stderr else None)
        raise HTTPException(status_code=500, detail=f"Tech motion encoder failed: {error}")


def render_tech_motion(
    scene: Scene,
    template_id: str | None = None,
    style_id: str | None = None,
) -> TechDirectedMotion:
    template = TEMPLATE_BY_ID.get(template_id or "")
    if template is None:
        template, _confidence, _reason = suggest_template(scene)
    style = art.STYLE_BY_ID.get(style_id or DEFAULT_STYLE_ID)
    if style is None:
        raise HTTPException(status_code=422, detail="Unknown exact visual style")
    ffmpeg = shutil.which(engine.FFMPEG_NAME)
    if ffmpeg is None:
        raise HTTPException(status_code=422, detail="FFmpeg is required to encode Tech & Behavior Motion videos.")

    duration = round(max(1.0, float(scene.duration_seconds)), 3)
    video_format = project_video_format(scene)
    profile = video_format_profile(video_format)
    asset_directory = project_directory(scene.project_id) / "assets"
    asset_directory.mkdir(parents=True, exist_ok=True)
    stem = asset_directory / (
        f"scene-{scene.scene_number:03d}-tech-"
        f"{safe_component(template.template_id)}-{safe_component(style.style_id)}-"
        f"{video_format}"
    )
    media_path = stem.with_suffix(".mp4")
    preview_path = Path(f"{stem}-poster.jpg")
    temporary_media = Path(f"{media_path}.part.mp4")
    temporary_preview = Path(f"{preview_path}.part.jpg")
    temporary_media.unlink(missing_ok=True)
    temporary_preview.unlink(missing_ok=True)

    try:
        _encode_frames(ffmpeg, template, style, duration, temporary_media, video_format)
        poster_time = min(max(0.8, duration * 0.55), max(0.0, duration - 0.03))
        format_exact_visual_frame(
            render_frame(template.template_id, duration, poster_time, style.style_id),
            video_format,
            "tech_behavior_motion",
            template.template_id,
        ).save(
            temporary_preview,
            format="JPEG",
            quality=93,
            optimize=True,
        )
        temporary_media.replace(media_path)
        temporary_preview.replace(preview_path)
    except HTTPException:
        temporary_media.unlink(missing_ok=True)
        temporary_preview.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temporary_media.unlink(missing_ok=True)
        temporary_preview.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Tech and behavior motion render failed: {type(exc).__name__}: {exc}",
        ) from exc

    media_relative = media_path.resolve().relative_to(MEDIA_ROOT).as_posix()
    preview_relative = preview_path.resolve().relative_to(MEDIA_ROOT).as_posix()
    return TechDirectedMotion(
        template=template,
        style=style,
        media_path=media_path,
        preview_path=preview_path,
        media_relative_path=media_relative,
        preview_relative_path=preview_relative,
        media_url=public_media_url(media_relative),
        preview_url=public_media_url(preview_relative),
        content_type="video/mp4",
        size_bytes=media_path.stat().st_size,
        checksum_sha256=engine._checksum(media_path),
        duration_seconds=duration,
        width=profile.width,
        height=profile.height,
        video_format=video_format,
    )
