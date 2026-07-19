from __future__ import annotations

"""Compatibility and delivery guard for the Internet attention visual family."""

from PIL import ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_visual_overhaul_v63 as v63
from . import cartoon_visual_overhaul_v65 as v65
from . import cartoon_visual_overhaul_v66 as v66
from . import internet_attention_visuals as internet
from . import native_shorts


def _safe_phone(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    scale: float,
    *,
    glow: float = 0.0,
) -> None:
    """Draw phone details proportionally so miniature props remain valid."""
    width = max(28, round(220 * scale))
    height = max(52, round(390 * scale))
    border = max(3, round(10 * scale))
    radius = max(5, round(34 * scale))
    draw.rounded_rectangle(
        (x - width // 2, y - height // 2, x + width // 2, y + height // 2),
        radius=radius,
        fill=(39, 52, 68),
        outline=internet.INK,
        width=border,
    )
    inset_x = max(4, round(22 * scale))
    inset_top = max(5, round(32 * scale))
    inset_bottom = max(7, round(48 * scale))
    screen = (
        x - width // 2 + inset_x,
        y - height // 2 + inset_top,
        x + width // 2 - inset_x,
        y + height // 2 - inset_bottom,
    )
    if screen[2] >= screen[0] and screen[3] >= screen[1]:
        draw.rounded_rectangle(
            screen,
            radius=max(3, round(18 * scale)),
            fill=(209, 229, 238),
        )
    home_radius = max(2, round(10 * scale))
    home_y = y + height // 2 - max(5, round(20 * scale))
    draw.ellipse(
        (x - home_radius, home_y - home_radius, x + home_radius, home_y + home_radius),
        fill=(120, 135, 150),
    )
    if glow > 0:
        glow_radius = max(8, round((34 + 18 * glow) * scale))
        glow_x = x + width // 2
        glow_y = y - height // 2 + glow_radius // 2
        draw.ellipse(
            (
                glow_x - glow_radius,
                glow_y - glow_radius,
                glow_x + glow_radius,
                glow_y + glow_radius,
            ),
            fill=internet.RED,
            outline=internet.WHITE,
            width=max(2, round(4 * scale)),
        )


internet._phone = _safe_phone

# Preserve the established public identity contract. Non-Internet scenes delegate
# to the captured v66 renderer, so all Mars release behavior remains unchanged.
v63.render_planned_frame = internet.render_planned_frame
v65.render_planned_frame = internet.render_planned_frame
v66.render_planned_frame = internet.render_planned_frame
cartoon.render_planned_frame = internet.render_planned_frame

# Every exact visual exposed in the catalog must have a semantic 9:16 route. The
# first Internet release uses the established native documentary composition; a
# dedicated vertical family can evolve after the regular zero-touch film passes.
for template in internet.INTERNET_TEMPLATES:
    key = ("tech_behavior_motion", template.template_id)
    native_shorts.COMPOSITIONS.setdefault(
        key,
        native_shorts.ShortsComposition(template.title),
    )
    native_shorts.RENDERERS.setdefault(key, native_shorts._generic)
