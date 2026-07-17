from __future__ import annotations

import math

from PIL import Image, ImageDraw

from . import documentary_assets as assets
from . import finance_motion as base
from . import finance_motion_polish as polish

# Visual Composition v1.2 replaces primitive bar-only layouts with a reusable
# semantic finance illustration vocabulary. It deliberately keeps rendering in
# Pillow so generated footage remains local, deterministic, rights-clean, and
# portable across ordinary Homebrew FFmpeg installations.

TEMPLATES = polish.TEMPLATES
OUTPUT_WIDTH = polish.OUTPUT_WIDTH
OUTPUT_HEIGHT = polish.OUTPUT_HEIGHT
template_catalog = polish.template_catalog
suggest_template = polish.suggest_template
ffmpeg_encoder_command = polish.ffmpeg_encoder_command
_background = polish._background

WHITE = base.WHITE
MUTED = base.MUTED
PANEL = base.PANEL
PANEL_LIGHT = base.PANEL_LIGHT
PURPLE = base.PURPLE
PURPLE_LIGHT = base.PURPLE_LIGHT
GREEN = base.GREEN
GREEN_LIGHT = base.GREEN_LIGHT
RED = base.RED
RED_LIGHT = base.RED_LIGHT
AMBER = base.AMBER

CYAN = (34, 211, 238)
CYAN_LIGHT = (165, 243, 252)
BLUE = (59, 130, 246)
BLUE_LIGHT = (191, 219, 254)
CORAL = (251, 113, 133)
GOLD = (245, 190, 73)
SLATE = (71, 85, 105)
INK = (9, 14, 27)
DEEP = (13, 20, 36)

SEMANTIC_ACCENT = {
    "paycheck_split": CYAN,
    "expense_breakdown": AMBER,
    "empty_balance": CORAL,
    "recurring_transfer": BLUE,
    "index_growth": GREEN,
    "compound_growth": PURPLE,
    "pay_self_comparison": GREEN,
    "subscribe_cta": GOLD,
}


def _shadowed_round_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: tuple[int, int, int] = PANEL,
    outline: tuple[int, int, int] | None = None,
    radius: int = 28,
    shadow: int = 16,
) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(
        (left + shadow, top + shadow, right + shadow, bottom + shadow),
        radius=radius,
        fill=(3, 6, 14),
    )
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2)


def _label(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    value: str,
    *,
    fill: tuple[int, int, int] = MUTED,
    size: int = 25,
    anchor: str | None = None,
) -> None:
    base._text(draw, position, value, size, fill, bold=True, anchor=anchor)


def _value(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    value: str,
    *,
    fill: tuple[int, int, int] = WHITE,
    size: int = 54,
    anchor: str | None = None,
) -> None:
    base._text(draw, position, value, size, fill, bold=True, anchor=anchor)


def _pill(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    text: str,
    *,
    fill: tuple[int, int, int],
    text_fill: tuple[int, int, int] = WHITE,
    width: int = 190,
    height: int = 58,
    size: int = 24,
) -> None:
    x, y = center
    draw.rounded_rectangle(
        (x - width // 2, y - height // 2, x + width // 2, y + height // 2),
        radius=height // 2,
        fill=fill,
    )
    base._text(draw, (x, y), text, size, text_fill, bold=True, anchor="mm")


def _arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    fill: tuple[int, int, int],
    width: int = 8,
) -> None:
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=fill, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    length = 28
    spread = 0.55
    draw.polygon(
        (
            (x2, y2),
            (
                round(x2 - length * math.cos(angle - spread)),
                round(y2 - length * math.sin(angle - spread)),
            ),
            (
                round(x2 - length * math.cos(angle + spread)),
                round(y2 - length * math.sin(angle + spread)),
            ),
        ),
        fill=fill,
    )


def _icon_wallet(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    *,
    scale: float = 1.0,
    accent: tuple[int, int, int] = CYAN,
    empty: bool = False,
) -> None:
    assets.render_asset(draw, "wallet", center, scale=scale, accent=accent, state="empty" if empty else "default")


def _icon_card(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    *,
    scale: float = 1.0,
    accent: tuple[int, int, int] = BLUE,
    declined: bool = False,
) -> None:
    assets.render_asset(draw, "payment_card", center, scale=scale, accent=accent, state="declined" if declined else "default")


def _icon_house(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    *,
    scale: float = 1.0,
    accent: tuple[int, int, int] = AMBER,
) -> None:
    assets.render_asset(draw, "home", center, scale=scale, accent=accent)


def _icon_bag(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    *,
    scale: float = 1.0,
    accent: tuple[int, int, int] = GREEN,
) -> None:
    assets.render_asset(draw, "groceries", center, scale=scale, accent=accent)


def _icon_calendar(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    *,
    scale: float = 1.0,
    accent: tuple[int, int, int] = BLUE,
    day: str = "15",
) -> None:
    assets.render_asset(draw, "calendar", center, scale=scale, accent=accent)
    _value(draw, (center[0], center[1] + round(20 * scale)), day, size=round(36 * scale), anchor="mm")


def _icon_bank(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    *,
    scale: float = 1.0,
    accent: tuple[int, int, int] = PURPLE,
) -> None:
    assets.render_asset(draw, "bank", center, scale=scale, accent=accent)


def _icon_paycheck(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    *,
    scale: float = 1.0,
    accent: tuple[int, int, int] = GREEN,
    received: bool = False,
) -> None:
    assets.render_asset(draw, "paycheck", center, scale=scale, accent=accent, state="received" if received else "default")


def _coin(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    *,
    radius: int = 34,
    fill: tuple[int, int, int] = GOLD,
    label: str = "$",
) -> None:
    x, y = center
    draw.ellipse((x - radius + 7, y - radius + 9, x + radius + 7, y + radius + 9), fill=(4, 8, 17))
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill, outline=(255, 230, 150), width=3)
    base._text(draw, (x, y), label, max(20, radius), (48, 39, 18), bold=True, anchor="mm")


def _phone(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    accent: tuple[int, int, int],
) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    draw.rounded_rectangle((left + 14, top + 18, right + 14, bottom + 18), radius=52, fill=(3, 6, 14))
    draw.rounded_rectangle(box, radius=52, fill=(18, 26, 42), outline=accent, width=4)
    draw.rounded_rectangle((left + 20, top + 28, right - 20, bottom - 26), radius=38, fill=(8, 14, 27))
    draw.rounded_rectangle(((left + right) // 2 - 56, top + 14, (left + right) // 2 + 56, top + 28), radius=7, fill=(59, 70, 91))
    return left + 46, top + 70, right - 46, bottom - 50


def _common_composed(image: Image.Image, template: base.MotionTemplate) -> ImageDraw.ImageDraw:
    draw = ImageDraw.Draw(image)
    accent = SEMANTIC_ACCENT.get(template.template_id, PURPLE)
    _pill(draw, (220, 96), "MONEY SYSTEM", fill=(29, 40, 61), text_fill=accent, width=220, height=48, size=20)
    base._text(draw, (110, 145), template.title, 68, bold=True)
    base._text(draw, (112, 230), template.subtitle, 30, base.PURPLE_LIGHT)
    draw.rounded_rectangle((110, 286, 510, 294), radius=4, fill=accent)
    return draw


def _paycheck_composed(draw: ImageDraw.ImageDraw, t: float) -> None:
    arrive = base._progress(t, 0.18, 0.72)
    split = base._progress(t, 0.76, 0.85)
    transfer = base._progress(t, 1.05, 1.20)
    confirm = base._progress(t, 2.12, 0.42)

    _shadowed_round_rect(draw, (120, 345, 650, 850), fill=(18, 29, 47), outline=CYAN)
    _label(draw, (170, 392), "PAYCHECK", fill=CYAN_LIGHT, size=28)
    _value(draw, (385, 495), f"${round(5000 * arrive):,}", size=76, anchor="mm")
    _icon_wallet(draw, (385, 675), scale=1.15, accent=CYAN)

    _shadowed_round_rect(draw, (1050, 345, 1800, 575), fill=(46, 35, 28), outline=AMBER)
    _icon_house(draw, (1165, 455), scale=0.65, accent=AMBER)
    _label(draw, (1285, 402), "LIFE + EXPENSES", fill=(253, 230, 138), size=28)
    _value(draw, (1285, 470), f"{round(90 * split)}%", size=58)

    _shadowed_round_rect(draw, (1050, 625, 1800, 855), fill=(14, 48, 43), outline=GREEN)
    _icon_bank(draw, (1170, 735), scale=0.60, accent=GREEN)
    _label(draw, (1285, 682), "FUTURE SELF", fill=GREEN_LIGHT, size=28)
    _value(draw, (1285, 752), f"{round(10 * split)}%", fill=GREEN_LIGHT, size=62)

    if split > 0.05:
        _arrow(draw, (660, 555), (1010, 455), fill=AMBER, width=7)
        _arrow(draw, (660, 655), (1010, 735), fill=GREEN, width=9)

    token_x = round(base._lerp(685, 1035, transfer))
    token_y = round(base._lerp(660, 735, transfer) - 70 * math.sin(math.pi * transfer))
    _coin(draw, (token_x, token_y), radius=42, fill=GREEN_LIGHT, label="10")
    if confirm > 0:
        _pill(draw, (1515, 826), "TRANSFERRED FIRST", fill=(18, 75, 62), text_fill=GREEN_LIGHT, width=360, size=23)


def _expenses_composed(draw: ImageDraw.ImageDraw, t: float) -> None:
    paycheck = base._progress(t, 0.15, 0.65)
    stages = [base._progress(t, 0.58 + index * 0.34, 0.58) for index in range(3)]
    drained = sum((0.46, 0.28, 0.20)[i] * stages[i] for i in range(3))
    remaining = max(0, round(100 * (1 - drained)))

    _shadowed_round_rect(draw, (110, 360, 620, 845), fill=(18, 29, 47), outline=CYAN)
    _label(draw, (160, 410), "PAYCHECK AVAILABLE", fill=CYAN_LIGHT)
    _value(draw, (365, 520), f"${round(5000 * paycheck):,}", size=72, anchor="mm")
    draw.rounded_rectangle((170, 610, 560, 670), radius=20, fill=(40, 53, 76))
    width = round(390 * max(0.0, remaining / 100))
    if width:
        draw.rounded_rectangle((170, 610, 170 + width, 670), radius=20, fill=CYAN)
    _value(draw, (365, 744), f"{remaining}% LEFT", fill=CYAN_LIGHT if remaining > 20 else CORAL, size=42, anchor="mm")

    cards = (
        ("RENT", "46%", (760, 360, 1110, 585), _icon_house, AMBER),
        ("GROCERIES", "28%", (1195, 360, 1545, 585), _icon_bag, GREEN),
        ("LIFESTYLE", "20%", (980, 645, 1330, 870), _icon_card, PURPLE),
    )
    for index, (label, percent, box, icon, accent) in enumerate(cards):
        left, top, right, bottom = box
        visible = stages[index]
        _shadowed_round_rect(draw, box, fill=(24, 31, 47), outline=accent)
        icon(draw, ((left + right) // 2, top + 82), scale=0.48, accent=accent)
        _label(draw, ((left + right) // 2, top + 151), label, fill=accent, size=24, anchor="mm")
        _value(draw, ((left + right) // 2, top + 194), f"{round(int(percent[:-1]) * visible)}%", size=38, anchor="mm")
        if visible > 0:
            _arrow(draw, (620, 540 + index * 55), (left - 28, (top + bottom) // 2), fill=accent, width=6)


def _empty_composed(draw: ImageDraw.ImageDraw, t: float) -> None:
    progress = base._progress(t, 0.34, 1.45)
    remaining = max(0, round(4200 * (1 - progress)))
    left, top, right, bottom = _phone(draw, (245, 330, 985, 900), accent=CORAL)
    _label(draw, (left, top), "EVERYDAY CHECKING", fill=BLUE_LIGHT, size=25)
    _label(draw, (left, top + 72), "AVAILABLE BALANCE", size=23)
    _value(draw, (left, top + 150), f"${remaining:,.2f}", fill=WHITE if remaining > 0 else CORAL, size=78)
    draw.rounded_rectangle((left, top + 250, right, top + 272), radius=11, fill=(48, 61, 83))
    fill_width = round((right - left) * max(0.0, 1 - progress))
    if fill_width:
        draw.rounded_rectangle((left, top + 250, left + fill_width, top + 272), radius=11, fill=BLUE)
    _pill(draw, ((left + right) // 2, top + 360), "PAYCHECK EXHAUSTED" if progress > 0.8 else "SPENDING CYCLE", fill=(76, 26, 39), text_fill=RED_LIGHT, width=360)

    _shadowed_round_rect(draw, (1110, 360, 1790, 865), fill=(27, 23, 37), outline=CORAL)
    _icon_wallet(draw, (1450, 535), scale=1.20, accent=CORAL, empty=True)
    _icon_card(draw, (1450, 720), scale=0.78, accent=CORAL, declined=progress > 0.70)
    if progress > 0.70:
        _pill(draw, (1450, 830), "NOTHING LEFT", fill=(94, 28, 43), text_fill=RED_LIGHT, width=280)


def _transfer_composed(draw: ImageDraw.ImageDraw, t: float) -> None:
    transfer = base._progress(t, 0.42, 1.35)
    confirmed = base._progress(t, 1.65, 0.45)

    _shadowed_round_rect(draw, (110, 350, 650, 845), fill=(20, 30, 47), outline=BLUE)
    _icon_card(draw, (380, 515), scale=0.92, accent=BLUE)
    _label(draw, (380, 655), "CHECKING", fill=BLUE_LIGHT, anchor="mm")
    _value(draw, (380, 725), f"{100 - round(10 * transfer)}%", size=62, anchor="mm")

    _shadowed_round_rect(draw, (1270, 350, 1810, 845), fill=(15, 48, 42), outline=GREEN)
    _icon_bank(draw, (1540, 505), scale=0.84, accent=GREEN)
    _label(draw, (1540, 655), "INDEX FUND", fill=GREEN_LIGHT, anchor="mm")
    _value(draw, (1540, 725), f"+{round(10 * transfer)}%", fill=GREEN_LIGHT, size=62, anchor="mm")

    _icon_calendar(draw, (960, 465), scale=0.72, accent=PURPLE, day="PAY")
    _arrow(draw, (675, 620), (1245, 620), fill=PURPLE_LIGHT, width=9)
    token_x = round(base._lerp(720, 1200, transfer))
    token_y = round(620 - 85 * math.sin(math.pi * transfer))
    _coin(draw, (token_x, token_y), radius=44, fill=GREEN_LIGHT, label="10")
    _pill(draw, (960, 810), "AUTOMATIC EVERY PAYDAY" if confirmed < 0.2 else "SCHEDULE CONFIRMED", fill=(29, 48, 78) if confirmed < 0.2 else (17, 75, 63), text_fill=BLUE_LIGHT if confirmed < 0.2 else GREEN_LIGHT, width=430)


def _index_composed(draw: ImageDraw.ImageDraw, t: float) -> None:
    _shadowed_round_rect(draw, (110, 335, 1810, 890), fill=(15, 28, 42), outline=GREEN)
    chart_left, chart_top, chart_right, chart_bottom = 560, 405, 1715, 800
    draw.line((chart_left, chart_bottom, chart_right, chart_bottom), fill=SLATE, width=3)
    draw.line((chart_left, chart_top, chart_left, chart_bottom), fill=SLATE, width=3)

    points: list[tuple[int, int]] = []
    values = (0.10, 0.18, 0.28, 0.40, 0.57, 0.80)
    for index, value in enumerate(values):
        progress = base._progress(t, 0.22 + index * 0.13, 0.78)
        x = chart_left + 80 + index * 190
        y = chart_bottom - round(360 * value * progress)
        points.append((x, y))
        if progress > 0.06:
            _coin(draw, (x, chart_bottom - 42), radius=27, fill=GOLD, label="+")
            draw.line((x, chart_bottom - 72, x, y + 18), fill=(39, 91, 76), width=4)
            draw.ellipse((x - 11, y - 11, x + 11, y + 11), fill=GREEN_LIGHT)
    visible = [point for index, point in enumerate(points) if base._progress(t, 0.22 + index * 0.13, 0.78) > 0.06]
    if len(visible) > 1:
        draw.line(visible, fill=GREEN, width=10, joint="curve")

    _icon_bank(draw, (330, 505), scale=0.78, accent=GREEN)
    _label(draw, (330, 650), "LOW-COST INDEX", fill=GREEN_LIGHT, anchor="mm")
    _value(draw, (330, 720), "MONTHLY", size=42, anchor="mm")
    _pill(draw, (1135, 850), "CONTRIBUTIONS + MARKET TIME", fill=(18, 70, 60), text_fill=GREEN_LIGHT, width=520)


def _compound_composed(draw: ImageDraw.ImageDraw, t: float) -> None:
    _shadowed_round_rect(draw, (110, 335, 1810, 890), fill=(24, 22, 45), outline=PURPLE)
    timeline_y = 760
    draw.line((230, timeline_y, 1690, timeline_y), fill=(76, 55, 140), width=6)

    points: list[tuple[int, int]] = []
    for index, value in enumerate((34, 54, 84, 128, 190, 270)):
        progress = base._progress(t, 0.20 + index * 0.15, 0.72)
        x = 285 + index * 270
        height = round(value * progress)
        y = timeline_y - height - 70
        points.append((x, y))
        _coin(draw, (x, timeline_y), radius=28 + round(index * 1.8), fill=GOLD, label="+")
        if progress > 0.05:
            draw.line((x, timeline_y - 34, x, y + 26), fill=(76, 55, 140), width=5)
            radius = 28 + round(index * 8 * progress)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=PURPLE, outline=PURPLE_LIGHT, width=4)
            _value(draw, (x, y), f"Y{index + 1}", size=22, anchor="mm")
    visible = [point for index, point in enumerate(points) if base._progress(t, 0.20 + index * 0.15, 0.72) > 0.08]
    if len(visible) > 1:
        draw.line(visible, fill=GREEN, width=9, joint="curve")

    momentum = round(100 + 260 * base._progress(t, 0.74, 1.35))
    _pill(draw, (960, 415), f"COMPOUND MOMENTUM  {momentum}%", fill=(57, 41, 108), text_fill=PURPLE_LIGHT, width=520, height=70, size=28)
    _label(draw, (960, 500), "CONTRIBUTIONS CREATE RETURNS. RETURNS CREATE MORE RETURNS.", fill=GREEN_LIGHT, size=25, anchor="mm")


def _comparison_composed(draw: ImageDraw.ImageDraw, t: float) -> None:
    progress = base._progress(t, 0.34, 0.95)
    _shadowed_round_rect(draw, (100, 340, 895, 890), fill=(57, 24, 35), outline=CORAL)
    _shadowed_round_rect(draw, (1025, 340, 1820, 890), fill=(13, 52, 45), outline=GREEN)

    _label(draw, (498, 400), "SPEND FIRST", fill=RED_LIGHT, size=34, anchor="mm")
    _icon_wallet(draw, (498, 565), scale=0.86, accent=CORAL, empty=True)
    _icon_card(draw, (280, 750), scale=0.56, accent=CORAL, declined=True)
    _icon_house(draw, (500, 750), scale=0.46, accent=AMBER)
    _icon_bag(draw, (710, 750), scale=0.48, accent=GREEN)
    _pill(draw, (498, 840), "$0 LEFT", fill=(102, 31, 47), text_fill=RED_LIGHT, width=250)

    _label(draw, (1422, 400), "PAY YOURSELF FIRST", fill=GREEN_LIGHT, size=34, anchor="mm")
    _icon_wallet(draw, (1218, 585), scale=0.72, accent=CYAN)
    _arrow(draw, (1325, 585), (1515, 585), fill=GREEN, width=9)
    _icon_bank(draw, (1630, 585), scale=0.62, accent=GREEN)
    _value(draw, (1422, 735), f"{round(10 * progress)}% INVESTED", fill=GREEN_LIGHT, size=54, anchor="mm")
    draw.rounded_rectangle((1160, 800, 1685, 828), radius=14, fill=(22, 72, 62))
    draw.rounded_rectangle((1160, 800, 1160 + round(525 * progress), 828), radius=14, fill=GREEN)


def _cta_composed(draw: ImageDraw.ImageDraw, t: float) -> None:
    reveal = base._progress(t, 0.24, 0.88)
    pulse = 1 + 0.02 * math.sin(t * 4.2)
    _shadowed_round_rect(draw, (210, 340, 1040, 870), fill=(22, 28, 45), outline=GOLD)
    _label(draw, (280, 390), "YOUR WEALTH BLUEPRINT", fill=(253, 230, 138), size=30)
    for index, (label, accent) in enumerate((("PAY YOURSELF FIRST", CYAN), ("AUTOMATE 10%", GREEN), ("LET TIME COMPOUND", PURPLE_LIGHT))):
        y = 500 + index * 112
        draw.rounded_rectangle((280, y - 34, 344, y + 30), radius=14, fill=accent)
        base._text(draw, (312, y), str(index + 1), 27, INK, bold=True, anchor="mm")
        _label(draw, (380, y - 8), label, fill=WHITE, size=28)
        draw.line((380, y + 34, 920, y + 34), fill=(69, 79, 99), width=2)

    width, height = round(600 * pulse), round(250 * pulse)
    left = 1325 - width // 2
    top = 535 - height // 2
    for ring in range(3):
        amount = round((50 + ring * 42) * reveal)
        draw.rounded_rectangle((left - amount, top - amount // 2, left + width + amount, top + height + amount // 2), radius=56, outline=(94 + ring * 24, 68, 176), width=4)
    draw.rounded_rectangle((left, top, left + width, top + height), radius=50, fill=PURPLE)
    _value(draw, (1325, top + 88), "SUBSCRIBE", size=68, anchor="mm")
    _label(draw, (1325, top + 174), "BUILD THE NEXT STEP", fill=(237, 233, 254), size=28, anchor="mm")
    _pill(draw, (1325, 780), "BLUEPRINT READY", fill=(51, 42, 87), text_fill=GOLD, width=300)


COMPOSITION_RENDERERS = {
    "paycheck_split": _paycheck_composed,
    "expense_breakdown": _expenses_composed,
    "empty_balance": _empty_composed,
    "recurring_transfer": _transfer_composed,
    "index_growth": _index_composed,
    "compound_growth": _compound_composed,
    "pay_self_comparison": _comparison_composed,
    "subscribe_cta": _cta_composed,
}


def install_visual_composition() -> None:
    base._common = _common_composed
    base.RENDERERS.update(COMPOSITION_RENDERERS)


install_visual_composition()

render_frame = base.render_frame
render_finance_motion = base.render_finance_motion
