from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFilter, ImageFont


SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
SAFE_LEFT = 70
SAFE_RIGHT = 1010
WHITE = (248, 250, 252)
MUTED = (165, 179, 201)
PANEL = (12, 24, 43)
PANEL_2 = (18, 34, 58)
CYAN = (34, 211, 238)
TEAL = (84, 214, 194)
AMBER = (224, 174, 83)
PURPLE = (147, 103, 246)
GREEN = (62, 211, 153)
RED = (220, 53, 69)
BLUE = (48, 126, 218)

RGB = tuple[int, int, int]
Renderer = Callable[[Image.Image, float, RGB], None]


@dataclass(frozen=True)
class ShortsComposition:
    focus_label: str
    terminal_cta: bool = False


COMPOSITIONS: dict[tuple[str, str], ShortsComposition] = {
    ("finance_motion", "paycheck_split"): ShortsComposition("10% MOVES FIRST"),
    ("finance_motion", "expense_breakdown"): ShortsComposition("SEE THE EXPENSE DRAIN"),
    ("finance_motion", "empty_balance"): ShortsComposition("THE CYCLE ENDS AT ZERO"),
    ("finance_motion", "recurring_transfer"): ShortsComposition("AUTOMATION REMOVES THE DECISION"),
    ("finance_motion", "index_growth"): ShortsComposition("CONSISTENCY BUILDS EXPOSURE"),
    ("finance_motion", "compound_growth"): ShortsComposition("TIME CREATES ACCELERATION"),
    ("finance_motion", "pay_self_comparison"): ShortsComposition("INVEST FIRST CHANGES THE OUTCOME"),
    ("finance_motion", "subscribe_cta"): ShortsComposition("BLUEPRINT READY", True),
    ("character_explainer", "paycheck_arrival"): ShortsComposition("PAY THE FUTURE FIRST"),
    ("character_explainer", "spend_first"): ShortsComposition("SPENDING REACTS TO INCOME"),
    ("character_explainer", "empty_balance_reaction"): ShortsComposition("NOTHING REMAINS TO INVEST"),
    ("character_explainer", "pay_self_character_comparison"): ShortsComposition("SAME PAYCHECK. DIFFERENT SYSTEM."),
    ("character_explainer", "automatic_investing_habit"): ShortsComposition("SET THE RULE ONCE"),
    ("tech_behavior_motion", "algorithm_chose_you"): ShortsComposition("ONE OUTCOME GETS SELECTED"),
    ("tech_behavior_motion", "behavior_prediction_engine"): ShortsComposition("SIGNALS BECOME PROBABILITY"),
    ("tech_behavior_motion", "life_event_timeline"): ShortsComposition("RECORDS BECOME ESTIMATES"),
    ("tech_behavior_motion", "digital_footprint_collector"): ShortsComposition("EVERY ACTION ADDS A SIGNAL"),
    ("tech_behavior_motion", "behavioral_twin"): ShortsComposition("THE MODEL LEARNS YOUR PATTERN"),
    ("tech_behavior_motion", "machine_choice_explainer"): ShortsComposition("THE RANKING STAYS HIDDEN"),
    ("tech_behavior_motion", "machine_choice_cta"): ShortsComposition("THE MACHINE RANK", True),
}

FAMILY_COPY = {
    "finance_motion": ("MONEY SYSTEM", AMBER),
    "character_explainer": ("HUMAN STORY", TEAL),
    "tech_behavior_motion": ("TECH & BEHAVIOR", CYAN),
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _smooth(value: float) -> float:
    value = _clamp(value)
    return value * value * (3 - 2 * value)


def _phase(progress: float, start: float, end: float) -> float:
    return _smooth((_clamp(progress) - start) / max(0.001, end - start))


def _lerp(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress


@lru_cache(maxsize=64)
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        Path("/System/Library/Fonts/Supplemental") / ("Arial Bold.ttf" if bold else "Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu") / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2") / ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"),
    )
    for path in names:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, size: int, fill: RGB = WHITE, *, bold: bool = False, anchor: str | None = None) -> None:
    font = _font(size, bold)
    draw.text((xy[0] + 2, xy[1] + 3), value, font=font, fill=(0, 0, 0), anchor=anchor)
    draw.text(xy, value, font=font, fill=fill, anchor=anchor)


def _wrap(value: str, width: int, size: int, lines: int = 2) -> list[str]:
    font = _font(size, True)
    words = str(value or "").strip().split()
    result: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or font.getlength(candidate) <= width:
            current = candidate
        else:
            result.append(current)
            current = word
    if current:
        result.append(current)
    if len(result) > lines:
        result = result[:lines]
        while result[-1] and font.getlength(result[-1] + "…") > width:
            result[-1] = result[-1][:-1]
        result[-1] += "…"
    return result


@lru_cache(maxsize=4)
def _background(accent: RGB) -> Image.Image:
    gradient = Image.new("RGB", (1, SHORTS_HEIGHT))
    px = gradient.load()
    for y in range(SHORTS_HEIGHT):
        t = y / (SHORTS_HEIGHT - 1)
        px[0, y] = tuple(round(_lerp(a, b, t)) for a, b in zip((3, 7, 15), (9, 14, 27)))
    canvas = gradient.resize((SHORTS_WIDTH, SHORTS_HEIGHT))
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((-250, 250, 1320, 1660), fill=(*accent, 27))
    return Image.alpha_composite(canvas.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(210))).convert("RGB")


def _card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], *, outline: RGB | None = None, fill: RGB = PANEL, radius: int = 34, width: int = 3) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _chip(draw: ImageDraw.ImageDraw, center: tuple[int, int], label: str, color: RGB, *, scale: float = 1.0) -> None:
    width = max(150, round(_font(23, True).getlength(label)) + 58)
    height = 58
    x, y = center
    box = (round(x - width * scale / 2), round(y - height * scale / 2), round(x + width * scale / 2), round(y + height * scale / 2))
    draw.rounded_rectangle(box, radius=28, fill=(28, 31, 58), outline=color, width=3)
    _text(draw, (x, y), label, 23, color, bold=True, anchor="mm")


def _arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: RGB, progress: float = 1.0, width: int = 8) -> None:
    p = _clamp(progress)
    ex = round(_lerp(start[0], end[0], p)); ey = round(_lerp(start[1], end[1], p))
    draw.line((start[0], start[1], ex, ey), fill=color, width=width)
    if p > 0.92:
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        for offset in (-0.65, 0.65):
            draw.line((end[0], end[1], end[0] - 24 * math.cos(angle + offset), end[1] - 24 * math.sin(angle + offset)), fill=color, width=width)


def _person(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float = 1.0, *, shirt: RGB = (63, 157, 218), jeans: RGB = (42, 83, 132), mood: str = "neutral", glow: RGB | None = None) -> None:
    x, y = center
    s = scale
    if glow:
        draw.ellipse((x - 130*s, y - 270*s, x + 130*s, y + 265*s), fill=(*glow, 28) if draw.mode == "RGBA" else glow)
    skin = (239, 190, 141); ink = (8, 14, 24); hair = (38, 28, 24)
    draw.ellipse((x-70*s, y-235*s, x+70*s, y-95*s), fill=skin, outline=ink, width=max(3, round(7*s)))
    draw.pieslice((x-75*s, y-245*s, x+75*s, y-105*s), 180, 355, fill=hair)
    draw.polygon(((x-72*s,y-184*s),(x-50*s,y-224*s),(x-22*s,y-210*s),(x,y-232*s),(x+24*s,y-208*s),(x+60*s,y-218*s),(x+72*s,y-179*s)), fill=hair)
    draw.ellipse((x-31*s,y-174*s,x-18*s,y-161*s), fill=ink); draw.ellipse((x+18*s,y-174*s,x+31*s,y-161*s), fill=ink)
    if mood == "sad": draw.arc((x-27*s,y-143*s,x+27*s,y-106*s), 205, 335, fill=ink, width=max(3,round(5*s)))
    else: draw.arc((x-28*s,y-151*s,x+28*s,y-115*s), 20, 160, fill=ink, width=max(3,round(5*s)))
    # tapered shirt and clear waist: no Big Mac torso
    torso = ((x-72*s,y-98*s),(x+72*s,y-98*s),(x+52*s,y+75*s),(x-52*s,y+75*s))
    draw.polygon(torso, fill=shirt, outline=ink)
    draw.line((x-68*s,y-84*s,x-112*s,y+15*s,x-105*s,y+105*s), fill=skin, width=max(8,round(22*s)))
    draw.line((x+68*s,y-84*s,x+112*s,y+15*s,x+105*s,y+105*s), fill=skin, width=max(8,round(22*s)))
    draw.ellipse((x-120*s,y+86*s,x-91*s,y+119*s), fill=skin); draw.ellipse((x+91*s,y+86*s,x+120*s,y+119*s), fill=skin)
    draw.polygon(((x-50*s,y+72*s),(x-4*s,y+72*s),(x-20*s,y+235*s),(x-85*s,y+235*s)), fill=jeans, outline=ink)
    draw.polygon(((x+4*s,y+72*s),(x+50*s,y+72*s),(x+85*s,y+235*s),(x+20*s,y+235*s)), fill=jeans, outline=ink)
    draw.rounded_rectangle((x-100*s,y+222*s,x-18*s,y+252*s), radius=12, fill=(20,27,38)); draw.rounded_rectangle((x+18*s,y+222*s,x+100*s,y+252*s), radius=12, fill=(20,27,38))


def _money(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label: str, color: RGB = GREEN) -> None:
    draw.rounded_rectangle(box, radius=22, fill=(228, 245, 237), outline=color, width=4)
    x1,y1,x2,y2 = box
    draw.rectangle((x1+24,y1+22,x1+70,y1+62), fill=(155,227,202))
    _text(draw, ((x1+x2)//2, (y1+y2)//2), label, 34, (15,48,39), bold=True, anchor="mm")


def _bar(draw: ImageDraw.ImageDraw, box: tuple[int,int,int,int], progress: float, color: RGB, label: str | None = None) -> None:
    x1,y1,x2,y2 = box
    draw.rounded_rectangle(box, radius=(y2-y1)//2, fill=(39,53,79))
    fill_right = round(x1 + (x2-x1)*_clamp(progress))
    if fill_right > x1: draw.rounded_rectangle((x1,y1,fill_right,y2), radius=(y2-y1)//2, fill=color)
    if label: _text(draw, (x1,y1-35), label, 22, MUTED, bold=True)


def _header(canvas: Image.Image, family_id: str, title: str, subtitle: str, accent: RGB) -> None:
    draw = ImageDraw.Draw(canvas)
    family = FAMILY_COPY.get(family_id, ("DOCUMENTARY VISUAL", accent))[0]
    w = max(230, round(_font(21, True).getlength(family)) + 52)
    draw.rounded_rectangle((SAFE_LEFT, 68, SAFE_LEFT+w, 120), radius=26, fill=(18,28,47))
    _text(draw, (SAFE_LEFT+w//2,94), family, 21, accent, bold=True, anchor="mm")
    clean = str(title or "DOCUMENTARY VISUAL").upper()
    size = 59 if len(clean) <= 32 else 51 if len(clean) <= 46 else 45
    y = 151
    for line in _wrap(clean, SAFE_RIGHT-SAFE_LEFT, size):
        _text(draw, (SAFE_LEFT,y), line, size, WHITE, bold=True); y += size+9
    for line in _wrap(str(subtitle or "One clear idea, designed for vertical viewing."), SAFE_RIGHT-SAFE_LEFT, 27):
        _text(draw, (SAFE_LEFT,y+4), line, 27, MUTED); y += 37
    _bar(draw, (SAFE_LEFT, 342, SAFE_RIGHT, 350), 0.34, accent)


def _footer(canvas: Image.Image, label: str, accent: RGB) -> None:
    draw = ImageDraw.Draw(canvas)
    _text(draw, (SAFE_LEFT,1543), "KEY IDEA", 21, accent, bold=True)
    y=1581
    for line in _wrap(label.upper(), SAFE_RIGHT-SAFE_LEFT, 45):
        _text(draw,(SAFE_LEFT,y),line,45,WHITE,bold=True); y+=55
    _text(draw,(SAFE_LEFT,1774),"AI DOCUMENTARY OS",19,(91,106,130),bold=True)


def _cta(canvas: Image.Image, progress: float) -> None:
    draw=ImageDraw.Draw(canvas); y=1450
    _text(draw,(SAFE_LEFT,1325),"KEEP THE STORY MOVING",28,MUTED,bold=True)
    p=_phase(progress,0.02,0.14)
    draw.rounded_rectangle((SAFE_LEFT,y,650,y+92),radius=22,fill=RED)
    draw.polygon(((118,y+26),(118,y+66),(151,y+46)),fill=WHITE)
    _text(draw,(390,y+46),"SUBSCRIBE",36,WHITE,bold=True,anchor="mm")
    draw.rounded_rectangle((680,y,SAFE_RIGHT,y+92),radius=46,fill=BLUE)
    _text(draw,(845,y+46),"LIKE  👍",32,WHITE,bold=True,anchor="mm")
    if p < 1:
        veil=Image.new("RGB",canvas.size,(3,7,15)); canvas.paste(Image.blend(veil,canvas,p))
    _text(draw,(SAFE_LEFT,1590),"THANKS FOR WATCHING",23,(122,138,162),bold=True)


# ---- Native semantic renderers -------------------------------------------------

def _algorithm(canvas: Image.Image, p: float, accent: RGB) -> None:
    d=ImageDraw.Draw(canvas); a=_phase(p,0,.32); b=_phase(p,.25,.68); c=_phase(p,.58,.92)
    _card(d,(100,430,980,1390),outline=(37,75,111),fill=(7,18,35))
    _text(d,(540,480),"RECOMMENDATION FIELD",25,MUTED,bold=True,anchor="mm")
    for i,(x,y) in enumerate(((200,610),(430,565),(700,610),(860,540),(250,850),(520,790),(820,870),(360,1100),(710,1080))):
        r=26+((i*7)%18); d.ellipse((x-r,y-r,x+r,y+r),fill=(34,93,152),outline=CYAN,width=2)
        if a>.2: _arrow(d,(x,y),(540,965),CYAN,min(1,a+.08*i),3)
    size=round(145+25*c); d.rounded_rectangle((540-size,965-size,540+size,965+size),radius=42,fill=(18,76,139),outline=CYAN,width=7)
    d.polygon(((505,900),(505,1030),(610,965)),fill=WHITE)
    if b>.2: _chip(d,(540,1245),"SELECTED FOR YOU",GREEN,scale=.9+.1*c)


def _prediction(canvas: Image.Image,p:float,accent:RGB)->None:
    d=ImageDraw.Draw(canvas); a=_phase(p,0,.35); b=_phase(p,.28,.7); c=_phase(p,.62,.95)
    _card(d,(90,440,990,1395),outline=(40,68,104),fill=(7,18,35))
    labels=("SCROLL","PAUSE","SEARCH","DRAFT")
    for i,label in enumerate(labels):
        y=600+i*145; _chip(d,(235,y),label,PURPLE)
        _arrow(d,(350,y),(500,845),PURPLE,a,6)
    d.ellipse((445,735,655,945),fill=(26,54,91),outline=CYAN,width=7); _text(d,(550,840),"MODEL",29,CYAN,bold=True,anchor="mm")
    _arrow(d,(655,840),(765,840),CYAN,b,8)
    d.arc((700,650,945,895),180,round(180+180*c),fill=GREEN,width=28)
    _text(d,(823,825),f"{round(82*c)}%",52,WHITE,bold=True,anchor="mm")
    _text(d,(823,930),"NEXT ACTION",23,MUTED,bold=True,anchor="mm")
    _bar(d,(700,1030,935,1060),c,GREEN,"CONFIDENCE")


def _timeline(canvas:Image.Image,p:float,accent:RGB)->None:
    d=ImageDraw.Draw(canvas); q=_phase(p,.05,.9)
    _card(d,(100,430,980,1400),outline=(38,69,105),fill=(7,18,35))
    x=330; d.line((x,540,x,1260),fill=(41,61,91),width=12); d.line((x,540,x,round(540+720*q)),fill=CYAN,width=12)
    events=((570,"PAST RECORDS","KNOWN",CYAN),(790,"HEALTH","ESTIMATE",PURPLE),(1010,"CAREER","ESTIMATE",PURPLE),(1230,"LONGEVITY","RANGE",AMBER))
    for i,(y,label,kind,color) in enumerate(events):
        active=q>i*.23; fill=color if active else (47,60,80)
        d.ellipse((x-25,y-25,x+25,y+25),fill=fill)
        _text(d,(405,y-22),label,31,WHITE if active else MUTED,bold=True)
        _text(d,(405,y+20),kind,21,color if active else (70,84,105),bold=True)
        if i: _bar(d,(690,y-8,900,y+12),min(1,max(0,q-i*.18)),color)
    _text(d,(540,1330),"THE FUTURE IS A PROBABILITY — NOT A FACT",22,MUTED,bold=True,anchor="mm")


def _footprint(canvas:Image.Image,p:float,accent:RGB)->None:
    d=ImageDraw.Draw(canvas); q=_phase(p,0,.85)
    _card(d,(90,430,990,1400),outline=(34,75,110),fill=(7,18,35))
    labels=("SCROLL","PAUSE","SEARCH","DRAFT","CLICK","WATCH")
    for i,label in enumerate(labels):
        x=210 if i%2==0 else 370; y=560+(i//2)*160
        _chip(d,(x,y),label,PURPLE)
        _arrow(d,(x+105,y),(650,930),PURPLE,min(1,q*1.5-i*.1),5)
    d.rounded_rectangle((610,620,910,1180),radius=32,fill=(19,43,76),outline=CYAN,width=5)
    _text(d,(760,675),"BEHAVIORAL",24,CYAN,bold=True,anchor="mm"); _text(d,(760,712),"RECORD",24,CYAN,bold=True,anchor="mm")
    bars=round(9*q)
    for i in range(bars):
        w=120+(i*37)%130; color=CYAN if i%2==0 else PURPLE
        d.rounded_rectangle((650,770+i*38,650+w,792+i*38),radius=10,fill=color)
    _text(d,(760,1150),f"{round(10000*q):,}",45,WHITE,bold=True,anchor="mm")


def _twin(canvas:Image.Image,p:float,accent:RGB)->None:
    d=ImageDraw.Draw(canvas); q=_phase(p,.1,.8)
    _card(d,(90,430,990,1400),outline=(34,75,110),fill=(7,18,35))
    _person(d,(300,930),.82,shirt=(57,149,215),jeans=(40,78,126))
    for i,y in enumerate((700,820,940,1060)):
        _arrow(d,(430,y),(650,y),CYAN,min(1,q*1.5-i*.1),5)
        if q>.25+i*.08: d.ellipse((510,y-8,526,y+8),fill=PURPLE)
    _person(d,(770,930),.82,shirt=(25,197,213),jeans=(34,84,126))
    if q>.65: d.rounded_rectangle((645,1230,895,1300),radius=34,fill=(17,67,81),outline=CYAN,width=3); _text(d,(770,1265),"NEXT: WATCH",24,CYAN,bold=True,anchor="mm")
    _text(d,(300,1265),"YOU",24,WHITE,bold=True,anchor="mm"); _text(d,(770,1350),"BEHAVIORAL TWIN",24,CYAN,bold=True,anchor="mm")


def _machine_choice(canvas:Image.Image,p:float,accent:RGB)->None:
    d=ImageDraw.Draw(canvas); q=_phase(p,.05,.9)
    _card(d,(90,430,990,1400),outline=(34,75,110),fill=(7,18,35))
    d.rounded_rectangle((130,560,410,1180),radius=34,fill=(18,37,64)); d.polygon(((230,780),(230,940),(350,860)),fill=WHITE); _text(d,(270,1080),"YOU PRESSED PLAY",21,MUTED,bold=True,anchor="mm")
    for i,(label,score) in enumerate((("WATCH TIME",.88),("RELEVANCE",.74),("TIMING",.92),("HISTORY",.63))):
        y=610+i*155; _bar(d,(520,y,915,y+34),score*q,GREEN if i==2 else PURPLE,label)
        _text(d,(915,y-35),f"{round(score*q*100)}",23,WHITE,bold=True,anchor="ra")
    if q>.75: _chip(d,(720,1260),"RANKED #1",GREEN)


def _paycheck(canvas:Image.Image,p:float,accent:RGB,*,person:bool=False)->None:
    d=ImageDraw.Draw(canvas); a=_phase(p,0,.35); b=_phase(p,.25,.72)
    _card(d,(90,450,990,1390),outline=(86,69,38),fill=(20,20,27))
    if person: _person(d,(280,1000),.72)
    _money(d,(130 if not person else 110,570,480 if not person else 450,710),"$5,000")
    _arrow(d,(470,640),(720,640),AMBER,a,8); _chip(d,(760,640),"FIRST 10%",AMBER)
    _arrow(d,(760,680),(760,960),GREEN,b,8)
    d.rounded_rectangle((570,980,930,1220),radius=34,fill=(18,55,49),outline=GREEN,width=5)
    _text(d,(750,1040),"FUTURE FUND",27,GREEN,bold=True,anchor="mm"); _text(d,(750,1135),f"${round(500*b):,}",58,WHITE,bold=True,anchor="mm")


def _expenses(canvas:Image.Image,p:float,accent:RGB,*,person:bool=False)->None:
    d=ImageDraw.Draw(canvas); q=_phase(p,.02,.9)
    _card(d,(90,430,990,1400),outline=(86,69,38),fill=(20,20,27))
    if person: _person(d,(250,1050),.65,mood="sad")
    left=420 if person else 160; _text(d,(left,545),"PAYCHECK",23,MUTED,bold=True); _bar(d,(left,585,910,635),1-q,AMBER)
    for i,(label,amount,color) in enumerate((("RENT","− $2,000",RED),("GROCERIES","− $900",PURPLE),("LIFESTYLE","− $2,100",CYAN))):
        y=750+i*150; _chip(d,(left+125,y),label,color); _text(d,(895,y),amount,29,color,bold=True,anchor="ra")
    _text(d,(540,1260),f"BALANCE  ${round(5000*(1-q)):,}",42,WHITE,bold=True,anchor="mm")


def _zero(canvas:Image.Image,p:float,accent:RGB,*,person:bool=False)->None:
    d=ImageDraw.Draw(canvas); q=_phase(p,.08,.75)
    _card(d,(90,430,990,1400),outline=(86,69,38),fill=(20,20,27))
    if person: _person(d,(290,1030),.72,mood="sad")
    cx=700 if person else 540
    _text(d,(cx,620),"AVAILABLE BALANCE",25,MUTED,bold=True,anchor="mm")
    _text(d,(cx,790),f"${round(1200*(1-q)):,}",100,WHITE,bold=True,anchor="mm")
    if q>.7:
        d.rounded_rectangle((cx-220,970,cx+220,1070),radius=24,fill=RED); _text(d,(cx,1020),"PAYMENT DECLINED",31,WHITE,bold=True,anchor="mm")


def _transfer(canvas:Image.Image,p:float,accent:RGB,*,person:bool=False)->None:
    d=ImageDraw.Draw(canvas); q=_phase(p,.04,.88)
    _card(d,(90,430,990,1400),outline=(86,69,38),fill=(20,20,27))
    if person: _person(d,(210,1050),.6)
    left=370 if person else 180
    _money(d,(left,590,left+280,710),"PAYDAY")
    _arrow(d,(left+140,730),(left+140,1000),GREEN,q,9)
    d.rounded_rectangle((left,1010,left+500,1190),radius=32,fill=(18,55,49),outline=GREEN,width=5)
    _text(d,(left+250,1070),"AUTO-TRANSFER",26,GREEN,bold=True,anchor="mm"); _text(d,(left+250,1130),"CONFIRMED  ✓",36,WHITE,bold=True,anchor="mm")
    if person: _text(d,(210,1340),"NO DAILY DECISION",20,MUTED,bold=True,anchor="mm")


def _growth(canvas:Image.Image,p:float,accent:RGB,*,compound:bool=False)->None:
    d=ImageDraw.Draw(canvas); q=_phase(p,.03,.92)
    _card(d,(90,430,990,1400),outline=(86,69,38),fill=(20,20,27))
    x0,y0=170,1220; d.line((x0,570,x0,y0,900,y0),fill=(75,78,91),width=4)
    pts=[]
    for i in range(81):
        t=i/80; x=x0+700*t; factor=t*t if compound else .25*t+.75*t*t; y=y0-530*factor; pts.append((x,y))
    visible=pts[:max(2,round(len(pts)*q))]; d.line(visible,fill=GREEN,width=12,joint="curve")
    for i in range(7):
        x=x0+100+i*95
        if q>i/8: d.ellipse((x-12,y0-12,x+12,y0+12),fill=AMBER)
    _text(d,(540,520),"CONTRIBUTIONS + TIME",28,MUTED,bold=True,anchor="mm")
    _text(d,(750,800 if compound else 900),"COMPOUNDING" if compound else "MARKET EXPOSURE",27,GREEN,bold=True,anchor="mm")


def _comparison(canvas:Image.Image,p:float,accent:RGB,*,characters:bool=False)->None:
    d=ImageDraw.Draw(canvas); q=_phase(p,.08,.85)
    _card(d,(80,430,1000,1400),outline=(86,69,38),fill=(20,20,27)); d.line((540,500,540,1310),fill=(70,65,61),width=3)
    _text(d,(310,530),"SPEND FIRST",27,RED,bold=True,anchor="mm"); _text(d,(770,530),"INVEST FIRST",27,GREEN,bold=True,anchor="mm")
    if characters:
        _person(d,(310,930),.55,mood="sad",shirt=(207,91,86)); _person(d,(770,930),.55,shirt=(55,171,137))
    else:
        _bar(d,(150,700,470,745),1-q,RED,"BALANCE"); _bar(d,(610,700,930,745),q,GREEN,"FUTURE FUND")
    _text(d,(310,1270),"$0 LEFT",42,RED,bold=True,anchor="mm"); _text(d,(770,1270),f"${round(5000*q):,} GROWING",36,GREEN,bold=True,anchor="mm")


def _finance_cta(canvas:Image.Image,p:float,accent:RGB)->None:
    d=ImageDraw.Draw(canvas); q=_phase(p,.05,.82); _card(d,(95,450,985,1240),outline=AMBER,fill=(20,20,27))
    for i,(n,label,color) in enumerate((("1","MOVE 10% FIRST",AMBER),("2","AUTOMATE THE TRANSFER",GREEN),("3","LET TIME COMPOUND",CYAN))):
        y=590+i*190; active=q >= i*.28
        resolved=color if active else (57,63,73)
        d.ellipse((155,y-43,241,y+43),fill=resolved); _text(d,(198,y),n,30,(12,18,27),bold=True,anchor="mm"); _text(d,(285,y),label,30,WHITE if active else (88,95,108),bold=True)


def _generic(canvas:Image.Image,p:float,accent:RGB)->None:
    d=ImageDraw.Draw(canvas); q=_phase(p,.05,.9); _card(d,(100,440,980,1400),outline=accent,fill=(8,19,35))
    for i in range(5):
        y=590+i*150; _bar(d,(180,y,900,y+34),min(1,q+i*.1),accent)
    d.ellipse((410,770,670,1030),fill=(22,58,83),outline=accent,width=8); _text(d,(540,900),"ONE IDEA",33,accent,bold=True,anchor="mm")


RENDERERS: dict[tuple[str,str],Renderer] = {
    ("tech_behavior_motion","algorithm_chose_you"):_algorithm,
    ("tech_behavior_motion","behavior_prediction_engine"):_prediction,
    ("tech_behavior_motion","life_event_timeline"):_timeline,
    ("tech_behavior_motion","digital_footprint_collector"):_footprint,
    ("tech_behavior_motion","behavioral_twin"):_twin,
    ("tech_behavior_motion","machine_choice_explainer"):_machine_choice,
    ("tech_behavior_motion","machine_choice_cta"):_machine_choice,
    ("finance_motion","paycheck_split"):_paycheck,
    ("finance_motion","expense_breakdown"):_expenses,
    ("finance_motion","empty_balance"):_zero,
    ("finance_motion","recurring_transfer"):_transfer,
    ("finance_motion","index_growth"):_growth,
    ("finance_motion","compound_growth"):lambda c,p,a:_growth(c,p,a,compound=True),
    ("finance_motion","pay_self_comparison"):_comparison,
    ("finance_motion","subscribe_cta"):_finance_cta,
    ("character_explainer","paycheck_arrival"):lambda c,p,a:_paycheck(c,p,a,person=True),
    ("character_explainer","spend_first"):lambda c,p,a:_expenses(c,p,a,person=True),
    ("character_explainer","empty_balance_reaction"):lambda c,p,a:_zero(c,p,a,person=True),
    ("character_explainer","pay_self_character_comparison"):lambda c,p,a:_comparison(c,p,a,characters=True),
    ("character_explainer","automatic_investing_habit"):lambda c,p,a:_transfer(c,p,a,person=True),
}


def compose_native_shorts(source: Image.Image, *, family_id: str | None, template_id: str | None, progress: float = .5, title: str | None = None, subtitle: str | None = None) -> Image.Image:
    """Render a semantic 9:16 scene without cropping or keying landscape art.

    Known templates use only native vector shapes and native typography. The
    source argument remains for API compatibility and for the untouched 16:9
    renderer, but no source pixels enter a Shorts frame.
    """
    del source
    family = family_id or ""
    template = template_id or ""
    composition = COMPOSITIONS.get((family, template), ShortsComposition("ONE CLEAR DOCUMENTARY IDEA"))
    accent = FAMILY_COPY.get(family, ("DOCUMENTARY VISUAL", TEAL))[1]
    canvas = _background(accent).copy()
    _header(canvas, family, title or template.replace("_"," "), subtitle or "One clear idea, designed for vertical viewing.", accent)
    RENDERERS.get((family, template), _generic)(canvas, _clamp(progress), accent)
    if composition.terminal_cta:
        _cta(canvas, progress)
    else:
        _footer(canvas, composition.focus_label, accent)
    visibility=min(_smooth(_clamp(progress)/.035),_smooth((1-_clamp(progress))/.035))
    if visibility<1: return Image.blend(Image.new("RGB",canvas.size,(3,7,15)),canvas,visibility)
    return canvas
