from __future__ import annotations

"""Final release polish for native 9:16 documentary compositions.

This layer keeps the proven semantic renderers intact while tightening the four
issues found in the 100-point QA pass: opening delay, repeated automation hold,
small supporting copy, and a crowded terminal CTA.
"""

from PIL import Image, ImageDraw

from . import native_shorts as shorts


def _final_transfer(canvas: Image.Image, progress: float, accent: shorts.RGB, *, person: bool = False) -> None:
    """Resolve the automation action earlier and give it three visible states."""
    draw = ImageDraw.Draw(canvas)
    move = shorts._phase(progress, 0.01, 0.52)
    confirm = shorts._phase(progress, 0.42, 0.68)
    shorts._card(draw, (90, 430, 990, 1400), outline=(86, 69, 38), fill=(20, 20, 27))

    if person:
        mood = "neutral"
        shorts._person(draw, (210, 1050), 0.6, shirt=(55, 171, 137), mood=mood)

    left = 370 if person else 180
    shorts._money(draw, (left, 590, left + 280, 710), "PAYDAY")
    shorts._arrow(draw, (left + 140, 730), (left + 140, 1000), shorts.GREEN, move, 9)

    panel_fill = (18, 55, 49) if confirm < 1 else (17, 67, 55)
    draw.rounded_rectangle(
        (left, 1010, left + 500, 1190),
        radius=32,
        fill=panel_fill,
        outline=shorts.GREEN,
        width=5,
    )
    shorts._text(draw, (left + 250, 1066), "AUTO-TRANSFER", 29, shorts.GREEN, bold=True, anchor="mm")
    status = "MOVING…" if confirm < 0.55 else "CONFIRMED  ✓"
    shorts._text(draw, (left + 250, 1132), status, 38, shorts.WHITE, bold=True, anchor="mm")

    if person:
        support = "RULE SET. NO DAILY DECISION."
        shorts._text(draw, (540, 1338), support, 25, shorts.MUTED, bold=True, anchor="mm")


def _final_growth(canvas: Image.Image, progress: float, accent: shorts.RGB, *, compound: bool = False) -> None:
    """Use three meaningful time milestones instead of decorative baseline dots."""
    draw = ImageDraw.Draw(canvas)
    q = shorts._phase(progress, 0.02, 0.88)
    shorts._card(draw, (90, 430, 990, 1400), outline=(86, 69, 38), fill=(20, 20, 27))
    x0, y0 = 170, 1220
    draw.line((x0, 570, x0, y0, 900, y0), fill=(75, 78, 91), width=4)

    points: list[tuple[float, float]] = []
    for index in range(81):
        t = index / 80
        x = x0 + 700 * t
        factor = t * t if compound else 0.25 * t + 0.75 * t * t
        y = y0 - 530 * factor
        points.append((x, y))
    visible = points[: max(2, round(len(points) * q))]
    draw.line(visible, fill=shorts.GREEN, width=12, joint="curve")

    milestones = ((0.18, "YEAR 1"), (0.52, "YEAR 5"), (0.88, "YEAR 10"))
    for threshold, label in milestones:
        x = round(x0 + 700 * threshold)
        if q >= threshold:
            draw.ellipse((x - 13, y0 - 13, x + 13, y0 + 13), fill=shorts.AMBER)
            shorts._text(draw, (x, y0 + 46), label, 22, shorts.MUTED, bold=True, anchor="mm")

    shorts._text(draw, (540, 520), "CONTRIBUTIONS + TIME", 31, shorts.MUTED, bold=True, anchor="mm")
    shorts._text(
        draw,
        (750, 800 if compound else 900),
        "COMPOUNDING" if compound else "MARKET EXPOSURE",
        30,
        shorts.GREEN,
        bold=True,
        anchor="mm",
    )


def _final_finance_cta(canvas: Image.Image, progress: float, accent: shorts.RGB) -> None:
    """Finish the blueprint above a visually separate terminal action area."""
    draw = ImageDraw.Draw(canvas)
    q = shorts._phase(progress, 0.02, 0.62)
    shorts._card(draw, (95, 440, 985, 1195), outline=shorts.AMBER, fill=(20, 20, 27))
    steps = (
        ("1", "MOVE 10% FIRST", shorts.AMBER),
        ("2", "AUTOMATE THE TRANSFER", shorts.GREEN),
        ("3", "LET TIME COMPOUND", shorts.CYAN),
    )
    for index, (number, label, color) in enumerate(steps):
        y = 575 + index * 188
        active = q >= index * 0.25
        resolved = color if active else (57, 63, 73)
        draw.ellipse((155, y - 43, 241, y + 43), fill=resolved)
        shorts._text(draw, (198, y), number, 30, (12, 18, 27), bold=True, anchor="mm")
        shorts._text(draw, (285, y), label, 32, shorts.WHITE if active else (105, 112, 125), bold=True)


def _final_cta(canvas: Image.Image, progress: float) -> None:
    """Dedicated closing panel with one dominant conversion action."""
    draw = ImageDraw.Draw(canvas)
    top = 1270
    draw.rounded_rectangle(
        (shorts.SAFE_LEFT, top, shorts.SAFE_RIGHT, 1715),
        radius=36,
        fill=(8, 17, 31),
        outline=(52, 65, 86),
        width=4,
    )
    shorts._text(draw, (540, 1350), "BUILD THE SYSTEM ONCE.", 31, shorts.MUTED, bold=True, anchor="mm")
    shorts._text(draw, (540, 1410), "LET IT WORK EVERY PAYDAY.", 39, shorts.WHITE, bold=True, anchor="mm")

    button = (150, 1490, 930, 1605)
    draw.rounded_rectangle(button, radius=30, fill=shorts.RED)
    draw.polygon(((205, 1522), (205, 1573), (246, 1548)), fill=shorts.WHITE)
    shorts._text(draw, (565, 1548), "SUBSCRIBE", 42, shorts.WHITE, bold=True, anchor="mm")
    shorts._text(draw, (540, 1660), "MORE CLEAR MONEY SYSTEMS", 24, (132, 149, 174), bold=True, anchor="mm")


def compose_native_shorts(
    source: Image.Image,
    *,
    family_id: str | None,
    template_id: str | None,
    progress: float = 0.5,
    title: str | None = None,
    subtitle: str | None = None,
) -> Image.Image:
    """Compose with an immediate designed first frame and a brief exit fade only."""
    del source
    family = family_id or ""
    template = template_id or ""
    composition = shorts.COMPOSITIONS.get((family, template), shorts.ShortsComposition("ONE CLEAR DOCUMENTARY IDEA"))
    accent = shorts.FAMILY_COPY.get(family, ("DOCUMENTARY VISUAL", shorts.TEAL))[1]
    canvas = shorts._background(accent).copy()
    shorts._header(
        canvas,
        family,
        title or template.replace("_", " "),
        subtitle or "One clear idea, designed for vertical viewing.",
        accent,
    )
    shorts.RENDERERS.get((family, template), shorts._generic)(canvas, shorts._clamp(progress), accent)
    if composition.terminal_cta:
        _final_cta(canvas, progress)
    else:
        shorts._footer(canvas, composition.focus_label, accent)

    # Start on the designed frame immediately. Retain only a short exit fade.
    visibility = shorts._smooth((1 - shorts._clamp(progress)) / 0.028)
    if visibility < 1:
        return Image.blend(Image.new("RGB", canvas.size, (3, 7, 15)), canvas, visibility)
    return canvas


# Install the final semantic renderers and composition contract.
shorts.RENDERERS[("finance_motion", "recurring_transfer")] = _final_transfer
shorts.RENDERERS[("character_explainer", "automatic_investing_habit")] = lambda c, p, a: _final_transfer(c, p, a, person=True)
shorts.RENDERERS[("finance_motion", "index_growth")] = _final_growth
shorts.RENDERERS[("finance_motion", "compound_growth")] = lambda c, p, a: _final_growth(c, p, a, compound=True)
shorts.RENDERERS[("finance_motion", "subscribe_cta")] = _final_finance_cta
shorts._cta = _final_cta
shorts.compose_native_shorts = compose_native_shorts
