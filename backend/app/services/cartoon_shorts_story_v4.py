from __future__ import annotations

"""Shorts Story v4: complete Mars vertical storyboard and safe ship compositing."""

import math
from PIL import Image, ImageDraw

from . import exact_visuals as exact
from . import native_shorts as shorts


def _paste_ship(canvas: Image.Image, x: int, y: int, angle: float, flame: float) -> None:
    layer = Image.new("RGBA", (520, 340), (0,0,0,0)); d=ImageDraw.Draw(layer); cx,cy=300,170
    d.polygon(((cx-165,cy),(cx-100,cy-50),(cx+92,cy-40),(cx+155,cy),(cx+92,cy+40),(cx-100,cy+50)),fill=(232,239,244),outline=(5,10,18))
    d.ellipse((cx-4,cy-27,cx+52,cy+27),fill=shorts.CYAN,outline=(5,10,18),width=5)
    length=round(85+65*flame)
    d.polygon(((cx-160,cy-28),(cx-160-length,cy),(cx-160,cy+28)),fill=shorts.AMBER,outline=(5,10,18))
    d.polygon(((cx-160,cy-13),(cx-160-round(length*.64),cy),(cx-160,cy+13)),fill=(255,243,166))
    rotated=layer.rotate(-math.degrees(angle),resample=Image.Resampling.BICUBIC,expand=True)
    rotated=rotated.resize((round(rotated.width*.82),round(rotated.height*.82)),Image.Resampling.LANCZOS)
    canvas.paste(rotated,(round(x-rotated.width/2),round(y-rotated.height/2)),rotated)


def _route(canvas: Image.Image,p:float,accent)->None:
    d=ImageDraw.Draw(canvas); q=shorts._smooth(min(1,p/.94))
    d.ellipse((35,575,405,945),fill=(43,143,196),outline=(5,10,18),width=12)
    d.ellipse((720,470,1090,840),fill=(193,91,57),outline=(5,10,18),width=12)
    d.ellipse((112,665,270,790),fill=(77,151,82))
    x=round(292+520*q); y=round(985-245*math.sin(math.pi*q)-225*q)
    dy=-245*math.pi*math.cos(math.pi*q)-225
    _paste_ship(canvas,x,y,math.atan2(dy,520),shorts._phase(p,.04,.9))
    shorts._text(d,(210,1020),"EARTH",30,shorts.WHITE,bold=True,anchor="mm")
    shorts._text(d,(855,920),"MARS",30,shorts.WHITE,bold=True,anchor="mm")
    shorts._chip(d,(540,1325),"EARTH → MARS",shorts.AMBER)


def _presenter(canvas:Image.Image,p:float,accent)->None:
    d=ImageDraw.Draw(canvas); q=shorts._phase(p,.08,.82)
    d.rounded_rectangle((85,470,995,1390),radius=42,fill=(225,238,246),outline=(44,72,102),width=5)
    shorts._person(d,(270,1070),.68,shirt=shorts.GREEN,jeans=(46,60,82))
    d.rounded_rectangle((455,560,930,1160),radius=28,fill=(250,250,248),outline=(5,10,18),width=8)
    pts=[]
    for i in range(7):
        x=510+i*58; y=1040-round((40*i+90*math.sin(i*.7))*q); pts.append((x,y))
    if len(pts)>1: d.line(pts,fill=shorts.BLUE,width=11,joint="curve")
    for x,y in pts: d.ellipse((x-10,y-10,x+10,y+10),fill=shorts.AMBER,outline=(5,10,18),width=3)
    # One short pointer object, clearly detached from limb geometry.
    d.line((350,900,470,790),fill=(65,76,88),width=5); d.ellipse((463,783,477,797),fill=shorts.AMBER)
    shorts._chip(d,(540,1325),"EVIDENCE → PLAN",shorts.CYAN)


def _council(canvas:Image.Image,p:float,accent)->None:
    d=ImageDraw.Draw(canvas); active=min(2,int(max(0,min(.999,p))*3))
    d.rounded_rectangle((70,470,1010,1370),radius=44,fill=(20,35,56),outline=(74,96,126),width=5)
    for i,x in enumerate((235,540,845)):
        color=(shorts.PURPLE,shorts.CYAN,shorts.AMBER)[i]
        y=835-(28 if i==active else 0)
        shorts._person(d,(x,y),.55,shirt=color,jeans=(45,58,77))
        d.rounded_rectangle((x-120,1090,x+120,1195),radius=22,fill=(43,51,66),outline=color if i==active else (5,10,18),width=7)
    shorts._text(d,(540,1285),"WHO SETS THE RULES?",38,shorts.WHITE,bold=True,anchor="mm")


def _crowd(canvas:Image.Image,p:float,accent)->None:
    d=ImageDraw.Draw(canvas); q=shorts._phase(p,.15,.78)
    d.rectangle((0,1110,1080,1450),fill=(171,91,61))
    d.pieslice((100,500,980,1240),180,360,fill=(185,222,232),outline=(5,10,18),width=12)
    for i,(x,y) in enumerate(((180,1180),(380,1240),(690,1210),(900,1270))):
        shorts._person(d,(x,y),.36,shirt=(shorts.BLUE,shorts.AMBER,shorts.GREEN,shorts.PURPLE)[i],jeans=(48,60,80))
    crossing_x=round(80+900*q)
    shorts._person(d,(crossing_x,1030),.48,shirt=shorts.CYAN,jeans=(44,58,78))
    shorts._chip(d,(540,1440),"PEOPLE MAKE THE CITY",shorts.GREEN)


def _process(canvas:Image.Image,p:float,accent)->None:
    d=ImageDraw.Draw(canvas); q=shorts._phase(p,.04,.9)
    items=(("1","TRANSPORT",shorts.CYAN),("2","HABITAT",shorts.GREEN),("3","GOVERNANCE",shorts.AMBER))
    for i,(number,label,color) in enumerate(items):
        y=590+i*250; active=q>i*.25
        d.rounded_rectangle((120,y,960,y+170),radius=34,fill=(20,42,69),outline=color if active else (48,60,78),width=7)
        d.ellipse((155,y+38,249,y+132),fill=color if active else (58,68,82))
        shorts._text(d,(202,y+85),number,34,(8,16,28),bold=True,anchor="mm")
        shorts._text(d,(300,y+85),label,34,shorts.WHITE if active else shorts.MUTED,bold=True)
    shorts._chip(d,(540,1390),"ONE SYSTEM — THREE REQUIREMENTS",shorts.PURPLE)


for template,renderer in {
    "route_map":_route,
    "presenter_desk":_presenter,
    "council_scene":_council,
    "crowd_focus":_crowd,
    "process_diagram":_process,
}.items():
    shorts.RENDERERS[(exact.TECH_FAMILY_ID,template)]=renderer
