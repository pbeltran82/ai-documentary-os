from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import median

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageStat


SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
SAFE_LEFT = 70
SAFE_RIGHT = 1010

Box = tuple[float, float, float, float]
RGB = tuple[int, int, int]

_CUTOUT_CACHE: OrderedDict[
    tuple[int, Box], tuple[Image.Image, Image.Image]
] = OrderedDict()
_CUTOUT_CACHE_SIZE = 6


@dataclass(frozen=True)
class ShortsComposition:
    """One durable visual thesis for a vertical documentary scene."""

    hero_region: Box
    focus_label: str
    terminal_cta: bool = False


DEFAULT_COMPOSITION = ShortsComposition(
    hero_region=(0.18, 0.27, 0.82, 0.93),
    focus_label="THE KEY IDEA",
)


# These regions deliberately sit inside the source cards. The foreground
# extractor removes their dark panels, borders, and grids before the selected
# visual is placed on a clean Shorts canvas.
COMPOSITIONS: dict[tuple[str, str], ShortsComposition] = {
    # Finance Motion
    ("finance_motion", "paycheck_split"): ShortsComposition(
        (0.48, 0.61, 0.90, 0.82), "FUTURE FUNDED"
    ),
    ("finance_motion", "expense_breakdown"): ShortsComposition(
        (0.38, 0.34, 0.79, 0.82), "THE EXPENSE DRAIN"
    ),
    ("finance_motion", "empty_balance"): ShortsComposition(
        (0.58, 0.38, 0.86, 0.75), "PAYMENT DECLINED"
    ),
    ("finance_motion", "recurring_transfer"): ShortsComposition(
        (0.36, 0.36, 0.87, 0.83), "TRANSFER CONFIRMED"
    ),
    ("finance_motion", "index_growth"): ShortsComposition(
        (0.28, 0.38, 0.91, 0.83), "LONG-TERM MARKET GROWTH"
    ),
    ("finance_motion", "compound_growth"): ShortsComposition(
        (0.34, 0.42, 0.90, 0.84), "COMPOUNDING ACCELERATES"
    ),
    ("finance_motion", "pay_self_comparison"): ShortsComposition(
        (0.53, 0.39, 0.90, 0.84), "INVEST FIRST"
    ),
    ("finance_motion", "subscribe_cta"): ShortsComposition(
        (0.12, 0.42, 0.50, 0.84), "BLUEPRINT READY", terminal_cta=True
    ),

    # Character Explainer
    ("character_explainer", "paycheck_arrival"): ShortsComposition(
        (0.14, 0.43, 0.39, 0.82), "PAYDAY"
    ),
    ("character_explainer", "spend_first"): ShortsComposition(
        (0.43, 0.37, 0.79, 0.85), "THE SPEND-FIRST CYCLE"
    ),
    ("character_explainer", "empty_balance_reaction"): ShortsComposition(
        (0.51, 0.48, 0.91, 0.78), "NOTHING LEFT"
    ),
    ("character_explainer", "pay_self_character_comparison"): ShortsComposition(
        (0.54, 0.40, 0.93, 0.84), "PAY SELF FIRST"
    ),
    ("character_explainer", "automatic_investing_habit"): ShortsComposition(
        (0.43, 0.39, 0.90, 0.80), "LET THE SYSTEM RUN"
    ),

    # Tech & Behavior Motion
    ("tech_behavior_motion", "algorithm_chose_you"): ShortsComposition(
        (0.75, 0.45, 0.88, 0.67), "THE SELECTED OUTCOME"
    ),
    ("tech_behavior_motion", "behavior_prediction_engine"): ShortsComposition(
        (0.68, 0.62, 0.93, 0.75), "PREDICTED PROBABILITY"
    ),
    ("tech_behavior_motion", "life_event_timeline"): ShortsComposition(
        (0.50, 0.53, 0.88, 0.68), "FUTURE ESTIMATES"
    ),
    ("tech_behavior_motion", "digital_footprint_collector"): ShortsComposition(
        (0.60, 0.46, 0.90, 0.77), "THE BEHAVIORAL RECORD"
    ),
    ("tech_behavior_motion", "behavioral_twin"): ShortsComposition(
        (0.72, 0.39, 0.87, 0.84), "BEHAVIORAL TWIN"
    ),
    ("tech_behavior_motion", "machine_choice_explainer"): ShortsComposition(
        (0.50, 0.44, 0.76, 0.73), "THE HIDDEN RANKING"
    ),
    ("tech_behavior_motion", "machine_choice_cta"): ShortsComposition(
        (0.61, 0.44, 0.80, 0.66), "THE MACHINE RANK", terminal_cta=True
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


def _edge_background_colors(image: Image.Image) -> tuple[RGB, ...]:
    """Estimate the dark panel colors from a sparse sample around the crop."""
    sample = image.convert("RGB").resize((48, 32), Image.Resampling.BILINEAR)
    pixels = sample.load()
    edge: list[RGB] = []
    for x in range(sample.width):
        edge.extend((pixels[x, 0], pixels[x, 1], pixels[x, sample.height - 2], pixels[x, sample.height - 1]))
    for y in range(1, sample.height - 1):
        edge.extend((pixels[0, y], pixels[1, y], pixels[sample.width - 2, y], pixels[sample.width - 1, y]))

    # The median is dependable for a uniform panel. Four edge quadrants make
    # the extraction robust to the gentle gradients used by the house styles.
    colors: list[RGB] = []
    for group in (edge, edge[: len(edge) // 2], edge[len(edge) // 2 :], edge[::2], edge[1::2]):
        if not group:
            continue
        colors.append(tuple(round(median(pixel[channel] for pixel in group)) for channel in range(3)))
    return tuple(dict.fromkeys(colors))


def _distance_from_color(image: Image.Image, color: RGB) -> Image.Image:
    difference = ImageChops.difference(image, Image.new("RGB", image.size, color))
    red, green, blue = difference.split()
    return ImageChops.lighter(ImageChops.lighter(red, green), blue)


def _foreground_mask(image: Image.Image) -> Image.Image:
    distances = [_distance_from_color(image, color) for color in _edge_background_colors(image)]
    distance = distances[0]
    for candidate in distances[1:]:
        distance = ImageChops.darker(distance, candidate)

    def resolved_mask(threshold: int) -> Image.Image:
        raw = distance.point(lambda value: 255 if value >= threshold else 0, mode="L")
        raw = _suppress_long_rules(raw)
        # Opening removes the thin grids and card outlines. The final, slightly
        # larger dilation restores antialiased edges and dark character detail
        # around the remaining solid shapes.
        return raw.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(9))

    mask = resolved_mask(34)
    if ImageStat.Stat(mask).mean[0] / 255 > 0.62:
        mask = resolved_mask(50)
    return mask.filter(ImageFilter.GaussianBlur(1.2))


def _suppress_long_rules(mask: Image.Image) -> Image.Image:
    """Remove full-width grid rules and panel edges without harming subjects."""
    cleaned = mask.copy()
    draw = ImageDraw.Draw(cleaned)

    def runs(values: list[int], threshold: int, maximum_thickness: int):
        start: int | None = None
        for index, value in enumerate(values + [0]):
            if value >= threshold and start is None:
                start = index
            elif value < threshold and start is not None:
                if index - start <= maximum_thickness:
                    yield start, index - 1
                start = None

    row_coverage = list(mask.resize((1, mask.height), Image.Resampling.BOX).getdata())
    for top, bottom in runs(row_coverage, 150, max(10, round(mask.height * 0.035))):
        draw.rectangle((0, max(0, top - 2), mask.width, min(mask.height - 1, bottom + 2)), fill=0)

    column_coverage = list(cleaned.resize((cleaned.width, 1), Image.Resampling.BOX).getdata())
    for left, right in runs(column_coverage, 150, max(10, round(mask.width * 0.035))):
        draw.rectangle((max(0, left - 2), 0, min(mask.width - 1, right + 2), mask.height), fill=0)
    return cleaned


def _foreground_cutout(region: Image.Image) -> Image.Image:
    source = region.convert("RGB")
    mask = _foreground_mask(source)
    solid_bbox = mask.point(lambda value: 255 if value >= 18 else 0, mode="L").getbbox()
    if solid_bbox is None:
        # Future renderers still get a useful image, but never inherit the
        # source's full bordered card as a second frame.
        inset = max(6, min(source.size) // 24)
        source = source.crop((inset, inset, source.width - inset, source.height - inset))
        mask = Image.new("L", source.size, 255)
        solid_bbox = (0, 0, source.width, source.height)
    else:
        source = source.crop(solid_bbox)
        mask = mask.crop(solid_bbox)
    cutout = source.convert("RGBA")
    cutout.putalpha(mask)
    return cutout


def _cached_foreground_cutout(source: Image.Image, box: Box) -> Image.Image:
    key = (id(source), box)
    cached = _CUTOUT_CACHE.get(key)
    if cached is not None and cached[0] is source:
        _CUTOUT_CACHE.move_to_end(key)
        return cached[1]
    cutout = _foreground_cutout(_relative_crop(source, box))
    _CUTOUT_CACHE[key] = (source, cutout)
    _CUTOUT_CACHE.move_to_end(key)
    while len(_CUTOUT_CACHE) > _CUTOUT_CACHE_SIZE:
        _CUTOUT_CACHE.popitem(last=False)
    return cutout


@lru_cache(maxsize=4)
def _clean_background(accent: RGB) -> Image.Image:
    top = (3, 7, 15)
    bottom = (8, 12, 24)
    gradient = Image.new("RGB", (1, SHORTS_HEIGHT))
    pixels = gradient.load()
    for y in range(SHORTS_HEIGHT):
        mix = y / max(1, SHORTS_HEIGHT - 1)
        pixels[0, y] = tuple(round(top[channel] + (bottom[channel] - top[channel]) * mix) for channel in range(3))
    canvas = gradient.resize((SHORTS_WIDTH, SHORTS_HEIGHT))

    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((-170, 300, 1250, 1600), fill=(*accent, 34))
    glow = glow.filter(ImageFilter.GaussianBlur(190))
    return Image.alpha_composite(canvas.convert("RGBA"), glow).convert("RGB")


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
    pill_width = max(218, round(_font(21, True).getlength(family_label)) + 50)
    draw.rounded_rectangle(
        (SAFE_LEFT, 68, SAFE_LEFT + pill_width, 120),
        radius=26,
        fill=(18, 28, 47),
    )
    _text(draw, (SAFE_LEFT + pill_width // 2, 94), family_label, 21, accent, bold=True, anchor="mm")

    resolved_title = str(title or "DOCUMENTARY VISUAL").upper()
    title_size = 61 if len(resolved_title) <= 30 else 53 if len(resolved_title) <= 44 else 47
    title_lines = _wrap_text(resolved_title, SAFE_RIGHT - SAFE_LEFT, title_size, bold=True, maximum_lines=2)
    y = 151
    for line in title_lines:
        _text(draw, (SAFE_LEFT, y), line, title_size, (248, 250, 252), bold=True)
        y += title_size + 10

    subtitle_lines = _wrap_text(subtitle, SAFE_RIGHT - SAFE_LEFT, 28, bold=False, maximum_lines=2)
    y += 4
    for line in subtitle_lines:
        _text(draw, (SAFE_LEFT, y), line, 28, (174, 187, 207))
        y += 38


def _draw_hero(
    canvas: Image.Image,
    cutout: Image.Image,
    *,
    progress: float,
    terminal_cta: bool,
) -> None:
    stage = (SAFE_LEFT, 410, SAFE_RIGHT, 1155 if terminal_cta else 1450)
    max_width = stage[2] - stage[0] - 24
    max_height = stage[3] - stage[1] - 24
    hero = _fit(cutout, max_width, max_height)

    # One uninterrupted visual idea: a restrained 1.8% camera push and a
    # six-pixel float replace the previous carousel and crossfades.
    camera = 0.982 + 0.018 * _smooth(progress)
    hero = hero.resize(
        (max(1, round(hero.width * camera)), max(1, round(hero.height * camera))),
        Image.Resampling.LANCZOS,
    )
    x = round((SHORTS_WIDTH - hero.width) / 2)
    float_y = round(6 * math.sin(_clamp(progress) * math.pi))
    y = round(stage[1] + (stage[3] - stage[1] - hero.height) / 2 - float_y)

    shadow_alpha = hero.getchannel("A").filter(ImageFilter.GaussianBlur(18))
    shadow_alpha = shadow_alpha.point(lambda value: round(value * 0.48), mode="L")
    shadow = Image.new("RGBA", hero.size, (0, 0, 0, 0))
    shadow.putalpha(shadow_alpha)
    canvas.paste(shadow, (x + 12, y + 18), shadow)
    canvas.paste(hero, (x, y), hero)


def _draw_focus_label(canvas: Image.Image, label: str, accent: RGB) -> None:
    draw = ImageDraw.Draw(canvas)
    _text(draw, (SAFE_LEFT, 1513), "KEY IDEA", 21, accent, bold=True)
    lines = _wrap_text(label.upper(), SAFE_RIGHT - SAFE_LEFT, 47, bold=True, maximum_lines=2)
    y = 1552
    for line in lines:
        _text(draw, (SAFE_LEFT, y), line, 47, (248, 250, 252), bold=True)
        y += 57
    _text(draw, (SAFE_LEFT, 1770), "AI DOCUMENTARY OS", 19, (91, 106, 130), bold=True)


def _draw_like_icon(draw: ImageDraw.ImageDraw, center: tuple[int, int]) -> None:
    x, y = center
    draw.rounded_rectangle((x - 31, y - 10, x - 15, y + 24), radius=4, fill=(248, 250, 252))
    hand = (
        (x - 10, y + 21), (x + 18, y + 21), (x + 27, y + 13),
        (x + 29, y - 5), (x + 23, y - 11), (x + 7, y - 11),
        (x + 13, y - 28), (x + 9, y - 36), (x + 2, y - 37),
        (x - 7, y - 17), (x - 12, y - 9),
    )
    draw.polygon(hand, fill=(248, 250, 252))


def _draw_terminal_cta(canvas: Image.Image, progress: float) -> None:
    draw = ImageDraw.Draw(canvas)
    _text(draw, (SAFE_LEFT, 1217), "SUPPORT THE NEXT STORY", 30, (187, 199, 217), bold=True)

    subscribe = _smooth((progress - 0.02) / 0.09)
    like = _smooth((progress - 0.07) / 0.09)
    y = 1382
    if subscribe > 0.02:
        width = round(540 * (0.90 + 0.10 * subscribe))
        left = SAFE_LEFT + (540 - width) // 2
        top = round(y - 48 + (1 - subscribe) * 18)
        right = left + width
        bottom = top + 96
        draw.rounded_rectangle((left + 7, top + 8, right + 7, bottom + 8), radius=24, fill=(2, 5, 12))
        draw.rounded_rectangle((left, top, right, bottom), radius=24, fill=(220, 53, 69))
        play_x = left + 61
        draw.polygon(((play_x - 10, y - 20), (play_x - 10, y + 20), (play_x + 21, y)), fill=(248, 250, 252))
        _text(draw, (left + round(width * 0.61), y), "SUBSCRIBE", 38, (248, 250, 252), bold=True, anchor="mm")

    if like > 0.02:
        width = round(274 * (0.88 + 0.12 * like))
        right = SAFE_RIGHT
        left = right - width
        top = round(y - 48 + (1 - like) * 18)
        bottom = top + 96
        draw.rounded_rectangle((left + 7, top + 8, right + 7, bottom + 8), radius=48, fill=(2, 5, 12))
        draw.rounded_rectangle((left, top, right, bottom), radius=48, fill=(48, 126, 218))
        _draw_like_icon(draw, (left + 59, y))
        _text(draw, (left + round(width * 0.70), y), "LIKE", 32, (248, 250, 252), bold=True, anchor="mm")

    _text(draw, (SAFE_LEFT, 1506), "THANKS FOR WATCHING", 23, (122, 138, 162), bold=True)


def compose_native_shorts(
    source: Image.Image,
    *,
    family_id: str | None,
    template_id: str | None,
    progress: float = 0.5,
    title: str | None = None,
    subtitle: str | None = None,
) -> Image.Image:
    """Compose one clean, persistent visual thesis for a 9:16 scene.

    Source panels are treated as raw art, not as a second layout. Their grids,
    card borders, and dark backgrounds are removed before the selected hero is
    placed on a clean vertical canvas. Progress controls only a subtle camera
    push; it never swaps ideas within the scene.
    """
    source = source if source.mode == "RGB" else source.convert("RGB")
    resolved_progress = _clamp(progress)
    composition = COMPOSITIONS.get((family_id or "", template_id or ""), DEFAULT_COMPOSITION)
    accent = FAMILY_COPY.get(family_id or "", ("DOCUMENTARY VISUAL", (84, 214, 194)))[1]
    canvas = _clean_background(accent).copy()

    resolved_title = title or str(template_id or "documentary visual").replace("_", " ")
    _draw_header(
        canvas,
        family_id=family_id,
        title=resolved_title,
        subtitle=subtitle or "One clear documentary idea, composed for vertical viewing.",
        accent=accent,
    )
    _draw_hero(
        canvas,
        _cached_foreground_cutout(source, composition.hero_region),
        progress=resolved_progress,
        terminal_cta=composition.terminal_cta,
    )

    if composition.terminal_cta:
        _draw_terminal_cta(canvas, resolved_progress)
    else:
        _draw_focus_label(canvas, composition.focus_label, accent)

    visibility = min(
        _smooth(resolved_progress / 0.045),
        _smooth((1.0 - resolved_progress) / 0.045),
    )
    if visibility < 1:
        return Image.blend(Image.new("RGB", canvas.size, (3, 7, 15)), canvas, visibility)
    return canvas
