from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageDraw

from ..models import Scene
from . import finance_motion as engine
from . import finance_motion_art as art
from . import finance_motion_composition as composition
from .media_library import MEDIA_ROOT, project_directory, public_media_url, safe_component

# Character Explainer v1.4 is an editorial icon-figure system for scenes where
# human behavior is the story. It deliberately shares Finance Motion Studio's
# local Pillow renderer, three house styles, ordinary H.264 encoder, and
# project-owned provenance workflow.

CHARACTER_TEMPLATES = (
    engine.MotionTemplate(
        "paycheck_arrival",
        "Paycheck Arrival",
        "A worker receives income and directs the first ten percent to the future.",
        tuple("paycheck salary paid income future self first ten percent receives".split()),
        "THE PAYCHECK ARRIVES",
        "The first decision happens before lifestyle spending",
    ),
    engine.MotionTemplate(
        "spend_first",
        "Spend First",
        "A person pays rent, groceries, and lifestyle costs until nothing remains.",
        tuple("rent groceries bills expenses lifestyle spending go out paid people".split()),
        "THE SPEND-FIRST CYCLE",
        "Income arrives. Expenses react. The wallet empties.",
    ),
    engine.MotionTemplate(
        "empty_balance_reaction",
        "Empty Balance Reaction",
        "A person checks the account, sees zero, and reacts to a declined payment.",
        tuple("empty zero nothing left balance declined wallet exhausted reaction".split()),
        "NOTHING LEFT",
        "The account reaches zero before investing begins",
    ),
    engine.MotionTemplate(
        "pay_self_character_comparison",
        "Pay Yourself First Comparison",
        "Two people receive the same paycheck but follow opposite money systems.",
        tuple("wealthy opposite pay yourself first compare choice people future".split()),
        "SAME PAYCHECK. DIFFERENT SYSTEM.",
        "Spend first on the left. Invest first on the right.",
    ),
    engine.MotionTemplate(
        "automatic_investing_habit",
        "Automatic Investing Habit",
        "A person sets the rule once while recurring deposits build in the background.",
        tuple("automatic auto invest habit recurring scheduled bill system relax".split()),
        "SET IT ONCE",
        "Automation keeps paying the future self",
    ),
)
CHARACTER_TEMPLATE_BY_ID = {item.template_id: item for item in CHARACTER_TEMPLATES}

DEFAULT_STYLE_ID = art.DEFAULT_STYLE_ID
STYLES = art.STYLES
OUTPUT_WIDTH = engine.OUTPUT_WIDTH
OUTPUT_HEIGHT = engine.OUTPUT_HEIGHT
ffmpeg_encoder_command = engine.ffmpeg_encoder_command
style_catalog = art.style_catalog

BEATS_BY_TEMPLATE = {
    "paycheck_arrival": (
        ("PAYDAY", "The character receives the full paycheck.", 0.18),
        ("FIRST 10%", "Ten percent separates before lifestyle can spend it.", 0.52),
        ("FUTURE FUNDED", "The transfer lands with the future self.", 0.84),
    ),
    "spend_first": (
        ("GET PAID", "The character begins with the full paycheck.", 0.16),
        ("SPEND", "Rent, groceries, and lifestyle consume the money.", 0.52),
        ("NOTHING LEFT", "The person reaches the empty-wallet outcome.", 0.86),
    ),
    "empty_balance_reaction": (
        ("CHECK", "The person opens the account and sees the remaining balance.", 0.16),
        ("ZERO", "The available balance counts down to nothing.", 0.52),
        ("DECLINED", "The character reacts to the empty account.", 0.84),
    ),
    "pay_self_character_comparison": (
        ("SAME PAYCHECK", "Both people begin with the same income.", 0.16),
        ("DIFFERENT CHOICE", "One spends first while the other invests first.", 0.52),
        ("DIFFERENT FUTURE", "The two systems land on opposite outcomes.", 0.86),
    ),
    "automatic_investing_habit": (
        ("SET THE RULE", "The character enables automatic investing once.", 0.16),
        ("RUN AUTOMATICALLY", "Recurring deposits move without another decision.", 0.52),
        ("LET IT GROW", "The person steps back while the investment builds.", 0.86),
    ),
}

PHRASE_WEIGHTS = {
    "paycheck_arrival": {
        "paycheck hits": 5,
        "future self": 5,
        "first 10 percent": 5,
        "first ten percent": 5,
        "get paid": 3,
        "gets paid": 3,
        "paycheck": 2,
    },
    "spend_first": {
        "most people": 5,
        "pay their rent": 5,
        "buy groceries": 5,
        "go out": 4,
        "spend first": 5,
        "rent": 2,
        "groceries": 2,
        "lifestyle": 2,
    },
    "empty_balance_reaction": {
        "never anything left": 7,
        "nothing left": 6,
        "balance is zero": 6,
        "zero balance": 5,
        "empty wallet": 5,
        "declined": 4,
        "zero": 2,
    },
    "pay_self_character_comparison": {
        "exact opposite": 7,
        "wealthy people": 6,
        "pay themselves first": 7,
        "pay yourself first": 6,
        "opposite": 3,
        "compare": 2,
    },
    "automatic_investing_habit": {
        "treating that 10 percent like a bill": 8,
        "treat it like a bill": 7,
        "automatic investing": 6,
        "set it once": 5,
        "build an invisible wealth machine": 5,
        "habit": 4,
        "automatically": 3,
        "recurring": 3,
    },
}


def _words(value: str) -> set[str]:
    return {
        "".join(character for character in token.lower() if character.isalnum())
        for token in value.split()
    } - {""}


def template_catalog() -> list[dict[str, object]]:
    return [
        {
            "template_id": item.template_id,
            "label": item.label,
            "description": item.description,
        }
        for item in CHARACTER_TEMPLATES
    ]


def score_character_templates(scene: Scene) -> list[tuple[int, engine.MotionTemplate]]:
    context = " ".join(
        [scene.narration, scene.visual_intent, *scene.search_keywords]
    ).lower()
    words = _words(context)
    scored: list[tuple[int, engine.MotionTemplate]] = []
    for template in CHARACTER_TEMPLATES:
        score = len(words & set(template.keywords))
        for phrase, weight in PHRASE_WEIGHTS[template.template_id].items():
            if phrase in context:
                score += weight
        scored.append((score, template))
    scored.sort(key=lambda pair: (pair[0], pair[1].template_id), reverse=True)
    return scored


def suggest_template(scene: Scene) -> tuple[engine.MotionTemplate, float, str]:
    score, template = score_character_templates(scene)[0]
    confidence = min(0.98, 0.48 + score * 0.045)
    reason = (
        f"Matched {score} human-behavior signal{'s' if score != 1 else ''} in the scene brief."
        if score
        else "Selected as the safest general character explainer for this scene."
    )
    return template, round(confidence, 2), reason


def storyboard_beats(template_id: str, duration_seconds: float) -> list[dict[str, object]]:
    if template_id not in CHARACTER_TEMPLATE_BY_ID:
        raise HTTPException(status_code=422, detail="Unknown character explainer template")
    duration = max(1.0, float(duration_seconds))
    return [
        {
            "label": label,
            "description": description,
            "time_seconds": round(
                min(duration - 0.04, max(0.08, duration * fraction)),
                3,
            ),
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
            "ink": (15, 23, 42),
            "surface": (240, 249, 255),
            "panel": (224, 242, 254),
            "person": (30, 64, 175),
            "person_alt": (13, 148, 136),
            "skin": (251, 191, 145),
            "accent": (14, 165, 233),
            "good": (16, 185, 129),
            "bad": (239, 68, 68),
            "gold": (245, 158, 11),
            "muted": (71, 85, 105),
            "white": (248, 250, 252),
        }
    if style_id == "editorial_documentary":
        return {
            "ink": (15, 18, 25),
            "surface": (38, 42, 50),
            "panel": (52, 56, 65),
            "person": (214, 168, 95),
            "person_alt": (148, 163, 184),
            "skin": (215, 181, 151),
            "accent": (214, 168, 95),
            "good": (110, 180, 142),
            "bad": (205, 112, 104),
            "gold": (214, 168, 95),
            "muted": (148, 163, 184),
            "white": (241, 245, 249),
        }
    return {
        "ink": (9, 14, 27),
        "surface": (24, 30, 50),
        "panel": (35, 43, 68),
        "person": (139, 92, 246),
        "person_alt": (34, 211, 238),
        "skin": (251, 191, 145),
        "accent": (34, 211, 238),
        "good": (52, 211, 153),
        "bad": (251, 113, 133),
        "gold": (245, 190, 73),
        "muted": (148, 163, 184),
        "white": (248, 250, 252),
    }


def _title(
    draw: ImageDraw.ImageDraw,
    template: engine.MotionTemplate,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    draw.rounded_rectangle((108, 92, 340, 144), radius=26, fill=palette["surface"])
    engine._text(
        draw,
        (224, 118),
        "CHARACTER EXPLAINER",
        18,
        palette["accent"],
        bold=True,
        anchor="mm",
    )
    engine._text(draw, (110, 166), template.title, 64, palette["white"], bold=True)
    engine._text(draw, (112, 246), template.subtitle, 29, palette["muted"])
    draw.rounded_rectangle((110, 302, 480, 310), radius=4, fill=palette["accent"])


def _panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    palette: dict[str, tuple[int, int, int]],
    *,
    outline: tuple[int, int, int] | None = None,
) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(
        (left + 14, top + 16, right + 14, bottom + 16),
        radius=32,
        fill=(3, 6, 14),
    )
    draw.rounded_rectangle(
        box,
        radius=32,
        fill=palette["surface"],
        outline=outline or palette["panel"],
        width=3,
    )


def _pill(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    label: str,
    *,
    fill: tuple[int, int, int],
    text_fill: tuple[int, int, int],
    width: int = 310,
    height: int = 62,
    size: int = 25,
) -> None:
    x, y = center
    draw.rounded_rectangle(
        (x - width // 2, y - height // 2, x + width // 2, y + height // 2),
        radius=height // 2,
        fill=fill,
    )
    engine._text(draw, (x, y), label, size, text_fill, bold=True, anchor="mm")


def _coin(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    palette: dict[str, tuple[int, int, int]],
    *,
    label: str = "$",
    radius: int = 35,
) -> None:
    x, y = center
    draw.ellipse(
        (x - radius + 6, y - radius + 8, x + radius + 6, y + radius + 8),
        fill=(3, 6, 14),
    )
    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        fill=palette["gold"],
        outline=palette["white"],
        width=3,
    )
    engine._text(draw, (x, y), label, max(19, radius - 5), palette["ink"], bold=True, anchor="mm")


def _quadratic_point(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
    progress: float,
) -> tuple[int, int]:
    inverse = 1 - progress
    return (
        round(inverse * inverse * start[0] + 2 * inverse * progress * control[0] + progress * progress * end[0]),
        round(inverse * inverse * start[1] + 2 * inverse * progress * control[1] + progress * progress * end[1]),
    )


def _route(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    control: tuple[int, int],
    end: tuple[int, int],
    progress: float,
    color: tuple[int, int, int],
) -> tuple[int, int]:
    progress = _clamp(progress)
    steps = max(2, round(30 * progress))
    points = [
        _quadratic_point(start, control, end, index / 30)
        for index in range(steps + 1)
    ]
    if len(points) > 1:
        draw.line(points, fill=color, width=7, joint="curve")
    return _quadratic_point(start, control, end, progress)


def _person(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    palette: dict[str, tuple[int, int, int]],
    *,
    scale: float = 1.0,
    pose: str = "idle",
    mood: str = "neutral",
    facing: int = 1,
    alternate: bool = False,
    performance_role: str = "directed",
) -> None:
    x, ground_y = center
    body_color = palette["person_alt"] if alternate else palette["person"]
    skin = palette["skin"]
    line_width = max(5, round(13 * scale))
    head_radius = round(38 * scale)
    head_y = ground_y - round(245 * scale)
    shoulder_y = ground_y - round(175 * scale)
    hip_y = ground_y - round(76 * scale)

    if pose == "slump":
        shoulder_y += round(18 * scale)
        head_y += round(14 * scale)
    bounce = round(5 * scale * math.sin((x + ground_y) * 0.013)) if pose == "celebrate" else 0
    head_y -= bounce
    shoulder_y -= bounce
    hip_y -= bounce

    draw.ellipse(
        (x - head_radius + 7, head_y - head_radius + 9, x + head_radius + 7, head_y + head_radius + 9),
        fill=(3, 6, 14),
    )
    draw.ellipse(
        (x - head_radius, head_y - head_radius, x + head_radius, head_y + head_radius),
        fill=skin,
        outline=body_color,
        width=max(3, round(5 * scale)),
    )
    draw.line((x, shoulder_y, x, hip_y), fill=body_color, width=line_width)
    draw.ellipse(
        (x - line_width // 2, shoulder_y - line_width // 2, x + line_width // 2, shoulder_y + line_width // 2),
        fill=body_color,
    )

    shoulder_left = (x - round(6 * scale), shoulder_y + round(5 * scale))
    shoulder_right = (x + round(6 * scale), shoulder_y + round(5 * scale))
    hip_left = (x - round(4 * scale), hip_y)
    hip_right = (x + round(4 * scale), hip_y)

    arm_span = round(82 * scale)
    leg_span = round(55 * scale)
    hand_drop = round(96 * scale)
    knee_y = ground_y - round(35 * scale)

    if pose in {"receive", "point"}:
        forward_hand = (x + facing * arm_span, shoulder_y + round(22 * scale))
        back_hand = (x - facing * round(48 * scale), shoulder_y + hand_drop)
    elif pose in {"phone", "tap"}:
        forward_hand = (x + facing * round(48 * scale), shoulder_y + round(60 * scale))
        back_hand = (x + facing * round(14 * scale), shoulder_y + round(65 * scale))
    elif pose == "celebrate":
        forward_hand = (x + arm_span, shoulder_y - round(75 * scale))
        back_hand = (x - arm_span, shoulder_y - round(75 * scale))
    elif pose == "relaxed":
        forward_hand = (x + facing * round(52 * scale), shoulder_y + round(82 * scale))
        back_hand = (x - facing * round(52 * scale), shoulder_y + round(82 * scale))
    elif pose == "slump":
        forward_hand = (x + round(45 * scale), shoulder_y + round(112 * scale))
        back_hand = (x - round(45 * scale), shoulder_y + round(112 * scale))
    else:
        forward_hand = (x + arm_span, shoulder_y + hand_drop)
        back_hand = (x - arm_span, shoulder_y + hand_drop)

    elbow_forward = (
        round((shoulder_right[0] + forward_hand[0]) / 2 + facing * 10 * scale),
        round((shoulder_right[1] + forward_hand[1]) / 2),
    )
    elbow_back = (
        round((shoulder_left[0] + back_hand[0]) / 2 - facing * 8 * scale),
        round((shoulder_left[1] + back_hand[1]) / 2),
    )
    draw.line((shoulder_right, elbow_forward, forward_hand), fill=body_color, width=line_width, joint="curve")
    draw.line((shoulder_left, elbow_back, back_hand), fill=body_color, width=line_width, joint="curve")

    left_foot = (x - leg_span, ground_y)
    right_foot = (x + leg_span, ground_y)
    if pose == "walk":
        left_foot = (x - leg_span - round(28 * scale), ground_y)
        right_foot = (x + leg_span + round(24 * scale), ground_y - round(8 * scale))
    draw.line((hip_left, (x - round(22 * scale), knee_y), left_foot), fill=body_color, width=line_width, joint="curve")
    draw.line((hip_right, (x + round(22 * scale), knee_y), right_foot), fill=body_color, width=line_width, joint="curve")

    eye_y = head_y - round(6 * scale)
    eye_offset = round(13 * scale)
    eye_radius = max(2, round(3 * scale))
    for eye_x in (x - eye_offset, x + eye_offset):
        draw.ellipse((eye_x - eye_radius, eye_y - eye_radius, eye_x + eye_radius, eye_y + eye_radius), fill=palette["ink"])
    mouth_y = head_y + round(14 * scale)
    if mood == "happy":
        draw.arc((x - round(16 * scale), mouth_y - round(9 * scale), x + round(16 * scale), mouth_y + round(10 * scale)), 10, 170, fill=palette["ink"], width=max(2, round(3 * scale)))
    elif mood == "sad":
        draw.arc((x - round(16 * scale), mouth_y - round(1 * scale), x + round(16 * scale), mouth_y + round(18 * scale)), 190, 350, fill=palette["ink"], width=max(2, round(3 * scale)))
    else:
        draw.line((x - round(12 * scale), mouth_y, x + round(12 * scale), mouth_y), fill=palette["ink"], width=max(2, round(3 * scale)))

    if pose in {"phone", "tap"}:
        phone_x = x + facing * round(58 * scale)
        phone_y = shoulder_y + round(48 * scale)
        draw.rounded_rectangle(
            (phone_x - round(18 * scale), phone_y - round(30 * scale), phone_x + round(18 * scale), phone_y + round(30 * scale)),
            radius=max(4, round(7 * scale)),
            fill=palette["ink"],
            outline=palette["accent"],
            width=max(2, round(3 * scale)),
        )


def _beat_indicator(
    draw: ImageDraw.ImageDraw,
    template_id: str,
    duration_seconds: float,
    time_seconds: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    beats = storyboard_beats(template_id, duration_seconds)
    active = min(range(len(beats)), key=lambda index: abs(float(beats[index]["time_seconds"]) - time_seconds))
    start_x = 1505
    for index in range(3):
        x = start_x + index * 70
        selected = index == active
        radius = 10 if selected else 6
        draw.ellipse((x - radius, 112 - radius, x + radius, 112 + radius), fill=palette["good"] if selected else palette["muted"])
    engine._text(draw, (1775, 140), str(beats[active]["label"]), 20, palette["good"], bold=True, anchor="ra")


def _paycheck_arrival(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    character_arrive = _phase(progress, 0.02, 0.15)
    paycheck_arrive = _phase(progress, 0.04, 0.30)
    split = _phase(progress, 0.32, 0.55)
    transfer = _phase(progress, 0.46, 0.76)
    result = _phase(progress, 0.75, 0.92)

    _panel(draw, (105, 350, 760, 900), palette, outline=palette["accent"])
    # Finish screen travel inside the directed walk beat. Continuing to move
    # the root after the pose settled into receive was the remaining glide.
    person_x = round(engine._lerp(265, 410, character_arrive))
    pose = "receive" if transfer < 0.72 else "point"
    _person(draw, (person_x, 835), palette, scale=1.18, pose=pose, mood="happy" if result > 0.5 else "neutral")
    engine._text(draw, (155, 390), "PAYDAY", 28, palette["accent"], bold=True)
    # The paycheck drops into its own prop lane instead of travelling through
    # the face-safe zone while the character enters from the left.
    paycheck_x = 620
    paycheck_y = round(engine._lerp(290, 540, paycheck_arrive))
    composition._icon_paycheck(draw, (paycheck_x, paycheck_y), scale=1.0, accent=palette["accent"], received=paycheck_arrive > 0.92)
    engine._text(draw, (paycheck_x + 30, paycheck_y + 28), "$5,000", 27, (29, 53, 54), bold=True, anchor="mm")

    _panel(draw, (930, 350, 1810, 585), palette, outline=palette["bad"])
    composition._icon_house(draw, (1050, 465), scale=0.58, accent=palette["bad"])
    engine._text(draw, (1175, 405), "LIFE + EXPENSES", 27, palette["muted"], bold=True)
    engine._text(draw, (1175, 478), f"{round(90 * split)}%", 62, palette["white"], bold=True)

    _panel(draw, (930, 650, 1810, 900), palette, outline=palette["good"])
    composition._icon_bank(draw, (1055, 775), scale=0.60, accent=palette["good"])
    engine._text(draw, (1185, 700), "FUTURE SELF", 27, palette["good"], bold=True)
    engine._text(draw, (1185, 782), f"{round(10 * split)}%", 66, palette["white"], bold=True)

    if transfer > 0:
        token = _route(draw, (650, 610), (820, 520), (1000, 760), transfer, palette["good"])
        _coin(draw, token, palette, label="10", radius=40)
    if result > 0.1:
        _pill(draw, (1515, 852), "FUTURE PAID FIRST", fill=palette["good"], text_fill=palette["ink"], width=360)


def _spend_first(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    income = _phase(progress, 0.03, 0.20)
    stages = (
        _phase(progress, 0.22, 0.43),
        _phase(progress, 0.40, 0.62),
        _phase(progress, 0.58, 0.78),
    )
    drained = 0.46 * stages[0] + 0.28 * stages[1] + 0.26 * stages[2]
    remaining = max(0, round(5000 * (1 - drained) * income))

    _panel(draw, (95, 350, 720, 900), palette, outline=palette["accent"])
    pose = "receive" if progress < 0.30 else "slump" if progress > 0.76 else "point"
    _person(draw, (385, 825), palette, scale=1.15, pose=pose, mood="sad" if progress > 0.76 else "neutral")
    engine._text(draw, (150, 390), "AVAILABLE", 25, palette["muted"], bold=True)
    engine._text(draw, (385, 480), f"${remaining:,}", 70, palette["white"] if remaining else palette["bad"], bold=True, anchor="mm")
    composition._icon_wallet(draw, (385, 610), scale=0.82, accent=palette["bad"] if remaining == 0 else palette["accent"], empty=remaining == 0)

    cards = (
        ("RENT", (850, 355, 1170, 605), composition._icon_house, palette["bad"], "46%"),
        ("GROCERIES", (1250, 355, 1570, 605), composition._icon_bag, palette["good"], "28%"),
        ("LIFESTYLE", (1050, 650, 1370, 900), composition._icon_card, palette["person"], "26%"),
    )
    starts = ((620, 535), (620, 610), (620, 685))
    controls = ((745, 420), (900, 540), (820, 790))
    for index, (label, box, icon, accent, percent) in enumerate(cards):
        _panel(draw, box, palette, outline=accent)
        left, top, right, _bottom = box
        icon(draw, ((left + right) // 2, top + 92), scale=0.46, accent=accent)
        engine._text(draw, ((left + right) // 2, top + 165), label, 24, accent, bold=True, anchor="mm")
        engine._text(draw, ((left + right) // 2, top + 210), f"{round(int(percent[:-1]) * stages[index])}%", 35, palette["white"], bold=True, anchor="mm")
        if stages[index] > 0:
            destination = ((left + right) // 2, (top + box[3]) // 2)
            token = _route(draw, starts[index], controls[index], destination, stages[index], accent)
            _coin(draw, token, palette, radius=25)
    if progress > 0.82:
        _pill(draw, (385, 865), "$0 LEFT TO INVEST", fill=palette["bad"], text_fill=palette["white"], width=350)


def _empty_balance_reaction(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    drain = _phase(progress, 0.16, 0.66)
    reveal = _phase(progress, 0.66, 0.84)
    remaining = max(0, round(4200 * (1 - drain)))

    _panel(draw, (110, 350, 740, 900), palette, outline=palette["bad"])
    pose = "phone" if reveal < 0.45 else "slump"
    _person(draw, (410, 830), palette, scale=1.20, pose=pose, mood="sad" if reveal > 0.3 else "neutral")
    engine._text(draw, (170, 390), "CHECKING THE ACCOUNT", 26, palette["muted"], bold=True)

    _panel(draw, (850, 350, 1810, 900), palette, outline=palette["bad"])
    phone = (980, 410, 1510, 850)
    draw.rounded_rectangle(phone, radius=50, fill=palette["ink"], outline=palette["accent"], width=4)
    draw.rounded_rectangle((1015, 450, 1475, 810), radius=36, fill=palette["surface"])
    engine._text(draw, (1060, 500), "AVAILABLE BALANCE", 23, palette["muted"], bold=True)
    engine._text(draw, (1245, 620), f"${remaining:,.2f}", 72, palette["bad"] if remaining == 0 else palette["white"], bold=True, anchor="mm")
    draw.rounded_rectangle((1060, 700, 1430, 724), radius=12, fill=palette["panel"])
    width = round(370 * (1 - drain))
    if width > 0:
        draw.rounded_rectangle((1060, 700, 1060 + width, 724), radius=12, fill=palette["accent"])
    composition._icon_card(draw, (1650, 590), scale=0.58, accent=palette["bad"], declined=reveal > 0.25)
    if reveal > 0.15:
        _pill(draw, (1650, 770), "DECLINED", fill=palette["bad"], text_fill=palette["white"], width=250)


def _comparison(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    decision = _phase(progress, 0.22, 0.62)
    result = _phase(progress, 0.62, 0.86)
    _panel(draw, (85, 350, 910, 905), palette, outline=palette["bad"])
    _panel(draw, (1010, 350, 1835, 905), palette, outline=palette["good"])
    draw.line((960, 350, 960, 905), fill=palette["muted"], width=3)

    engine._text(draw, (498, 398), "SPEND FIRST", 31, palette["bad"], bold=True, anchor="mm")
    _person(
        draw,
        (390, 815),
        palette,
        scale=1.02,
        pose="slump" if result > 0.35 else "receive",
        mood="sad" if result > 0.35 else "neutral",
        performance_role="authored",
    )
    composition._icon_wallet(draw, (690, 565), scale=0.70, accent=palette["bad"], empty=result > 0.35)
    composition._icon_house(draw, (650, 750), scale=0.38, accent=palette["bad"])
    composition._icon_bag(draw, (770, 750), scale=0.38, accent=palette["good"])
    engine._text(draw, (690, 850), "$0 LEFT", 38, palette["bad"], bold=True, anchor="mm")

    engine._text(draw, (1422, 398), "PAY SELF FIRST", 31, palette["good"], bold=True, anchor="mm")
    _person(
        draw,
        (1240, 815),
        palette,
        scale=1.02,
        pose="celebrate" if result > 0.55 else "point",
        mood="happy",
        alternate=True,
        performance_role="authored",
    )
    composition._icon_bank(draw, (1650, 590), scale=0.66, accent=palette["good"])
    if decision > 0:
        token = _route(draw, (1320, 600), (1450, 470), (1575, 600), decision, palette["good"])
        _coin(draw, token, palette, label="10", radius=34)
    engine._text(draw, (1650, 760), f"{round(10 * decision)}% INVESTED", 39, palette["good"], bold=True, anchor="mm")
    if result > 0.35:
        _pill(draw, (1422, 855), "AUTOMATIC ADVANTAGE", fill=palette["good"], text_fill=palette["ink"], width=380)


def _automatic_habit(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    setup = _phase(progress, 0.06, 0.30)
    cycle = _phase(progress, 0.28, 0.78)
    result = _phase(progress, 0.74, 0.92)

    _panel(draw, (95, 350, 710, 900), palette, outline=palette["accent"])
    pose = "tap" if setup < 0.90 else "relaxed" if result > 0.25 else "point"
    _person(draw, (390, 825), palette, scale=1.16, pose=pose, mood="happy" if result > 0.2 else "neutral")
    engine._text(draw, (150, 392), "ONE-TIME SETUP", 26, palette["accent"], bold=True)
    _pill(draw, (390, 520), "AUTO-INVEST 10%", fill=palette["panel"], text_fill=palette["good"], width=350)
    if setup > 0.75:
        _pill(draw, (390, 610), "ENABLED", fill=palette["good"], text_fill=palette["ink"], width=220)

    _panel(draw, (820, 350, 1815, 900), palette, outline=palette["good"])
    composition._icon_calendar(draw, (980, 540), scale=0.62, accent=palette["person"], day="PAY")
    composition._icon_bank(draw, (1630, 555), scale=0.70, accent=palette["good"])
    engine._text(draw, (1305, 405), "THE SYSTEM RUNS", 29, palette["muted"], bold=True, anchor="mm")
    cycles = max(1, min(4, math.ceil(cycle * 4))) if cycle > 0 else 0
    for index in range(cycles):
        local = _clamp(cycle * 4 - index)
        start = (1045, 600 + index * 30)
        end = (1535, 600 - index * 18)
        token = _route(draw, start, (1290, 430 - index * 24), end, local, palette["good"])
        _coin(draw, token, palette, label="10", radius=26)
    chart_points = []
    for index, value in enumerate((0.18, 0.30, 0.46, 0.66, 0.90)):
        visible = _phase(cycle, index * 0.13, min(1.0, index * 0.13 + 0.35))
        x = 1040 + index * 135
        y = 820 - round(180 * value * visible)
        chart_points.append((x, y))
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=palette["good"])
    if len(chart_points) > 1:
        draw.line(chart_points, fill=palette["good"], width=8, joint="curve")
    if result > 0.2:
        _pill(draw, (1330, 850), "GROWTH WITHOUT ANOTHER DECISION", fill=palette["good"], text_fill=palette["ink"], width=540, size=22)


RENDERERS = {
    "paycheck_arrival": _paycheck_arrival,
    "spend_first": _spend_first,
    "empty_balance_reaction": _empty_balance_reaction,
    "pay_self_character_comparison": _comparison,
    "automatic_investing_habit": _automatic_habit,
}

CAMERA_FOCUS = {
    "paycheck_arrival": ((0.30, 0.55), (0.68, 0.56), 0.014),
    "spend_first": ((0.28, 0.55), (0.63, 0.58), 0.012),
    "empty_balance_reaction": ((0.30, 0.55), (0.69, 0.55), 0.015),
    "pay_self_character_comparison": ((0.45, 0.55), (0.58, 0.55), 0.010),
    "automatic_investing_habit": ((0.30, 0.56), (0.68, 0.52), 0.014),
}


def _camera_move(image: Image.Image, template_id: str, progress: float) -> Image.Image:
    start, end, zoom_amount = CAMERA_FOCUS[template_id]
    eased = _ease(progress)
    zoom = 1 + zoom_amount * eased
    width, height = image.size
    scaled_width = round(width * zoom)
    scaled_height = round(height * zoom)
    scaled = image.resize((scaled_width, scaled_height), Image.Resampling.BILINEAR)
    focus_x = start[0] + (end[0] - start[0]) * eased
    focus_y = start[1] + (end[1] - start[1]) * eased
    left = round((scaled_width - width) * focus_x)
    top = round((scaled_height - height) * focus_y)
    return scaled.crop((left, top, left + width, top + height))


def render_frame(
    template_id: str,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    template = CHARACTER_TEMPLATE_BY_ID.get(template_id)
    if template is None:
        raise HTTPException(status_code=422, detail="Unknown character explainer template")
    style = art._resolve_style(style_id)
    duration = max(1.0, float(duration_seconds))
    time_value = max(0.0, min(float(time_seconds), duration))
    progress = time_value / duration
    palette = _palette(style.style_id)

    image = engine._background().copy()
    draw = ImageDraw.Draw(image)
    _title(draw, template, palette)
    RENDERERS[template_id](draw, progress, palette)
    _beat_indicator(draw, template_id, duration, time_value, palette)
    image = _camera_move(image, template_id, progress)
    styled = art.STYLE_RENDERERS[style.style_id](image, time_value)
    fade_seconds = max(0.15, min(0.35, duration / 6))
    visibility = min(
        engine._clamp(time_value / fade_seconds),
        engine._clamp((duration - time_value) / fade_seconds),
    )
    if visibility < 1:
        return Image.blend(Image.new("RGB", styled.size, engine.BG_TOP), styled, visibility)
    return styled


def _encode_frames(
    ffmpeg: str,
    template: engine.MotionTemplate,
    style: art.MotionStyle,
    duration_seconds: float,
    output_path: Path,
) -> None:
    process = subprocess.Popen(
        ffmpeg_encoder_command(ffmpeg, output_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    frame_count = max(1, math.ceil(duration_seconds * engine.OUTPUT_FPS))
    code = -1
    try:
        assert process.stdin is not None
        for index in range(frame_count):
            process.stdin.write(
                render_frame(
                    template.template_id,
                    duration_seconds,
                    min(duration_seconds, index / engine.OUTPUT_FPS),
                    style.style_id,
                ).tobytes()
            )
        process.stdin.close()
        code = process.wait(timeout=engine.RENDER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        raise HTTPException(status_code=504, detail="Character explainer render timed out") from exc
    except BrokenPipeError as exc:
        process.kill()
        process.wait()
        error = engine._compact_error(process.stderr.read() if process.stderr else None)
        raise HTTPException(status_code=500, detail=f"Character explainer encoder stopped unexpectedly: {error}") from exc
    finally:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
    if code != 0:
        error = engine._compact_error(process.stderr.read() if process.stderr else None)
        raise HTTPException(status_code=500, detail=f"Character explainer encoder failed: {error}")


def render_character_motion(
    scene: Scene,
    template_id: str | None = None,
    style_id: str | None = None,
) -> art.ArtDirectedMotion:
    template = CHARACTER_TEMPLATE_BY_ID.get(template_id or "")
    if template is None:
        template, _confidence, _reason = suggest_template(scene)
    style = art._resolve_style(style_id)
    ffmpeg = shutil.which(engine.FFMPEG_NAME)
    if ffmpeg is None:
        raise HTTPException(status_code=422, detail="FFmpeg is required to encode Character Explainer videos.")

    duration = round(max(1.0, float(scene.duration_seconds)), 3)
    asset_directory = project_directory(scene.project_id) / "assets"
    asset_directory.mkdir(parents=True, exist_ok=True)
    stem = asset_directory / (
        f"scene-{scene.scene_number:03d}-character-"
        f"{safe_component(template.template_id)}-{safe_component(style.style_id)}"
    )
    media_path = stem.with_suffix(".mp4")
    preview_path = Path(f"{stem}-poster.jpg")
    temporary_media = Path(f"{media_path}.part.mp4")
    temporary_preview = Path(f"{preview_path}.part.jpg")
    temporary_media.unlink(missing_ok=True)
    temporary_preview.unlink(missing_ok=True)

    try:
        _encode_frames(ffmpeg, template, style, duration, temporary_media)
        poster_time = min(max(0.8, duration * 0.55), max(0.0, duration - 0.03))
        render_frame(template.template_id, duration, poster_time, style.style_id).save(
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
        raise HTTPException(status_code=500, detail=f"Character explainer render failed: {type(exc).__name__}: {exc}") from exc

    media_relative = media_path.resolve().relative_to(MEDIA_ROOT).as_posix()
    preview_relative = preview_path.resolve().relative_to(MEDIA_ROOT).as_posix()
    return art.ArtDirectedMotion(
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
    )
