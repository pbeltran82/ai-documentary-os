from __future__ import annotations

"""Small layered compositor for deterministic documentary illustrations.

Architecture, actors, moving doors, and effects render to separate RGBA layers.
Foreground mechanisms therefore occlude people correctly without destructive masks
or post-render pixel scrubbing.
"""

from dataclasses import dataclass
from typing import Iterable

from PIL import Image, ImageDraw

RGB = tuple[int, int, int]
RGBA = tuple[int, int, int, int]
Bounds = tuple[int, int, int, int]

INK: RGB = (12, 18, 27)


@dataclass(frozen=True)
class DoorGeometry:
    outer: Bounds
    opening: Bounds
    center_x: int
    gap: int


class LayerStack:
    """Named transparent layers composited in one explicit order."""

    def __init__(
        self,
        size: tuple[int, int],
        names: Iterable[str] = ("environment", "actors", "foreground", "effects"),
    ) -> None:
        self.size = size
        self.order = tuple(names)
        self.layers = {
            name: Image.new("RGBA", size, (0, 0, 0, 0))
            for name in self.order
        }

    def image(self, name: str) -> Image.Image:
        return self.layers[name]

    def draw(self, name: str) -> ImageDraw.ImageDraw:
        return ImageDraw.Draw(self.layers[name])

    def composite(self, base: Image.Image | RGB | RGBA) -> Image.Image:
        if isinstance(base, Image.Image):
            result = base.convert("RGBA")
        else:
            color = base if len(base) == 4 else (*base, 255)
            result = Image.new("RGBA", self.size, color)
        for name in self.order:
            result = Image.alpha_composite(result, self.layers[name])
        return result.convert("RGB")


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def smooth(value: float) -> float:
    p = clamp01(value)
    return p * p * (3.0 - 2.0 * p)


def phase(progress: float, start: float, end: float) -> float:
    if end <= start:
        return 1.0 if progress >= end else 0.0
    return smooth((float(progress) - start) / (end - start))


def draw_person(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    scale: float,
    *,
    shirt: RGB = (63, 151, 205),
    pants: RGB = (50, 61, 78),
    skin: RGB = (215, 164, 119),
    facing: int = 1,
    stride: float = 0.0,
    arm_raise: float = 0.0,
) -> None:
    """Draw one compact, readable figure with restrained pose variation."""
    x, y = center
    s = max(0.1, float(scale))
    line = max(3, round(7 * s))
    head = round(28 * s)
    torso_w = round(54 * s)
    torso_h = round(72 * s)
    top = y - round(112 * s)

    draw.ellipse(
        (x - head, top - head * 2, x + head, top),
        fill=skin,
        outline=INK,
        width=line,
    )
    draw.arc(
        (x - head + 2, top - head * 2 + 2, x + head - 2, top - 4),
        190,
        350,
        fill=INK,
        width=max(3, line),
    )
    eye_y = top - head
    eye_dx = round(9 * s)
    eye_r = max(2, round(3 * s))
    for dx in (-eye_dx, eye_dx):
        draw.ellipse(
            (x + dx - eye_r, eye_y - eye_r, x + dx + eye_r, eye_y + eye_r),
            fill=INK,
        )

    body_top = top + round(8 * s)
    draw.rounded_rectangle(
        (x - torso_w // 2, body_top, x + torso_w // 2, body_top + torso_h),
        radius=round(17 * s),
        fill=shirt,
        outline=INK,
        width=line,
    )

    shoulder_y = body_top + round(18 * s)
    hand_y = body_top + round(65 * s)
    lift = round(52 * s * clamp01(arm_raise))
    reach = round(43 * s)
    draw.line(
        (x - torso_w // 2, shoulder_y, x - reach * facing, hand_y - lift),
        fill=INK,
        width=line,
    )
    draw.line(
        (x + torso_w // 2, shoulder_y, x + reach * facing, hand_y),
        fill=INK,
        width=line,
    )

    hip_y = body_top + torso_h
    step = round(22 * s * max(-1.0, min(1.0, stride)))
    leg = round(57 * s)
    draw.line((x - round(15 * s), hip_y, x - round(18 * s) - step, hip_y + leg), fill=pants, width=line + 2)
    draw.line((x + round(15 * s), hip_y, x + round(18 * s) + step, hip_y + leg), fill=pants, width=line + 2)
    shoe = round(19 * s)
    draw.line((x - round(18 * s) - step, hip_y + leg, x - round(18 * s) - step - shoe, hip_y + leg), fill=INK, width=line + 3)
    draw.line((x + round(18 * s) + step, hip_y + leg, x + round(18 * s) + step + shoe, hip_y + leg), fill=INK, width=line + 3)


def draw_cart(
    draw: ImageDraw.ImageDraw,
    bounds: Bounds,
    *,
    fill: RGB = (58, 76, 92),
    accent: RGB = (74, 194, 211),
) -> None:
    left, top, right, bottom = bounds
    draw.rounded_rectangle(bounds, radius=max(8, (bottom - top) // 6), fill=fill, outline=INK, width=6)
    draw.rectangle((left + 16, top + 16, right - 16, top + 31), fill=accent)
    wheel = max(7, (bottom - top) // 9)
    for x in (left + 30, right - 30):
        draw.ellipse((x - wheel, bottom - wheel, x + wheel, bottom + wheel), fill=INK)


def draw_airlock(
    stack: LayerStack,
    outer: Bounds,
    *,
    opening: float,
    frame_fill: RGB = (49, 64, 79),
    panel_fill: RGB = (79, 94, 108),
    interior_fill: RGB = (10, 22, 33),
    accent: RGB = (74, 194, 211),
) -> DoorGeometry:
    """Draw an airlock with panels guaranteed to live on the foreground layer."""
    left, top, right, bottom = outer
    width = right - left
    height = bottom - top
    border_x = max(34, round(width * 0.11))
    border_top = max(38, round(height * 0.11))
    border_bottom = max(26, round(height * 0.07))
    opening_bounds = (
        left + border_x,
        top + border_top,
        right - border_x,
        bottom - border_bottom,
    )
    inner_left, inner_top, inner_right, inner_bottom = opening_bounds
    center = (inner_left + inner_right) // 2
    half_width = (inner_right - inner_left) // 2
    gap = round(half_width * 0.78 * smooth(opening))

    environment = stack.draw("environment")
    environment.rounded_rectangle(outer, radius=max(18, round(width * 0.05)), fill=frame_fill, outline=INK, width=10)
    environment.rounded_rectangle(opening_bounds, radius=max(10, round(width * 0.025)), fill=interior_fill, outline=accent, width=6)
    environment.rectangle((inner_left + 14, inner_bottom - 42, inner_right - 14, inner_bottom - 20), fill=(31, 44, 55))

    foreground = stack.draw("foreground")
    left_panel = (inner_left, inner_top, max(inner_left + 12, center - gap), inner_bottom)
    right_panel = (min(inner_right - 12, center + gap), inner_top, inner_right, inner_bottom)
    for panel in (left_panel, right_panel):
        foreground.rounded_rectangle(panel, radius=max(8, round(width * 0.018)), fill=panel_fill, outline=INK, width=7)
        panel_left, panel_top, panel_right, panel_bottom = panel
        if panel_right - panel_left > 42:
            foreground.line(
                (panel_left + 20, panel_top + 26, panel_right - 20, panel_top + 26),
                fill=accent,
                width=5,
            )
    foreground.rounded_rectangle(outer, radius=max(18, round(width * 0.05)), outline=INK, width=10)
    foreground.line((left + border_x, top + 18, right - border_x, top + 18), fill=accent, width=7)

    return DoorGeometry(outer=outer, opening=opening_bounds, center_x=center, gap=gap)
