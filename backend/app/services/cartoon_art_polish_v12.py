from __future__ import annotations

"""Art Polish v12: break the v11 human monkeypatch recursion safely."""

from PIL import ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v6 as v6
from . import cartoon_art_polish_v8 as v8
from . import cartoon_art_polish_v11 as v11


def _human(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    scale: float,
    color: tuple[int, int, int],
    pose: str = "stand",
) -> None:
    """Render from the stable v6 base, then apply the v11 limb refinement.

    v11 replaced ``v8._human`` with ``v11._human`` while ``v11._human`` called
    ``v8._human``. Calling the stable v6 implementation directly avoids that
    circular dispatch while preserving the intended thicker-limb refinement.
    """
    v6._human(draw, x, y, scale, color, pose)

    line = max(7, round(11 * scale))
    head_r = round(29 * scale)
    neck_h = round(22 * scale)
    body_w = round(78 * scale)
    body_h = round(92 * scale)
    torso_top = y + head_r + neck_h - round(2 * scale)
    shoulder_y = torso_top + round(15 * scale)
    bottom = torso_top + body_h
    elbow_y = shoulder_y + round(34 * scale)
    hand_y = shoulder_y + round(62 * scale)

    if pose == "point":
        draw.line(
            (x - body_w // 2, shoulder_y, x - round(58 * scale), elbow_y, x - round(92 * scale), y),
            fill=cartoon.INK,
            width=line,
            joint="curve",
        )
        draw.line(
            (x + body_w // 2, shoulder_y, x + round(50 * scale), elbow_y, x + round(42 * scale), hand_y),
            fill=cartoon.INK,
            width=line,
            joint="curve",
        )
    else:
        for direction in (-1, 1):
            draw.line(
                (
                    x + direction * body_w // 2,
                    shoulder_y,
                    x + direction * round(49 * scale),
                    elbow_y,
                    x + direction * round(38 * scale),
                    hand_y,
                ),
                fill=cartoon.INK,
                width=line,
                joint="curve",
            )

    hip_y = bottom
    knee_y = hip_y + round(34 * scale)
    foot_y = hip_y + round(67 * scale)
    for direction in (-1, 1):
        foot_x = x + direction * round(27 * scale)
        draw.line(
            (x + direction * round(17 * scale), hip_y, x + direction * round(22 * scale), knee_y, foot_x, foot_y),
            fill=cartoon.INK,
            width=line,
            joint="curve",
        )


# Replace every dynamic lookup involved in the recursion cycle.
v11._human = _human
v8._human = _human
