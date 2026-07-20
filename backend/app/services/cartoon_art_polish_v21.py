from __future__ import annotations

"""Art Polish v21: final staged-beat integration and safe focal confirmation cues."""

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v19 as v19
from . import cartoon_art_polish_v20 as v20


_ACTIVE_VARIANT = 0


def _crowd_response(draw: ImageDraw.ImageDraw, progress: float) -> None:
    """Use a floor guidance trail instead of a post-composited actor shadow."""
    action = v20._window(progress, 0.29, 0.71, 0.08)
    if action <= 0.0:
        return
    floor = round(cartoon.OUTPUT_HEIGHT * 0.76)
    center = round(420 + 610 * cartoon._ease((progress - 0.29) / 0.42))
    trail = round(50 + 90 * action)
    draw.rounded_rectangle(
        (center - trail, floor + 18, center + trail, floor + 28),
        radius=5,
        fill=cartoon.CYAN,
    )


def _transport_confirmation(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    state, local = v19._beat_state(progress)
    if state != 2:
        return
    floor = round(cartoon.OUTPUT_HEIGHT * 0.80)
    color = cartoon.GREEN
    if variant % 4 == 0:
        # Three sequential confirmation lamps make the doorway beat visibly resolve.
        for index, x in enumerate((835, 960, 1085)):
            active = local >= index * 0.22
            radius = 12 if active else 7
            draw.ellipse((x - radius, 260 - radius, x + radius, 260 + radius), fill=color if active else cartoon.MUTED, outline=cartoon.INK, width=3)
    else:
        width = round(160 + 220 * local)
        draw.line((960 - width // 2, floor - 38, 960 + width // 2, floor - 38), fill=color, width=7)


def _habitat_confirmation(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    if variant % 4 != 2:
        return
    state, local = v19._beat_state(progress)
    if state != 2:
        return
    panel_x, panel_y = 1110, 525
    # A simple two-stroke check replaces another pulsing ring.
    rise = round(10 * local)
    draw.line((panel_x - 24, panel_y + 2, panel_x - 5, panel_y + 20 - rise), fill=cartoon.GREEN, width=8)
    draw.line((panel_x - 5, panel_y + 20 - rise, panel_x + 31, panel_y - 24), fill=cartoon.GREEN, width=8)


def _presenter_confirmation(draw: ImageDraw.ImageDraw, progress: float, variant: int) -> None:
    state, local = v19._beat_state(progress)
    if state != 2:
        return
    right_side = variant % 4 in (0, 3)
    marker_x = 770 if right_side else 1090
    marker_y = 300
    # Resolve the teaching beat with a short underline rather than another arm overlay.
    width = round(35 + 80 * local)
    draw.rounded_rectangle(
        (marker_x - width, marker_y + 44, marker_x + width, marker_y + 54),
        radius=5,
        fill=cartoon.GREEN,
    )


def _council_confirmation(draw: ImageDraw.ImageDraw, progress: float) -> None:
    state, local = v19._beat_state(progress)
    centers = (650, 960, 1270)
    cx = centers[state]
    # Speaker indicator grows, holds, then stops; no extra body geometry is added.
    half = round(52 + 36 * local)
    draw.rounded_rectangle((cx - half, 704, cx + half, 716), radius=6, fill=cartoon.CYAN)


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    global _ACTIVE_VARIANT
    beat = cartoon._beat_for_time(scene, time_seconds)
    extra = str((beat or {}).get("visual_intent", ""))
    selected = cartoon.TEMPLATE_BY_ID.get(template_id or "")
    if selected is None or beat is not None:
        selected, _confidence, _reason = cartoon.suggest_template(scene, extra)

    beat_start = float((beat or {}).get("relative_start_seconds", 0.0))
    beat_end = float((beat or {}).get("relative_end_seconds", duration_seconds))
    progress = cartoon._ease((time_seconds - beat_start) / max(0.001, beat_end - beat_start))
    scene_number = int(getattr(scene, "scene_number", 1) or 1)
    offsets = {"transport_scene": 0, "habitat_build": 1, "presenter_desk": 2, "crowd_focus": 3, "route_map": 4, "council_scene": 5}
    _ACTIVE_VARIANT = (scene_number * 7 + offsets.get(selected.template_id, 0)) % 12

    image = v20.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    if selected.template_id == "route_map":
        return image

    draw = ImageDraw.Draw(image)
    if selected.template_id == "transport_scene":
        _transport_confirmation(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "habitat_build":
        _habitat_confirmation(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "presenter_desk":
        _presenter_confirmation(draw, progress, _ACTIVE_VARIANT)
    elif selected.template_id == "council_scene":
        _council_confirmation(draw, progress)
    elif selected.template_id == "crowd_focus":
        _crowd_response(draw, progress)
    return image


# Replace the unsafe v20 crowd overlay before the v21 wrapper invokes it.
v20._crowd_response = lambda draw, progress: None
cartoon.render_planned_frame = render_planned_frame
