from __future__ import annotations

"""Release compatibility for public helpers and the terminal Shorts CTA."""

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_documentary_polish as polish
from . import native_shorts as shorts
from . import native_shorts_final_polish as final


def _wrap_text(value: str, width: int, *, size: int, max_lines: int = 2) -> list[str]:
    font = cartoon._font(size, True)
    words = " ".join(str(value or "").split()).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or font.getlength(candidate) <= width:
            current = candidate
            continue
        lines.append(current)
        current = word
    if current:
        lines.append(current)
    if len(lines) <= max_lines:
        return lines
    result = lines[:max_lines]
    tail = result[-1]
    while tail and font.getlength(tail + "…") > width:
        tail = tail[:-1].rstrip()
    result[-1] = tail + "…"
    return result


def _thesis_first_cta(canvas: Image.Image, progress: float) -> None:
    draw = ImageDraw.Draw(canvas)
    top = 1270
    draw.rounded_rectangle(
        (shorts.SAFE_LEFT, top, shorts.SAFE_RIGHT, 1715),
        radius=36,
        fill=(8, 17, 31),
        outline=(52, 65, 86),
        width=4,
    )
    shorts._text(draw, (540, 1350), "THE STORY IS CLEAR.", 31, shorts.MUTED, bold=True, anchor="mm")
    shorts._text(draw, (540, 1410), "NOW CHOOSE WHAT COMES NEXT.", 38, shorts.WHITE, bold=True, anchor="mm")

    reveal = shorts._phase(progress, 0.66, 0.82)
    if reveal < 0.5:
        shorts._text(draw, (540, 1550), "THE THESIS LANDS BEFORE THE ASK", 24, (132, 149, 174), bold=True, anchor="mm")
        return

    draw.rounded_rectangle((100, 1490, 650, 1605), radius=30, fill=shorts.RED)
    draw.polygon(((145, 1522), (145, 1573), (186, 1548)), fill=shorts.WHITE)
    shorts._text(draw, (390, 1548), "SUBSCRIBE", 38, shorts.WHITE, bold=True, anchor="mm")
    draw.rounded_rectangle((680, 1490, 1010, 1605), radius=30, fill=shorts.BLUE)
    shorts._text(draw, (845, 1548), "LIKE  👍", 32, shorts.WHITE, bold=True, anchor="mm")
    shorts._text(draw, (540, 1660), "KEEP THE DOCUMENTARY MOVING", 24, (132, 149, 174), bold=True, anchor="mm")


polish._wrap_text = _wrap_text
final._final_cta = _thesis_first_cta
shorts._cta = _thesis_first_cta
