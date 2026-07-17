from __future__ import annotations

"""Additional Tech & Behavior compositions for long documentary sequences.

The original family had six non-terminal templates. A 60–70 second documentary
can contain far more than six generated scenes, making visible repetition
unavoidable even with perfect scoring. This module adds four genuinely distinct
visual ideas and registers matching landscape and native-Shorts renderers.
"""

from typing import Any

from PIL import Image, ImageDraw

from . import native_shorts as shorts
from . import tech_behavior_motion as base
from . import tech_behavior_truthful as truthful


EXPANSION_TEMPLATES = (
    base.TechTemplate(
        "attention_auction",
        "Attention Auction",
        "Show competing systems bidding for the next moment of a viewer's attention.",
        tuple("attention auction bidder advertisers compete competition target targeting highest opportunity feed reach".split()),
        "WHO COMPETES FOR YOUR ATTENTION?",
        "Multiple systems score the same next moment.",
    ),
    base.TechTemplate(
        "signal_feedback_loop",
        "Signal Feedback Loop",
        "Reveal how a prediction changes what is shown, creating the next behavioral signal.",
        tuple("feedback loop shown response react reaction next signal reinforce update model changes behavior".split()),
        "THE PREDICTION CHANGES THE NEXT SIGNAL",
        "What reaches you becomes new evidence.",
    ),
    base.TechTemplate(
        "profile_forecast",
        "Profile to Forecast",
        "Transform accumulated profile records into a forward-looking behavioral forecast.",
        tuple("profile record history identity forecast estimate future likely probability pattern document data".split()),
        "A PROFILE BECOMES A FORECAST",
        "Stored behavior is converted into likely outcomes.",
    ),
    base.TechTemplate(
        "consequence_map",
        "Recommendation Consequence Map",
        "Trace one ranking decision into several downstream choices and outcomes.",
        tuple("consequence outcome path pathway recommendation shapes reaches next choice influence decision downstream".split()),
        "RANKINGS SHAPE WHAT YOU SEE NEXT",
        "One selection changes the path in front of you.",
    ),
)


BEATS = {
    "attention_auction": (
        ("COMPETITORS", "Establish several systems competing for attention.", 0.16),
        ("SCORING", "Compare the hidden bids and relevance scores.", 0.52),
        ("WINNER", "Reveal the opportunity placed first.", 0.86),
    ),
    "signal_feedback_loop": (
        ("PREDICTION", "Establish the model's current forecast.", 0.16),
        ("EXPOSURE", "Show the selected content reaching the viewer.", 0.52),
        ("NEW SIGNAL", "Feed the viewer response back into the model.", 0.86),
    ),
    "profile_forecast": (
        ("PROFILE", "Collect the stored behavioral record.", 0.16),
        ("TRANSFORM", "Convert the record into weighted features.", 0.52),
        ("FORECAST", "Reveal a range of likely outcomes.", 0.86),
    ),
    "consequence_map": (
        ("RANK", "Select one opportunity from the field.", 0.16),
        ("PATHS", "Branch the selection into downstream choices.", 0.52),
        ("CONSEQUENCE", "Show how the visible environment changes.", 0.86),
    ),
}


PHRASE_WEIGHTS = {
    "attention_auction": {"highest bidder": 15, "compete for your attention": 15, "attention": 5, "targeting": 7},
    "signal_feedback_loop": {"change your behavior": 14, "what reaches you": 9, "next signal": 13, "feedback loop": 15},
    "profile_forecast": {"personality traits": 11, "future events": 12, "likely outcome": 11, "profile": 7},
    "consequence_map": {"what reaches you": 13, "help us navigate the world": 10, "shapes what": 11, "next choice": 10},
}


def _landscape_attention_auction(draw: ImageDraw.ImageDraw, progress: float, palette: dict[str, tuple[int, int, int]]) -> None:
    q = base._phase(progress, 0.05, 0.90)
    bidders = (("NEWS", 0.62), ("VIDEO", 0.88), ("SHOP", 0.71), ("SOCIAL", 0.79))
    base._panel(draw, (110, 365, 1810, 900), palette, outline=palette["accent_alt"])
    base.engine._text(draw, (960, 415), "HIDDEN ATTENTION MARKET", 28, palette["accent"], bold=True, anchor="mm")
    for index, (label, score) in enumerate(bidders):
        y = 510 + index * 92
        base.engine._text(draw, (250, y), label, 24, palette["white"], bold=True, anchor="lm")
        draw.rounded_rectangle((440, y - 16, 1510, y + 16), radius=16, fill=palette["panel_alt"])
        width = round(1070 * score * q)
        color = palette["good"] if label == "VIDEO" else palette["accent_alt"]
        if width:
            draw.rounded_rectangle((440, y - 16, 440 + width, y + 16), radius=16, fill=color)
        base.engine._text(draw, (1600, y), f"{round(score * q * 100)}", 23, color, bold=True, anchor="mm")
    if q > 0.70:
        base._pill(draw, (960, 850), "VIDEO WINS THE NEXT MOMENT", palette, fill=palette["good"], width=470, text_fill=palette["ink"])


def _landscape_feedback_loop(draw: ImageDraw.ImageDraw, progress: float, palette: dict[str, tuple[int, int, int]]) -> None:
    q = base._phase(progress, 0.04, 0.90)
    points = ((330, 610, "MODEL"), (820, 450, "RANK"), (1390, 610, "VIEW"), (820, 805, "RESPONSE"))
    base._panel(draw, (110, 350, 1810, 920), palette, outline=palette["accent"])
    for index, (x, y, label) in enumerate(points):
        active = q > index * 0.17
        color = palette["accent"] if index % 2 == 0 else palette["accent_alt"]
        base._node(draw, (x, y), 62, color if active else palette["panel_alt"], label=str(index + 1))
        base.engine._text(draw, (x, y + 105), label, 23, palette["white"] if active else palette["muted"], bold=True, anchor="mm")
    for index, (start, end) in enumerate(((0, 1), (1, 2), (2, 3), (3, 0))):
        if q > index * 0.17:
            x1, y1, _ = points[start]
            x2, y2, _ = points[end]
            draw.line((x1, y1, x2, y2), fill=palette["good"], width=7)
    base.engine._text(draw, (960, 865), "THE OUTPUT BECOMES THE NEXT INPUT", 25, palette["warning"], bold=True, anchor="mm")


def _landscape_profile_forecast(draw: ImageDraw.ImageDraw, progress: float, palette: dict[str, tuple[int, int, int]]) -> None:
    q = base._phase(progress, 0.05, 0.90)
    base._panel(draw, (100, 360, 670, 910), palette, outline=palette["accent_alt"])
    base.engine._text(draw, (385, 415), "PROFILE RECORD", 27, palette["accent_alt"], bold=True, anchor="mm")
    for index, label in enumerate(("SEARCH", "WATCH", "PURCHASE", "PAUSE", "DRAFT")):
        y = 505 + index * 70
        base.engine._text(draw, (175, y), label, 20, palette["muted"], bold=True)
        draw.rounded_rectangle((350, y, 590, y + 18), radius=9, fill=palette["panel_alt"])
        draw.rounded_rectangle((350, y, 350 + round((95 + index * 25) * q), y + 18), radius=9, fill=palette["accent_alt"])
    draw.line((710, 635, 960, 635), fill=palette["accent"], width=8)
    draw.polygon(((960, 635), (920, 610), (920, 660)), fill=palette["accent"])
    base._panel(draw, (1010, 360, 1820, 910), palette, outline=palette["good"])
    base.engine._text(draw, (1415, 415), "FORECAST RANGE", 27, palette["good"], bold=True, anchor="mm")
    for index, (label, score) in enumerate((("WATCH", 0.82), ("IGNORE", 0.46), ("BUY", 0.31))):
        y = 535 + index * 125
        base.engine._text(draw, (1110, y), label, 23, palette["white"], bold=True)
        draw.rounded_rectangle((1290, y, 1690, y + 34), radius=17, fill=palette["panel_alt"])
        draw.rounded_rectangle((1290, y, 1290 + round(400 * score * q), y + 34), radius=17, fill=palette["good"] if index == 0 else palette["accent"])
        base.engine._text(draw, (1745, y + 17), f"{round(score * q * 100)}%", 21, palette["muted"], bold=True, anchor="mm")


def _landscape_consequence_map(draw: ImageDraw.ImageDraw, progress: float, palette: dict[str, tuple[int, int, int]]) -> None:
    q = base._phase(progress, 0.04, 0.90)
    base._panel(draw, (100, 350, 1820, 920), palette, outline=palette["accent"])
    base._node(draw, (300, 635), 66, palette["good"], label="1")
    base.engine._text(draw, (300, 750), "RANKED FIRST", 23, palette["good"], bold=True, anchor="mm")
    outcomes = ((900, 465, "WATCH"), (900, 635, "SEARCH"), (900, 805, "IGNORE"), (1510, 520, "NEXT FEED"), (1510, 750, "NEXT OFFER"))
    for index, (x, y, label) in enumerate(outcomes):
        active = q > index * 0.13
        color = palette["accent"] if index < 3 else palette["accent_alt"]
        base._node(draw, (x, y), 40, color if active else palette["panel_alt"])
        base.engine._text(draw, (x, y + 72), label, 21, palette["white"] if active else palette["muted"], bold=True, anchor="mm")
    for index, target in enumerate(outcomes[:3]):
        if q > index * 0.13:
            draw.line((366, 635, target[0] - 48, target[1]), fill=palette["accent"], width=5)
    for index, target in enumerate(outcomes[3:]):
        if q > 0.48 + index * 0.13:
            draw.line((940, 550 + index * 155, target[0] - 48, target[1]), fill=palette["accent_alt"], width=5)


def _shorts_attention(canvas: Image.Image, progress: float, accent: shorts.RGB) -> None:
    draw = ImageDraw.Draw(canvas)
    q = shorts._phase(progress, 0.03, 0.90)
    shorts._text(draw, (540, 470), "HIDDEN ATTENTION MARKET", 25, shorts.MUTED, bold=True, anchor="mm")
    for index, (label, score, color) in enumerate((("NEWS", .62, shorts.PURPLE), ("VIDEO", .88, shorts.GREEN), ("SHOP", .71, shorts.AMBER), ("SOCIAL", .79, shorts.CYAN))):
        y = 620 + index * 155
        shorts._text(draw, (120, y), label, 24, shorts.WHITE, bold=True, anchor="lm")
        shorts._bar(draw, (310, y - 20, 930, y + 20), score * q, color)
    if q > .68:
        shorts._chip(draw, (540, 1300), "VIDEO RANKED FIRST", shorts.GREEN)


def _shorts_loop(canvas: Image.Image, progress: float, accent: shorts.RGB) -> None:
    draw = ImageDraw.Draw(canvas)
    q = shorts._phase(progress, 0.03, 0.90)
    points = ((540, 590, "MODEL"), (800, 850, "RANK"), (540, 1110, "VIEW"), (280, 850, "RESPONSE"))
    for index, (x, y, label) in enumerate(points):
        color = shorts.CYAN if index % 2 == 0 else shorts.PURPLE
        draw.ellipse((x - 62, y - 62, x + 62, y + 62), fill=color if q > index * .16 else (37, 52, 75))
        shorts._text(draw, (x, y + 100), label, 22, shorts.WHITE, bold=True, anchor="mm")
    for index, (start, end) in enumerate(((0, 1), (1, 2), (2, 3), (3, 0))):
        if q > index * .16:
            shorts._arrow(draw, points[start][:2], points[end][:2], shorts.GREEN, 1.0, 7)
    shorts._text(draw, (540, 1325), "OUTPUT → NEXT INPUT", 26, shorts.GREEN, bold=True, anchor="mm")


def _shorts_forecast(canvas: Image.Image, progress: float, accent: shorts.RGB) -> None:
    draw = ImageDraw.Draw(canvas)
    q = shorts._phase(progress, 0.03, 0.90)
    draw.rounded_rectangle((90, 500, 470, 1320), radius=38, fill=(13, 31, 55), outline=shorts.PURPLE, width=4)
    shorts._text(draw, (280, 565), "PROFILE", 26, shorts.PURPLE, bold=True, anchor="mm")
    for index in range(7):
        y = 690 + index * 70
        draw.rounded_rectangle((145, y, 415, y + 25), radius=12, fill=shorts.PURPLE if q > index * .09 else (42, 53, 73))
    shorts._arrow(draw, (485, 905), (595, 905), shorts.CYAN, q, 7)
    draw.rounded_rectangle((610, 500, 990, 1320), radius=38, fill=(13, 31, 55), outline=shorts.GREEN, width=4)
    shorts._text(draw, (800, 565), "FORECAST", 26, shorts.GREEN, bold=True, anchor="mm")
    for index, (label, score) in enumerate((("WATCH", .82), ("IGNORE", .46), ("BUY", .31))):
        y = 730 + index * 170
        shorts._text(draw, (665, y), label, 22, shorts.WHITE, bold=True)
        shorts._bar(draw, (665, y + 45, 930, y + 75), score * q, shorts.GREEN if index == 0 else shorts.CYAN)


def _shorts_consequence(canvas: Image.Image, progress: float, accent: shorts.RGB) -> None:
    draw = ImageDraw.Draw(canvas)
    q = shorts._phase(progress, 0.03, 0.90)
    shorts._chip(draw, (540, 555), "RANKED FIRST", shorts.GREEN)
    root = (540, 680)
    targets = ((230, 900, "WATCH"), (540, 1030, "SEARCH"), (850, 900, "IGNORE"), (330, 1250, "NEXT FEED"), (750, 1250, "NEXT OFFER"))
    for index, target in enumerate(targets):
        active = q > index * .12
        start = root if index < 3 else targets[index - 3][:2]
        shorts._arrow(draw, start, target[:2], shorts.CYAN if index < 3 else shorts.PURPLE, max(0, q - index * .08), 6)
        draw.ellipse((target[0] - 34, target[1] - 34, target[0] + 34, target[1] + 34), fill=shorts.GREEN if active else (40, 53, 75))
        shorts._text(draw, (target[0], target[1] + 68), target[2], 20, shorts.WHITE if active else shorts.MUTED, bold=True, anchor="mm")


def install(route: Any) -> None:
    if "attention_auction" in base.TEMPLATE_BY_ID:
        return
    base.TEMPLATES = (*base.TEMPLATES, *EXPANSION_TEMPLATES)
    base.TEMPLATE_BY_ID = {template.template_id: template for template in base.TEMPLATES}
    base.BEATS_BY_TEMPLATE.update(BEATS)
    base.CAMERA_PROFILES.update({template.template_id: ((0.28, 0.52), (0.72, 0.52), 0.012) for template in EXPANSION_TEMPLATES})
    base.RENDERERS.update({"attention_auction": _landscape_attention_auction, "signal_feedback_loop": _landscape_feedback_loop, "profile_forecast": _landscape_profile_forecast, "consequence_map": _landscape_consequence_map})
    truthful.TEMPLATE_PHRASE_WEIGHTS.update(PHRASE_WEIGHTS)
    truthful.TEMPLATES = base.TEMPLATES
    truthful.TEMPLATE_BY_ID = base.TEMPLATE_BY_ID
    route.base.TEMPLATES = base.TEMPLATES
    route.base.TEMPLATE_BY_ID = base.TEMPLATE_BY_ID
    route.truthful.TEMPLATES = base.TEMPLATES
    route.truthful.TEMPLATE_BY_ID = base.TEMPLATE_BY_ID
    route.SEMANTIC_VARIANT_GROUPS["ranking"].update({"attention_auction", "consequence_map"})
    route.SEMANTIC_VARIANT_GROUPS["behavioral_signals"].update({"signal_feedback_loop", "profile_forecast"})
    shorts.COMPOSITIONS.update({
        ("tech_behavior_motion", "attention_auction"): shorts.ShortsComposition("ATTENTION IS A COMPETITION"),
        ("tech_behavior_motion", "signal_feedback_loop"): shorts.ShortsComposition("OUTPUT BECOMES NEW EVIDENCE"),
        ("tech_behavior_motion", "profile_forecast"): shorts.ShortsComposition("A PROFILE BECOMES A FORECAST"),
        ("tech_behavior_motion", "consequence_map"): shorts.ShortsComposition("ONE RANKING CHANGES THE PATH"),
    })
    shorts.RENDERERS.update({
        ("tech_behavior_motion", "attention_auction"): _shorts_attention,
        ("tech_behavior_motion", "signal_feedback_loop"): _shorts_loop,
        ("tech_behavior_motion", "profile_forecast"): _shorts_forecast,
        ("tech_behavior_motion", "consequence_map"): _shorts_consequence,
    })


# This module is imported from app.services.__init__. At this point the base Tech
# renderer is complete; importing the route patch finishes its final-pass setup,
# then the expansion is registered for both selection and rendering.
from . import tech_behavior_route_patch as _route  # noqa: E402

install(_route)
