from __future__ import annotations

"""Compatibility guard for Art Polish v15 route-map integration."""

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v14 as v14
from . import cartoon_art_polish_v15 as v15


# v15 renders route maps directly from its planned-frame renderer. Restore the
# public drawing hook for any legacy preview or utility caller that still invokes
# ``cartoon._draw_route_map`` independently.
cartoon._draw_route_map = v14._draw_route_map
cartoon.render_planned_frame = v15.render_planned_frame
