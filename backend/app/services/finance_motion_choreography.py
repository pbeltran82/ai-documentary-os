from __future__ import annotations

import math
from dataclasses import dataclass

from fastapi import HTTPException
from PIL import Image, ImageDraw

from . import finance_motion as base
from . import finance_motion_composition as composition
from . import finance_motion_art as art


@dataclass(frozen=True)
class StoryBeat:
    label: str
    description: str
    fraction: float


DEFAULT_BEATS = (
    StoryBeat("ESTABLISH", "Introduce the financial system and its starting state.", 0.18),
    StoryBeat("DECISION", "Animate the money choice or behavior change.", 0.52),
    StoryBeat("RESULT", "Land on the consequence and takeaway.", 0.84),
)

BEATS_BY_TEMPLATE: dict[str, tuple[StoryBeat, StoryBeat, StoryBeat]] = {
    "paycheck_split": (
        StoryBeat("PAYCHECK", "Income arrives before lifestyle can claim it.", 0.18),
        StoryBeat("SPLIT", "The first ten percent separates from spending money.", 0.50),
        StoryBeat("FUTURE FUNDED", "The transfer lands with the future self.", 0.84),
    ),
    "expense_breakdown": (
        StoryBeat("INCOME", "Start with the full paycheck available.", 0.16),
        StoryBeat("EXPENSE DRAIN", "Rent, groceries, and lifestyle consume it in sequence.", 0.52),
        StoryBeat("NOTHING LEFT", "The remaining balance reaches the consequence.", 0.86),
    ),
    "empty_balance": (
        StoryBeat("BALANCE", "Show the account before the spending cycle finishes.", 0.16),
        StoryBeat("DRAIN", "Count the available balance down visibly.", 0.52),
        StoryBeat("DECLINED", "Land on the empty-wallet and declined-card outcome.", 0.84),
    ),
    "recurring_transfer": (
        StoryBeat("PAYDAY", "Establish the checking account and scheduled payday.", 0.18),
        StoryBeat("AUTO-TRANSFER", "Move ten percent along a deliberate path.", 0.50),
        StoryBeat("CONFIRMED", "Lock the money into the investment account.", 0.84),
    ),
    "index_growth": (
        StoryBeat("CONTRIBUTE", "Introduce recurring deposits into the index fund.", 0.16),
        StoryBeat("MARKET TIME", "Draw the growth path as time advances.", 0.54),
        StoryBeat("COMPOUND BASE", "Finish with a visibly larger invested base.", 0.86),
    ),
    "compound_growth": (
        StoryBeat("CONSISTENCY", "Establish repeated contributions across time.", 0.16),
        StoryBeat("RETURNS", "Show returns feeding the next stage of growth.", 0.52),
        StoryBeat("ACCELERATION", "Land on the compounding momentum payoff.", 0.86),
    ),
    "pay_self_comparison": (
        StoryBeat("SPEND FIRST", "Show the reactive system and empty outcome.", 0.18),
        StoryBeat("CHOOSE", "Move the decision toward paying the future first.", 0.50),
        StoryBeat("INVEST FIRST", "Finish on the automatic investing system.", 0.84),
    ),
    "subscribe_cta": (
        StoryBeat("BLUEPRINT", "Reveal the three-part money system.", 0.16),
        StoryBeat("NEXT STEP", "Focus attention on the channel action.", 0.52),
        StoryBeat("LIKE + SUBSCRIBE", "Land on two clean, recognizable channel actions.", 0.84),
    ),
}

CAMERA_PROFILES = {
    "paycheck_split": ((0.34, 0.52), (0.66, 0.54), 0.016),
    "expense_breakdown": ((0.30, 0.52), (0.66, 0.56), 0.012),
    "empty_balance": ((0.36, 0.50), (0.67, 0.56), 0.018),
    "recurring_transfer": ((0.28, 0.52), (0.72, 0.52), 0.016),
    "index_growth": ((0.38, 0.55), (0.68, 0.46), 0.014),
    "compound_growth": ((0.34, 0.58), (0.70, 0.42), 0.016),
    "pay_self_comparison": ((0.34, 0.54), (0.68, 0.52), 0.012),
    "subscribe_cta": ((0.52, 0.52), (0.70, 0.48), 0.018),
}

_ORIGINAL_RENDER_FRAME = art.render_frame


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _ease(value: float) -> float:
    value = _clamp(value)
    return value * value * (3 - 2 * value)


def storyboard_beats(template_id: str, duration_seconds: float) -> list[dict[str, object]]:
    if template_id not in base.TEMPLATE_BY_ID:
        raise HTTPException(status_code=422, detail="Unknown finance motion template")
    duration = max(1.0, float(duration_seconds))
    beats = BEATS_BY_TEMPLATE.get(template_id, DEFAULT_BEATS)
    return [
        {
            "label": beat.label,
            "description": beat.description,
            "time_seconds": round(min(duration - 0.04, max(0.08, duration * beat.fraction)), 3),
        }
        for beat in beats
    ]


def _camera_move(image: Image.Image, template_id: str, progress: float) -> Image.Image:
    start, end, zoom_amount = CAMERA_PROFILES.get(
        template_id,
        ((0.45, 0.50), (0.55, 0.50), 0.012),
    )
    eased = _ease(progress)
    zoom = 1 + zoom_amount * eased
    width, height = image.size
    scaled_width = max(width, round(width * zoom))
    scaled_height = max(height, round(height * zoom))
    if scaled_width == width and scaled_height == height:
        return image
    scaled = image.resize((scaled_width, scaled_height), Image.Resampling.BILINEAR)
    focus_x = start[0] + (end[0] - start[0]) * eased
    focus_y = start[1] + (end[1] - start[1]) * eased
    left = round((scaled_width - width) * _clamp(focus_x))
    top = round((scaled_height - height) * _clamp(focus_y))
    return scaled.crop((left, top, left + width, top + height))


def _quadratic_point(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
    progress: float,
) -> tuple[int, int]:
    inverse = 1 - progress
    x = inverse * inverse * start[0] + 2 * inverse * progress * control[0] + progress * progress * end[0]
    y = inverse * inverse * start[1] + 2 * inverse * progress * control[1] + progress * progress * end[1]
    return round(x), round(y)


def _draw_route(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    control: tuple[int, int],
    end: tuple[int, int],
    progress: float,
    color: tuple[int, int, int, int],
) -> None:
    progress = _clamp(progress)
    steps = max(2, round(28 * progress))
    points = [
        _quadratic_point(start, control, end, index / 28)
        for index in range(steps + 1)
    ]
    if len(points) > 1:
        draw.line(points, fill=color, width=6, joint="curve")
    for index, point in enumerate(points[-5:]):
        radius = 3 + index
        alpha = 45 + index * 32
        draw.ellipse(
            (point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius),
            fill=(color[0], color[1], color[2], min(220, alpha)),
        )


def _point_on_polyline(points: tuple[tuple[int, int], ...], progress: float) -> tuple[int, int]:
    progress = _clamp(progress)
    segment_count = len(points) - 1
    position = progress * segment_count
    segment = min(segment_count - 1, int(position))
    local = position - segment
    start = points[segment]
    end = points[segment + 1]
    return (
        round(start[0] + (end[0] - start[0]) * local),
        round(start[1] + (end[1] - start[1]) * local),
    )


def _pulse(draw: ImageDraw.ImageDraw, center: tuple[int, int], progress: float, color: tuple[int, int, int]) -> None:
    if progress <= 0:
        return
    radius = round(34 + 68 * progress)
    alpha = round(150 * (1 - progress))
    draw.ellipse(
        (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
        outline=(color[0], color[1], color[2], alpha),
        width=5,
    )


def _template_choreography(
    draw: ImageDraw.ImageDraw,
    template_id: str,
    time_seconds: float,
) -> None:
    if template_id == "paycheck_split":
        progress = base._progress(time_seconds, 1.05, 1.20)
        _draw_route(draw, (660, 655), (845, 535), (1030, 735), progress, (52, 211, 153, 160))
        _pulse(draw, (1515, 826), base._progress(time_seconds, 2.08, 0.75), composition.GREEN)
    elif template_id == "expense_breakdown":
        for index, center in enumerate(((935, 472), (1370, 472), (1155, 758))):
            local = _clamp((time_seconds - (0.82 + index * 0.34)) / 0.72)
            _pulse(draw, center, local, (245, 158, 11) if index == 0 else (52, 211, 153) if index == 1 else (139, 92, 246))
    elif template_id == "empty_balance":
        warning = _clamp((time_seconds - 1.26) / 0.90)
        _pulse(draw, (1450, 720), warning, composition.CORAL)
        if warning > 0.18:
            scan_y = round(455 + 280 * warning)
            draw.line((300, scan_y, 930, scan_y), fill=(251, 113, 133, 80), width=3)
    elif template_id == "recurring_transfer":
        progress = base._progress(time_seconds, 0.42, 1.35)
        _draw_route(draw, (675, 620), (960, 475), (1245, 620), progress, (167, 243, 208, 170))
        _pulse(draw, (1540, 655), base._progress(time_seconds, 1.62, 0.80), composition.GREEN)
    elif template_id == "index_growth":
        progress = base._progress(time_seconds, 0.42, 1.75)
        path = ((640, 765), (830, 735), (1020, 690), (1210, 620), (1400, 520), (1590, 410))
        x, y = _point_on_polyline(path, progress)
        draw.ellipse((x - 16, y - 16, x + 16, y + 16), fill=(167, 243, 208, 210))
        _pulse(draw, (x, y), (math.sin(time_seconds * 4) + 1) / 2, composition.GREEN)
    elif template_id == "compound_growth":
        progress = base._progress(time_seconds, 0.42, 1.75)
        path = ((285, 690), (555, 665), (825, 625), (1095, 560), (1365, 480), (1635, 365))
        x, y = _point_on_polyline(path, progress)
        draw.ellipse((x - 17, y - 17, x + 17, y + 17), fill=(196, 181, 253, 220))
        for offset in range(3):
            local = _clamp(progress - offset * 0.08)
            px, py = _point_on_polyline(path, local)
            draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=(52, 211, 153, 120))
    elif template_id == "pay_self_comparison":
        progress = base._progress(time_seconds, 0.62, 1.18)
        _draw_route(draw, (930, 650), (1120, 500), (1510, 585), progress, (167, 243, 208, 175))
        x, y = _quadratic_point((930, 650), (1120, 500), (1510, 585), progress)
        draw.ellipse((x - 28, y - 28, x + 28, y + 28), fill=(167, 243, 208, 230))
        base._text(draw, (x, y), "10", 25, (20, 48, 42), bold=True, anchor="mm")
    elif template_id == "subscribe_cta":
        pulse = (math.sin(time_seconds * 4.0) + 1) / 2
        radius = round(28 + 28 * pulse)
        draw.rounded_rectangle(
            (1010 - radius, 370 - radius // 2, 1640 + radius, 700 + radius // 2),
            radius=60,
            outline=(245, 190, 73, round(70 + 80 * (1 - pulse))),
            width=5,
        )


def _beat_indicator(
    draw: ImageDraw.ImageDraw,
    template_id: str,
    duration_seconds: float,
    time_seconds: float,
) -> None:
    beats = storyboard_beats(template_id, duration_seconds)
    active = 0
    for index, beat in enumerate(beats):
        if time_seconds >= float(beat["time_seconds"]):
            active = index
    start_x = 1490
    y = 116
    draw.line((start_x, y, start_x + 250, y), fill=(100, 116, 139, 100), width=3)
    for index, beat in enumerate(beats):
        x = start_x + index * 125
        selected = index == active
        radius = 11 if selected else 7
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(52, 211, 153, 230) if selected else (100, 116, 139, 165),
        )
    base._text(
        draw,
        (1770, 142),
        str(beats[active]["label"]),
        20,
        (167, 243, 208),
        bold=True,
        anchor="ra",
    )


def apply_choreography(
    image: Image.Image,
    template_id: str,
    duration_seconds: float,
    time_seconds: float,
) -> Image.Image:
    if template_id not in base.TEMPLATE_BY_ID:
        raise HTTPException(status_code=422, detail="Unknown finance motion template")
    duration = max(1.0, float(duration_seconds))
    time_value = max(0.0, min(float(time_seconds), duration))
    progress = time_value / duration
    frame = _camera_move(image, template_id, progress).convert("RGBA")
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    _template_choreography(draw, template_id, time_value)
    _beat_indicator(draw, template_id, duration, time_value)
    visibility = min(_clamp(time_value / 0.24), _clamp((duration - time_value) / 0.24))
    if visibility < 1:
        overlay.putalpha(overlay.getchannel("A").point(lambda alpha: round(alpha * visibility)))
    return Image.alpha_composite(frame, overlay).convert("RGB")


def render_frame(
    template_id: str,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    frame = _ORIGINAL_RENDER_FRAME(template_id, duration_seconds, time_seconds, style_id)
    return apply_choreography(frame, template_id, duration_seconds, time_seconds)


# Finance Motion Studio's encoder resolves art.render_frame dynamically. Replacing
# it here upgrades both previews and full MP4 output without duplicating the
# portable Pillow/H.264 rendering pipeline.
art.render_frame = render_frame

DEFAULT_STYLE_ID = art.DEFAULT_STYLE_ID
OUTPUT_HEIGHT = art.OUTPUT_HEIGHT
OUTPUT_WIDTH = art.OUTPUT_WIDTH
STYLES = art.STYLES
TEMPLATES = art.TEMPLATES
ffmpeg_encoder_command = art.ffmpeg_encoder_command
render_finance_motion = art.render_finance_motion
style_catalog = art.style_catalog
suggest_template = art.suggest_template
template_catalog = art.template_catalog
