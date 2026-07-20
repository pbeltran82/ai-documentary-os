from __future__ import annotations

"""Topic-aware visual direction for Internet and human-attention documentaries.

The Mars reference renderer proved a production can be finished, but its broad
cartoon route was installed globally. This module restores a hard domain gate:
Mars compositions only run for Mars projects, while Internet/attention projects
receive a dedicated, beat-aware visual family. Long narration scenes can now
change composition at every planned visual beat inside one exact-visual asset.
"""

import math
from collections import Counter
from typing import Any

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_documentary_patch as patch
from .cartoon_scene_graph import LayerStack, draw_person, phase
from .finance_motion import MotionTemplate

INK = cartoon.INK
WHITE = cartoon.WHITE
CYAN = cartoon.CYAN
BLUE = cartoon.BLUE
GREEN = cartoon.GREEN
AMBER = cartoon.AMBER
PURPLE = cartoon.PURPLE
RED = cartoon.RED
NAVY = (12, 25, 42)
SLATE = (45, 61, 78)
PALE = (226, 237, 244)
PAPER = (247, 247, 244)
FLOOR = (177, 188, 194)

INTERNET_TEMPLATE_IDS = {
    "internet_early_web",
    "internet_search_growth",
    "internet_smartphone_shift",
    "internet_algorithm_feed",
    "internet_notification_lab",
    "internet_evidence_review",
    "internet_connected_benefits",
    "internet_fragmented_day",
    "internet_intentional_design",
    "internet_attention_choice",
}

MARS_CARTOON_TEMPLATE_IDS = {
    "route_map",
    "crowd_focus",
    "presenter_desk",
    "transport_scene",
    "habitat_build",
    "council_scene",
    "process_diagram",
}

INTERNET_TEMPLATES = (
    MotionTemplate(
        "internet_early_web",
        "The Web Was a Place",
        "A deliberate early-Web session on a CRT desktop before the network became constant.",
        ("early web", "world wide web", "cern", "dial", "desktop", "browser", "1993", "search"),
        "THE WEB WAS A PLACE YOU VISITED",
        "A slower, intentional session",
    ),
    MotionTemplate(
        "internet_search_growth",
        "Information Expands",
        "Search, broadband, archives, and pages multiplying across a growing network.",
        ("search", "information", "archive", "broadband", "knowledge", "web page", "access"),
        "INFORMATION BECAME ABUNDANT",
        "Search turned scarcity into navigation",
    ),
    MotionTemplate(
        "internet_smartphone_shift",
        "The Internet Becomes Constant",
        "The network moves from a desk into pockets, streets, cafés, and commutes.",
        ("smartphone", "portable", "pocket", "2011", "2025", "constant", "wherever"),
        "THE INTERNET MOVED INTO OUR POCKETS",
        "From occasional destination to constant companion",
    ),
    MotionTemplate(
        "internet_algorithm_feed",
        "The Feed Chooses Next",
        "Recommendation cards pass through a ranking system driven by engagement signals.",
        ("algorithm", "recommendation", "feed", "engagement", "autoplay", "ranking", "platform"),
        "WHAT APPEARS NEXT IS SELECTED",
        "Signals become rankings, rankings become feeds",
    ),
    MotionTemplate(
        "internet_notification_lab",
        "The Cost of Interruption",
        "A concentration task is interrupted by a silent phone notification in a laboratory scene.",
        ("notification", "experiment", "laboratory", "attention task", "interruption", "phone nearby"),
        "A PING CAN BREAK THE TASK",
        "Interruption without even touching the phone",
    ),
    MotionTemplate(
        "internet_evidence_review",
        "What the Evidence Says",
        "Research cards separate measured immediate effects from unanswered long-term questions.",
        ("evidence", "study", "review", "papers", "cognitive", "lasting", "open question"),
        "MEASURED EFFECTS, CAREFUL CLAIMS",
        "Immediate interference is not the same as permanent decline",
    ),
    MotionTemplate(
        "internet_connected_benefits",
        "Connection and Access",
        "Learning, navigation, creativity, communication, and accessibility shown as real benefits.",
        ("learning", "education", "navigation", "creativity", "community", "accessibility", "benefit"),
        "THE SAME NETWORK ALSO EXPANDS ACCESS",
        "Connection creates real capability",
    ),
    MotionTemplate(
        "internet_fragmented_day",
        "A Day Split Into Fragments",
        "A student, worker, and commuter switch among tabs, messages, feeds, and focused reading.",
        ("student", "worker", "commuter", "task switching", "tabs", "apps", "reading", "short-form"),
        "ATTENTION IS NEGOTIATED ALL DAY",
        "Work, learning, and leisure compete in the same device",
    ),
    MotionTemplate(
        "internet_intentional_design",
        "Design for Intention",
        "People change notification defaults while a designer builds calmer interface choices.",
        ("notification settings", "device-free", "reader mode", "defaults", "humane", "design", "agency"),
        "BETTER DEFAULTS RESTORE AGENCY",
        "Personal practices and humane design work together",
    ),
    MotionTemplate(
        "internet_attention_choice",
        "Choose When to Look",
        "A connected city remains lit while people deliberately choose when screens receive attention.",
        ("choose", "attention", "city", "control", "intentional", "path forward", "final"),
        "ATTENTION SHAPES A LIFE",
        "The network can remain available without always taking priority",
    ),
)
INTERNET_TEMPLATE_BY_ID = {template.template_id: template for template in INTERNET_TEMPLATES}

# Scene-level semantic arcs guarantee useful variety even when the generated beat
# descriptions repeat the last phrase of a visual-intent paragraph.
SCENE_ARCS: dict[int, tuple[str, ...]] = {
    1: (
        "internet_early_web",
        "internet_search_growth",
        "internet_smartphone_shift",
        "internet_notification_lab",
        "internet_fragmented_day",
    ),
    2: (
        "internet_early_web",
        "internet_search_growth",
        "internet_smartphone_shift",
        "internet_connected_benefits",
    ),
    3: (
        "internet_smartphone_shift",
        "internet_algorithm_feed",
        "internet_notification_lab",
        "internet_fragmented_day",
    ),
    4: (
        "internet_notification_lab",
        "internet_evidence_review",
        "internet_fragmented_day",
        "internet_attention_choice",
    ),
    5: (
        "internet_connected_benefits",
        "internet_algorithm_feed",
        "internet_fragmented_day",
        "internet_evidence_review",
    ),
    6: (
        "internet_fragmented_day",
        "internet_notification_lab",
        "internet_connected_benefits",
        "internet_intentional_design",
    ),
    7: (
        "internet_intentional_design",
        "internet_connected_benefits",
        "internet_attention_choice",
    ),
}

PHRASE_WEIGHTS: dict[str, dict[str, int]] = {
    "internet_early_web": {
        "early web": 12, "world wide web": 12, "cern": 12, "1989": 10,
        "1993": 10, "dial": 10, "desktop": 7, "browser window": 7,
    },
    "internet_search_growth": {
        "search": 9, "broadband": 10, "archive": 9, "information": 6,
        "knowledge": 7, "web page": 7, "newspaper": 5,
    },
    "internet_smartphone_shift": {
        "smartphone": 14, "portable": 11, "pocket": 10, "2011": 9,
        "2025": 9, "91 percent": 10, "wherever": 6,
    },
    "internet_algorithm_feed": {
        "algorithm": 14, "recommendation": 14, "feed": 12, "engagement": 10,
        "autoplay": 9, "platform": 6, "ranking": 10,
    },
    "internet_notification_lab": {
        "notification": 14, "experiment": 12, "laboratory": 12,
        "interruption": 11, "phone nearby": 12, "attention-demanding": 9,
    },
    "internet_evidence_review": {
        "evidence": 11, "study": 10, "review": 10, "papers": 9,
        "cognitive": 8, "lasting": 8, "open question": 10,
    },
    "internet_connected_benefits": {
        "learning": 10, "education": 10, "navigation": 10, "creativity": 10,
        "community": 8, "accessibility": 12, "benefit": 9,
    },
    "internet_fragmented_day": {
        "student": 10, "worker": 10, "commuter": 10, "task switching": 12,
        "tabs": 9, "apps": 7, "reading": 7, "short-form": 9,
    },
    "internet_intentional_design": {
        "notification settings": 14, "device-free": 12, "reader mode": 12,
        "defaults": 10, "humane": 12, "designer": 10, "agency": 9,
    },
    "internet_attention_choice": {
        "choose": 8, "attention": 4, "city": 10, "control": 8,
        "path forward": 12, "final": 8, "ending": 8,
    },
}

_previous_suggest_template = cartoon.suggest_template
_previous_render_planned_frame = cartoon.render_planned_frame
_previous_use_cartoon = patch._use_cartoon


def _project_context(scene: Any) -> str:
    project = getattr(scene, "project", None)
    pieces = [
        str(getattr(scene, "narration", "")),
        str(getattr(scene, "visual_intent", "")),
        " ".join(str(item) for item in (getattr(scene, "search_keywords", None) or [])),
    ]
    if project is not None:
        pieces.extend(
            str(getattr(project, field, ""))
            for field in ("title", "topic", "audience", "tone", "visual_style")
        )
    return " ".join(pieces).lower()


def is_internet_attention(scene: Any) -> bool:
    context = _project_context(scene)
    strong = (
        "how the internet changed human attention",
        "human attention",
        "attention economy",
        "world wide web",
    )
    if any(signal in context for signal in strong):
        return True
    internet_signals = sum(
        signal in context
        for signal in ("internet", "web", "smartphone", "social media", "notification", "algorithmic feed")
    )
    attention_signals = sum(
        signal in context
        for signal in ("attention", "distraction", "task switching", "focus", "interruption")
    )
    return internet_signals >= 2 and attention_signals >= 1


def is_mars_documentary(scene: Any) -> bool:
    context = _project_context(scene)
    return any(
        signal in context
        for signal in (
            "mars", "martian", "interplanetary", "off-planet", "red planet",
            "space settlement", "mars habitat", "mars colony",
        )
    )


def _use_cartoon(scene: Any) -> bool:
    if is_internet_attention(scene):
        return True
    if is_mars_documentary(scene):
        return _previous_use_cartoon(scene)
    # The legacy general cartoon family is Mars-authored. Unknown subjects stay on
    # the neutral Tech/Character/Finance engines until they receive a domain family.
    return False


def _score_template(context: str, template_id: str) -> int:
    return sum(weight for phrase, weight in PHRASE_WEIGHTS[template_id].items() if phrase in context)


def _scene_arc(scene: Any) -> tuple[str, ...]:
    scene_number = int(getattr(scene, "scene_number", 1) or 1)
    return SCENE_ARCS.get(scene_number, tuple(INTERNET_TEMPLATE_BY_ID))


def _ranked_templates(scene: Any, extra_context: str = "") -> list[tuple[int, str]]:
    context = f"{_project_context(scene)} {extra_context.lower()}"
    arc = _scene_arc(scene)
    ranked = [(_score_template(context, template_id), template_id) for template_id in INTERNET_TEMPLATE_BY_ID]
    ranked.sort(
        key=lambda pair: (
            pair[0],
            -(arc.index(pair[1]) if pair[1] in arc else len(arc)),
            pair[1],
        ),
        reverse=True,
    )
    return ranked


def suggest_template(scene: Any, extra_context: str = ""):
    if not is_internet_attention(scene):
        return _previous_suggest_template(scene, extra_context)
    score, template_id = _ranked_templates(scene, extra_context)[0]
    if score <= 0:
        template_id = _scene_arc(scene)[0]
    confidence = min(0.98, 0.72 + max(0, score) * 0.012)
    return (
        INTERNET_TEMPLATE_BY_ID[template_id],
        round(confidence, 2),
        "Topic-aware Internet and attention visual direction.",
    )


def _visual_beats(scene: Any) -> list[dict[str, Any]]:
    plan = dict(getattr(scene, "animation_plan", None) or {})
    return list(plan.get("visual_beats") or [])


def beat_template_sequence(scene: Any, template_id: str | None = None) -> list[str]:
    beats = _visual_beats(scene)
    count = max(1, len(beats))
    arc = list(_scene_arc(scene))
    selected: list[str] = []
    counts: Counter[str] = Counter()

    for index in range(count):
        beat = beats[index] if index < len(beats) else {}
        extra = str(beat.get("visual_intent", ""))
        ranked = _ranked_templates(scene, extra)
        if index == 0 and template_id in INTERNET_TEMPLATE_IDS:
            ranked = [(10_000, str(template_id)), *[item for item in ranked if item[1] != template_id]]

        # Semantic score wins, but recent repetition and project overuse are costly.
        candidates: list[tuple[int, str]] = []
        for score, candidate in ranked:
            adjusted = score - counts[candidate] * 16
            if selected and candidate == selected[-1]:
                adjusted -= 90
            if candidate in selected[-3:]:
                adjusted -= 24
            if candidate in arc:
                desired = arc[index % len(arc)]
                if candidate == desired:
                    adjusted += 18
            candidates.append((adjusted, candidate))
        candidates.sort(key=lambda pair: (pair[0], pair[1]), reverse=True)
        chosen = candidates[0][1]
        selected.append(chosen)
        counts[chosen] += 1

    # Long scenes need genuine composition changes even when every generated beat
    # repeats one broad visual-intent phrase.
    diversity_target = min(4, count, len(arc))
    unique = set(selected)
    if len(unique) < diversity_target:
        for index in range(count):
            candidate = arc[index % len(arc)]
            if candidate not in unique or selected[index] == selected[index - 1 if index else 0]:
                selected[index] = candidate
                unique.add(candidate)
            if len(unique) >= diversity_target:
                break
    return selected


def _beat_state(scene: Any, time_seconds: float, duration_seconds: float) -> tuple[int, float]:
    beats = _visual_beats(scene)
    if not beats:
        return 0, max(0.0, min(1.0, time_seconds / max(0.001, duration_seconds)))
    for index, beat in enumerate(beats):
        start = float(beat.get("relative_start_seconds", 0.0))
        end = float(beat.get("relative_end_seconds", duration_seconds))
        if start <= time_seconds < end or index == len(beats) - 1:
            return index, max(0.0, min(1.0, (time_seconds - start) / max(0.001, end - start)))
    return len(beats) - 1, 1.0


def _title(draw: ImageDraw.ImageDraw, headline: str, subline: str = "") -> None:
    draw.rounded_rectangle((82, 70, 1160, 205), radius=30, fill=NAVY, outline=(72, 99, 126), width=6)
    draw.text((120, 100), headline, font=cartoon._font(38, True), fill=WHITE)
    if subline:
        draw.text((120, 153), subline, font=cartoon._font(24), fill=(185, 203, 218))


def _screen(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], *, fill: tuple[int, int, int] = PALE) -> None:
    draw.rounded_rectangle(box, radius=30, fill=fill, outline=INK, width=9)
    left, top, right, bottom = box
    draw.rectangle((left + 22, top + 22, right - 22, top + 72), fill=SLATE)
    for index, color in enumerate((RED, AMBER, GREEN)):
        x = left + 48 + index * 34
        draw.ellipse((x, top + 36, x + 16, top + 52), fill=color)


def _phone(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, *, glow: float = 0.0) -> None:
    width = round(220 * scale)
    height = round(390 * scale)
    draw.rounded_rectangle((x - width // 2, y - height // 2, x + width // 2, y + height // 2), radius=round(34 * scale), fill=(39, 52, 68), outline=INK, width=max(5, round(10 * scale)))
    draw.rounded_rectangle((x - width // 2 + 22, y - height // 2 + 32, x + width // 2 - 22, y + height // 2 - 48), radius=round(18 * scale), fill=(209, 229, 238))
    draw.ellipse((x - 10, y + height // 2 - 30, x + 10, y + height // 2 - 10), fill=(120, 135, 150))
    if glow > 0:
        radius = round((34 + 18 * glow) * scale)
        draw.ellipse((x + width // 2 - radius, y - height // 2 - radius // 2, x + width // 2 + radius, y - height // 2 + radius * 1.5), fill=RED, outline=WHITE, width=4)


def _early_web(progress: float, variant: int) -> Image.Image:
    stack = LayerStack((1920, 1080))
    env, actors, effects = stack.draw("environment"), stack.draw("actors"), stack.draw("effects")
    env.rectangle((0, 0, 1920, 1080), fill=(224, 226, 218))
    env.rectangle((0, 790, 1920, 1080), fill=(142, 117, 92))
    env.rounded_rectangle((210, 190, 1220, 800), radius=38, fill=(103, 111, 111), outline=INK, width=11)
    _screen(env, (300, 250, 1130, 690), fill=(224, 238, 232))
    env.rounded_rectangle((540, 700, 900, 820), radius=20, fill=(91, 94, 91), outline=INK, width=8)
    draw_person(actors, (1500, 720), 1.02, shirt=BLUE, pants=(52, 61, 75), arm_raise=0.18)
    reveal = phase(progress, 0.05, 0.92)
    page_count = 1 + min(4, int(reveal * 5))
    for index in range(page_count):
        top = 355 + index * 58
        effects.rounded_rectangle((390, top, 1025 - index * 36, top + 34), radius=10, fill=(69, 124, 145) if index == 0 else (117, 150, 153))
    cable_x = round(1220 + 180 * math.sin(progress * math.pi))
    effects.line((1215, 610, cable_x, 610, 1490, 550), fill=(61, 74, 84), width=10)
    _title(effects, "THE WEB WAS A PLACE", "You connected, searched, read, and left")
    return stack.composite((224, 226, 218))


def _search_growth(progress: float, variant: int) -> Image.Image:
    stack = LayerStack((1920, 1080))
    env, effects = stack.draw("environment"), stack.draw("effects")
    env.rectangle((0, 0, 1920, 1080), fill=(218, 233, 241))
    env.rounded_rectangle((350, 340, 1570, 520), radius=72, fill=WHITE, outline=INK, width=9)
    env.ellipse((410, 385, 470, 445), outline=BLUE, width=10)
    env.line((455, 435, 495, 475), fill=BLUE, width=10)
    reveal = phase(progress, 0.03, 0.94)
    cards = ((160, 650), (505, 650), (850, 650), (1195, 650), (1540, 650))
    for index, (x, y) in enumerate(cards):
        active = reveal >= index / len(cards)
        lift = round(70 * (1 - phase(reveal, index / len(cards), min(1.0, index / len(cards) + 0.25))))
        env.rounded_rectangle((x - 130, y - 115 + lift, x + 130, y + 115 + lift), radius=25, fill=WHITE if active else (193, 207, 216), outline=BLUE if active else (115, 129, 142), width=7)
        for row in range(3):
            env.rounded_rectangle((x - 92, y - 60 + row * 48 + lift, x + 92 - row * 18, y - 36 + row * 48 + lift), radius=8, fill=CYAN if active and row == 0 else (112, 132, 145))
    effects.line((250, 930, 1670, 930), fill=(78, 94, 108), width=7)
    for x, label in ((310, "1993"), (960, "SEARCH"), (1605, "ALWAYS ON")):
        effects.ellipse((x - 13, 917, x + 13, 943), fill=AMBER, outline=INK, width=3)
        effects.text((x, 970), label, font=cartoon._font(25, True), fill=NAVY, anchor="mm")
    _title(effects, "INFORMATION EXPANDED", "Search made abundance navigable")
    return stack.composite((218, 233, 241))


def _smartphone_shift(progress: float, variant: int) -> Image.Image:
    stack = LayerStack((1920, 1080))
    env, actors, effects = stack.draw("environment"), stack.draw("actors"), stack.draw("effects")
    env.rectangle((0, 0, 1920, 1080), fill=(225, 236, 241))
    env.rectangle((0, 780, 1920, 1080), fill=(181, 189, 194))
    env.rounded_rectangle((120, 300, 690, 760), radius=38, fill=(242, 242, 236), outline=INK, width=9)
    _screen(env, (205, 360, 605, 620), fill=(217, 233, 226))
    phone_x = round(970 + 250 * phase(progress, 0.04, 0.66))
    _phone(effects, phone_x, 530, 1.12, glow=phase(progress, 0.55, 0.90))
    draw_person(actors, (1550, 760), 0.92, shirt=GREEN, pants=(49, 60, 76), arm_raise=0.42)
    chart_left, chart_bottom = 780, 920
    effects.line((chart_left, chart_bottom, 1530, chart_bottom), fill=(77, 91, 104), width=6)
    heights = (0.35, 0.48, 0.66, 0.78, 0.91)
    for index, value in enumerate(heights):
        x = chart_left + index * 130
        visible = phase(progress, index * 0.10, 0.45 + index * 0.08)
        top = chart_bottom - round(240 * value * visible)
        effects.rounded_rectangle((x, top, x + 76, chart_bottom), radius=13, fill=BLUE if index < 4 else PURPLE)
    effects.text((790, 955), "35%", font=cartoon._font(26, True), fill=NAVY)
    effects.text((1320, 955), "91%", font=cartoon._font(26, True), fill=NAVY)
    _title(effects, "THE INTERNET BECAME CONSTANT", "From a desk to every moment of the day")
    return stack.composite((225, 236, 241))


def _algorithm_feed(progress: float, variant: int) -> Image.Image:
    stack = LayerStack((1920, 1080))
    env, effects = stack.draw("environment"), stack.draw("effects")
    env.rectangle((0, 0, 1920, 1080), fill=(210, 225, 237))
    env.rounded_rectangle((760, 245, 1160, 790), radius=52, fill=NAVY, outline=INK, width=10)
    env.text((960, 330), "RANKING", font=cartoon._font(42, True), fill=WHITE, anchor="mm")
    for index, label in enumerate(("WATCH", "PAUSE", "SHARE")):
        y = 430 + index * 110
        amount = phase(progress, 0.06 + index * 0.14, 0.52 + index * 0.12)
        env.rounded_rectangle((835, y, 1085, y + 62), radius=18, fill=(50, 70, 92), outline=CYAN if amount > 0.5 else (91, 108, 126), width=5)
        env.text((960, y + 31), label, font=cartoon._font(24, True), fill=WHITE, anchor="mm")
    cards = ((220, 300, BLUE), (220, 590, GREEN), (1700, 270, AMBER), (1700, 590, PURPLE))
    reveal = phase(progress, 0.04, 0.88)
    for index, (x, y, color) in enumerate(cards):
        local = phase(reveal, index * 0.12, 0.50 + index * 0.10)
        target_x = 650 if x < 960 else 1270
        current_x = round(x + (target_x - x) * local)
        env.rounded_rectangle((current_x - 150, y - 90, current_x + 150, y + 90), radius=24, fill=WHITE, outline=color, width=8)
        env.rounded_rectangle((current_x - 100, y - 35, current_x + 100, y + 10), radius=10, fill=color)
    output_y = round(900 - 80 * math.sin(progress * math.pi))
    effects.rounded_rectangle((1320, output_y - 70, 1770, output_y + 70), radius=30, fill=WHITE, outline=RED, width=8)
    effects.text((1545, output_y), "WHAT APPEARS NEXT", font=cartoon._font(28, True), fill=NAVY, anchor="mm")
    _title(effects, "THE FEED CHOOSES NEXT", "Behavioral signals become ranked recommendations")
    return stack.composite((210, 225, 237))


def _notification_lab(progress: float, variant: int) -> Image.Image:
    stack = LayerStack((1920, 1080))
    env, actors, effects = stack.draw("environment"), stack.draw("actors"), stack.draw("effects")
    env.rectangle((0, 0, 1920, 1080), fill=(229, 237, 240))
    env.rectangle((0, 800, 1920, 1080), fill=FLOOR)
    env.rounded_rectangle((160, 180, 1080, 780), radius=40, fill=WHITE, outline=INK, width=9)
    env.text((620, 270), "FOCUS TASK", font=cartoon._font(34, True), fill=NAVY, anchor="mm")
    for row in range(4):
        for col in range(6):
            color = BLUE if (row + col + variant) % 5 == 0 else (174, 188, 198)
            env.rounded_rectangle((310 + col * 100, 350 + row * 82, 370 + col * 100, 400 + row * 82), radius=10, fill=color)
    draw_person(actors, (1320, 760), 0.94, shirt=AMBER, pants=(49, 60, 76), arm_raise=0.06)
    ping = phase(progress, 0.35, 0.52)
    _phone(effects, 1610, 670, 0.62, glow=ping)
    baseline = 0.88
    performance = baseline - 0.28 * phase(progress, 0.43, 0.82)
    effects.line((1220, 300, 1740, 300), fill=(80, 95, 108), width=5)
    effects.line((1220, 300, 1220, 520), fill=(80, 95, 108), width=5)
    effects.line((1240, 500 - round(180 * baseline), 1480, 500 - round(180 * baseline), 1690, 500 - round(180 * performance)), fill=RED, width=12)
    effects.text((1450, 560), "PERFORMANCE", font=cartoon._font(24, True), fill=NAVY, anchor="mm")
    _title(effects, "THE COST OF INTERRUPTION", "A notification can disrupt the task without being opened")
    return stack.composite((229, 237, 240))


def _evidence_review(progress: float, variant: int) -> Image.Image:
    stack = LayerStack((1920, 1080))
    env, effects = stack.draw("environment"), stack.draw("effects")
    env.rectangle((0, 0, 1920, 1080), fill=(218, 230, 238))
    columns = (
        (130, 300, 850, 830, "MEASURED NOW", GREEN),
        (1070, 300, 1790, 830, "STILL UNKNOWN", AMBER),
    )
    for left, top, right, bottom, label, color in columns:
        env.rounded_rectangle((left, top, right, bottom), radius=40, fill=WHITE, outline=color, width=9)
        env.text(((left + right) // 2, top + 70), label, font=cartoon._font(34, True), fill=NAVY, anchor="mm")
    immediate = ("NOTIFICATIONS", "TASK SWITCHING", "DEVICE PRESENCE")
    unknown = ("PERMANENT CHANGE", "EVERY PERSON", "ONE ATTENTION SPAN")
    reveal = phase(progress, 0.04, 0.90)
    for index, label in enumerate(immediate):
        y = 440 + index * 105
        active = reveal > index * 0.18
        env.rounded_rectangle((230, y, 750, y + 64), radius=18, fill=(222, 239, 230) if active else (208, 214, 219))
        env.text((490, y + 32), label, font=cartoon._font(25, True), fill=NAVY, anchor="mm")
    for index, label in enumerate(unknown):
        y = 440 + index * 105
        active = reveal > 0.35 + index * 0.15
        env.rounded_rectangle((1170, y, 1690, y + 64), radius=18, fill=(248, 235, 203) if active else (208, 214, 219))
        env.text((1430, y + 32), label, font=cartoon._font(25, True), fill=NAVY, anchor="mm")
    effects.text((960, 930), "CAREFUL CLAIMS MAKE STRONGER DOCUMENTARIES", font=cartoon._font(30, True), fill=NAVY, anchor="mm")
    _title(effects, "WHAT THE EVIDENCE SAYS", "Immediate interference is not permanent decline")
    return stack.composite((218, 230, 238))


def _connected_benefits(progress: float, variant: int) -> Image.Image:
    stack = LayerStack((1920, 1080))
    env, actors, effects = stack.draw("environment"), stack.draw("actors"), stack.draw("effects")
    env.rectangle((0, 0, 1920, 1080), fill=(222, 237, 236))
    cards = (
        (110, 300, 590, 760, "LEARN", BLUE),
        (720, 300, 1200, 760, "CREATE", PURPLE),
        (1330, 300, 1810, 760, "NAVIGATE", GREEN),
    )
    reveal = phase(progress, 0.03, 0.88)
    for index, (left, top, right, bottom, label, color) in enumerate(cards):
        lift = round(55 * (1 - phase(reveal, index * 0.16, 0.48 + index * 0.14)))
        env.rounded_rectangle((left, top + lift, right, bottom + lift), radius=42, fill=WHITE, outline=color, width=9)
        env.text(((left + right) // 2, top + 75 + lift), label, font=cartoon._font(34, True), fill=NAVY, anchor="mm")
    # Classroom, creator desk, and map pin.
    for x in (225, 350, 475):
        draw_person(actors, (x, 650), 0.45, shirt=BLUE, pants=(50, 61, 76))
    env.rounded_rectangle((830, 455, 1090, 650), radius=24, fill=(220, 231, 239), outline=INK, width=7)
    env.polygon(((900, 610), (950, 500), (1000, 610)), fill=PURPLE)
    env.ellipse((1490, 450, 1650, 610), fill=(221, 239, 228), outline=GREEN, width=8)
    env.polygon(((1570, 650), (1518, 565), (1622, 565)), fill=GREEN)
    effects.line((590, 530, 720, 530), fill=CYAN, width=10)
    effects.line((1200, 530, 1330, 530), fill=CYAN, width=10)
    _title(effects, "CONNECTION CREATES CAPABILITY", "Access, creativity, and communication are real gains")
    return stack.composite((222, 237, 236))


def _fragmented_day(progress: float, variant: int) -> Image.Image:
    stack = LayerStack((1920, 1080))
    env, actors, effects = stack.draw("environment"), stack.draw("actors"), stack.draw("effects")
    env.rectangle((0, 0, 1920, 1080), fill=(220, 230, 238))
    separators = (640, 1280)
    for x in separators:
        env.line((x, 245, x, 970), fill=(118, 135, 149), width=5)
    labels = ((320, "STUDENT"), (960, "WORK"), (1600, "COMMUTE"))
    for x, label in labels:
        env.text((x, 300), label, font=cartoon._font(30, True), fill=NAVY, anchor="mm")
    draw_person(actors, (300, 775), 0.72, shirt=BLUE, pants=(49, 60, 76), arm_raise=0.18)
    draw_person(actors, (930, 775), 0.72, shirt=GREEN, pants=(49, 60, 76), arm_raise=0.18)
    draw_person(actors, (1550, 775), 0.72, shirt=PURPLE, pants=(49, 60, 76), arm_raise=0.18)
    pulse = phase(progress, 0.05, 0.94)
    for index in range(5):
        x = 90 + (index % 3) * 170
        y = 410 + (index // 3) * 110 + round(18 * math.sin((progress + index * 0.13) * math.pi * 2))
        effects.rounded_rectangle((x, y, x + 145, y + 70), radius=18, fill=WHITE, outline=BLUE if index == int(pulse * 4) else (120, 137, 151), width=5)
    for index in range(4):
        y = 410 + index * 100
        active = index == int(min(3, pulse * 4))
        effects.rounded_rectangle((730, y, 1170, y + 68), radius=18, fill=(238, 246, 240), outline=RED if active else GREEN, width=6)
    _phone(effects, 1700, 560, 0.55, glow=phase(progress, 0.30, 0.46))
    effects.rounded_rectangle((1370, 790, 1810, 900), radius=24, fill=WHITE, outline=AMBER, width=7)
    effects.text((1590, 845), "SHORT VIDEO → NEXT VIDEO", font=cartoon._font(23, True), fill=NAVY, anchor="mm")
    _title(effects, "A DAY SPLIT INTO FRAGMENTS", "Tabs, pings, and feeds share the same hours")
    return stack.composite((220, 230, 238))


def _intentional_design(progress: float, variant: int) -> Image.Image:
    stack = LayerStack((1920, 1080))
    env, actors, effects = stack.draw("environment"), stack.draw("actors"), stack.draw("effects")
    env.rectangle((0, 0, 1920, 1080), fill=(224, 237, 235))
    _phone(env, 430, 585, 1.0)
    settings = (("NOTIFICATIONS", 0.20), ("AUTOPLAY", 0.43), ("FOCUS MODE", 0.66))
    for index, (label, start) in enumerate(settings):
        y = 410 + index * 110
        env.text((760, y + 28), label, font=cartoon._font(25, True), fill=NAVY)
        enabled = phase(progress, start, start + 0.18) < 0.55 if index < 2 else phase(progress, start, start + 0.18) > 0.45
        color = GREEN if enabled else (145, 156, 166)
        env.rounded_rectangle((1120, y, 1300, y + 62), radius=31, fill=color, outline=INK, width=5)
        knob_x = 1262 if enabled else 1158
        env.ellipse((knob_x - 24, y + 7, knob_x + 24, y + 55), fill=WHITE, outline=INK, width=3)
    draw_person(actors, (1560, 760), 0.82, shirt=AMBER, pants=(49, 60, 76), arm_raise=0.64)
    effects.rounded_rectangle((1390, 380, 1780, 600), radius=28, fill=WHITE, outline=PURPLE, width=8)
    effects.text((1585, 440), "HUMANE DEFAULTS", font=cartoon._font(27, True), fill=NAVY, anchor="mm")
    for row, width in enumerate((290, 240, 320)):
        effects.rounded_rectangle((1440, 500 + row * 42, 1440 + width, 525 + row * 42), radius=8, fill=(146, 166, 177))
    _title(effects, "BETTER DEFAULTS RESTORE AGENCY", "Design can make interruption less automatic")
    return stack.composite((224, 237, 235))


def _attention_choice(progress: float, variant: int) -> Image.Image:
    stack = LayerStack((1920, 1080))
    env, actors, effects = stack.draw("environment"), stack.draw("actors"), stack.draw("effects")
    env.rectangle((0, 0, 1920, 1080), fill=(25, 42, 61))
    env.rectangle((0, 720, 1920, 1080), fill=(50, 63, 73))
    heights = (430, 330, 520, 390, 470, 310, 550, 360)
    for index, height in enumerate(heights):
        left = 80 + index * 230
        env.rectangle((left, 720 - height, left + 160, 720), fill=(42, 62, 82), outline=(78, 103, 128), width=5)
        for row in range(max(2, height // 90)):
            for col in range(2):
                active = ((index + row + col) % 3 == 0) and progress > 0.15
                color = AMBER if active else (57, 75, 93)
                env.rectangle((left + 28 + col * 64, 720 - height + 45 + row * 75, left + 60 + col * 64, 720 - height + 78 + row * 75), fill=color)
    draw_person(actors, (720, 875), 0.72, shirt=CYAN, pants=(29, 39, 54), arm_raise=0.08)
    draw_person(actors, (980, 875), 0.72, shirt=GREEN, pants=(29, 39, 54), arm_raise=0.08)
    draw_person(actors, (1240, 875), 0.72, shirt=PURPLE, pants=(29, 39, 54), arm_raise=0.08)
    basket_reveal = phase(progress, 0.28, 0.72)
    effects.rounded_rectangle((825, 860, 1135, 1020), radius=30, fill=(105, 76, 55), outline=INK, width=7)
    for index in range(3):
        x = 875 + index * 95
        y = round(830 - 50 * basket_reveal + index * 7)
        _phone(effects, x, y, 0.20)
    effects.rounded_rectangle((395, 65, 1525, 215), radius=34, fill=(8, 20, 36), outline=CYAN, width=6)
    effects.text((960, 118), "THE NETWORK CAN STAY AVAILABLE", font=cartoon._font(38, True), fill=WHITE, anchor="mm")
    effects.text((960, 170), "WITHOUT ALWAYS TAKING PRIORITY", font=cartoon._font(30, True), fill=(179, 211, 220), anchor="mm")
    return stack.composite((25, 42, 61))


RENDERERS = {
    "internet_early_web": _early_web,
    "internet_search_growth": _search_growth,
    "internet_smartphone_shift": _smartphone_shift,
    "internet_algorithm_feed": _algorithm_feed,
    "internet_notification_lab": _notification_lab,
    "internet_evidence_review": _evidence_review,
    "internet_connected_benefits": _connected_benefits,
    "internet_fragmented_day": _fragmented_day,
    "internet_intentional_design": _intentional_design,
    "internet_attention_choice": _attention_choice,
}


def render_planned_frame(
    scene: Any,
    template_id: str | None,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    if not is_internet_attention(scene) and template_id not in INTERNET_TEMPLATE_IDS:
        return _previous_render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    sequence = beat_template_sequence(scene, template_id)
    beat_index, local_progress = _beat_state(scene, float(time_seconds), float(duration_seconds))
    selected = sequence[min(beat_index, len(sequence) - 1)]
    return RENDERERS[selected](local_progress, beat_index % 6).convert("RGB")


# Register the domain templates and make the final routing functions authoritative.
cartoon.TEMPLATES = tuple(
    [template for template in cartoon.TEMPLATES if template.template_id not in INTERNET_TEMPLATE_IDS]
    + list(INTERNET_TEMPLATES)
)
cartoon.TEMPLATE_BY_ID.update(INTERNET_TEMPLATE_BY_ID)
patch.CARTOON_TEMPLATE_IDS.update(INTERNET_TEMPLATE_IDS)
patch._use_cartoon = _use_cartoon
cartoon.suggest_template = suggest_template
cartoon.render_planned_frame = render_planned_frame
