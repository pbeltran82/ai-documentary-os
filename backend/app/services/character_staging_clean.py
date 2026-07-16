from __future__ import annotations

from PIL import ImageDraw

from . import character_staging as staged
from .visual_staging import CharacterPlacement


# v1.5.1 hotfix: the colored full-body separation ellipse introduced by
# Visual Staging read as a visible purple oval in finished footage. Keep the
# face-safe layouts and camera profiles, but use only a compact neutral contact
# shadow beneath the feet.


def _character_stage_clean(
    draw: ImageDraw.ImageDraw,
    placement: CharacterPlacement,
    palette: dict[str, tuple[int, int, int]],
    *,
    pose: str,
    mood: str = "neutral",
    alternate: bool = False,
) -> None:
    x = placement.center_x
    ground_y = placement.ground_y
    scale = placement.scale

    # Two small neutral ellipses create contact depth without surrounding the
    # person with a colored spotlight or silhouette halo.
    draw.ellipse(
        (
            x - round(86 * scale),
            ground_y - round(12 * scale),
            x + round(86 * scale),
            ground_y + round(12 * scale),
        ),
        fill=(3, 6, 14),
    )
    draw.ellipse(
        (
            x - round(56 * scale),
            ground_y - round(7 * scale),
            x + round(56 * scale),
            ground_y + round(7 * scale),
        ),
        fill=(7, 12, 24),
    )
    staged.base._person(
        draw,
        (x, ground_y),
        palette,
        scale=scale,
        pose=pose,
        mood=mood,
        facing=placement.facing,
        alternate=alternate,
    )


# The staged renderer functions resolve this module global at draw time, so the
# hotfix preserves every v1.5 layout while replacing only the backdrop primitive.
staged._character_stage = _character_stage_clean

CHARACTER_TEMPLATES = staged.CHARACTER_TEMPLATES
CHARACTER_TEMPLATE_BY_ID = staged.CHARACTER_TEMPLATE_BY_ID
DEFAULT_STYLE_ID = staged.DEFAULT_STYLE_ID
STYLES = staged.STYLES
OUTPUT_WIDTH = staged.OUTPUT_WIDTH
OUTPUT_HEIGHT = staged.OUTPUT_HEIGHT
ffmpeg_encoder_command = staged.ffmpeg_encoder_command
render_frame = staged.render_frame
render_character_motion = staged.render_character_motion
score_character_templates = staged.score_character_templates
storyboard_beats = staged.storyboard_beats
style_catalog = staged.style_catalog
suggest_template = staged.suggest_template
template_catalog = staged.template_catalog
