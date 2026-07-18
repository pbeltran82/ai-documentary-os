from __future__ import annotations

"""Art Polish v29: compatibility and overdraw guards for the v22-v28 stack."""

from PIL import ImageDraw

from . import cartoon_art_polish_v19 as v19
from . import cartoon_art_polish_v20 as v20
from . import cartoon_art_polish_v27 as v27


def _noop(*args, **kwargs) -> None:
    return None


# New complete pose layers replace these older partial-body/focal overlays.
v19._presenter_beat = _noop
v19._council_beat = _noop
v19._crowd_beat = _noop

# v25 owns the crowd focal crossing; remove older trailing overlays.
v20._crowd_response = _noop

# The review found this framing layer too UI-like for documentary imagery.
v27._focus_frame = _noop


def validate_renderer_contract(draw: ImageDraw.ImageDraw | None = None) -> bool:
    """Tiny import-time contract surface for tests and future compatibility checks."""
    return callable(v19.render_planned_frame) and callable(v20.render_planned_frame) and callable(v27.render_planned_frame)


RENDERER_CONTRACT_OK = validate_renderer_contract()
