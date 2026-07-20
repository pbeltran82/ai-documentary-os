from __future__ import annotations

import hashlib
import math
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageFont

from ..models import Scene
from .finance_motion import GeneratedMotion, MotionTemplate
from .media_library import MEDIA_ROOT, project_directory, public_media_url, safe_component
from .video_format import format_exact_visual_frame, project_video_format, video_format_profile

FAMILY_ID = "cartoon_documentary"
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
OUTPUT_FPS = 30
FFMPEG_NAME = os.getenv("FFMPEG_BIN", "ffmpeg")
RENDER_TIMEOUT_SECONDS = int(os.getenv("CARTOON_DOCUMENTARY_RENDER_TIMEOUT_SECONDS", "360"))

INK = (18, 22, 29)
PAPER = (247, 247, 244)
MUTED = (158, 163, 169)
DARK_MUTED = (64, 68, 74)
BLUE = (48, 144, 214)
CYAN = (95, 202, 224)
GREEN = (79, 157, 86)
RED = (226, 68, 57)
AMBER = (247, 190, 57)
PURPLE = (139, 112, 224)
MARS = (196, 91, 54)
WHITE = (255, 255, 255)

TEMPLATES = (
    MotionTemplate("route_map", "World & Route", "Cartoon map, planet, or journey with directional motion.", tuple("world earth mars route travel migration evacuation launch journey map".split()), "A JOURNEY CHANGES EVERYTHING", "A clear route through the story"),
    MotionTemplate("crowd_focus", "Crowd & Focus", "Muted crowd with one highlighted subject or group.", tuple("crowd people society survivors community family population public stranded".split()), "ONE STORY INSIDE THE CROWD", "The human consequence comes into focus"),
    MotionTemplate("presenter_desk", "Expert at the Desk", "Editorial presenter, researcher, or official with large readable props.", tuple("expert researcher scientist report records evidence interview official explains".split()), "THE EVIDENCE ON THE TABLE", "A simple explanation of a complex system"),
    MotionTemplate("transport_scene", "Transport & Movement", "Characters boarding, traveling, evacuating, or moving through infrastructure.", tuple("transport evacuation boarding train spacecraft vehicle launch relocation migration".split()), "MOVING PEOPLE THROUGH THE SYSTEM", "The journey becomes visible"),
    MotionTemplate("habitat_build", "Build the Environment", "Robots, tools, habitats, infrastructure, or machinery assembling a new place.", tuple("habitat colony build construction robot robotic machinery infrastructure life support".split()), "BUILDING A NEW WORLD", "People, machines, and systems take shape"),
    MotionTemplate("council_scene", "Council & Choice", "Public meeting, governance, debate, or ethical decision with characters.", tuple("governance council law choice ethics power accountability decision debate authority".split()), "WHO GETS TO DECIDE?", "A public choice with human consequences"),
    MotionTemplate("process_diagram", "Objects & Process", "Large cartoon objects and arrows that explain a relationship instantly.", tuple("process system exchange comparison cause effect flow relationship tradeoff".split()), "HOW THE SYSTEM CONNECTS", "A bold visual explanation"),
)
TEMPLATE_BY_ID = {item.template_id: item for item in TEMPLATES}


def template_catalog() -> list[dict[str, object]]:
    return [{"template_id": item.template_id, "label": item.label, "description": item.description} for item in TEMPLATES]


def _context(scene: Scene, extra: str = "") -> str:
    return " ".join([scene.narration, scene.visual_intent, *scene.search_keywords, extra]).lower()


def _words(value: str) -> set[str]:
    return {"".join(char for char in token.lower() if char.isalnum()) for token in value.split()} - {""}


def suggest_template(scene: Scene, extra_context: str = "") -> tuple[MotionTemplate, float, str]:
    words = _words(_context(scene, extra_context))
    scored = [(len(words & set(item.keywords)), item) for item in TEMPLATES]
    scored.sort(key=lambda pair: (pair[0], pair[1].template_id), reverse=True)
    matched, template = scored[0]
    if matched == 0:
        index = max(0, int(scene.scene_number) - 1) % len(TEMPLATES)
        template = TEMPLATES[index]
    confidence = min(0.96, 0.55 + matched * 0.08)
    return template, round(confidence, 2), f"Matched {matched} general documentary visual signal{'s' if matched != 1 else ''}."


def storyboard_beats(template_id: str, duration_seconds: float) -> list[dict[str, object]]:
    if template_id not in TEMPLATE_BY_ID:
        raise HTTPException(status_code=422, detail="Unknown cartoon documentary template")
    duration = max(1.0, float(duration_seconds))
    return [
        {"label": "ESTABLISH", "description": "Establish the setting and focal subject.", "time_seconds": round(duration * 0.16, 3)},
        {"label": "ACTION", "description": "Show the central action or relationship.", "time_seconds": round(duration * 0.50, 3)},
        {"label": "CONSEQUENCE", "description": "Land on the human consequence or takeaway.", "time_seconds": round(duration * 0.84, 3)},
    ]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def _person(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0, *, accent: tuple[int, int, int] | None = None, pose: str = "stand") -> None:
    line = max(5, round(11 * scale))
    head_r = round(34 * scale)
    body_w = round(64 * scale)
    body_h = round(86 * scale)
    fill = accent or MUTED
    draw.ellipse((x-head_r, y-head_r, x+head_r, y+head_r), fill=fill, outline=INK, width=line)
    top = y + head_r - round(2 * scale)
    draw.rounded_rectangle((x-body_w//2, top, x+body_w//2, top+body_h), radius=round(18*scale), fill=fill if accent else DARK_MUTED, outline=INK, width=line)
    shoulder_y = top + round(24*scale)
    hand_y = shoulder_y + round(56*scale)
    if pose == "point":
        draw.line((x-body_w//2, shoulder_y, x-round(85*scale), y-round(10*scale)), fill=INK, width=line)
        draw.ellipse((x-round(92*scale), y-round(18*scale), x-round(76*scale), y-round(2*scale)), fill=fill, outline=INK, width=max(3,line//2))
    else:
        draw.line((x-body_w//2, shoulder_y, x-round(56*scale), hand_y), fill=INK, width=line)
        draw.line((x+body_w//2, shoulder_y, x+round(56*scale), hand_y), fill=INK, width=line)
    leg_y = top + body_h
    draw.line((x-round(18*scale), leg_y, x-round(20*scale), leg_y+round(55*scale)), fill=INK, width=line)
    draw.line((x+round(18*scale), leg_y, x+round(20*scale), leg_y+round(55*scale)), fill=INK, width=line)
    if accent:
        draw.ellipse((x-round(12*scale), y-round(4*scale), x-round(4*scale), y+round(4*scale)), fill=INK)
        draw.ellipse((x+round(4*scale), y-round(4*scale), x+round(12*scale), y+round(4*scale)), fill=INK)
        draw.arc((x-round(14*scale), y+round(3*scale), x+round(14*scale), y+round(24*scale)), 5, 170, fill=INK, width=max(3,round(4*scale)))


def _crowd(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, focal: bool = True) -> None:
    rows = 4
    for row in range(rows):
        count = 8 + row * 2
        base_y = round(height * (0.48 + row * 0.12))
        for index in range(count):
            x = round((index + 0.5) * width / count + (row % 2) * 18)
            scale = 0.72 + row * 0.1
            accent = None
            if focal and row == 1 and index == count // 2:
                accent = PURPLE
                y = base_y - round(35 * _ease(progress))
            else:
                y = base_y
            _person(draw, x, y, scale, accent=accent)


def _planet(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int, color: tuple[int, int, int], progress: float) -> None:
    x, y = center
    draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color, outline=INK, width=18)
    wobble = round(14 * math.sin(progress * math.pi * 2))
    draw.ellipse((x-radius//2+wobble, y-radius//3, x+radius//4+wobble, y+radius//6), fill=GREEN if color == BLUE else AMBER, outline=INK, width=8)


def _arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], progress: float) -> None:
    p = _ease(progress)
    x2 = round(start[0] + (end[0]-start[0]) * p)
    y2 = round(start[1] + (end[1]-start[1]) * p)
    draw.line((start[0], start[1], x2, y2), fill=INK, width=22)
    if p > 0.72:
        draw.polygon([(end[0], end[1]), (end[0]-48, end[1]-32), (end[0]-48, end[1]+32)], fill=INK)


def _draw_route_map(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    _planet(draw, (round(width*0.25), round(height*0.55)), round(height*0.19), BLUE, progress)
    _planet(draw, (round(width*0.76), round(height*0.55)), round(height*0.15), MARS, 1-progress)
    _arrow(draw, (round(width*0.40), round(height*0.50)), (round(width*0.62), round(height*0.50)), progress)
    if progress > 0.55:
        _arrow(draw, (round(width*0.62), round(height*0.61)), (round(width*0.40), round(height*0.61)), (progress-0.55)/0.45)


def _draw_presenter(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    for x in range(0, width, 86):
        draw.line((x, 0, x, height), fill=(205, 228, 241), width=4)
    for y in range(0, height, 86):
        draw.line((0, y, width, y), fill=(205, 228, 241), width=4)
    _person(draw, round(width*0.5), round(height*0.30), 1.65, accent=BLUE, pose="point")
    desk_y = round(height*0.70)
    draw.rectangle((0, desk_y, width, height), fill=(64,64,64), outline=INK, width=18)
    draw.rectangle((round(width*0.12), desk_y-80, round(width*0.24), desk_y), fill=WHITE, outline=INK, width=10)
    draw.ellipse((round(width*0.78), desk_y-105, round(width*0.86), desk_y-25), fill=AMBER, outline=INK, width=10)


def _draw_transport(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    train_y = round(height*0.23)
    draw.rounded_rectangle((round(width*0.08), train_y, round(width*0.92), round(height*0.58)), radius=28, fill=(186,188,192), outline=INK, width=18)
    for index in range(5):
        x1 = round(width*(0.12+index*0.16))
        draw.rectangle((x1, train_y+55, x1+round(width*0.11), train_y+185), fill=(45,47,51), outline=INK, width=10)
    draw.line((round(width*0.08), round(height*0.54), round(width*0.92), round(height*0.54)), fill=RED, width=16)
    _crowd(draw, width, height, progress, focal=True)


def _draw_habitat(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    ground = round(height*0.72)
    draw.rectangle((0, ground, width, height), fill=(192,113,76))
    dome_w = round(width*(0.18+0.18*_ease(progress)))
    dome_h = round(height*(0.12+0.16*_ease(progress)))
    cx = round(width*0.58)
    draw.pieslice((cx-dome_w, ground-dome_h*2, cx+dome_w, ground), 180, 360, fill=(185,222,232), outline=INK, width=18)
    _person(draw, round(width*0.27), round(height*0.50), 1.05, accent=AMBER, pose="point")
    for index in range(3):
        x = round(width*(0.70+index*0.07))
        draw.rectangle((x, ground-90, x+45, ground), fill=BLUE, outline=INK, width=8)


def _draw_council(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    _crowd(draw, width, height, progress, focal=False)
    table_y = round(height*0.36)
    draw.rounded_rectangle((round(width*0.20), table_y, round(width*0.80), table_y+105), radius=25, fill=(91,75,64), outline=INK, width=16)
    _person(draw, round(width*0.38), round(height*0.25), 0.95, accent=PURPLE, pose="point")
    _person(draw, round(width*0.62), round(height*0.25), 0.95, accent=AMBER)


def _draw_process(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    left = (round(width*0.25), round(height*0.55))
    right = (round(width*0.75), round(height*0.55))
    draw.rounded_rectangle((left[0]-170,left[1]-150,left[0]+170,left[1]+150), radius=36, fill=CYAN, outline=INK, width=18)
    draw.rounded_rectangle((right[0]-170,right[1]-150,right[0]+170,right[1]+150), radius=36, fill=AMBER, outline=INK, width=18)
    _arrow(draw, (left[0]+190,left[1]-35), (right[0]-190,right[1]-35), progress)
    _arrow(draw, (right[0]-190,right[1]+65), (left[0]+190,left[1]+65), progress)


def _beat_for_time(scene: Scene, time_seconds: float) -> dict[str, Any] | None:
    plan = dict(scene.animation_plan or {})
    beats = list(plan.get("visual_beats") or [])
    for beat in beats:
        start = float(beat.get("relative_start_seconds", 0.0))
        end = float(beat.get("relative_end_seconds", scene.duration_seconds))
        if start <= time_seconds < end or beat is beats[-1] and time_seconds <= end:
            return beat
    return None


def render_planned_frame(scene: Scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    beat = _beat_for_time(scene, time_seconds)
    extra = str((beat or {}).get("visual_intent", ""))
    selected = TEMPLATE_BY_ID.get(template_id or "")
    if selected is None or beat is not None:
        selected, _confidence, _reason = suggest_template(scene, extra)
    image = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    beat_start = float((beat or {}).get("relative_start_seconds", 0.0))
    beat_end = float((beat or {}).get("relative_end_seconds", duration_seconds))
    progress = _ease((time_seconds-beat_start)/max(0.001,beat_end-beat_start))
    if selected.template_id == "route_map":
        _draw_route_map(draw, OUTPUT_WIDTH, OUTPUT_HEIGHT, progress)
    elif selected.template_id == "crowd_focus":
        _crowd(draw, OUTPUT_WIDTH, OUTPUT_HEIGHT, progress, focal=True)
    elif selected.template_id == "presenter_desk":
        _draw_presenter(draw, OUTPUT_WIDTH, OUTPUT_HEIGHT, progress)
    elif selected.template_id == "transport_scene":
        _draw_transport(draw, OUTPUT_WIDTH, OUTPUT_HEIGHT, progress)
    elif selected.template_id == "habitat_build":
        _draw_habitat(draw, OUTPUT_WIDTH, OUTPUT_HEIGHT, progress)
    elif selected.template_id == "council_scene":
        _draw_council(draw, OUTPUT_WIDTH, OUTPUT_HEIGHT, progress)
    else:
        _draw_process(draw, OUTPUT_WIDTH, OUTPUT_HEIGHT, progress)
    label = extra or scene.visual_intent or selected.description
    label = " ".join(label.split())[:110]
    draw.rounded_rectangle((60, 50, 1160, 170), radius=24, fill=WHITE, outline=INK, width=8)
    draw.text((92, 74), label, font=_font(34, True), fill=INK)
    return image


def render_frame(template_id: str, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    template = TEMPLATE_BY_ID.get(template_id)
    if template is None:
        raise HTTPException(status_code=422, detail="Unknown cartoon documentary template")
    class PreviewScene:
        narration = template.description
        visual_intent = template.description
        search_keywords = list(template.keywords)
        scene_number = 1
        animation_plan = {}
        duration_seconds = duration_seconds
    return render_planned_frame(PreviewScene(), template_id, duration_seconds, time_seconds, style_id)


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _encode(scene: Scene, template: MotionTemplate, output_path: Path, video_format: str) -> None:
    ffmpeg = shutil.which(FFMPEG_NAME)
    if ffmpeg is None:
        raise HTTPException(status_code=422, detail="FFmpeg is required to encode cartoon documentary videos")
    profile = video_format_profile(video_format)
    command = [ffmpeg,"-y","-loglevel","error","-f","rawvideo","-vcodec","rawvideo","-pix_fmt","rgb24","-s",f"{profile.width}x{profile.height}","-r",str(OUTPUT_FPS),"-i","-","-an","-c:v","libx264","-preset","ultrafast","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(output_path)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    duration = max(1.0, float(scene.duration_seconds))
    try:
        assert process.stdin is not None
        for index in range(max(1, math.ceil(duration*OUTPUT_FPS))):
            time_value = min(duration, index/OUTPUT_FPS)
            frame = render_planned_frame(scene, template.template_id, duration, time_value)
            framed = format_exact_visual_frame(frame, video_format, FAMILY_ID, template.template_id, progress=time_value/max(0.001,duration), title=template.title, subtitle=template.subtitle)
            process.stdin.write(framed.tobytes())
        process.stdin.close()
        code = process.wait(timeout=RENDER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        process.kill(); process.wait()
        raise HTTPException(status_code=504, detail="Cartoon documentary render timed out") from exc
    finally:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
    if code != 0:
        detail = (process.stderr.read().decode("utf-8", errors="replace") if process.stderr else "")[-1200:]
        raise HTTPException(status_code=500, detail=f"Cartoon documentary encoder failed: {detail}")


def render_cartoon_documentary(scene: Scene, template_id: str | None = None, style_id: str | None = None) -> GeneratedMotion:
    template = TEMPLATE_BY_ID.get(template_id or "")
    if template is None:
        template, _confidence, _reason = suggest_template(scene)
    duration = round(max(1.0, float(scene.duration_seconds)), 3)
    video_format = project_video_format(scene)
    profile = video_format_profile(video_format)
    directory = project_directory(scene.project_id) / "assets"
    directory.mkdir(parents=True, exist_ok=True)
    stem = directory / f"scene-{scene.scene_number:03d}-cartoon-{safe_component(template.template_id)}-{video_format}"
    media_path = stem.with_suffix(".mp4")
    preview_path = Path(f"{stem}-poster.jpg")
    temporary_media = Path(f"{media_path}.part.mp4")
    temporary_preview = Path(f"{preview_path}.part.jpg")
    temporary_media.unlink(missing_ok=True); temporary_preview.unlink(missing_ok=True)
    try:
        _encode(scene, template, temporary_media, video_format)
        poster_time = min(max(0.8, duration*0.55), max(0.0,duration-0.03))
        frame = render_planned_frame(scene, template.template_id, duration, poster_time)
        format_exact_visual_frame(frame, video_format, FAMILY_ID, template.template_id, progress=poster_time/max(0.001,duration), title=template.title, subtitle=template.subtitle).save(temporary_preview, format="JPEG", quality=92, optimize=True)
        temporary_media.replace(media_path); temporary_preview.replace(preview_path)
    except Exception:
        temporary_media.unlink(missing_ok=True); temporary_preview.unlink(missing_ok=True)
        raise
    media_relative = media_path.resolve().relative_to(MEDIA_ROOT).as_posix()
    preview_relative = preview_path.resolve().relative_to(MEDIA_ROOT).as_posix()
    return GeneratedMotion(template=template, media_path=media_path, preview_path=preview_path, media_relative_path=media_relative, preview_relative_path=preview_relative, media_url=public_media_url(media_relative), preview_url=public_media_url(preview_relative), content_type="video/mp4", size_bytes=media_path.stat().st_size, checksum_sha256=_checksum(media_path), duration_seconds=duration, width=profile.width, height=profile.height, video_format=video_format)
