from __future__ import annotations

"""Final cross-format polish for character stance and documentary conclusions."""

from PIL import Image, ImageDraw

from . import documentary_visual_polish as polish
from . import native_shorts as shorts
from . import tech_behavior_motion
from . import tech_behavior_route_patch as route

_ACTIVE_FAMILY_ID = ""
_ORIGINAL_ATTRIBUTE = "__ai_documentary_original_native_compose__"
_CURRENT_NATIVE_COMPOSE = shorts.compose_native_shorts
_ORIGINAL_NATIVE_COMPOSE = getattr(
    _CURRENT_NATIVE_COMPOSE,
    _ORIGINAL_ATTRIBUTE,
    _CURRENT_NATIVE_COMPOSE,
)


def _blend(
    muted: tuple[int, int, int],
    vivid: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    """Blend two RGB colors without depending on another patch module."""
    amount = max(0.0, min(1.0, float(amount)))
    return tuple(
        round(start + (end - start) * amount)
        for start, end in zip(muted, vivid, strict=True)
    )


def _upright_landscape_person(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    palette: dict[str, tuple[int, int, int]],
    *,
    digital: bool = False,
) -> None:
    """Draw a finished character with straight legs and a natural narrow stance."""
    x, ground_y = center
    accent = palette["accent"] if digital else palette["accent_alt"]
    shirt = accent
    denim = (43, 79, 126) if not digital else (35, 88, 132)
    skin = (239, 190, 145)
    ink = palette.get("ink", (5, 10, 20))
    hair = (38, 29, 26)

    head_y = ground_y - 356
    draw.ellipse((x - 58, head_y - 62, x + 58, head_y + 54), fill=skin, outline=ink, width=6)
    draw.pieslice((x - 62, head_y - 70, x + 62, head_y + 25), 180, 356, fill=hair)
    draw.polygon(
        (
            (x - 56, head_y - 18),
            (x - 42, head_y - 54),
            (x - 16, head_y - 45),
            (x + 2, head_y - 63),
            (x + 27, head_y - 44),
            (x + 52, head_y - 51),
            (x + 58, head_y - 15),
        ),
        fill=hair,
    )
    draw.ellipse((x - 25, head_y - 7, x - 14, head_y + 4), fill=ink)
    draw.ellipse((x + 14, head_y - 7, x + 25, head_y + 4), fill=ink)
    draw.arc((x - 23, head_y + 8, x + 23, head_y + 38), 20, 160, fill=ink, width=4)

    neck_top = head_y + 45
    draw.rounded_rectangle((x - 14, neck_top, x + 14, neck_top + 32), radius=7, fill=skin)
    torso_top = neck_top + 23
    torso_bottom = ground_y - 154
    shirt_points = (
        (x - 58, torso_top),
        (x + 58, torso_top),
        (x + 38, torso_bottom),
        (x - 38, torso_bottom),
    )
    draw.polygon(tuple((px + 5, py + 6) for px, py in shirt_points), fill=ink)
    draw.polygon(shirt_points, fill=shirt, outline=ink)

    for side in (-1, 1):
        shoulder = (x + side * 53, torso_top + 18)
        elbow = (x + side * 79, torso_top + 87)
        hand = (x + side * 70, torso_bottom + 38)
        draw.line((shoulder, elbow), fill=ink, width=22)
        draw.line((shoulder, elbow), fill=shirt, width=15)
        draw.line((elbow, hand), fill=ink, width=19)
        draw.line((elbow, hand), fill=skin, width=12)
        draw.ellipse((hand[0] - 12, hand[1] - 12, hand[0] + 12, hand[1] + 12), fill=skin, outline=ink, width=3)

    waist_y = torso_bottom - 3
    draw.rounded_rectangle((x - 40, waist_y, x + 40, waist_y + 29), radius=7, fill=denim, outline=ink, width=4)

    # Nearly vertical trouser legs keep the knees and shoes beneath the hips.
    left_leg = (
        (x - 38, waist_y + 20),
        (x - 5, waist_y + 20),
        (x - 10, ground_y - 17),
        (x - 45, ground_y - 17),
    )
    right_leg = (
        (x + 5, waist_y + 20),
        (x + 38, waist_y + 20),
        (x + 45, ground_y - 17),
        (x + 10, ground_y - 17),
    )
    draw.polygon(left_leg, fill=denim, outline=ink)
    draw.polygon(right_leg, fill=denim, outline=ink)
    draw.rounded_rectangle((x - 53, ground_y - 25, x - 6, ground_y + 5), radius=10, fill=(22, 29, 40))
    draw.rounded_rectangle((x + 6, ground_y - 25, x + 53, ground_y + 5), radius=10, fill=(22, 29, 40))

    if digital:
        for offset in (-35, 0, 35):
            draw.line((x - 34, torso_top + 68 + offset, x + 34, torso_top + 68 + offset), fill=palette["accent"], width=3)


def _family_story_cta(canvas: Image.Image, progress: float) -> None:
    family = _ACTIVE_FAMILY_ID
    if family in {"finance_motion", "character_explainer"}:
        thesis = "YOUR SYSTEM SHAPES YOUR FUTURE."
        support_top = "AUTOMATION TURNS INCOME"
        support_bottom = "INTO LONG-TERM WEALTH."
        label = "THE FINANCIAL IDEA"
    elif family == "tech_behavior_motion":
        thesis = "YOUR ACTIONS BECOME PREDICTIONS."
        support_top = "THOSE PREDICTIONS SHAPE"
        support_bottom = "WHAT REACHES YOU NEXT."
        label = "THE FINAL IDEA"
    else:
        thesis = "SMALL SYSTEMS SHAPE WHAT COMES NEXT."
        support_top = "BUILD THE PROCESS"
        support_bottom = "THAT SUPPORTS THE OUTCOME."
        label = "THE FINAL IDEA"

    draw = ImageDraw.Draw(canvas)
    thesis_reveal = shorts._phase(progress, 0.02, 0.24)
    cta_reveal = shorts._phase(progress, 0.48, 0.74)
    panel = (48, 1080, 1032, 1665)
    draw.rounded_rectangle(panel, radius=42, fill=(5, 12, 24), outline=(27, 48, 74), width=3)

    shorts._text(draw, (shorts.SAFE_LEFT, 1135), label, 21, _blend((55, 68, 89), shorts.CYAN, thesis_reveal), bold=True)
    shorts._text(draw, (shorts.SAFE_LEFT, 1190), thesis, 39, _blend((66, 76, 94), shorts.WHITE, thesis_reveal), bold=True)
    support = _blend((50, 61, 78), shorts.MUTED, thesis_reveal)
    shorts._text(draw, (shorts.SAFE_LEFT, 1260), support_top, 27, support, bold=True)
    shorts._text(draw, (shorts.SAFE_LEFT, 1302), support_bottom, 27, support, bold=True)

    if cta_reveal <= 0.01:
        shorts._text(draw, (shorts.SAFE_LEFT, 1515), "AI DOCUMENTARY OS", 19, (78, 91, 112), bold=True)
        return

    red = _blend((46, 31, 42), shorts.RED, cta_reveal)
    blue = _blend((24, 42, 66), shorts.BLUE, cta_reveal)
    button_text = _blend((92, 100, 115), shorts.WHITE, cta_reveal)
    y = 1435
    draw.rounded_rectangle((shorts.SAFE_LEFT, y, 650, y + 92), radius=22, fill=red)
    draw.polygon(((118, y + 26), (118, y + 66), (151, y + 46)), fill=button_text)
    shorts._text(draw, (390, y + 46), "SUBSCRIBE", 36, button_text, bold=True, anchor="mm")
    draw.rounded_rectangle((680, y, shorts.SAFE_RIGHT, y + 92), radius=46, fill=blue)
    shorts._text(draw, (845, y + 46), "LIKE  👍", 32, button_text, bold=True, anchor="mm")
    shorts._text(draw, (shorts.SAFE_LEFT, 1585), "KEEP BUILDING THE SYSTEM", 22, _blend((52, 62, 78), (122, 138, 162), cta_reveal), bold=True)


def _tracked_native_compose(*args, **kwargs):
    global _ACTIVE_FAMILY_ID
    previous = _ACTIVE_FAMILY_ID
    _ACTIVE_FAMILY_ID = str(kwargs.get("family_id") or "")
    try:
        return _ORIGINAL_NATIVE_COMPOSE(*args, **kwargs)
    finally:
        _ACTIVE_FAMILY_ID = previous


setattr(_tracked_native_compose, _ORIGINAL_ATTRIBUTE, _ORIGINAL_NATIVE_COMPOSE)


def install_cross_format_polish() -> None:
    polish._landscape_person = _upright_landscape_person
    polish._story_cta = _family_story_cta
    tech_behavior_motion._person_wireframe = _upright_landscape_person
    route.base._person_wireframe = _upright_landscape_person
    route.truthful.base._person_wireframe = _upright_landscape_person
    shorts.compose_native_shorts = _tracked_native_compose


install_cross_format_polish()
