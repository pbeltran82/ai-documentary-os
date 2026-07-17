from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
SAFE_LEFT = 58
SAFE_RIGHT = 946

Box = tuple[float, float, float, float]
RGB = tuple[int, int, int]


@dataclass(frozen=True)
class ShortsComposition:
    regions: tuple[Box, ...]
    beat_labels: tuple[str, ...]
    terminal_cta: bool = False


DEFAULT_COMPOSITION = ShortsComposition(
    regions=(
        (0.02, 0.30, 0.39, 0.95),
        (0.315, 0.30, 0.685, 0.95),
        (0.61, 0.30, 0.98, 0.95),
    ),
    beat_labels=("ESTABLISH", "DEVELOP", "RESOLVE"),
)


COMPOSITIONS: dict[tuple[str, str], ShortsComposition] = {
    # Finance Motion
    ("finance_motion", "paycheck_split"): ShortsComposition(
        ((0.05, 0.29, 0.38, 0.88), (0.50, 0.29, 0.96, 0.60), (0.50, 0.55, 0.96, 0.89)),
        ("PAYCHECK", "LIFE + EXPENSES", "FUTURE FUNDED"),
    ),
    ("finance_motion", "expense_breakdown"): ShortsComposition(
        ((0.04, 0.30, 0.36, 0.89), (0.38, 0.30, 0.83, 0.62), (0.49, 0.56, 0.79, 0.92)),
        ("INCOME", "EXPENSE DRAIN", "NOTHING LEFT"),
    ),
    ("finance_motion", "empty_balance"): ShortsComposition(
        ((0.10, 0.28, 0.53, 0.92), (0.54, 0.30, 0.96, 0.91)),
        ("BALANCE", "DECLINED"),
    ),
    ("finance_motion", "recurring_transfer"): ShortsComposition(
        ((0.04, 0.30, 0.38, 0.90), (0.34, 0.30, 0.66, 0.90), (0.62, 0.30, 0.96, 0.90)),
        ("PAYDAY", "AUTO-TRANSFER", "CONFIRMED"),
    ),
    ("finance_motion", "index_growth"): ShortsComposition(
        ((0.04, 0.29, 0.31, 0.90), (0.26, 0.29, 0.64, 0.90), (0.58, 0.29, 0.96, 0.90)),
        ("CONTRIBUTE", "MARKET TIME", "COMPOUND BASE"),
    ),
    ("finance_motion", "compound_growth"): ShortsComposition(
        ((0.04, 0.29, 0.38, 0.91), (0.33, 0.29, 0.69, 0.91), (0.64, 0.29, 0.96, 0.91)),
        ("CONSISTENCY", "RETURNS", "ACCELERATION"),
    ),
    ("finance_motion", "pay_self_comparison"): ShortsComposition(
        ((0.04, 0.30, 0.49, 0.92), (0.51, 0.30, 0.96, 0.92)),
        ("SPEND FIRST", "INVEST FIRST"),
    ),
    ("finance_motion", "subscribe_cta"): ShortsComposition(
        ((0.08, 0.29, 0.56, 0.93),),
        ("BLUEPRINT READY",),
        terminal_cta=True,
    ),

    # Character Explainer
    ("character_explainer", "paycheck_arrival"): ShortsComposition(
        ((0.04, 0.30, 0.41, 0.93), (0.46, 0.30, 0.96, 0.62), (0.46, 0.57, 0.96, 0.93)),
        ("PAYDAY", "FIRST 10%", "FUTURE FUNDED"),
    ),
    ("character_explainer", "spend_first"): ShortsComposition(
        ((0.03, 0.30, 0.40, 0.93), (0.42, 0.30, 0.84, 0.63), (0.49, 0.57, 0.78, 0.94)),
        ("GET PAID", "SPEND", "NOTHING LEFT"),
    ),
    ("character_explainer", "empty_balance_reaction"): ShortsComposition(
        ((0.04, 0.30, 0.41, 0.93), (0.43, 0.30, 0.96, 0.93)),
        ("CHECK", "DECLINED"),
    ),
    ("character_explainer", "pay_self_character_comparison"): ShortsComposition(
        ((0.03, 0.30, 0.49, 0.94), (0.51, 0.30, 0.97, 0.94)),
        ("SPEND FIRST", "PAY SELF FIRST"),
    ),
    ("character_explainer", "automatic_investing_habit"): ShortsComposition(
        ((0.03, 0.30, 0.40, 0.93), (0.41, 0.30, 0.97, 0.93)),
        ("SET THE RULE", "LET IT RUN"),
    ),

    # Tech & Behavior Motion
    ("tech_behavior_motion", "algorithm_chose_you"): ShortsComposition(
        ((0.035, 0.315, 0.335, 0.925), (0.345, 0.315, 0.645, 0.925), (0.665, 0.315, 0.965, 0.925)),
        ("POSSIBILITIES", "RANKING", "SELECTED"),
    ),
    ("tech_behavior_motion", "behavior_prediction_engine"): ShortsComposition(
        ((0.040, 0.335, 0.385, 0.835), (0.380, 0.335, 0.640, 0.835), (0.660, 0.335, 0.955, 0.835)),
        ("SIGNALS", "MODEL", "PROBABILITY"),
    ),
    ("tech_behavior_motion", "life_event_timeline"): ShortsComposition(
        ((0.035, 0.315, 0.500, 0.735), (0.500, 0.315, 0.965, 0.735)),
        ("PAST RECORDS", "FUTURE ESTIMATES"),
    ),
    ("tech_behavior_motion", "digital_footprint_collector"): ShortsComposition(
        ((0.040, 0.320, 0.390, 0.920), (0.500, 0.320, 0.960, 0.920)),
        ("INTERACTIONS", "BEHAVIORAL RECORD"),
    ),
    ("tech_behavior_motion", "behavioral_twin"): ShortsComposition(
        ((0.035, 0.350, 0.320, 0.930), (0.325, 0.350, 0.675, 0.930), (0.680, 0.350, 0.965, 0.930)),
        ("PERSON", "SIGNALS", "BEHAVIORAL TWIN"),
    ),
    ("tech_behavior_motion", "machine_choice_explainer"): ShortsComposition(
        ((0.035, 0.320, 0.400, 0.850), (0.425, 0.300, 0.960, 0.850)),
        ("VISIBLE ACTION", "HIDDEN RANKING"),
    ),
    ("tech_behavior_motion", "machine_choice_cta"): ShortsComposition(
        ((0.040, 0.320, 0.480, 0.755), (0.520, 0.320, 0.960, 0.755)),
        ("YOUR CHOICE", "MACHINE RANK"),
        terminal_cta=True,
    ),
}


FAMILY_COPY = {
    "finance_motion": ("MONEY SYSTEM", (224, 174, 83)),
    "character_explainer": ("HUMAN STORY", (84, 214, 194)),
    "tech_behavior_motion": ("TECH & BEHAVIOR", (34, 211, 238)),
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _smooth(value: float) -> float:
    value = _clamp(value)
    return value * value * (3 - 2 * value)


@lru_cache(maxsize=48)
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    mac_name = "Arial Bold.ttf" if bold else "Arial.ttf"
    linux_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    candidates = (
        Path("/System/Library/Fonts/Supplemental") / mac_name,
        Path("/Library/Fonts") / mac_name,
        Path("/usr/share/fonts/truetype/dejavu") / linux_name,
        Path("/usr/share/fonts/truetype/liberation2")
        / ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"),
    )
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _text(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    value: str,
    size: int,
    fill: RGB,
    *,
    bold: bool = False,
    anchor: str | None = None,
) -> None:
    x, y = position
    font = _font(size, bold)
    draw.text((x + 2, y + 3), value, font=font, fill=(0, 0, 0), anchor=anchor)
    draw.text((x, y), value, font=font, fill=fill, anchor=anchor)


def _wrap_text(value: str, maximum_width: int, size: int, *, bold: bool, maximum_lines: int) -> list[str]:
    font = _font(size, bold)
    words = str(value or "").strip().split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font.getlength(candidate) <= maximum_width:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)
    if len(lines) <= maximum_lines:
        return lines
    kept = lines[:maximum_lines]
    final_words = " ".join(lines[maximum_lines - 1 :]).split()
    final = ""
    for word in final_words:
        candidate = f"{final} {word}".strip()
        if font.getlength(f"{candidate}…") > maximum_width:
            break
        final = candidate
    kept[-1] = f"{final}…" if final else kept[-1]
    return kept


def _relative_crop(source: Image.Image, box: Box) -> Image.Image:
    width, height = source.size
    return source.crop(
        (
            round(box[0] * width),
            round(box[1] * height),
            round(box[2] * width),
            round(box[3] * height),
        )
    )


def _fit(image: Image.Image, width: int, height: int) -> Image.Image:
    scale = min(width / image.width, height / image.height)
    return image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )


def _cover(image: Image.Image, width: int, height: int) -> Image.Image:
    scale = max(width / image.width, height / image.height)
    resized = image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.BILINEAR,
    )
    left = max(0, (resized.width - width) // 2)
    top = max(0, (resized.height - height) // 2)
    return resized.crop((left, top, left + width, top + height))


def _ambient_background(source: Image.Image) -> Image.Image:
    small = _cover(source, SHORTS_WIDTH // 4, SHORTS_HEIGHT // 4)
    small = small.filter(ImageFilter.GaussianBlur(radius=18))
    small = ImageEnhance.Brightness(small).enhance(0.27)
    small = ImageEnhance.Color(small).enhance(0.72)
    canvas = small.resize((SHORTS_WIDTH, SHORTS_HEIGHT), Image.Resampling.BILINEAR).convert("RGB")
    overlay = Image.new("RGBA", canvas.size, (1, 5, 14, 138))
    return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def _focus_surface(region: Image.Image, size: tuple[int, int], accent: RGB) -> Image.Image:
    width, height = size
    background = _cover(region, width, height).filter(ImageFilter.GaussianBlur(radius=22))
    background = ImageEnhance.Brightness(background).enhance(0.34).convert("RGB")
    fitted = _fit(region, width - 28, height - 28)
    background.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))

    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=34, fill=255)
    surface = Image.new("RGB", (width, height), (4, 10, 22))
    surface.paste(background, (0, 0), mask)
    draw = ImageDraw.Draw(surface)
    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=34, outline=accent, width=3)
    return surface


def _focus_state(progress: float, count: int) -> tuple[int, int | None, float]:
    if count <= 1:
        return 0, None, 0.0
    position = _clamp(progress) * count
    current = min(count - 1, int(position))
    local = position - current
    if current >= count - 1 or local < 0.78:
        return current, None, 0.0
    return current, current + 1, _smooth((local - 0.78) / 0.22)


def _draw_header(
    canvas: Image.Image,
    *,
    family_id: str | None,
    title: str,
    subtitle: str,
    accent: RGB,
) -> None:
    draw = ImageDraw.Draw(canvas)
    family_label = FAMILY_COPY.get(family_id or "", ("DOCUMENTARY VISUAL", accent))[0]
    pill_width = max(220, round(_font(22, True).getlength(family_label)) + 54)
    draw.rounded_rectangle(
        (SAFE_LEFT, 62, SAFE_LEFT + pill_width, 118),
        radius=28,
        fill=(24, 34, 55),
        outline=accent,
        width=2,
    )
    _text(draw, (SAFE_LEFT + pill_width // 2, 90), family_label, 22, accent, bold=True, anchor="mm")

    resolved_title = str(title or "DOCUMENTARY VISUAL").upper()
    title_size = 62 if len(resolved_title) <= 30 else 54 if len(resolved_title) <= 44 else 48
    title_lines = _wrap_text(resolved_title, SAFE_RIGHT - SAFE_LEFT, title_size, bold=True, maximum_lines=2)
    y = 148
    for line in title_lines:
        _text(draw, (SAFE_LEFT, y), line, title_size, (248, 250, 252), bold=True)
        y += title_size + 11

    subtitle_lines = _wrap_text(subtitle, SAFE_RIGHT - SAFE_LEFT, 29, bold=False, maximum_lines=2)
    y += 5
    for line in subtitle_lines:
        _text(draw, (SAFE_LEFT, y), line, 29, (171, 184, 204))
        y += 39
    draw.rounded_rectangle((SAFE_LEFT, 371, SAFE_RIGHT, 379), radius=4, fill=(30, 42, 67))
    draw.rounded_rectangle((SAFE_LEFT, 371, SAFE_LEFT + 260, 379), radius=4, fill=accent)


def _draw_beat_footer(
    canvas: Image.Image,
    *,
    labels: tuple[str, ...],
    active_index: int,
    progress: float,
    accent: RGB,
) -> None:
    draw = ImageDraw.Draw(canvas)
    count = max(1, len(labels))
    label = labels[min(active_index, count - 1)] if labels else "STORY BEAT"
    _text(draw, (SAFE_LEFT, 1498), f"BEAT {active_index + 1:02d} / {count:02d}", 24, (139, 154, 178), bold=True)
    lines = _wrap_text(label.upper(), SAFE_RIGHT - SAFE_LEFT, 48, bold=True, maximum_lines=2)
    y = 1545
    for line in lines:
        _text(draw, (SAFE_LEFT, y), line, 48, (248, 250, 252), bold=True)
        y += 58

    gap = 14
    segment_width = (SAFE_RIGHT - SAFE_LEFT - gap * (count - 1)) // count
    y = 1672
    for index in range(count):
        left = SAFE_LEFT + index * (segment_width + gap)
        draw.rounded_rectangle((left, y, left + segment_width, y + 12), radius=6, fill=(38, 50, 76))
        if index < active_index:
            amount = 1.0
        elif index > active_index:
            amount = 0.0
        else:
            segment_position = _clamp(progress) * count - active_index
            amount = max(0.08, min(1.0, segment_position))
        if amount > 0:
            draw.rounded_rectangle((left, y, left + round(segment_width * amount), y + 12), radius=6, fill=accent)
    _text(draw, (SAFE_LEFT, 1742), "AI DOCUMENTARY OS", 20, (101, 116, 139), bold=True)


def _draw_like_icon(draw: ImageDraw.ImageDraw, center: tuple[int, int]) -> None:
    x, y = center
    draw.rounded_rectangle((x - 35, y - 12, x - 17, y + 27), radius=5, fill=(248, 250, 252))
    hand = (
        (x - 12, y + 24), (x + 20, y + 24), (x + 29, y + 15),
        (x + 31, y - 5), (x + 25, y - 12), (x + 8, y - 12),
        (x + 14, y - 30), (x + 10, y - 39), (x + 2, y - 40),
        (x - 8, y - 19), (x - 14, y - 10),
    )
    draw.polygon(hand, fill=(248, 250, 252))


def _draw_terminal_cta(canvas: Image.Image, progress: float, accent: RGB) -> None:
    draw = ImageDraw.Draw(canvas)
    _text(draw, (SAFE_LEFT, 1268), "SUPPORT THE NEXT STORY", 34, (190, 201, 218), bold=True)

    subscribe = _smooth((progress - 0.04) / 0.08)
    like = _smooth((progress - 0.10) / 0.08)
    y = 1450
    if subscribe > 0.02:
        width = round(560 * (0.86 + 0.14 * subscribe))
        left = SAFE_LEFT + (560 - width) // 2
        top = round(y - 61 + (1 - subscribe) * 24)
        right = left + width
        bottom = top + 122
        draw.rounded_rectangle((left + 8, top + 9, right + 8, bottom + 9), radius=30, fill=(3, 6, 14))
        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=30,
            fill=(220, 53, 69),
            outline=(254, 202, 202),
            width=3,
        )
        play_x = left + 68
        draw.polygon(((play_x - 12, y - 24), (play_x - 12, y + 24), (play_x + 25, y)), fill=(248, 250, 252))
        _text(draw, (left + round(width * 0.61), y), "SUBSCRIBE", 43, (248, 250, 252), bold=True, anchor="mm")

    if like > 0.02:
        width = round(276 * (0.82 + 0.18 * like))
        right = SAFE_RIGHT
        left = right - width
        top = round(y - 53 + (1 - like) * 24)
        bottom = top + 106
        draw.rounded_rectangle((left + 7, top + 8, right + 7, bottom + 8), radius=53, fill=(3, 6, 14))
        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=53,
            fill=(48, 126, 218),
            outline=(160, 211, 255),
            width=3,
        )
        _draw_like_icon(draw, (left + 62, y))
        _text(draw, (left + round(width * 0.69), y), "LIKE", 35, (248, 250, 252), bold=True, anchor="mm")

    draw.rounded_rectangle((SAFE_LEFT, 1586, SAFE_RIGHT, 1598), radius=6, fill=(38, 50, 76))
    draw.rounded_rectangle(
        (
            SAFE_LEFT,
            1586,
            SAFE_LEFT + round((SAFE_RIGHT - SAFE_LEFT) * _clamp(progress)),
            1598,
        ),
        radius=6,
        fill=accent,
    )
    _text(draw, (SAFE_LEFT, 1643), "THANKS FOR WATCHING", 25, (139, 154, 178), bold=True)


def compose_native_shorts(
    source: Image.Image,
    *,
    family_id: str | None,
    template_id: str | None,
    progress: float = 0.5,
    title: str | None = None,
    subtitle: str | None = None,
) -> Image.Image:
    """Build a native 9:16 story from semantic regions of a 16:9 exact visual.

    Known templates receive deliberate focus regions. Unknown future templates
    automatically progress through overlapping left, center, and right beats.
    Only one large visual idea is presented at a time, preserving mobile-scale
    readability without changing the source family's 16:9 renderer.
    """
    source = source.convert("RGB")
    resolved_progress = _clamp(progress)
    composition = COMPOSITIONS.get((family_id or "", template_id or ""), DEFAULT_COMPOSITION)
    accent = FAMILY_COPY.get(family_id or "", ("DOCUMENTARY VISUAL", (84, 214, 194)))[1]
    canvas = _ambient_background(source)

    resolved_title = title or str(template_id or "documentary visual").replace("_", " ")
    _draw_header(
        canvas,
        family_id=family_id,
        title=resolved_title,
        subtitle=subtitle or "A focused visual story, composed for vertical viewing.",
        accent=accent,
    )

    focus_box = (SAFE_LEFT, 410, SAFE_RIGHT, 1208 if composition.terminal_cta else 1458)
    focus_width = focus_box[2] - focus_box[0]
    focus_height = focus_box[3] - focus_box[1]
    current, following, blend = _focus_state(resolved_progress, len(composition.regions))
    current_surface = _focus_surface(
        _relative_crop(source, composition.regions[current]),
        (focus_width, focus_height),
        accent,
    )
    if following is not None and blend > 0:
        following_surface = _focus_surface(
            _relative_crop(source, composition.regions[following]),
            (focus_width, focus_height),
            accent,
        )
        current_surface = Image.blend(current_surface, following_surface, blend)
    canvas.paste(current_surface, (focus_box[0], focus_box[1]))

    active = following if following is not None and blend >= 0.5 else current
    if composition.terminal_cta:
        _draw_terminal_cta(canvas, resolved_progress, accent)
    else:
        _draw_beat_footer(
            canvas,
            labels=composition.beat_labels,
            active_index=active,
            progress=resolved_progress,
            accent=accent,
        )

    visibility = min(
        _smooth(resolved_progress / 0.035),
        _smooth((1.0 - resolved_progress) / 0.035),
    )
    if visibility < 1:
        return Image.blend(Image.new("RGB", canvas.size, (3, 8, 18)), canvas, visibility)
    return canvas
