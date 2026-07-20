from __future__ import annotations

"""Art Polish v51: remove accidental long vertical construction seams."""

from PIL import Image

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v50 as v50


def _scrub_long_vertical_seams(image: Image.Image) -> Image.Image:
    """Replace only thin columns containing unusually long dark runs.

    This targets architectural guide/seam artifacts while leaving ordinary
    character and object outlines intact.
    """
    rgb = image.convert("RGB")
    px = rgb.load()
    width, height = rgb.size
    scan_top = 120
    scan_bottom = min(height - 80, 860)
    candidates: list[int] = []
    for x in range(16, width - 16):
        longest = current = 0
        for y in range(scan_top, scan_bottom):
            r, g, b = px[x, y]
            dark = r < 42 and g < 48 and b < 60
            current = current + 1 if dark else 0
            longest = max(longest, current)
        if longest >= 260:
            candidates.append(x)
    if not candidates:
        return rgb

    groups: list[tuple[int, int]] = []
    start = prev = candidates[0]
    for x in candidates[1:]:
        if x <= prev + 2:
            prev = x
            continue
        groups.append((start, prev))
        start = prev = x
    groups.append((start, prev))

    for left, right in groups:
        if right - left > 18:
            continue
        sample_left = max(0, left - 7)
        sample_right = min(width - 1, right + 7)
        for y in range(scan_top, scan_bottom):
            a = px[sample_left, y]
            b = px[sample_right, y]
            fill = tuple((a[i] + b[i]) // 2 for i in range(3))
            for x in range(max(0, left - 2), min(width, right + 3)):
                r, g, bl = px[x, y]
                if r < 65 and g < 70 and bl < 82:
                    px[x, y] = fill
    return rgb


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v50.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    selected, _progress, _variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id in {"transport_scene", "habitat_build"}:
        image = _scrub_long_vertical_seams(image)
    return image


cartoon.render_planned_frame = render_planned_frame
