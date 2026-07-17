from __future__ import annotations

"""Correct the shared expressive character's wide, inward-kneed stance.

Finance and character-led 16:9 scenes use ``character_expressive`` rather than
Tech's dedicated landscape figure.  The original neutral rig placed each ankle
far outside its hip while pulling the knee inward, which read as crouched or
bow-legged at documentary scale.  This patch narrows only the leg chains and
moves each shoe to the corrected ankle.  Arms, gestures, faces, clothes, and
vertical Shorts characters remain unchanged.
"""

from collections.abc import Iterable

from PIL import ImageDraw

from . import character_expressive as character


_ORIGINAL_LIMB = character._limb
_ORIGINAL_SHOE = character._shoe
_CORRECTED_ANKLES: dict[tuple[int, int], tuple[int, int]] = {}


def _straight_leg_limb(
    draw: ImageDraw.ImageDraw,
    points: Iterable[tuple[int, int]],
    color: tuple[int, int, int],
    width: int,
) -> None:
    sequence = list(points)
    if len(sequence) != 3:
        _ORIGINAL_LIMB(draw, sequence, color, width)
        return

    hip, knee, ankle = sequence
    vertical_span = max(1, ankle[1] - hip[1])
    # The source rig's hip-to-ground span is roughly 78 design units.  Derive
    # scale from the actual rendered chain so the correction works at every size.
    scale = max(0.35, vertical_span / 78.0)
    direction_source = ankle[0] - hip[0]
    if direction_source == 0:
        direction_source = knee[0] - hip[0]
    direction = -1 if direction_source < 0 else 1

    corrected_knee = (
        hip[0] + direction * max(5, round(10 * scale)),
        knee[1],
    )
    corrected_ankle = (
        hip[0] + direction * max(9, round(18 * scale)),
        ankle[1],
    )
    _CORRECTED_ANKLES[ankle] = corrected_ankle
    _ORIGINAL_LIMB(draw, (hip, corrected_knee, corrected_ankle), color, width)


def _straight_leg_shoe(
    draw: ImageDraw.ImageDraw,
    ankle: tuple[int, int],
    facing: int,
    color: tuple[int, int, int],
    scale: float,
) -> None:
    corrected = _CORRECTED_ANKLES.pop(ankle, ankle)
    _ORIGINAL_SHOE(draw, corrected, facing, color, scale)


def install_character_stance_patch() -> None:
    character._limb = _straight_leg_limb
    character._shoe = _straight_leg_shoe


install_character_stance_patch()
