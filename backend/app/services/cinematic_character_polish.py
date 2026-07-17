from __future__ import annotations

import math
from functools import lru_cache

from PIL import Image, ImageDraw, ImageEnhance

from . import animation_script_runtime as runtime
from . import character_expressive as character
from . import character_staging as staging
from . import finance_motion as engine
from . import finance_motion_art as art
from . import finance_motion_choreography as choreography
from . import finance_motion_composition as composition
from . import finance_motion_polish as polish

# Cinematic Character Polish v1.9.2 removes the dashboard-purple visual bias,
# stabilizes the expressive rig, repairs hand/prop staging, and makes generated
# finance and character scenes read more like directed footage than slide decks.

TEAL = (67, 185, 166)
TEAL_LIGHT = (174, 235, 222)
TEAL_DARK = (25, 88, 82)
AMBER = (224, 174, 83)
AMBER_LIGHT = (244, 218, 160)
CORAL = (218, 111, 101)
GRAPHITE = (9, 15, 24)
MIDNIGHT = (15, 27, 40)
SURFACE = (24, 39, 54)
PANEL = (31, 49, 66)
MUTED = (150, 166, 181)
OFF_WHITE = (241, 245, 244)

_ORIGINAL_CHARACTER_PALETTE = staging.base._palette


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _smooth(value: float) -> float:
    value = _clamp(value)
    return value * value * (3 - 2 * value)


def _mix(
    first: tuple[int, int, int],
    second: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    amount = _clamp(amount)
    return tuple(
        round(first[index] + (second[index] - first[index]) * amount)
        for index in range(3)
    )


@lru_cache(maxsize=1)
def _cinematic_background() -> Image.Image:
    """Return a clean full-frame background with no graph-paper grid."""
    gradient = Image.new("RGB", (1, engine.OUTPUT_HEIGHT))
    gradient.putdata(
        [
            _mix(GRAPHITE, MIDNIGHT, y / max(1, engine.OUTPUT_HEIGHT - 1))
            for y in range(engine.OUTPUT_HEIGHT)
        ]
    )
    image = gradient.resize((engine.OUTPUT_WIDTH, engine.OUTPUT_HEIGHT))
    return Image.alpha_composite(image.convert("RGBA"), _cinematic_static_overlay()).convert("RGB")


@lru_cache(maxsize=1)
def _cinematic_static_overlay() -> Image.Image:
    """Use broad edge light and vignette instead of localized character halos."""
    small_width, small_height = 240, 135
    pixels: list[tuple[int, int, int, int]] = []
    for y in range(small_height):
        ny = y / max(1, small_height - 1)
        for x in range(small_width):
            nx = x / max(1, small_width - 1)
            teal = max(0.0, 1.0 - math.hypot(nx - 1.05, ny - 0.08) / 1.0)
            amber = max(0.0, 1.0 - math.hypot(nx + 0.10, ny - 1.05) / 1.1)
            edge = min(nx, ny, 1 - nx, 1 - ny)
            vignette = max(0.0, 1.0 - edge / 0.32)
            grain = ((x * 29 + y * 47) % 19) / 18
            pixels.append(
                (
                    round(TEAL[0] * teal + AMBER[0] * amber),
                    round(TEAL[1] * teal + AMBER[1] * amber),
                    round(TEAL[2] * teal + AMBER[2] * amber),
                    round(10 + 20 * teal + 14 * amber + 28 * vignette + 4 * grain),
                )
            )
    overlay = Image.new("RGBA", (small_width, small_height))
    overlay.putdata(pixels)
    return overlay.resize((engine.OUTPUT_WIDTH, engine.OUTPUT_HEIGHT), Image.Resampling.BICUBIC)


def _apply_cinematic(image: Image.Image, _time_seconds: float) -> Image.Image:
    image = ImageEnhance.Color(image).enhance(0.94)
    image = ImageEnhance.Contrast(image).enhance(1.08)
    return Image.alpha_composite(image.convert("RGBA"), _cinematic_static_overlay()).convert("RGB")


def _character_palette(style_id: str) -> dict[str, tuple[int, int, int]]:
    if style_id != "premium_motion":
        return _ORIGINAL_CHARACTER_PALETTE(style_id)
    return {
        "ink": GRAPHITE,
        "surface": SURFACE,
        "panel": PANEL,
        "person": TEAL,
        "person_alt": AMBER,
        "skin": (238, 187, 145),
        "denim": (47, 84, 129),
        "denim_alt": (40, 72, 110),
        "shoe": (29, 37, 49),
        "hair": (35, 31, 29),
        "hair_alt": (64, 40, 24),
        "accent": TEAL_LIGHT,
        "good": (75, 184, 139),
        "bad": CORAL,
        "gold": AMBER,
        "muted": MUTED,
        "white": OFF_WHITE,
    }


def _restrained_performance_pulse() -> float:
    """One intentional action arc instead of a repeating full-body wobble."""
    progress = character._CURRENT_TIME / max(0.01, character._CURRENT_DURATION)
    if progress < 0.16:
        return 0.0
    if progress < 0.26:
        return -0.025 * _smooth((progress - 0.16) / 0.10)
    if progress < 0.50:
        local = _smooth((progress - 0.26) / 0.24)
        return -0.025 + 0.075 * local
    if progress < 0.68:
        return 0.05 * (1 - _smooth((progress - 0.50) / 0.18))
    return 0.0


def _polished_hand(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    color: tuple[int, int, int],
    scale: float,
    *,
    open_hand: bool = False,
    hand_shape: str | None = None,
    facing: int = 1,
) -> None:
    """Draw a restrained hand shape with only one readable intention."""
    x, y = center
    shape = hand_shape or ("wave" if open_hand else "relaxed")
    outline = (3, 7, 12)
    palm_x = max(9, round(13 * scale))
    palm_y = max(9, round(15 * scale))
    draw.ellipse(
        (x - palm_x - 3, y - palm_y + 4, x + palm_x + 4, y + palm_y + 8),
        fill=outline,
    )
    draw.ellipse((x - palm_x, y - palm_y, x + palm_x, y + palm_y), fill=color)
    stroke = max(2, round(3 * scale))

    if shape == "wave":
        # Only an intentional wave receives separated fingers, kept short so
        # the silhouette does not resemble signing at documentary scale.
        for offset, angle in ((-6, -104), (0, -90), (6, -76)):
            start = (x + round(offset * scale), y - round(7 * scale))
            length = round(12 * scale)
            radians = math.radians(angle)
            end = (
                round(start[0] + math.cos(radians) * length),
                round(start[1] + math.sin(radians) * length),
            )
            draw.line((start, end), fill=color, width=stroke)
        thumb_start = (x + facing * round(8 * scale), y + round(1 * scale))
        thumb_end = (x + facing * round(19 * scale), y + round(5 * scale))
        draw.line((thumb_start, thumb_end), fill=color, width=stroke + 1)
    elif shape == "point":
        draw.line(
            (x + facing * round(7 * scale), y - round(3 * scale), x + facing * round(27 * scale), y - round(6 * scale)),
            fill=color,
            width=stroke + 1,
        )
        draw.line(
            (x - facing * round(7 * scale), y + round(3 * scale), x + facing * round(6 * scale), y + round(3 * scale)),
            fill=_mix(color, outline, 0.30),
            width=max(1, stroke - 1),
        )
    elif shape == "cup":
        draw.arc(
            (x - round(8 * scale), y - round(7 * scale), x + round(10 * scale), y + round(9 * scale)),
            15 if facing > 0 else 165,
            165 if facing > 0 else 345,
            fill=_mix(color, outline, 0.34),
            width=max(1, stroke - 1),
        )
    elif shape == "fist":
        for offset in (-5, 2):
            draw.line(
                (
                    x - round(7 * scale),
                    y + round(offset * scale),
                    x + round(7 * scale),
                    y + round(offset * scale),
                ),
                fill=_mix(color, outline, 0.28),
                width=max(1, stroke - 1),
            )
    else:
        # Relaxed hands use one crease and one short thumb—no finger fan.
        draw.line(
            (x - round(6 * scale), y - round(2 * scale), x + round(6 * scale), y - round(2 * scale)),
            fill=_mix(color, outline, 0.28),
            width=max(1, stroke - 1),
        )
        draw.line(
            (x + facing * round(7 * scale), y, x + facing * round(17 * scale), y + round(5 * scale)),
            fill=color,
            width=max(2, stroke),
        )


def _character_title(
    draw: ImageDraw.ImageDraw,
    template: engine.MotionTemplate,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    engine._text(draw, (110, 92), "CHARACTER STORY", 16, palette["accent"], bold=True)
    engine._text(draw, (108, 132), template.title, 54, palette["white"], bold=True)
    engine._text(draw, (110, 205), template.subtitle, 24, palette["muted"])
    draw.rounded_rectangle((110, 262, 330, 268), radius=3, fill=palette["accent"])


def _character_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    palette: dict[str, tuple[int, int, int]],
    *,
    outline: tuple[int, int, int] | None = None,
) -> None:
    border = _mix(outline or palette["muted"], palette["surface"], 0.58)
    draw.rounded_rectangle(
        box,
        radius=20,
        fill=palette["surface"],
        outline=border,
        width=2,
    )


def _finance_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int] = SURFACE,
    outline: tuple[int, int, int] | None = None,
) -> None:
    border = _mix(outline or MUTED, fill, 0.66)
    draw.rounded_rectangle(box, radius=20, fill=fill, outline=border, width=2)


def _finance_shadowed_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: tuple[int, int, int] = SURFACE,
    outline: tuple[int, int, int] | None = None,
    radius: int = 22,
    shadow: int = 0,
) -> None:
    del shadow
    border = _mix(outline or MUTED, fill, 0.62)
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=border, width=2)


def _finance_title(image: Image.Image, template: engine.MotionTemplate) -> ImageDraw.ImageDraw:
    draw = ImageDraw.Draw(image)
    accent = composition.SEMANTIC_ACCENT.get(template.template_id, TEAL)
    engine._text(draw, (112, 88), "MONEY STORY", 16, accent, bold=True)
    engine._text(draw, (108, 128), template.title, 54, OFF_WHITE, bold=True)
    engine._text(draw, (110, 202), template.subtitle, 24, MUTED)
    draw.rounded_rectangle((110, 260, 340, 266), radius=3, fill=accent)
    return draw


def _wallet_anchor(placement) -> tuple[int, int]:
    return (
        round(placement.center_x + placement.facing * 112 * placement.scale),
        round(placement.ground_y - 142 * placement.scale),
    )


def _spend_first_cinematic(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    income = staging.base._phase(progress, 0.03, 0.20)
    stages = (
        staging.base._phase(progress, 0.22, 0.43),
        staging.base._phase(progress, 0.40, 0.62),
        staging.base._phase(progress, 0.58, 0.78),
    )
    drained = 0.46 * stages[0] + 0.28 * stages[1] + 0.26 * stages[2]
    remaining = max(0, round(5000 * (1 - drained) * income))
    plan = staging.staging_plan("spend_first")

    staging.base._panel(draw, (95, 350, 720, 900), palette, outline=palette["accent"])
    engine._text(draw, (145, 390), "AVAILABLE", 23, palette["muted"], bold=True)
    engine._text(
        draw,
        (390, 470),
        f"${remaining:,}",
        62,
        palette["white"] if remaining else palette["bad"],
        bold=True,
        anchor="mm",
    )

    pose = "receive" if progress < 0.30 else "slump" if progress > 0.76 else "point"
    staging._character_stage(
        draw,
        plan.character,
        palette,
        pose=pose,
        mood="sad" if progress > 0.76 else "neutral",
    )

    wallet_center = _wallet_anchor(plan.character)
    staging.composition._icon_wallet(
        draw,
        wallet_center,
        scale=0.56,
        accent=palette["bad"] if remaining == 0 else palette["accent"],
        empty=remaining == 0,
    )

    cards = (
        ("RENT", (850, 355, 1170, 605), staging.composition._icon_house, palette["bad"], 46),
        ("GROCERIES", (1250, 355, 1570, 605), staging.composition._icon_bag, palette["good"], 28),
        ("LIFESTYLE", (1050, 650, 1370, 900), staging.composition._icon_card, palette["person_alt"], 26),
    )
    starts = (
        (wallet_center[0] + 48, wallet_center[1] - 18),
        (wallet_center[0] + 48, wallet_center[1] + 4),
        (wallet_center[0] + 48, wallet_center[1] + 26),
    )
    controls = ((745, 430), (900, 555), (820, 800))
    for index, (label, box, icon, accent, percent) in enumerate(cards):
        staging.base._panel(draw, box, palette, outline=accent)
        left, top, right, bottom = box
        icon(draw, ((left + right) // 2, top + 92), scale=0.46, accent=accent)
        engine._text(draw, ((left + right) // 2, top + 165), label, 23, accent, bold=True, anchor="mm")
        engine._text(
            draw,
            ((left + right) // 2, top + 210),
            f"{round(percent * stages[index])}%",
            34,
            palette["white"],
            bold=True,
            anchor="mm",
        )
        if stages[index] > 0:
            destination = ((left + right) // 2, (top + bottom) // 2)
            token = staging.base._route(
                draw,
                starts[index],
                controls[index],
                destination,
                stages[index],
                accent,
            )
            staging.base._coin(draw, token, palette, radius=25)

    if progress > 0.82:
        staging.base._pill(
            draw,
            (500, 855),
            "$0 LEFT TO INVEST",
            fill=palette["bad"],
            text_fill=palette["white"],
            width=350,
        )


def _cinematic_finance_choreography(
    draw: ImageDraw.ImageDraw,
    template_id: str,
    time_seconds: float,
) -> None:
    if template_id == "paycheck_split":
        progress = engine._progress(time_seconds, 1.05, 1.20)
        choreography._draw_route(draw, (660, 655), (845, 535), (1030, 735), progress, (*TEAL, 170))
        choreography._pulse(draw, (1515, 826), engine._progress(time_seconds, 2.08, 0.75), TEAL)
    elif template_id == "expense_breakdown":
        for index, (center, color) in enumerate(
            zip(((935, 472), (1370, 472), (1155, 758)), (AMBER, TEAL, CORAL), strict=True)
        ):
            local = _clamp((time_seconds - (0.82 + index * 0.34)) / 0.72)
            choreography._pulse(draw, center, local, color)
    elif template_id == "empty_balance":
        warning = _clamp((time_seconds - 1.26) / 0.90)
        choreography._pulse(draw, (1450, 720), warning, CORAL)
        if warning > 0.18:
            scan_y = round(455 + 280 * warning)
            draw.line((300, scan_y, 930, scan_y), fill=(*CORAL, 80), width=3)
    elif template_id == "recurring_transfer":
        progress = engine._progress(time_seconds, 0.42, 1.35)
        choreography._draw_route(draw, (675, 620), (960, 475), (1245, 620), progress, (*TEAL_LIGHT, 170))
        choreography._pulse(draw, (1540, 655), engine._progress(time_seconds, 1.62, 0.80), TEAL)
    elif template_id == "index_growth":
        progress = engine._progress(time_seconds, 0.42, 1.75)
        path = ((640, 765), (830, 735), (1020, 690), (1210, 620), (1400, 520), (1590, 410))
        x, y = choreography._point_on_polyline(path, progress)
        draw.ellipse((x - 15, y - 15, x + 15, y + 15), fill=(*TEAL_LIGHT, 220))
    elif template_id == "compound_growth":
        progress = engine._progress(time_seconds, 0.42, 1.75)
        path = ((285, 690), (555, 665), (825, 625), (1095, 560), (1365, 480), (1635, 365))
        x, y = choreography._point_on_polyline(path, progress)
        draw.ellipse((x - 16, y - 16, x + 16, y + 16), fill=(*AMBER_LIGHT, 225))
        for offset in range(3):
            local = _clamp(progress - offset * 0.08)
            px, py = choreography._point_on_polyline(path, local)
            draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=(*TEAL, 125))
    elif template_id == "pay_self_comparison":
        progress = engine._progress(time_seconds, 0.62, 1.18)
        choreography._draw_route(draw, (930, 650), (1120, 500), (1510, 585), progress, (*TEAL_LIGHT, 175))
        x, y = choreography._quadratic_point((930, 650), (1120, 500), (1510, 585), progress)
        draw.ellipse((x - 28, y - 28, x + 28, y + 28), fill=(*TEAL_LIGHT, 230))
        engine._text(draw, (x, y), "10", 25, (20, 48, 42), bold=True, anchor="mm")
    elif template_id == "subscribe_cta":
        pulse = (math.sin(time_seconds * 3.2) + 1) / 2
        radius = round(20 + 20 * pulse)
        draw.rounded_rectangle(
            (1010 - radius, 370 - radius // 2, 1640 + radius, 700 + radius // 2),
            radius=54,
            outline=(*AMBER, round(58 + 58 * (1 - pulse))),
            width=4,
        )


def _no_indicator(*_args, **_kwargs) -> None:
    return None


# Install the neutral cinematic visual language.
engine.BG_TOP = GRAPHITE
engine.BG_BOTTOM = MIDNIGHT
engine.PANEL = SURFACE
engine.PANEL_LIGHT = PANEL
engine.PURPLE = TEAL
engine.PURPLE_LIGHT = TEAL_LIGHT
engine._background = _cinematic_background
engine._panel = _finance_panel

polish._background = _cinematic_background
polish.PURPLE = TEAL
polish.PURPLE_LIGHT = TEAL_LIGHT
polish.PURPLE_DARK = TEAL_DARK

composition._background = _cinematic_background
composition.PURPLE = TEAL
composition.PURPLE_LIGHT = TEAL_LIGHT
composition.SEMANTIC_ACCENT["compound_growth"] = AMBER
composition.SEMANTIC_ACCENT["expense_breakdown"] = AMBER
composition._shadowed_round_rect = _finance_shadowed_panel
composition._common_composed = _finance_title
engine._common = _finance_title

cinematic_style = art.MotionStyle(
    "premium_motion",
    "Cinematic Motion",
    "Neutral graphite, teal action, warm emphasis, restrained depth, and no dashboard grid.",
    ("#0f1b28", "#43b9a6", "#e0ae53", "#f1f5f4"),
)
style_by_id = {style.style_id: style for style in art.STYLES}
style_by_id["premium_motion"] = cinematic_style
art.STYLES = tuple(style_by_id[style_id] for style_id in ("clean_infographic", "premium_motion", "editorial_documentary"))
art.STYLE_BY_ID = {style.style_id: style for style in art.STYLES}
art.STYLE_RENDERERS["premium_motion"] = _apply_cinematic

choreography._template_choreography = _cinematic_finance_choreography
choreography._beat_indicator = _no_indicator
choreography.STYLES = art.STYLES

# Stabilize and restage the expressive character family.
staging.base._palette = _character_palette
staging.base._title = _character_title
staging.base._panel = _character_panel
staging.base._beat_indicator = _no_indicator
staging.base.RENDERERS["spend_first"] = _spend_first_cinematic
character._performance_pulse = _restrained_performance_pulse
character._hand = _polished_hand
character.STYLES = art.STYLES

# The animation-script runtime retained a reference to the expressive person.
# Its helper lookups remain dynamic, so the stabilized pulse and hand system are
# consumed while saved pose/expression plans continue to control performance.
runtime.character.STYLES = art.STYLES
