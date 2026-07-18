from __future__ import annotations

"""Art Polish v45: clean Earth-to-Mars travel without dotted trajectory graphics."""

import math
from PIL import Image, ImageDraw
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v7 as v7
from . import cartoon_art_polish_v14 as v14
from . import cartoon_art_polish_v17 as v17
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v44 as v44


def _spacecraft(image: Image.Image, x: int, y: int, scale: float, progress: float, angle: float) -> None:
    pad = 460
    sprite = Image.new("RGBA", (pad * 2, pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sprite)
    v7._spacecraft(draw, pad, pad, scale, progress)
    rotated = sprite.rotate(-math.degrees(angle), resample=Image.Resampling.BICUBIC, expand=True)
    image.paste(rotated, (round(x - rotated.width / 2), round(y - rotated.height / 2)), rotated)


def _clean_route(progress: float, variant: int) -> Image.Image:
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    # Background shifts from Earth blue to deep-space violet to Mars dusk.
    if progress < 0.34:
        bg = (214, 235, 247)
    elif progress < 0.74:
        bg = (221, 218, 238)
    else:
        bg = (242, 218, 199)
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    for index in range(34):
        sx = (index * 181 + variant * 43) % width
        sy = 25 + (index * 83) % round(height * 0.38)
        r = 2 + index % 2
        draw.ellipse((sx-r, sy-r, sx+r, sy+r), fill=(118, 126, 143))
    layouts = (
        ((360, 690), (1540, 410), (960, 130), 225, 190),
        ((300, 760), (1580, 300), (930, 100), 180, 235),
        ((270, 760), (1480, 560), (850, 180), 135, 285),
    )
    earth, mars, control, earth_r, mars_r = layouts[variant % 3]
    cartoon._planet(draw, earth, earth_r, cartoon.BLUE, progress)
    cartoon._planet(draw, mars, mars_r, cartoon.MARS, 1-progress)
    scale = 0.74 if variant % 3 < 2 else 0.68
    safe_start, safe_end = v14._safe_route_interval(earth, mars, control, earth_r, mars_r, scale)
    # Finish travel by 78% and hold a clean Mars-arrival composition afterward.
    travel = cartoon._ease(min(1.0, progress / 0.78))
    t = safe_start + (safe_end-safe_start) * travel
    x, y = v17._bezier_point(earth, control, mars, t)
    tx, ty = v17._bezier_tangent(earth, control, mars, t)
    _spacecraft(image, round(x), round(y), scale, progress, math.atan2(ty, tx))
    return image


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    selected, progress, variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id == "route_map":
        return _clean_route(progress, variant)
    return v44.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)


cartoon.render_planned_frame = render_planned_frame
