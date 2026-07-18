from __future__ import annotations

"""Art Polish v46: stronger attached booster plume on the rotated spacecraft layer."""

import math
from PIL import Image, ImageDraw
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v7 as v7
from . import cartoon_art_polish_v45 as v45


def _spacecraft(image: Image.Image, x: int, y: int, scale: float, progress: float, angle: float) -> None:
    pad = 500
    sprite = Image.new("RGBA", (pad * 2, pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sprite)
    pulse = 0.5 + 0.5 * math.sin(progress * math.tau * 4.0)
    outer = round((115 + 35 * pulse) * scale)
    inner = round((70 + 22 * pulse) * scale)
    nozzle_x = pad - round(145 * scale)
    draw.polygon(
        ((nozzle_x, pad), (nozzle_x-outer, pad-round(38*scale)), (nozzle_x-outer, pad+round(38*scale))),
        fill=(244, 137, 44), outline=cartoon.INK,
    )
    draw.polygon(
        ((nozzle_x-6, pad), (nozzle_x-inner, pad-round(20*scale)), (nozzle_x-inner, pad+round(20*scale))),
        fill=(255, 214, 74),
    )
    v7._spacecraft(draw, pad, pad, scale, progress)
    rotated = sprite.rotate(-math.degrees(angle), resample=Image.Resampling.BICUBIC, expand=True)
    image.paste(rotated, (round(x-rotated.width/2), round(y-rotated.height/2)), rotated)


v45._spacecraft = _spacecraft


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    return v45.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)


cartoon.render_planned_frame = render_planned_frame
