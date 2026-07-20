from __future__ import annotations

"""Shorts Story v6: final native Mars shorts contract."""

from PIL import Image

from . import native_shorts as shorts
from . import cartoon_shorts_story_v2 as _story_v2  # noqa: F401
from . import cartoon_shorts_story_v3 as _story_v3  # noqa: F401
from . import cartoon_shorts_story_v4 as _story_v4  # noqa: F401
from . import cartoon_shorts_story_v5 as _story_v5  # noqa: F401


def render_native_short(source: Image.Image, *, family_id: str | None, template_id: str | None, progress: float = .5, title: str | None = None, subtitle: str | None = None) -> Image.Image:
    """Stable entry point for subject-specific 9:16 documentary frames."""
    return shorts.compose_native_shorts(
        source,
        family_id=family_id,
        template_id=template_id,
        progress=progress,
        title=title,
        subtitle=subtitle,
    )
