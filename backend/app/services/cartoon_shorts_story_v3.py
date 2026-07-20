from __future__ import annotations

"""Shorts Story v3: subject-specific Mars compositions for 9:16."""

import math
from PIL import Image, ImageDraw

from . import exact_visuals as exact
from . import native_shorts as shorts


def _ship(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, angle: float, flame: float) -> None:
    layer = Image.new("RGBA", (460, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = 260, 150
    d.polygon(((cx-150,cy),(cx-95,cy-46),(cx+82,cy-38),(cx+145,cy),(cx+82,cy+38),(cx-95,cy+46)), fill=(232,239,244), outline=(5,10,18))
    d.ellipse((cx-8,cy-25,cx+42,cy+25), fill=shorts.CYAN, outline=(5,10,18), width=5)
    length = round(72 + 54 * flame)
    d.polygon(((cx-145,cy-25),(cx-145-length,cy),(cx-145,cy+25)), fill=shorts.AMBER, outline=(5,10,18))
    d.polygon(((cx-145,cy-12),(cx-145-round(length*.63),cy),(cx-145,cy+12)), fill=(255,243,166))
    rotated = layer.rotate(-math.degrees(angle), resample=Image.Resampling.BICUBIC, expand=True)
    rotated = rotated.resize((round(rotated.width*scale), round(rotated.height*scale)), Image.Resampling.LANCZOS)
    draw._image.paste(rotated, (round(x-rotated.width/2), round(y-rotated.height/2)), rotated)


def _route(canvas: Image.Image, progress: float, accent) -> None:
    d = ImageDraw.Draw(canvas)
    p = shorts._smooth(min(1.0, progress / .92))
    d.ellipse((45,560,405,920), fill=(43,143,196), outline=(5,10,18), width=12)
    d.ellipse((720,480,1080,840), fill=(193,91,57), outline=(5,10,18), width=12)
    d.ellipse((115,650,265,770), fill=(77,151,82))
    t = p
    x = round(300 + 500*t)
    y = round(970 - 235*math.sin(math.pi*t) - 220*t)
    dx = 500
    dy = -235*math.pi*math.cos(math.pi*t) - 220
    _ship(d, x, y, .82, math.atan2(dy, dx), shorts._phase(progress,.05,.88))
    shorts._text(d,(220,1000),"EARTH",30,shorts.WHITE,bold=True,anchor="mm")
    shorts._text(d,(850,930),"MARS",30,shorts.WHITE,bold=True,anchor="mm")
    shorts._chip(d,(540,1290),"DEPARTURE → CRUISE → ARRIVAL",shorts.AMBER)


def _transport(canvas: Image.Image, progress: float, accent) -> None:
    d=ImageDraw.Draw(canvas); q=shorts._phase(progress,.04,.88)
    d.rounded_rectangle((95,490,985,1170),radius=48,fill=(33,48,66),outline=(5,10,18),width=12)
    gap=round(28+225*q); center=540
    d.rectangle((120,520,center-gap,1085),fill=(97,109,122),outline=(5,10,18),width=8)
    d.rectangle((center+gap,520,960,1085),fill=(97,109,122),outline=(5,10,18),width=8)
    d.rectangle((center-gap+12,545,center+gap-12,1060),fill=(17,29,42))
    for i,x in enumerate((190,390,690,890)):
        if abs(x-center)>gap+70:
            shorts._person(d,(x,1275),.34,shirt=shorts.AMBER if i==1 else (82,111,142),jeans=(45,58,77))
    shorts._chip(d,(540,1450),"CLEAR THE DOORWAY",shorts.CYAN)


def _habitat(canvas: Image.Image, progress: float, accent) -> None:
    d=ImageDraw.Draw(canvas); q=shorts._phase(progress,.04,.9)
    d.rectangle((0,1120,1080,1500),fill=(171,91,61))
    d.pieslice((95,520,985,1290),180,360,fill=(185,222,232),outline=(5,10,18),width=12)
    door_gap=round(20+120*q)
    d.rectangle((540-door_gap,760,540+door_gap,1160),fill=(37,53,66),outline=shorts.CYAN,width=6)
    d.rectangle((230,780,390,1040),fill=(31,52,67),outline=shorts.GREEN,width=6)
    d.ellipse((285,850,335,900),fill=shorts.GREEN)
    shorts._person(d,(220,1285),.42,shirt=shorts.AMBER,jeans=(56,65,82))
    shorts._chip(d,(540,1435),"AIR • POWER • SHELTER",shorts.GREEN)


for template, renderer in {
    "route_map": _route,
    "transport_scene": _transport,
    "habitat_build": _habitat,
}.items():
    shorts.RENDERERS[(exact.TECH_FAMILY_ID, template)] = renderer
