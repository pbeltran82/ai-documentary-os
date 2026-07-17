from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

YOUTUBE_FORMAT = "youtube"
SHORTS_FORMAT = "shorts"
DEFAULT_VIDEO_FORMAT = YOUTUBE_FORMAT


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


TECH_SHORTS_STORY_BOXES: dict[
    str,
    tuple[tuple[float, float, float, float], ...],
] = {
    # Tech templates use deliberate two- and three-column compositions. Their
    # meaningful units must be separated before stacking; a generic 50/50 crop
    # cuts labels, diagrams, and engagement controls in half.
    "algorithm_chose_you": (
        (0.035, 0.315, 0.335, 0.925),
        (0.345, 0.315, 0.645, 0.925),
        (0.665, 0.315, 0.965, 0.925),
    ),
    "behavior_prediction_engine": (
        (0.040, 0.335, 0.385, 0.835),
        (0.380, 0.335, 0.640, 0.835),
        (0.660, 0.335, 0.955, 0.835),
    ),
    "life_event_timeline": (
        (0.035, 0.320, 0.500, 0.700),
        (0.500, 0.320, 0.965, 0.700),
    ),
    "digital_footprint_collector": (
        (0.040, 0.320, 0.390, 0.920),
        (0.500, 0.320, 0.960, 0.920),
    ),
    "behavioral_twin": (
        (0.035, 0.350, 0.320, 0.930),
        (0.325, 0.350, 0.675, 0.930),
        (0.680, 0.350, 0.965, 0.930),
    ),
    "machine_choice_explainer": (
        (0.035, 0.320, 0.400, 0.850),
        (0.425, 0.300, 0.960, 0.850),
    ),
    "machine_choice_cta": (
        (0.040, 0.320, 0.480, 0.755),
        (0.520, 0.320, 0.960, 0.755),
        (0.270, 0.735, 0.730, 0.965),
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


def _fit_image(image: Image.Image, bounds: tuple[int, int]) -> Image.Image:
    maximum_width, maximum_height = bounds
    scale = min(maximum_width / image.width, maximum_height / image.height)
    size = (
        max(1, round(image.width * scale)),
        max(1, round(image.height * scale)),
    )
    return image.resize(size, Image.Resampling.LANCZOS)


def _ambient_background(image: Image.Image, profile: VideoFormatProfile) -> Image.Image:
    # Work at quarter resolution while blurring. The ambient layer is meant to
    # be soft, and this keeps frame-by-frame Shorts rendering practical locally.
    small_width = max(1, profile.width // 4)
    small_height = max(1, profile.height // 4)
    scale = max(small_width / image.width, small_height / image.height)
    cover = image.resize(
        (
            max(1, round(image.width * scale)),
            max(1, round(image.height * scale)),
        ),
        Image.Resampling.BILINEAR,
    )
    left = max(0, (cover.width - small_width) // 2)
    top = max(0, (cover.height - small_height) // 2)
    cover = cover.crop((left, top, left + small_width, top + small_height))
    cover = cover.filter(ImageFilter.GaussianBlur(radius=14))
    cover = ImageEnhance.Brightness(cover).enhance(0.40)
    cover = ImageEnhance.Color(cover).enhance(0.78)
    return cover.resize((profile.width, profile.height), Image.Resampling.BILINEAR)


def _paste_panel(
    canvas: Image.Image,
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    accent: tuple[int, int, int] = (84, 214, 194),
) -> None:
    left, top, right, bottom = box
    panel_width = right - left
    panel_height = bottom - top
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle(
        (left + 8, top + 12, right + 8, bottom + 12),
        radius=30,
        fill=(0, 0, 0, 105),
    )
    draw.rounded_rectangle(
        box,
        radius=30,
        fill=(5, 13, 25, 225),
        outline=(*accent, 150),
        width=3,
    )
    fitted = _fit_image(image, (panel_width - 52, panel_height - 52))
    x = left + (panel_width - fitted.width) // 2
    y = top + (panel_height - fitted.height) // 2
    canvas.paste(fitted, (x, y))


def _story_regions(
    source: Image.Image,
    family_id: str | None,
    template_id: str | None,
) -> tuple[Image.Image, Image.Image]:
    width, height = source.size
    if family_id == "finance_motion" and template_id == "subscribe_cta":
        # The landscape CTA intentionally overlaps two large cards. Isolate the
        # useful blueprint copy and the actions instead of carrying either
        # card's stray border into its neighbor's vertical panel.
        left_box = (0.09, 0.30, 0.50, 0.91)
        right_box = (0.56, 0.30, 0.91, 0.91)
    elif family_id == "character_explainer":
        # Character templates consistently stage the person on the left and
        # the consequence/system on the right.
        left_box = (0.035, 0.30, 0.45, 0.955)
        right_box = (0.47, 0.30, 0.975, 0.955)
    else:
        left_box = (0.025, 0.30, 0.50, 0.955)
        right_box = (0.50, 0.30, 0.975, 0.955)

    def crop(box: tuple[float, float, float, float]) -> Image.Image:
        return source.crop(
            tuple(
                round(value * (width if index % 2 == 0 else height))
                for index, value in enumerate(box)
            )
        )

    return crop(left_box), crop(right_box)


def _crop_relative(
    source: Image.Image,
    box: tuple[float, float, float, float],
) -> Image.Image:
    width, height = source.size
    return source.crop(
        tuple(
            round(value * (width if index % 2 == 0 else height))
            for index, value in enumerate(box)
        )
    )


def _tech_story_regions(
    source: Image.Image,
    template_id: str | None,
) -> tuple[Image.Image, ...] | None:
    boxes = TECH_SHORTS_STORY_BOXES.get(template_id or "")
    if boxes is None:
        return None
    return tuple(_crop_relative(source, box) for box in boxes)


def _story_panel_boxes(count: int) -> tuple[tuple[int, int, int, int], ...]:
    if count == 3:
        return (
            (34, 320, 1046, 812),
            (34, 846, 1046, 1338),
            (34, 1372, 1046, 1874),
        )
    return (
        (34, 320, 1046, 1080),
        (34, 1114, 1046, 1874),
    )


def format_exact_visual_frame(
    frame: Image.Image,
    video_format: Any,
    family_id: str | None = None,
    template_id: str | None = None,
) -> Image.Image:
    """Adapt a house-format exact visual to the selected delivery canvas.

    Landscape remains pixel-identical. Shorts gets a semantic-safe reflow:
    the full title area is retained, and the overlapping left/right story
    regions are enlarged and stacked instead of being center-cropped.
    """
    profile = video_format_profile(video_format)
    source = frame.convert("RGB")
    if profile.format_id == YOUTUBE_FORMAT:
        if source.size == (profile.width, profile.height):
            return source
        return source.resize((profile.width, profile.height), Image.Resampling.LANCZOS)

    canvas = _ambient_background(source, profile)
    width, height = source.size

    header = source.crop(
        (
            round(width * 0.035),
            round(height * 0.035),
            round(width * 0.965),
            round(height * 0.275),
        )
    )
    tech_regions = (
        _tech_story_regions(source, template_id)
        if family_id == "tech_behavior_motion"
        else None
    )
    story_regions = tech_regions or _story_regions(source, family_id, template_id)

    _paste_panel(canvas, header, (34, 48, 1046, 286))
    for region, box in zip(story_regions, _story_panel_boxes(len(story_regions))):
        _paste_panel(canvas, region, box)

    return canvas
