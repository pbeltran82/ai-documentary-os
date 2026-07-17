from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image

from . import documentary_final_pass as _documentary_final_pass
from .documentary_visual_polish import (
    compose_documentary_shorts,
    install_landscape_character_patch,
)

YOUTUBE_FORMAT = "youtube"
SHORTS_FORMAT = "shorts"
DEFAULT_VIDEO_FORMAT = YOUTUBE_FORMAT
SHORTS_HERO_SOURCE_PROGRESS = 0.82


@dataclass(frozen=True)
class VideoFormatProfile:
    format_id: str
    label: str
    width: int
    height: int
    description: str

    @property
    def aspect_ratio(self) -> str:
        return "16:9" if self.width > self.height else "9:16"


VIDEO_FORMATS = {
    YOUTUBE_FORMAT: VideoFormatProfile(
        format_id=YOUTUBE_FORMAT,
        label="YouTube",
        width=1920,
        height=1080,
        description="Landscape 16:9 for standard YouTube videos.",
    ),
    SHORTS_FORMAT: VideoFormatProfile(
        format_id=SHORTS_FORMAT,
        label="Shorts",
        width=1080,
        height=1920,
        description="Vertical 9:16 for YouTube Shorts.",
    ),
}


def normalize_video_format(value: Any) -> str:
    candidate = str(value or DEFAULT_VIDEO_FORMAT).strip().lower()
    return candidate if candidate in VIDEO_FORMATS else DEFAULT_VIDEO_FORMAT


def project_video_format(value: Any) -> str:
    """Resolve a format from an id, Project, or Scene-like object."""
    if isinstance(value, str) or value is None:
        return normalize_video_format(value)
    project = getattr(value, "project", None)
    owner = project if project is not None else value
    return normalize_video_format(getattr(owner, "video_format", None))


def video_format_profile(value: Any) -> VideoFormatProfile:
    return VIDEO_FORMATS[project_video_format(value)]


def video_format_catalog() -> list[dict[str, Any]]:
    return [
        {
            "format_id": profile.format_id,
            "label": profile.label,
            "width": profile.width,
            "height": profile.height,
            "aspect_ratio": profile.aspect_ratio,
            "description": profile.description,
        }
        for profile in VIDEO_FORMATS.values()
    ]


def exact_visual_source_time(
    video_format: Any,
    duration_seconds: float,
    time_seconds: float,
) -> float:
    """Resolve the source renderer time for an exact-visual output frame.

    Landscape preserves the renderer's original animation clock. Shorts holds
    one mature hero state for the whole scene so the vertical composition does
    not cycle through several disconnected source layouts beneath the camera.
    """
    duration = max(0.0, float(duration_seconds))
    requested = max(0.0, min(float(time_seconds), duration))
    if project_video_format(video_format) != SHORTS_FORMAT or duration <= 0:
        return requested
    return min(max(0.0, duration - 0.03), duration * SHORTS_HERO_SOURCE_PROGRESS)


def format_exact_visual_frame(
    frame: Image.Image,
    video_format: Any,
    family_id: str | None = None,
    template_id: str | None = None,
    *,
    progress: float = 0.5,
    title: str | None = None,
    subtitle: str | None = None,
) -> Image.Image:
    """Adapt a house-format exact visual to the selected delivery canvas.

    Landscape remains dimensionally identical while receiving the shared,
    finished character rig. Shorts gets a native mobile story with stronger
    visual variety, a hard first-frame hook, and a thesis-led ending.
    """
    # This is intentionally installed at render time. Tech Behavior imports this
    # module before defining its legacy wireframe helper, so delaying the patch
    # avoids a circular import and guarantees the finished rig wins.
    install_landscape_character_patch()

    profile = video_format_profile(video_format)
    source = frame if frame.mode == "RGB" else frame.convert("RGB")
    if profile.format_id == YOUTUBE_FORMAT:
        if source.size == (profile.width, profile.height):
            return source
        return source.resize((profile.width, profile.height), Image.Resampling.LANCZOS)

    return compose_documentary_shorts(
        source,
        family_id=family_id,
        template_id=template_id,
        progress=progress,
        title=title,
        subtitle=subtitle,
    )
