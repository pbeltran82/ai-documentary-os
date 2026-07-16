from __future__ import annotations

from PIL import ImageDraw

from . import character_explainer as base
from . import finance_motion as engine
from . import finance_motion_composition as composition
from .visual_staging import CharacterPlacement, face_safe_zone, staging_plan


# Visual Staging v1.5 keeps faces and gestures readable before adding more
# complexity. It upgrades the existing Character Explainer renderer by replacing
# the two layouts that could place foreground UI across the face, then applies
# safer camera profiles to every character template.


def _character_stage(
    draw: ImageDraw.ImageDraw,
    placement: CharacterPlacement,
    palette: dict[str, tuple[int, int, int]],
    *,
    pose: str,
    mood: str = "neutral",
    alternate: bool = False,
) -> None:
    x = placement.center_x
    ground_y = placement.ground_y
    scale = placement.scale
    body_color = palette["person_alt"] if alternate else palette["person"]

    # A restrained silhouette halo and ground shadow separate the figure from
    # panels without becoming visible product decoration.
    halo_radius_x = round(100 * scale)
    halo_radius_y = round(145 * scale)
    halo_center_y = ground_y - round(160 * scale)
    draw.ellipse(
        (
            x - halo_radius_x,
            halo_center_y - halo_radius_y,
            x + halo_radius_x,
            halo_center_y + halo_radius_y,
        ),
        fill=tuple(round(channel * 0.22) for channel in body_color),
    )
    draw.ellipse(
        (
            x - round(80 * scale),
            ground_y - round(14 * scale),
            x + round(80 * scale),
            ground_y + round(14 * scale),
        ),
        fill=(3, 6, 14),
    )
    base._person(
        draw,
        (x, ground_y),
        palette,
        scale=scale,
        pose=pose,
        mood=mood,
        facing=placement.facing,
        alternate=alternate,
    )


def _spend_first_staged(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    income = base._phase(progress, 0.03, 0.20)
    stages = (
        base._phase(progress, 0.22, 0.43),
        base._phase(progress, 0.40, 0.62),
        base._phase(progress, 0.58, 0.78),
    )
    drained = 0.46 * stages[0] + 0.28 * stages[1] + 0.26 * stages[2]
    remaining = max(0, round(5000 * (1 - drained) * income))
    plan = staging_plan("spend_first")

    base._panel(draw, (95, 350, 720, 900), palette, outline=palette["accent"])
    engine._text(draw, (145, 390), "AVAILABLE", 25, palette["muted"], bold=True)
    engine._text(
        draw,
        (390, 465),
        f"${remaining:,}",
        66,
        palette["white"] if remaining else palette["bad"],
        bold=True,
        anchor="mm",
    )

    pose = "receive" if progress < 0.30 else "slump" if progress > 0.76 else "point"
    _character_stage(
        draw,
        plan.character,
        palette,
        pose=pose,
        mood="sad" if progress > 0.76 else "neutral",
    )

    # The wallet is deliberately staged beside the person rather than over the
    # head or torso. Its center is outside the padded face-safe zone.
    wallet_center = (520, 690)
    composition._icon_wallet(
        draw,
        wallet_center,
        scale=0.72,
        accent=palette["bad"] if remaining == 0 else palette["accent"],
        empty=remaining == 0,
    )
    engine._text(
        draw,
        (520, 790),
        "WALLET",
        20,
        palette["bad"] if remaining == 0 else palette["accent"],
        bold=True,
        anchor="mm",
    )

    cards = (
        ("RENT", (850, 355, 1170, 605), composition._icon_house, palette["bad"], "46%"),
        ("GROCERIES", (1250, 355, 1570, 605), composition._icon_bag, palette["good"], "28%"),
        ("LIFESTYLE", (1050, 650, 1370, 900), composition._icon_card, palette["person"], "26%"),
    )
    starts = ((590, 650), (600, 690), (585, 735))
    controls = ((745, 430), (900, 555), (820, 800))
    for index, (label, box, icon, accent, percent) in enumerate(cards):
        base._panel(draw, box, palette, outline=accent)
        left, top, right, bottom = box
        icon(draw, ((left + right) // 2, top + 92), scale=0.46, accent=accent)
        engine._text(draw, ((left + right) // 2, top + 165), label, 24, accent, bold=True, anchor="mm")
        engine._text(
            draw,
            ((left + right) // 2, top + 210),
            f"{round(int(percent[:-1]) * stages[index])}%",
            35,
            palette["white"],
            bold=True,
            anchor="mm",
        )
        if stages[index] > 0:
            destination = ((left + right) // 2, (top + bottom) // 2)
            token = base._route(draw, starts[index], controls[index], destination, stages[index], accent)
            base._coin(draw, token, palette, radius=25)

    if progress > 0.82:
        base._pill(
            draw,
            (500, 855),
            "$0 LEFT TO INVEST",
            fill=palette["bad"],
            text_fill=palette["white"],
            width=350,
        )


def _automatic_habit_staged(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    setup = base._phase(progress, 0.06, 0.30)
    cycle = base._phase(progress, 0.28, 0.78)
    result = base._phase(progress, 0.74, 0.92)
    plan = staging_plan("automatic_investing_habit")

    base._panel(draw, (95, 350, 710, 900), palette, outline=palette["accent"])
    engine._text(draw, (145, 392), "ONE-TIME SETUP", 26, palette["accent"], bold=True)

    pose = "tap" if setup < 0.90 else "relaxed" if result > 0.25 else "point"
    _character_stage(
        draw,
        plan.character,
        palette,
        pose=pose,
        mood="happy" if result > 0.2 else "neutral",
    )

    # Setup controls occupy a dedicated right-side column. The protected face
    # box remains clear during every beat, even after ENABLED appears.
    base._pill(
        draw,
        (525, 465),
        "AUTO-INVEST 10%",
        fill=palette["panel"],
        text_fill=palette["good"],
        width=330,
    )
    draw.line((350, 560, 390, 500), fill=palette["accent"], width=5)
    if setup > 0.75:
        base._pill(
            draw,
            (545, 560),
            "✓ ENABLED",
            fill=palette["good"],
            text_fill=palette["ink"],
            width=245,
        )
    else:
        engine._text(draw, (520, 550), "TAP ONCE", 20, palette["muted"], bold=True, anchor="mm")

    base._panel(draw, (820, 350, 1815, 900), palette, outline=palette["good"])
    composition._icon_calendar(draw, (980, 540), scale=0.62, accent=palette["person"], day="PAY")
    composition._icon_bank(draw, (1630, 555), scale=0.70, accent=palette["good"])
    engine._text(draw, (1305, 405), "THE SYSTEM RUNS", 29, palette["muted"], bold=True, anchor="mm")

    cycles = max(1, min(4, __import__("math").ceil(cycle * 4))) if cycle > 0 else 0
    for index in range(cycles):
        local = base._clamp(cycle * 4 - index)
        start = (1045, 600 + index * 30)
        end = (1535, 600 - index * 18)
        token = base._route(draw, start, (1290, 430 - index * 24), end, local, palette["good"])
        base._coin(draw, token, palette, label="10", radius=26)

    chart_points = []
    for index, value in enumerate((0.18, 0.30, 0.46, 0.66, 0.90)):
        visible = base._phase(cycle, index * 0.13, min(1.0, index * 0.13 + 0.35))
        x = 1040 + index * 135
        y = 820 - round(180 * value * visible)
        chart_points.append((x, y))
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=palette["good"])
    if len(chart_points) > 1:
        draw.line(chart_points, fill=palette["good"], width=8, joint="curve")
    if result > 0.2:
        base._pill(
            draw,
            (1330, 850),
            "GROWTH WITHOUT ANOTHER DECISION",
            fill=palette["good"],
            text_fill=palette["ink"],
            width=540,
            size=22,
        )


base.RENDERERS.update(
    {
        "spend_first": _spend_first_staged,
        "automatic_investing_habit": _automatic_habit_staged,
    }
)
base.CAMERA_FOCUS.update(
    {
        "paycheck_arrival": ((0.27, 0.54), (0.64, 0.55), 0.010),
        "spend_first": ((0.23, 0.56), (0.61, 0.57), 0.008),
        "empty_balance_reaction": ((0.26, 0.55), (0.66, 0.55), 0.010),
        "pay_self_character_comparison": ((0.43, 0.55), (0.57, 0.55), 0.007),
        "automatic_investing_habit": ((0.22, 0.56), (0.66, 0.52), 0.009),
    }
)

CHARACTER_TEMPLATES = base.CHARACTER_TEMPLATES
CHARACTER_TEMPLATE_BY_ID = base.CHARACTER_TEMPLATE_BY_ID
DEFAULT_STYLE_ID = base.DEFAULT_STYLE_ID
STYLES = base.STYLES
OUTPUT_WIDTH = base.OUTPUT_WIDTH
OUTPUT_HEIGHT = base.OUTPUT_HEIGHT
ffmpeg_encoder_command = base.ffmpeg_encoder_command
render_frame = base.render_frame
render_character_motion = base.render_character_motion
score_character_templates = base.score_character_templates
storyboard_beats = base.storyboard_beats
style_catalog = base.style_catalog
suggest_template = base.suggest_template
template_catalog = base.template_catalog
