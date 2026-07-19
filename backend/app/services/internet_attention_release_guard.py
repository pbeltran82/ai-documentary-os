from __future__ import annotations

"""Compatibility and delivery guard for the Internet attention visual family."""

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_visual_overhaul_v62 as v62
from . import cartoon_visual_overhaul_v63 as v63
from . import cartoon_visual_overhaul_v64 as v64
from . import cartoon_visual_overhaul_v65 as v65
from . import cartoon_visual_overhaul_v66 as v66
from . import internet_attention_visuals as internet
from . import native_shorts

_original_render_cartoon_documentary = cartoon.render_cartoon_documentary


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


def _legacy_core_renderer(
    scene,
    template_id: str | None,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    """Render the seven approved Mars/general templates without wrapper recursion."""
    selected = v63._selected_template(scene, template_id)
    progress = v63._absolute_progress(duration_seconds, time_seconds)
    variant = int(getattr(scene, "scene_number", 1) or 1) % 6

    if selected == "transport_scene":
        return v62._transport_frame(progress, variant)
    if selected == "habitat_build":
        return v62._habitat_frame(progress, variant)
    if selected == "presenter_desk":
        return v63._presenter_frame(progress, variant)
    if selected == "council_scene":
        return v63._council_frame(progress, variant)
    if selected == "crowd_focus":
        return v65._community_frame(progress, variant)
    if selected == "process_diagram":
        return v65._settlement_frame(progress, variant)
    if selected == "route_map":
        rank, count = v65._route_rank(scene)
        if v64._is_final_project_scene(scene):
            return v65._settlement_frame(progress, variant)
        if count > 1 and rank > 0:
            return v65._arrival_frame(progress, variant)
        return v63._route_frame(progress, variant)
    return v63._process_frame(progress, variant)


def _legacy_v66_renderer(
    scene,
    template_id: str | None,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    selected = v63._selected_template(scene, template_id)
    progress = v63._absolute_progress(duration_seconds, time_seconds)
    variant = int(getattr(scene, "scene_number", 1) or 1) % 6
    if v66._is_consecutive_transport(scene, selected):
        return v66._logistics_frame(progress, variant)
    # Kept as a module-level compatibility seam so existing tests and extensions
    # can still intercept the pre-v66 renderer without causing import recursion.
    return v66._previous_render_planned_frame(
        scene,
        template_id,
        duration_seconds,
        time_seconds,
        style_id,
    )


def render_cartoon_documentary(
    scene,
    template_id: str | None = None,
    style_id: str | None = None,
):
    """Replace stale Mars identities when an Internet project is regenerated."""
    resolved_template_id = template_id
    if internet.is_internet_attention(scene):
        selected, _confidence, _reason = internet.suggest_template(scene)
        resolved_template_id = selected.template_id
    return _original_render_cartoon_documentary(
        scene,
        resolved_template_id,
        style_id,
    )


internet._phone = _safe_phone
v66._previous_render_planned_frame = _legacy_core_renderer
internet._previous_render_planned_frame = _legacy_v66_renderer

# Preserve the established public identity contract. Internet scenes are handled
# by the new director; every other subject delegates to the explicit legacy core.
v63.render_planned_frame = internet.render_planned_frame
v65.render_planned_frame = internet.render_planned_frame
v66.render_planned_frame = internet.render_planned_frame
cartoon.render_planned_frame = internet.render_planned_frame
cartoon.render_cartoon_documentary = render_cartoon_documentary

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
