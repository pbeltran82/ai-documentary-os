from __future__ import annotations

"""Shorts Story v5: pacing and fallback guard for native Mars scenes."""

from PIL import Image

from . import exact_visuals as exact
from . import native_shorts as shorts

_PREVIOUS_COMPOSE = shorts.compose_native_shorts
_MARS_TEMPLATES = {
    "route_map",
    "crowd_focus",
    "presenter_desk",
    "transport_scene",
    "habitat_build",
    "council_scene",
    "process_diagram",
}


def _paced(progress: float) -> float:
    """Reserve brief open/close beats and maximize useful action time."""
    p = max(0.0, min(1.0, float(progress)))
    if p <= 0.08:
        return 0.12 * (p / 0.08)
    if p >= 0.92:
        return 0.88 + 0.12 * ((p - 0.92) / 0.08)
    return 0.12 + 0.76 * ((p - 0.08) / 0.84)


def _compose(source: Image.Image, *, family_id: str | None, template_id: str | None, progress: float = .5, title: str | None = None, subtitle: str | None = None) -> Image.Image:
    template = template_id or ""
    if template in _MARS_TEMPLATES:
        family_id = exact.TECH_FAMILY_ID
        # A missing semantic renderer is a configuration error; use the Mars
        # process storyboard rather than silently returning generic bars.
        if (exact.TECH_FAMILY_ID, template) not in shorts.RENDERERS:
            template = "process_diagram"
        progress = _paced(progress)
    image = _PREVIOUS_COMPOSE(
        source,
        family_id=family_id,
        template_id=template,
        progress=progress,
        title=title,
        subtitle=subtitle,
    )
    if image.mode != "RGB":
        image = image.convert("RGB")
    if image.size != (shorts.SHORTS_WIDTH, shorts.SHORTS_HEIGHT):
        image = image.resize((shorts.SHORTS_WIDTH, shorts.SHORTS_HEIGHT), Image.Resampling.LANCZOS)
    return image


shorts.compose_native_shorts = _compose
