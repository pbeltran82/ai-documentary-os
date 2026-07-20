from __future__ import annotations

"""Native 9:16 compositions for the general cartoon documentary family."""

from PIL import Image, ImageDraw

from . import exact_visuals as exact
from . import native_shorts as shorts


def _outlined_person(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0, *, accent=shorts.PURPLE) -> None:
    shorts._person(draw, (x, y), scale, shirt=accent, jeans=(58, 65, 78))


def _route(canvas: Image.Image, progress: float, accent) -> None:
    draw = ImageDraw.Draw(canvas)
    q = shorts._phase(progress, 0.03, 0.9)
    draw.ellipse((95, 560, 405, 870), fill=(43, 143, 196), outline=(5, 10, 18), width=12)
    draw.ellipse((675, 610, 965, 900), fill=(193, 91, 57), outline=(5, 10, 18), width=12)
    draw.ellipse((150, 620, 290, 735), fill=(77, 151, 82), outline=(5, 10, 18), width=6)
    shorts._arrow(draw, (430, 690), (650, 690), accent, q, 12)
    shorts._text(draw, (250, 950), "EARTH", 31, shorts.WHITE, bold=True, anchor="mm")
    shorts._text(draw, (820, 950), "MARS", 31, shorts.WHITE, bold=True, anchor="mm")
    shorts._chip(draw, (540, 1135), "THE JOURNEY", shorts.AMBER)


def _crowd(canvas: Image.Image, progress: float, accent) -> None:
    draw = ImageDraw.Draw(canvas)
    lift = round(36 * shorts._phase(progress, 0.15, 0.72))
    positions = []
    for row, count in enumerate((6, 7, 8)):
        y = 650 + row * 245
        for index in range(count):
            x = round((index + 0.5) * 1080 / count)
            positions.append((x, y, row, index, count))
    for x, y, row, index, count in positions:
        focal = row == 1 and index == count // 2
        _outlined_person(draw, x, y - (lift if focal else 0), 0.38 + row * 0.04, accent=shorts.AMBER if focal else (93, 101, 114))
    shorts._chip(draw, (540, 1325), "ONE HUMAN STORY", shorts.AMBER)


def _presenter(canvas: Image.Image, progress: float, accent) -> None:
    draw = ImageDraw.Draw(canvas)
    for x in range(80, 1001, 92):
        draw.line((x, 430, x, 1390), fill=(44, 72, 102), width=3)
    for y in range(460, 1391, 92):
        draw.line((70, y, 1010, y), fill=(44, 72, 102), width=3)
    _outlined_person(draw, 540, 790, 1.0, accent=shorts.BLUE)
    draw.rectangle((80, 1120, 1000, 1390), fill=(61, 63, 69), outline=(5, 10, 18), width=10)
    draw.rectangle((150, 1030, 360, 1120), fill=shorts.WHITE, outline=(5, 10, 18), width=8)
    draw.ellipse((760, 1015, 900, 1155), fill=shorts.AMBER, outline=(5, 10, 18), width=8)
    shorts._chip(draw, (540, 1285), "THE EVIDENCE", shorts.CYAN)


def _transport(canvas: Image.Image, progress: float, accent) -> None:
    draw = ImageDraw.Draw(canvas)
    q = shorts._phase(progress, 0.04, 0.88)
    draw.rounded_rectangle((95, 500, 985, 880), radius=42, fill=(183, 188, 197), outline=(5, 10, 18), width=12)
    for index in range(4):
        x = 150 + index * 205
        draw.rectangle((x, 565, x + 145, 745), fill=(34, 39, 48), outline=(5, 10, 18), width=8)
    draw.line((100, 810, 980, 810), fill=shorts.RED, width=16)
    shorts._arrow(draw, (230, 1010), (840, 1010), accent, q, 12)
    for index in range(5):
        _outlined_person(draw, 210 + index * 165, 1210, 0.46, accent=shorts.AMBER if index == 2 else (94, 101, 114))
    shorts._chip(draw, (540, 1380), "EVACUATION IN MOTION", shorts.AMBER)


def _habitat(canvas: Image.Image, progress: float, accent) -> None:
    draw = ImageDraw.Draw(canvas)
    q = shorts._phase(progress, 0.04, 0.9)
    draw.rectangle((0, 1110, 1080, 1410), fill=(164, 87, 61))
    width = round(230 + 170 * q)
    draw.pieslice((540 - width, 640, 540 + width, 1190), 180, 360, fill=(185, 222, 232), outline=(5, 10, 18), width=12)
    for index in range(3):
        x = 760 + index * 78
        draw.rectangle((x, 985, x + 52, 1110), fill=shorts.BLUE, outline=(5, 10, 18), width=7)
    _outlined_person(draw, 270, 980, 0.75, accent=shorts.AMBER)
    shorts._arrow(draw, (340, 900), (505, 790), accent, q, 10)
    shorts._chip(draw, (540, 1325), "BUILDING A NEW WORLD", shorts.GREEN)


def _council(canvas: Image.Image, progress: float, accent) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((95, 500, 985, 1335), radius=44, fill=(20, 35, 56), outline=(74, 96, 126), width=5)
    for index, x in enumerate((245, 540, 835)):
        _outlined_person(draw, x, 780, 0.72, accent=(shorts.PURPLE, shorts.CYAN, shorts.AMBER)[index])
        draw.rounded_rectangle((x - 125, 1035, x + 125, 1155), radius=24, fill=(43, 51, 66), outline=(5, 10, 18), width=7)
    shorts._text(draw, (540, 1265), "WHO GETS TO DECIDE?", 42, shorts.WHITE, bold=True, anchor="mm")


def _process(canvas: Image.Image, progress: float, accent) -> None:
    draw = ImageDraw.Draw(canvas)
    q = shorts._phase(progress, 0.05, 0.9)
    boxes = ((115, 620, 405, 850), (675, 620, 965, 850), (395, 1080, 685, 1310))
    labels = ("INPUT", "SYSTEM", "OUTCOME")
    colors = (shorts.PURPLE, shorts.CYAN, shorts.GREEN)
    for box, label, color in zip(boxes, labels, colors, strict=True):
        draw.rounded_rectangle(box, radius=36, fill=(20, 42, 69), outline=color, width=7)
        shorts._text(draw, ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2), label, 35, color, bold=True, anchor="mm")
    shorts._arrow(draw, (420, 735), (650, 735), colors[1], q, 10)
    shorts._arrow(draw, (820, 875), (590, 1060), colors[2], q, 10)
    shorts._arrow(draw, (490, 1060), (260, 875), colors[0], q, 10)


_RENDERERS = {
    "route_map": _route,
    "crowd_focus": _crowd,
    "presenter_desk": _presenter,
    "transport_scene": _transport,
    "habitat_build": _habitat,
    "council_scene": _council,
    "process_diagram": _process,
}

for template_id, renderer in _RENDERERS.items():
    shorts.RENDERERS[(exact.TECH_FAMILY_ID, template_id)] = renderer
