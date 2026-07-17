from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PIL import ImageDraw


Color = tuple[int, int, int]
Renderer = Callable[[ImageDraw.ImageDraw, tuple[int, int], float, Color, str], None]

INK: Color = (6, 13, 24)
SHADOW: Color = (3, 7, 14)
SURFACE: Color = (24, 37, 52)
SURFACE_LIGHT: Color = (53, 69, 86)
PAPER: Color = (231, 238, 238)
CORAL: Color = (231, 101, 96)
GREEN: Color = (67, 185, 166)
AMBER: Color = (224, 174, 83)


@dataclass(frozen=True)
class DocumentaryAsset:
    asset_id: str
    label: str
    supported_states: tuple[str, ...] = ("default",)


ASSET_CATALOG = (
    DocumentaryAsset("wallet", "Wallet", ("default", "empty")),
    DocumentaryAsset("payment_card", "Payment card", ("default", "declined")),
    DocumentaryAsset("home", "Home"),
    DocumentaryAsset("groceries", "Groceries"),
    DocumentaryAsset("calendar", "Calendar"),
    DocumentaryAsset("bank", "Investment account"),
    DocumentaryAsset("paycheck", "Paycheck", ("default", "received")),
    DocumentaryAsset("phone", "Phone", ("default", "alert")),
)


def asset_catalog() -> list[dict[str, object]]:
    return [
        {
            "asset_id": asset.asset_id,
            "label": asset.label,
            "supported_states": list(asset.supported_states),
        }
        for asset in ASSET_CATALOG
    ]


def _stroke(scale: float, base: int = 4) -> int:
    return max(2, round(base * scale))


def _shadowed_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    radius: int,
    accent: Color,
    scale: float,
    fill: Color = SURFACE,
) -> None:
    left, top, right, bottom = box
    offset = max(4, round(9 * scale))
    draw.rounded_rectangle(
        (left + offset, top + offset, right + offset, bottom + offset),
        radius=radius,
        fill=SHADOW,
    )
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=accent,
        width=_stroke(scale),
    )


def _wallet(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float, accent: Color, state: str) -> None:
    x, y = center
    width = round(190 * scale)
    height = round(124 * scale)
    left, top = x - width // 2, y - height // 2
    right, bottom = x + width // 2, y + height // 2
    radius = max(8, round(22 * scale))
    _shadowed_panel(draw, (left, top, right, bottom), radius=radius, accent=accent, scale=scale)

    # A visible folded edge and stitched seam make this read as an object,
    # rather than another generic interface card.
    draw.line(
        (left + round(24 * scale), top + round(24 * scale), right - round(24 * scale), top + round(24 * scale)),
        fill=SURFACE_LIGHT,
        width=_stroke(scale, 3),
    )
    stitch_y = bottom - round(18 * scale)
    for offset in range(round(22 * scale), width - round(20 * scale), max(7, round(13 * scale))):
        draw.line(
            (left + offset, stitch_y, left + offset + round(6 * scale), stitch_y),
            fill=accent,
            width=max(1, round(2 * scale)),
        )

    clasp = (
        x + round(18 * scale),
        y - round(27 * scale),
        right + round(10 * scale),
        y + round(29 * scale),
    )
    draw.rounded_rectangle(clasp, radius=max(5, round(12 * scale)), fill=INK, outline=accent, width=_stroke(scale, 3))
    draw.ellipse(
        (x + round(49 * scale), y - round(7 * scale), x + round(63 * scale), y + round(7 * scale)),
        fill=accent,
    )
    if state == "empty":
        draw.line(
            (left + round(30 * scale), y - round(15 * scale), x - round(10 * scale), y + round(15 * scale)),
            fill=CORAL,
            width=_stroke(scale, 7),
        )
        draw.line(
            (left + round(30 * scale), y + round(15 * scale), x - round(10 * scale), y - round(15 * scale)),
            fill=CORAL,
            width=_stroke(scale, 7),
        )
    else:
        cash_top = top - round(22 * scale)
        draw.rounded_rectangle(
            (left + round(23 * scale), cash_top, x + round(21 * scale), top + round(13 * scale)),
            radius=max(3, round(6 * scale)),
            fill=(190, 224, 206),
            outline=GREEN,
            width=_stroke(scale, 2),
        )
        draw.ellipse(
            (left + round(56 * scale), cash_top + round(7 * scale), left + round(74 * scale), cash_top + round(25 * scale)),
            outline=GREEN,
            width=_stroke(scale, 2),
        )


def _payment_card(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float, accent: Color, state: str) -> None:
    x, y = center
    width = round(210 * scale)
    height = round(128 * scale)
    box = (x - width // 2, y - height // 2, x + width // 2, y + height // 2)
    _shadowed_panel(draw, box, radius=max(8, round(22 * scale)), accent=accent, scale=scale, fill=(20, 31, 47))
    draw.rounded_rectangle(
        (x - round(73 * scale), y - round(17 * scale), x - round(35 * scale), y + round(13 * scale)),
        radius=max(3, round(6 * scale)),
        fill=AMBER,
        outline=(255, 218, 145),
        width=_stroke(scale, 2),
    )
    draw.line((x - round(54 * scale), y - round(17 * scale), x - round(54 * scale), y + round(13 * scale)), fill=(126, 91, 38), width=_stroke(scale, 2))
    draw.line((x - round(73 * scale), y - round(2 * scale), x - round(35 * scale), y - round(2 * scale)), fill=(126, 91, 38), width=_stroke(scale, 2))
    for radius in (18, 28, 38):
        draw.arc(
            (x + round((34 - radius) * scale), y - round(radius * scale), x + round((34 + radius) * scale), y + round(radius * scale)),
            -48,
            48,
            fill=accent,
            width=_stroke(scale, 2),
        )
    draw.line(
        (x - round(73 * scale), y + round(38 * scale), x - round(12 * scale), y + round(38 * scale)),
        fill=SURFACE_LIGHT,
        width=_stroke(scale, 5),
    )
    if state == "declined":
        for direction in (-1, 1):
            draw.line(
                (x - round(75 * scale), y + direction * round(45 * scale), x + round(75 * scale), y - direction * round(45 * scale)),
                fill=CORAL,
                width=_stroke(scale, 9),
            )


def _home(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float, accent: Color, _state: str) -> None:
    x, y = center
    half = round(72 * scale)
    shadow = round(8 * scale)
    roof = ((x - half - 16, y - 10), (x, y - half - 16), (x + half + 16, y - 10))
    draw.polygon(tuple((px + shadow, py + shadow) for px, py in roof), fill=SHADOW)
    draw.polygon(roof, fill=accent)
    draw.rounded_rectangle(
        (x - half, y - round(8 * scale), x + half, y + half),
        radius=max(7, round(13 * scale)),
        fill=(40, 43, 45),
        outline=accent,
        width=_stroke(scale),
    )
    door = (x - round(18 * scale), y + round(20 * scale), x + round(18 * scale), y + half)
    draw.rounded_rectangle(door, radius=max(4, round(7 * scale)), fill=INK, outline=SURFACE_LIGHT, width=_stroke(scale, 2))
    draw.ellipse((x + round(8 * scale), y + round(47 * scale), x + round(14 * scale), y + round(53 * scale)), fill=accent)
    for window_x in (x - round(48 * scale), x + round(48 * scale)):
        draw.rounded_rectangle(
            (window_x - round(14 * scale), y + round(13 * scale), window_x + round(14 * scale), y + round(43 * scale)),
            radius=max(2, round(4 * scale)),
            fill=(153, 212, 205),
            outline=accent,
            width=_stroke(scale, 2),
        )
        draw.line((window_x, y + round(14 * scale), window_x, y + round(42 * scale)), fill=SURFACE, width=_stroke(scale, 2))


def _groceries(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float, accent: Color, _state: str) -> None:
    x, y = center
    width = round(142 * scale)
    top = y - round(42 * scale)
    bottom = y + round(75 * scale)
    bag = ((x - width // 2, top), (x + width // 2, top), (x + round(55 * scale), bottom), (x - round(55 * scale), bottom))
    draw.polygon(tuple((px + round(8 * scale), py + round(8 * scale)) for px, py in bag), fill=SHADOW)
    draw.polygon(bag, fill=(28, 66, 58), outline=accent)
    draw.line((x - width // 2, top, x - round(55 * scale), bottom), fill=accent, width=_stroke(scale))
    draw.line((x + width // 2, top, x + round(55 * scale), bottom), fill=accent, width=_stroke(scale))
    draw.arc(
        (x - round(43 * scale), y - round(91 * scale), x + round(43 * scale), y - round(5 * scale)),
        190,
        350,
        fill=accent,
        width=_stroke(scale, 7),
    )
    # Produce silhouettes add narrative specificity at small sizes.
    draw.ellipse((x - round(44 * scale), y - round(63 * scale), x - round(6 * scale), y - round(24 * scale)), fill=CORAL)
    draw.polygon(
        ((x + round(6 * scale), y - round(24 * scale)), (x + round(16 * scale), y - round(74 * scale)), (x + round(28 * scale), y - round(25 * scale))),
        fill=GREEN,
    )
    draw.ellipse((x + round(22 * scale), y - round(58 * scale), x + round(55 * scale), y - round(22 * scale)), fill=AMBER)
    draw.line((x - round(35 * scale), y + round(20 * scale), x + round(35 * scale), y + round(20 * scale)), fill=SURFACE_LIGHT, width=_stroke(scale, 3))


def _calendar(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float, accent: Color, _state: str) -> None:
    x, y = center
    width = round(190 * scale)
    height = round(174 * scale)
    box = (x - width // 2, y - height // 2, x + width // 2, y + height // 2)
    _shadowed_panel(draw, box, radius=max(8, round(22 * scale)), accent=accent, scale=scale, fill=(28, 39, 55))
    header_bottom = y - round(35 * scale)
    draw.rounded_rectangle(
        (box[0], box[1], box[2], header_bottom),
        radius=max(8, round(20 * scale)),
        fill=accent,
    )
    for ring_x in (x - round(50 * scale), x + round(50 * scale)):
        draw.rounded_rectangle(
            (ring_x - round(7 * scale), box[1] - round(14 * scale), ring_x + round(7 * scale), box[1] + round(25 * scale)),
            radius=max(3, round(6 * scale)),
            fill=PAPER,
        )
    for row in range(2):
        for column in range(4):
            dot_x = x - round(54 * scale) + column * round(36 * scale)
            dot_y = y + round((8 + row * 34) * scale)
            radius = max(2, round(5 * scale))
            draw.ellipse((dot_x - radius, dot_y - radius, dot_x + radius, dot_y + radius), fill=accent if (row, column) == (1, 2) else SURFACE_LIGHT)


def _bank(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float, accent: Color, _state: str) -> None:
    x, y = center
    width = round(220 * scale)
    roof_y = y - round(88 * scale)
    draw.polygon(
        ((x - width // 2 + round(8 * scale), y - round(30 * scale)), (x + round(8 * scale), roof_y + round(8 * scale)), (x + width // 2 + round(8 * scale), y - round(30 * scale))),
        fill=SHADOW,
    )
    draw.polygon(
        ((x - width // 2, y - round(30 * scale)), (x, roof_y), (x + width // 2, y - round(30 * scale))),
        fill=accent,
    )
    draw.line((x - round(82 * scale), y - round(18 * scale), x + round(82 * scale), y - round(18 * scale)), fill=PAPER, width=_stroke(scale, 4))
    for offset in (-72, -24, 24, 72):
        column_x = x + round(offset * scale)
        draw.rounded_rectangle(
            (column_x - round(12 * scale), y - round(12 * scale), column_x + round(12 * scale), y + round(62 * scale)),
            radius=max(3, round(5 * scale)),
            fill=(95, 112, 123),
            outline=accent,
            width=_stroke(scale, 2),
        )
    for level, inset in enumerate((0, 10, 20)):
        step_y = y + round((62 + level * 15) * scale)
        draw.rectangle((x - width // 2 + round(inset * scale), step_y, x + width // 2 - round(inset * scale), step_y + round(11 * scale)), fill=accent if level == 0 else SURFACE_LIGHT)


def _paycheck(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float, accent: Color, state: str) -> None:
    x, y = center
    width = round(230 * scale)
    height = round(116 * scale)
    box = (x - width // 2, y - height // 2, x + width // 2, y + height // 2)
    _shadowed_panel(draw, box, radius=max(7, round(16 * scale)), accent=accent, scale=scale, fill=(226, 235, 232))
    ink = (29, 53, 54)
    draw.rectangle((box[0] + round(18 * scale), box[1] + round(17 * scale), box[0] + round(58 * scale), box[1] + round(42 * scale)), fill=accent)
    for offset, length in ((19, 78), (37, 58), (55, 86)):
        draw.line((x - round(20 * scale), box[1] + round(offset * scale), x + round(length * scale), box[1] + round(offset * scale)), fill=ink, width=_stroke(scale, 3))
    draw.line((box[0] + round(20 * scale), box[1] + round(80 * scale), box[2] - round(20 * scale), box[1] + round(80 * scale)), fill=accent, width=_stroke(scale, 3))
    if state == "received":
        radius = max(8, round(17 * scale))
        badge_x, badge_y = box[2] - radius, box[1] + radius
        draw.ellipse((badge_x - radius, badge_y - radius, badge_x + radius, badge_y + radius), fill=GREEN)
        draw.line((badge_x - radius // 2, badge_y, badge_x - radius // 8, badge_y + radius // 3, badge_x + radius // 2, badge_y - radius // 3), fill=INK, width=_stroke(scale, 3), joint="curve")


def _phone(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float, accent: Color, state: str) -> None:
    x, y = center
    width = round(108 * scale)
    height = round(190 * scale)
    box = (x - width // 2, y - height // 2, x + width // 2, y + height // 2)
    _shadowed_panel(draw, box, radius=max(10, round(25 * scale)), accent=accent, scale=scale, fill=(17, 27, 40))
    draw.rounded_rectangle(
        (box[0] + round(10 * scale), box[1] + round(18 * scale), box[2] - round(10 * scale), box[3] - round(18 * scale)),
        radius=max(5, round(13 * scale)),
        fill=(12, 42, 46),
    )
    draw.rounded_rectangle((x - round(22 * scale), box[1] + round(8 * scale), x + round(22 * scale), box[1] + round(13 * scale)), radius=3, fill=SURFACE_LIGHT)
    if state == "alert":
        radius = max(8, round(17 * scale))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=CORAL)
        draw.line((x, y - radius // 2, x, y + radius // 4), fill=PAPER, width=_stroke(scale, 3))
        draw.ellipse((x - 2, y + radius // 2 - 2, x + 2, y + radius // 2 + 2), fill=PAPER)


_RENDERERS: dict[str, Renderer] = {
    "wallet": _wallet,
    "payment_card": _payment_card,
    "home": _home,
    "groceries": _groceries,
    "calendar": _calendar,
    "bank": _bank,
    "paycheck": _paycheck,
    "phone": _phone,
}


def render_asset(
    draw: ImageDraw.ImageDraw,
    asset_id: str,
    center: tuple[int, int],
    *,
    scale: float = 1.0,
    accent: Color = GREEN,
    state: str = "default",
) -> None:
    renderer = _RENDERERS.get(asset_id)
    if renderer is None:
        raise ValueError(f"Unknown documentary asset: {asset_id}")
    specification = next(asset for asset in ASSET_CATALOG if asset.asset_id == asset_id)
    if state not in specification.supported_states:
        raise ValueError(f"Unsupported {asset_id} state: {state}")
    renderer(draw, center, max(0.1, float(scale)), accent, state)
