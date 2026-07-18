from __future__ import annotations

"""Art Polish v43: one presenter pointer, clearly distinct from anatomy."""

from PIL import Image, ImageDraw
from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v19 as v19
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v34 as v34
from . import cartoon_art_polish_v33 as v33
from . import cartoon_art_polish_v42 as v42


def _safe_v34_render(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    image = v33.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)
    selected, progress, variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id != "presenter_desk":
        return image
    state, local = v19._beat_state(progress)
    if state == 0:
        return image
    draw = ImageDraw.Draw(image)
    right = variant % 4 in (0, 3)
    hand = (1095, 515) if right else (685, 535)
    direction = -1 if right else 1
    handle = (hand[0] + direction * 18, hand[1] - 12)
    tip = (handle[0] + direction * round(145 + 30 * local), handle[1] - round(72 + 18 * local))
    # Small handle + thin shaft + contrasting tip makes this unmistakably an object.
    draw.rounded_rectangle((hand[0] - 12, hand[1] - 10, hand[0] + 12, hand[1] + 10), radius=5, fill=cartoon.AMBER, outline=cartoon.INK, width=3)
    draw.line((handle, tip), fill=(74, 83, 91), width=5)
    draw.ellipse((tip[0] - 7, tip[1] - 7, tip[0] + 7, tip[1] + 7), fill=cartoon.CYAN, outline=cartoon.INK, width=3)
    return image


# Downstream modules call v34 dynamically; replace the faulty double-line source once.
v34.render_planned_frame = _safe_v34_render


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    return v42.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)


cartoon.render_planned_frame = render_planned_frame
