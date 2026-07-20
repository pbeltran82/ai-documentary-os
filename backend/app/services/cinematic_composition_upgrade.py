from __future__ import annotations

"""Cinematic composition upgrades for regular 16:9 documentary frames.

This patch changes only the drawing layer. Narration, timing, audio, captions,
persistence, APIs, and FFmpeg behavior remain untouched.
"""

import math

from PIL import ImageDraw

from . import documentary_variety_expansion as expansion
from . import tech_behavior_motion as base
from . import tech_behavior_truthful as truthful


UPGRADED_TEMPLATES = (
    "algorithm_chose_you",
    "behavioral_twin",
    "consequence_map",
)


def _compact_common(
    draw: ImageDraw.ImageDraw,
    template: base.TechTemplate,
    palette: dict[str, tuple[int, int, int]],
    progress: float,
) -> None:
    """Keep a single short headline and make the image carry the scene."""
    base._pill(
        draw,
        (235, 94),
        "TECH & BEHAVIOR",
        palette,
        fill=palette["panel_alt"],
        width=275,
        text_fill=palette["accent"],
    )
    title = " ".join(template.title.split()[:7])[:54].rstrip(" ,.;:-")
    base.engine._text(draw, (110, 150), title, 50, palette["white"], bold=True)
    draw.rounded_rectangle((112, 235, 690, 243), radius=4, fill=palette["panel_alt"])
    draw.rounded_rectangle(
        (112, 235, 112 + round(578 * progress), 243),
        radius=4,
        fill=palette["accent"],
    )


def _atmospheric_depth(
    draw: ImageDraw.ImageDraw,
    palette: dict[str, tuple[int, int, int]],
    progress: float,
    *,
    focus_x: int,
) -> None:
    """Add deterministic foreground, midground, and background depth."""
    drift = round(28 * math.sin(progress * math.pi * 2))
    draw.ellipse(
        (focus_x - 620 + drift, 300, focus_x + 560 + drift, 1120),
        fill=palette["panel"],
    )
    draw.ellipse(
        (focus_x - 420 - drift, 410, focus_x + 420 - drift, 1040),
        outline=palette["panel_alt"],
        width=18,
    )
    draw.polygon(((0, 960), (360, 820), (690, 1080), (0, 1080)), fill=(3, 7, 17))
    draw.polygon(((1920, 930), (1590, 790), (1320, 1080), (1920, 1080)), fill=(3, 7, 17))


def _cinematic_algorithm_chose_you(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    rank = base._phase(progress, 0.08, 0.62)
    selection = base._phase(progress, 0.52, 0.92)
    _atmospheric_depth(draw, palette, progress, focus_x=1280)
    field = ((180, 410), (430, 350), (680, 470), (300, 650), (570, 760), (850, 610), (250, 870))
    target = (1235, 620)
    for index, point in enumerate(field):
        local = base._phase(rank, index * 0.08, min(1.0, index * 0.08 + 0.42))
        radius = 22 + (index % 3) * 8
        color = palette["accent_alt"] if local > 0.25 else palette["panel_alt"]
        base._node(draw, point, radius, color)
        if local > 0.18:
            draw.line((*point, *target), fill=palette["accent"], width=2 + index % 3)
    phone = (1110, 320, 1905, 1010)
    draw.rounded_rectangle(phone, radius=78, fill=(3, 7, 18), outline=palette["accent"], width=8)
    draw.rounded_rectangle((1160, 390, 1855, 945), radius=52, fill=palette["panel"])
    selected_y = 520 + round(75 * (1.0 - selection))
    for index in range(4):
        y = 440 + index * 125
        active = index == 1
        fill = palette["accent"] if active and selection > 0.28 else palette["panel_alt"]
        draw.rounded_rectangle((1225, y, 1790, y + 88), radius=24, fill=fill)
        if active:
            draw.rounded_rectangle((1260, selected_y, 1450, selected_y + 24), radius=12, fill=palette["good"])
            base.engine._text(draw, (1515, y + 44), "RANKED FIRST", 24, palette["ink"], bold=True, anchor="mm")
        else:
            draw.rounded_rectangle((1260, y + 28, 1540, y + 48), radius=10, fill=palette["muted"])
    draw.ellipse((1740, 560, 1820, 640), fill=palette["good"])
    base.engine._text(draw, (1780, 600), "1", 30, palette["ink"], bold=True, anchor="mm")


def _cinematic_behavioral_twin(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    transfer = base._phase(progress, 0.10, 0.70)
    _atmospheric_depth(draw, palette, progress, focus_x=980)
    character_palette = truthful.tech_character_palette(palette)
    draw.polygon(((120, 905), (960, 710), (1820, 905), (1920, 1080), (0, 1080)), fill=palette["panel_alt"])
    draw.ellipse((170, 825, 760, 965), fill=(4, 9, 20))
    draw.ellipse((1110, 810, 1770, 975), fill=(4, 9, 20))
    truthful.characters.draw_expressive_person(
        draw, (530, 920), character_palette, progress=progress, scale=1.48,
        pose="relaxed", mood="neutral", facing=1,
    )
    truthful.characters.draw_expressive_person(
        draw, (1390, 915), character_palette, progress=progress, scale=1.55,
        pose="explain", mood="confident", facing=-1, alternate=True,
        hair_style="curly_crop",
    )
    paths = ((650, 430, "SEARCH"), (760, 560, "PAUSE"), (875, 690, "DRAFT"), (1000, 805, "WATCH"))
    for index, (x, y, label) in enumerate(paths):
        local = base._phase(transfer, index * 0.13, min(1.0, index * 0.13 + 0.44))
        end_x = round(x + (1170 - x) * local)
        draw.line((x, y, end_x, y), fill=palette["accent_alt"], width=5)
        if local > 0.15:
            base._pill(draw, (end_x, y), label, palette, fill=palette["accent_alt"], width=145, text_fill=palette["white"])
    base._pill(draw, (1450, 355), "PREDICTIVE COUNTERPART", palette, fill=palette["good"], width=360, text_fill=palette["ink"])


def _cinematic_consequence_map(
    draw: ImageDraw.ImageDraw,
    progress: float,
    palette: dict[str, tuple[int, int, int]],
) -> None:
    q = base._phase(progress, 0.04, 0.92)
    _atmospheric_depth(draw, palette, progress, focus_x=790)
    draw.rounded_rectangle((120, 380, 760, 930), radius=58, fill=palette["panel"], outline=palette["good"], width=7)
    draw.rounded_rectangle((175, 445, 705, 690), radius=34, fill=palette["panel_alt"])
    draw.ellipse((350, 515, 510, 675), fill=palette["accent"])
    base.engine._text(draw, (430, 595), "1", 64, palette["ink"], bold=True, anchor="mm")
    base.engine._text(draw, (440, 770), "RANKED FIRST", 30, palette["good"], bold=True, anchor="mm")
    outcomes = (
        (920, 360, 1450, 575, "NEXT FEED", palette["accent"]),
        (1160, 585, 1780, 825, "NEXT CHOICE", palette["accent_alt"]),
        (880, 790, 1430, 1010, "NEXT OFFER", palette["warning"]),
    )
    origin = (760, 650)
    for index, (left, top, right, bottom, label, color) in enumerate(outcomes):
        local = base._phase(q, index * 0.16, min(1.0, index * 0.16 + 0.50))
        if local <= 0.02:
            continue
        center = ((left + right) // 2, (top + bottom) // 2)
        draw.line((*origin, *center), fill=color, width=6)
        draw.rounded_rectangle((left, top, right, bottom), radius=34, fill=palette["panel"], outline=color, width=5)
        base.engine._text(draw, center, label, 30, palette["white"], bold=True, anchor="mm")


def install_cinematic_composition_upgrade() -> None:
    base._common = _compact_common
    base.RENDERERS["algorithm_chose_you"] = _cinematic_algorithm_chose_you
    base.RENDERERS["behavioral_twin"] = _cinematic_behavioral_twin
    base.RENDERERS["consequence_map"] = _cinematic_consequence_map
    expansion.base.RENDERERS["consequence_map"] = _cinematic_consequence_map
    truthful.base.RENDERERS["algorithm_chose_you"] = _cinematic_algorithm_chose_you
    truthful.base.RENDERERS["behavioral_twin"] = _cinematic_behavioral_twin


install_cinematic_composition_upgrade()
