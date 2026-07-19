from __future__ import annotations

"""Shorts Story v2: semantic template dispatch and Mars-specific copy."""

from . import exact_visuals as exact
from . import native_shorts as shorts

_ORIGINAL_COMPOSE = shorts.compose_native_shorts
_MARS_TEMPLATES = {
    "route_map",
    "crowd_focus",
    "presenter_desk",
    "transport_scene",
    "habitat_build",
    "council_scene",
    "process_diagram",
}

_MARS_COPY = {
    "route_map": shorts.ShortsComposition("EARTH TO MARS — ONE WAY FORWARD"),
    "transport_scene": shorts.ShortsComposition("MOVE PEOPLE BEFORE THE WINDOW CLOSES"),
    "habitat_build": shorts.ShortsComposition("SURVIVAL STARTS WITH SHELTER"),
    "presenter_desk": shorts.ShortsComposition("THE EVIDENCE SETS THE PLAN"),
    "council_scene": shorts.ShortsComposition("WHO DECIDES THE FUTURE?"),
    "crowd_focus": shorts.ShortsComposition("A CIVILIZATION IS MADE OF PEOPLE"),
    "process_diagram": shorts.ShortsComposition("TRANSPORT. HABITAT. GOVERNANCE."),
}

for template_id, composition in _MARS_COPY.items():
    shorts.COMPOSITIONS[(exact.TECH_FAMILY_ID, template_id)] = composition


def _compose(source, *, family_id: str | None, template_id: str | None, progress: float = .5, title: str | None = None, subtitle: str | None = None):
    template = template_id or ""
    family = family_id or ""
    if template in _MARS_TEMPLATES:
        # The documentary planner can assign a broad family. For native shorts,
        # a known semantic template is stronger evidence than that family label.
        family = exact.TECH_FAMILY_ID
        if not subtitle:
            subtitle = {
                "route_map": "A one-way journey from Earth to a permanent Mars settlement.",
                "transport_scene": "The first challenge is moving people safely and quickly.",
                "habitat_build": "Air, shelter, power, and food must work before arrival.",
                "presenter_desk": "Evidence turns a bold idea into an operating plan.",
                "council_scene": "Survival also requires rules, authority, and trust.",
                "crowd_focus": "The mission succeeds only when ordinary people can live there.",
                "process_diagram": "A civilization needs transport, habitat, and governance.",
            }.get(template)
    return _ORIGINAL_COMPOSE(
        source,
        family_id=family,
        template_id=template,
        progress=progress,
        title=title,
        subtitle=subtitle,
    )


shorts.compose_native_shorts = _compose
