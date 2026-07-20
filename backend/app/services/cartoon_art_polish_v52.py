from __future__ import annotations

"""Art Polish v52: monotonic Earth-to-Mars pacing with a short arrival hold."""

import math
from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v14 as v14
from . import cartoon_art_polish_v17 as v17
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v45 as v45
from . import cartoon_art_polish_v51 as v51


def _route(progress: float, variant: int) -> Image.Image:
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    if progress < 0.28:
        bg = (207, 232, 247)
    elif progress < 0.70:
        bg = (215, 214, 237)
    else:
        bg = (241, 215, 195)
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    for index in range(28):
        sx = (index * 193 + variant * 47) % width
        sy = 30 + (index * 89) % round(height * 0.36)
        radius = 2 + index % 2
        draw.ellipse((sx-radius, sy-radius, sx+radius, sy+radius), fill=(118, 126, 143))

    layouts = (
        ((360, 690), (1540, 410), (960, 130), 225, 190),
        ((300, 760), (1580, 300), (930, 100), 180, 235),
        ((270, 760), (1480, 560), (850, 180), 135, 285),
    )
    earth, mars, control, earth_r, mars_r = layouts[variant % 3]
    # Arrival depth: Mars grows modestly only during final approach.
    approach = cartoon._ease(max(0.0, min(1.0, (progress - 0.68) / 0.27)))
    drawn_mars_r = round(mars_r * (0.90 + 0.10 * approach))
    cartoon._planet(draw, earth, earth_r, cartoon.BLUE, progress)
    cartoon._planet(draw, mars, drawn_mars_r, cartoon.MARS, 1.0-progress)

    scale = 0.74 if variant % 3 < 2 else 0.68
    safe_start, safe_end = v14._safe_route_interval(earth, mars, control, earth_r, drawn_mars_r, scale)
    # Travel through 94% of the scene; reserve only the final 6% for arrival.
    travel = cartoon._ease(min(1.0, progress / 0.94))
    t = safe_start + (safe_end-safe_start) * travel
    x, y = v17._bezier_point(earth, control, mars, t)
    tx, ty = v17._bezier_tangent(earth, control, mars, t)
    v45._spacecraft(image, round(x), round(y), scale, progress, math.atan2(ty, tx))
    return image


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    selected, progress, variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id == "route_map":
        return _route(progress, variant)
    return v51.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)


cartoon.render_planned_frame = render_planned_frame
