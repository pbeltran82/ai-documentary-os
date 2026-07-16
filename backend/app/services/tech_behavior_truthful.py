from __future__ import annotations

import math

from PIL import ImageDraw

from ..models import Scene
from . import finance_motion as engine
from . import finance_motion_art as art
from . import tech_behavior_motion as base


TEMPLATE_PHRASE_WEIGHTS: dict[str, dict[str, int]] = {
    "algorithm_chose_you": {
        "exact video would reach you": 12,
        "what reaches you": 10,
        "most likely to change your behavior": 11,
        "recommendation system": 9,
        "ranked the opportunity": 9,
    },
    "behavior_prediction_engine": {
        "predicts behavior": 14,
        "predict human behavior": 14,
        "predicting human behavior": 14,
        "prediction engine": 12,
        "predictive behavioral modeling": 14,
        "what you might do next": 10,
    },
    "life_event_timeline": {
        "life records": 13,
        "six million people": 12,
        "personality traits": 10,
        "early mortality": 12,
        "health event": 9,
        "job change": 9,
    },
    "digital_footprint_collector": {
        "every scroll": 10,
        "every pause": 10,
        "every click": 10,
        "abandoned draft": 11,
        "digital footprint": 12,
        "becomes a signal": 9,
    },
    "behavioral_twin": {
        "behavioral version of you": 15,
        "behavioral twin": 15,
        "digital twin": 15,
        "systems that learn how to navigate us": 16,
        "learn how to navigate us": 15,
        "navigate us": 12,
        "anticipate what you might do next": 12,
    },
    "machine_choice_cta": {
        "help us navigate the world": 11,
        "did you choose": 13,
        "machine choose the moment": 15,
        "subscribe if you're still awake": 14,
        "subscribe if you’re still awake": 14,
    },
}

_ORIGINAL_COMMON = base._common


def _context(scene: Scene) -> str:
    return " ".join(
        [scene.narration, scene.visual_intent, *scene.search_keywords]
    ).lower()


def score_templates(scene: Scene) -> list[tuple[int, base.TechTemplate]]:
    context = _context(scene)
    words = base._words(context)
    scored: list[tuple[int, base.TechTemplate]] = []
    for template in base.TEMPLATES:
        score = len(words & set(template.keywords))
        for phrase, weight in TEMPLATE_PHRASE_WEIGHTS.get(template.template_id, {}).items():
            if phrase in context:
                score += weight
        scored.append((score, template))
    scored.sort(key=lambda pair: (pair[0], pair[1].template_id), reverse=True)
    return scored


def suggest_template(scene: Scene) -> tuple[base.TechTemplate, float, str]:
    context = _context(scene)
    matched, template = score_templates(scene)[0]
    phrase_matches = [
        (weight, phrase)
        for phrase, weight in TEMPLATE_PHRASE_WEIGHTS.get(template.template_id, {}).items()
        if phrase in context
    ]
    if phrase_matches:
        weight, phrase = max(phrase_matches)
        confidence = min(0.98, 0.76 + weight * 0.014)
        reason = f'Direct phrase match: “{phrase}”.'
    else:
        confidence = min(0.94, 0.52 + matched * 0.075)
        reason = (
            f"Matched {matched} technology and behavior signal"
            f"{'s' if matched != 1 else ''} in the scene brief."
            if matched
            else "Selected as the safest general algorithmic-behavior composition."
        )
    return template, round(confidence, 2), reason


def prediction_confidence_state(inference_progress: float) -> tuple[str, str, float]:
    progress = base._clamp(inference_progress)
    if progress <= 0.02:
        return "LOW CONFIDENCE", "NOT ENOUGH SIGNALS", 0.18
    if progress < 0.72:
        return "MODEL UPDATING", "EVIDENCE ACCUMULATING", 0.42 + 0.34 * progress
    return "HIGH CONFIDENCE", "ILLUSTRATIVE MODEL OUTPUT", 0.92


def _truthful_common(
    draw: ImageDraw.ImageDraw,
    template: base.TechTemplate,
    palette: dict[str, tuple[int, int, int]],
    progress: float,
) -> None:
    _ORIGINAL_COMMON(draw, template, palette, progress)
    base._pill(
        draw,
        (1635, 260),
        "CONCEPTUAL VISUALIZATION",
        palette,
        fill=palette["panel_alt"],
        width=350,
        text_fill=palette["muted"],
    )


def _truthful_algorithm_chose_you(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    rank = base._phase(progress, 0.12, 0.62)
    selection = base._phase(progress, 0.55, 0.90)
    base._panel(draw, (100, 350, 610, 930), palette, outline=palette["accent_alt"])
    base._phone(draw, (210, 390, 500, 885), palette)
    for index in range(5):
        y = 485 + index * 72
        active = index == 2
        draw.rounded_rectangle(
            (245, y, 465, y + 48),
            radius=13,
            fill=palette["accent"] if active and selection > 0.35 else palette["panel_alt"],
        )
        engine._text(
            draw,
            (270, y + 13),
            f"VIDEO {index + 1}",
            16,
            palette["ink"] if active and selection > 0.35 else palette["muted"],
            bold=True,
        )

    base._panel(draw, (690, 350, 1220, 930), palette, outline=palette["accent"])
    engine._text(draw, (955, 395), "RANKING ENGINE", 27, palette["accent"], bold=True, anchor="mm")
    candidates = 12 - round(rank * 11)
    for row in range(4):
        for column in range(3):
            index = row * 3 + column
            x = 790 + column * 160
            y = 500 + row * 105
            visible = index < candidates or index == 0
            base._node(
                draw,
                (x, y),
                18 if visible else 10,
                palette["accent_alt"] if visible else palette["panel_alt"],
            )
    for y in (500, 605, 710, 815):
        draw.line((815, y, 1090, 650), fill=palette["accent"], width=2)
    base._node(draw, (1110, 650), 42, palette["good"], label="1")

    base._panel(draw, (1300, 350, 1820, 930), palette, outline=palette["good"])
    engine._text(draw, (1560, 395), "PLACED IN YOUR FEED", 25, palette["good"], bold=True, anchor="mm")
    draw.rounded_rectangle(
        (1390, 485, 1730, 690),
        radius=24,
        fill=palette["panel_alt"],
        outline=palette["accent"],
        width=3,
    )
    play_radius = 45 + round(10 * math.sin(progress * math.pi * 8))
    draw.ellipse(
        (1560 - play_radius, 588 - play_radius, 1560 + play_radius, 588 + play_radius),
        fill=palette["accent"],
    )
    draw.polygon(((1548, 560), (1548, 616), (1592, 588)), fill=palette["ink"])
    rank_label = "TOP-RANKED" if selection > 0.72 else "RANKING CANDIDATE"
    base._pill(
        draw,
        (1560, 770),
        rank_label,
        palette,
        fill=palette["good"],
        width=300,
        text_fill=palette["ink"],
    )
    if selection > 0.72:
        engine._text(
            draw,
            (1560, 850),
            "YOU + THIS VIDEO + THIS MOMENT",
            20,
            palette["white"],
            bold=True,
            anchor="mm",
        )


def _truthful_prediction_engine(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    collect = base._phase(progress, 0.08, 0.48)
    infer = base._phase(progress, 0.42, 0.86)
    signals = (("SCROLL", "1.8s"), ("PAUSE", "4.2s"), ("CLICK", "YES"), ("DRAFT", "DELETED"))
    for index, (label, value) in enumerate(signals):
        y = 405 + index * 126
        base._panel(draw, (110, y, 520, y + 94), palette, outline=palette["accent_alt"])
        engine._text(draw, (145, y + 20), label, 20, palette["muted"], bold=True)
        engine._text(draw, (470, y + 47), value, 26, palette["accent"], bold=True, anchor="rm")
        local = base._phase(collect, index * 0.16, min(1.0, index * 0.16 + 0.45))
        x = round(520 + (765 - 520) * local)
        base._node(draw, (x, y + 47), 14, palette["accent"])
        draw.line((520, y + 47, 765, 610), fill=palette["accent_alt"], width=3)

    base._panel(draw, (760, 385, 1210, 850), palette, outline=palette["accent"])
    engine._text(draw, (985, 425), "PREDICTION MODEL", 27, palette["accent"], bold=True, anchor="mm")
    nodes = ((875, 525), (1095, 525), (820, 650), (985, 690), (1150, 650))
    for index, center in enumerate(nodes):
        pulse = 22 + round(8 * math.sin(progress * 10 + index))
        base._node(draw, center, pulse, palette["accent_alt"] if index % 2 else palette["accent"])
    for start, end in ((0, 3), (1, 3), (2, 3), (4, 3), (0, 1), (2, 4)):
        draw.line((*nodes[start], *nodes[end]), fill=palette["muted"], width=3)

    base._panel(draw, (1290, 385, 1810, 850), palette, outline=palette["good"])
    engine._text(draw, (1550, 425), "NEXT ACTION", 25, palette["good"], bold=True, anchor="mm")
    label, detail, bar_progress = prediction_confidence_state(infer)
    engine._text(draw, (1550, 560), label, 44, palette["white"], bold=True, anchor="mm")
    engine._text(draw, (1550, 625), detail, 18, palette["muted"], bold=True, anchor="mm")
    engine._text(draw, (1550, 690), "WATCH TO THE END", 25, palette["accent"], bold=True, anchor="mm")
    draw.rounded_rectangle((1370, 755, 1730, 775), radius=10, fill=palette["panel_alt"])
    draw.rounded_rectangle(
        (1370, 755, 1370 + round(360 * bar_progress), 775),
        radius=10,
        fill=palette["good"],
    )


def _truthful_behavioral_twin(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    transfer = base._phase(progress, 0.12, 0.68)
    anticipate = base._phase(progress, 0.62, 0.90)
    base._panel(draw, (100, 360, 700, 920), palette, outline=palette["white"])
    base._person_wireframe(draw, (400, 645), palette)
    engine._text(draw, (400, 865), "YOU", 26, palette["white"], bold=True, anchor="mm")

    base._panel(draw, (1220, 360, 1820, 920), palette, outline=palette["accent"])
    base._person_wireframe(draw, (1520, 645), palette, digital=True)
    engine._text(draw, (1520, 865), "BEHAVIORAL TWIN", 26, palette["accent"], bold=True, anchor="mm")

    for index, label in enumerate(("SEARCH", "PAUSE", "PURCHASE", "DRAFT")):
        y = 450 + index * 115
        local = base._phase(transfer, index * 0.14, min(1.0, index * 0.14 + 0.42))
        x = round(700 + 520 * local)
        draw.line((700, y, 1220, y), fill=palette["panel_alt"], width=3)
        base._pill(draw, (x, y), label, palette, fill=palette["accent_alt"], width=150, text_fill=palette["white"])

    if anticipate > 0.15:
        state = "LIKELY" if anticipate >= 0.72 else "ESTIMATING"
        base._pill(
            draw,
            (960, 810),
            f"NEXT ACTION · {state}",
            palette,
            fill=palette["good"],
            width=390,
            text_fill=palette["ink"],
        )
    engine._text(
        draw,
        (960, 405),
        "SIGNALS BECOME A PREDICTIVE COUNTERPART",
        22,
        palette["muted"],
        bold=True,
        anchor="mm",
    )


base._common = _truthful_common
base.RENDERERS["algorithm_chose_you"] = _truthful_algorithm_chose_you
base.RENDERERS["behavior_prediction_engine"] = _truthful_prediction_engine
base.RENDERERS["behavioral_twin"] = _truthful_behavioral_twin
base.score_templates = score_templates
base.suggest_template = suggest_template

DEFAULT_STYLE_ID = base.DEFAULT_STYLE_ID
STYLES = base.STYLES
TEMPLATES = base.TEMPLATES
TEMPLATE_BY_ID = base.TEMPLATE_BY_ID
OUTPUT_WIDTH = base.OUTPUT_WIDTH
OUTPUT_HEIGHT = base.OUTPUT_HEIGHT
OUTPUT_FPS = base.OUTPUT_FPS
ffmpeg_encoder_command = base.ffmpeg_encoder_command
style_catalog = base.style_catalog
template_catalog = base.template_catalog
storyboard_beats = base.storyboard_beats
render_frame = base.render_frame
render_tech_motion = base.render_tech_motion
