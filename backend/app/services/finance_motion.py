from __future__ import annotations

import hashlib
import math
import os
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageFont

from ..models import Scene
from .media_library import MEDIA_ROOT, project_directory, public_media_url, safe_component

OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
OUTPUT_FPS = 30
FFMPEG_NAME = os.getenv("FFMPEG_BIN", "ffmpeg")
RENDER_TIMEOUT_SECONDS = int(os.getenv("FINANCE_MOTION_RENDER_TIMEOUT_SECONDS", "240"))

BG_TOP = (8, 13, 25)
BG_BOTTOM = (25, 17, 52)
PANEL = (17, 24, 39)
PANEL_LIGHT = (30, 41, 59)
WHITE = (248, 250, 252)
MUTED = (148, 163, 184)
PURPLE = (139, 92, 246)
PURPLE_LIGHT = (196, 181, 253)
GREEN = (52, 211, 153)
GREEN_LIGHT = (167, 243, 208)
RED = (239, 68, 68)
RED_LIGHT = (252, 165, 165)
AMBER = (245, 158, 11)


@dataclass(frozen=True)
class MotionTemplate:
    template_id: str
    label: str
    description: str
    keywords: tuple[str, ...]
    title: str
    subtitle: str


@dataclass(frozen=True)
class GeneratedMotion:
    template: MotionTemplate
    media_path: Path
    preview_path: Path
    media_relative_path: str
    preview_relative_path: str
    media_url: str
    preview_url: str
    content_type: str
    size_bytes: int
    checksum_sha256: str
    duration_seconds: float


TEMPLATES = (
    MotionTemplate("paycheck_split", "Paycheck Split", "Animate 10% moving to the future before expenses.", tuple("paycheck salary paid pay yourself first 10 percent future".split()), "PAY YOURSELF FIRST", "10% moves before lifestyle can spend it"),
    MotionTemplate("expense_breakdown", "Expense Breakdown", "Visualize rent, groceries, and lifestyle draining a paycheck.", tuple("rent groceries bills expenses spending checkout lifestyle".split()), "WHERE THE PAYCHECK GOES", "Rent. Groceries. Lifestyle. Then nothing."),
    MotionTemplate("empty_balance", "Empty Balance", "Show an account falling to zero without weak stock metaphors.", tuple("empty zero nothing left balance declined wallet exhausted".split()), "NOTHING LEFT", "$0.00 after the spending cycle"),
    MotionTemplate("recurring_transfer", "Recurring Transfer", "Animate an automatic transfer into an investment account.", tuple("automatic route transfer recurring scheduled bill invest".split()), "AUTOMATE THE FIRST 10%", "Pay your future self like a required bill"),
    MotionTemplate("index_growth", "Index Fund Growth", "Show regular contributions building long-term market exposure.", tuple("s&p index fund market investing investment".split()), "LOW-COST INDEX FUND", "Small automatic deposits. Long-term market growth."),
    MotionTemplate("compound_growth", "Compound Growth", "Show contributions accelerating through compounding.", tuple("compound interest wealth growth machine future".split()), "COMPOUNDING TAKES OVER", "Time turns consistency into acceleration"),
    MotionTemplate("pay_self_comparison", "Pay Yourself First", "Compare spending-first and investing-first money flows.", tuple("opposite pay yourself first spending wealthy".split()), "TWO DIFFERENT SYSTEMS", "Spend first vs. invest first"),
    MotionTemplate("subscribe_cta", "Blueprint CTA", "End with animated Like and Subscribe actions beside the completed blueprint.", tuple("subscribe like blueprint follow channel".split()), "BUILD YOUR BLUEPRINT", "Like and subscribe for the next step"),
)
TEMPLATE_BY_ID = {item.template_id: item for item in TEMPLATES}


def _words(value: str) -> set[str]:
    return {"".join(char for char in token.lower() if char.isalnum()) for token in value.split()} - {""}


def template_catalog() -> list[dict[str, object]]:
    return [{"template_id": item.template_id, "label": item.label, "description": item.description} for item in TEMPLATES]


def suggest_template(scene: Scene) -> tuple[MotionTemplate, float, str]:
    context = " ".join([scene.narration, scene.visual_intent, *scene.search_keywords])
    words = _words(context)
    scored = [(len(words & set(item.keywords)), item) for item in TEMPLATES]
    scored.sort(key=lambda pair: (pair[0], pair[1].template_id), reverse=True)
    matched, template = scored[0]
    confidence = min(0.98, 0.50 + matched * 0.09)
    reason = f"Matched {matched} finance concept keyword{'s' if matched != 1 else ''} in the scene brief." if matched else "Selected as the safest general finance composition for this scene."
    return template, round(confidence, 2), reason


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _progress(time_seconds: float, start: float, duration: float) -> float:
    raw = _clamp((time_seconds - start) / max(duration, 0.001))
    return raw * raw * (3 - 2 * raw)


def _lerp(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress


@lru_cache(maxsize=32)
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    mac_name = "Arial Bold.ttf" if bold else "Arial.ttf"
    linux_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    candidates = [
        Path("/System/Library/Fonts/Supplemental") / mac_name,
        Path("/Library/Fonts") / mac_name,
        Path("/usr/share/fonts/truetype/dejavu") / linux_name,
        Path("/usr/share/fonts/truetype/liberation2") / ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    for name in (linux_name, mac_name):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


@lru_cache(maxsize=1)
def _background() -> Image.Image:
    gradient = Image.new("RGB", (1, OUTPUT_HEIGHT))
    gradient.putdata([
        tuple(round(_lerp(BG_TOP[channel], BG_BOTTOM[channel], y / max(1, OUTPUT_HEIGHT - 1))) for channel in range(3))
        for y in range(OUTPUT_HEIGHT)
    ])
    image = gradient.resize((OUTPUT_WIDTH, OUTPUT_HEIGHT))
    draw = ImageDraw.Draw(image)
    for x in range(0, OUTPUT_WIDTH, 160):
        draw.line((x, 0, x, OUTPUT_HEIGHT), fill=(18, 24, 38), width=1)
    for y in range(0, OUTPUT_HEIGHT, 160):
        draw.line((0, y, OUTPUT_WIDTH, y), fill=(18, 24, 38), width=1)
    return image


def _text(draw: ImageDraw.ImageDraw, position: tuple[int, int], value: str, size: int, fill: tuple[int, int, int] = WHITE, *, bold: bool = False, anchor: str | None = None) -> None:
    x, y = position
    font = _font(size, bold)
    draw.text((x + 2, y + 3), value, font=font, fill=(0, 0, 0), anchor=anchor)
    draw.text((x, y), value, font=font, fill=fill, anchor=anchor)


def _panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int] = PANEL, outline: tuple[int, int, int] | None = None) -> None:
    draw.rounded_rectangle(box, radius=28, fill=fill, outline=outline, width=2)


def _common(image: Image.Image, template: MotionTemplate) -> ImageDraw.ImageDraw:
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((110, 100, 118, 250), radius=4, fill=PURPLE)
    _text(draw, (150, 105), template.title, 68, bold=True)
    _text(draw, (150, 195), template.subtitle, 31, PURPLE_LIGHT)
    draw.line((120, 940, 1800, 940), fill=(71, 85, 105), width=2)
    _text(draw, (120, 970), "AI DOCUMENTARY OS  •  LOCAL MOTION", 21, MUTED, bold=True)
    return draw


def _paycheck(draw: ImageDraw.ImageDraw, t: float) -> None:
    life = _progress(t, 0.45, 0.8)
    future = _progress(t, 0.95, 0.65)
    _panel(draw, (170, 390, 1750, 760))
    _text(draw, (220, 435), "PAYCHECK", 38, bold=True)
    draw.rounded_rectangle((220, 560, 1700, 650), radius=18, fill=PANEL_LIGHT)
    if life:
        draw.rounded_rectangle((220, 560, 220 + round(1240 * life), 650), radius=18, fill=(71, 85, 105))
    if future:
        draw.rounded_rectangle((1480, 560, 1480 + round(220 * future), 650), radius=18, fill=PURPLE)
    _text(draw, (250, 585), "90%  LIFE", 34, bold=True)
    _text(draw, (1520, 585), "10%", 34, bold=True)
    _text(draw, (1490, 680), "FUTURE", 28, PURPLE_LIGHT, bold=True)


def _expenses(draw: ImageDraw.ImageDraw, t: float) -> None:
    _panel(draw, (150, 340, 1770, 850))
    for index, (label, percent, color) in enumerate((("RENT", 0.46, RED), ("GROCERIES", 0.28, AMBER), ("LIFESTYLE", 0.20, (100, 116, 139)))):
        y = 410 + index * 145
        p = _progress(t, 0.35 + index * 0.18, 0.75)
        _text(draw, (190, y), label, 30, bold=True)
        draw.rounded_rectangle((500, y + 5, 1580, y + 65), radius=16, fill=PANEL_LIGHT)
        width = round(1080 * percent * p)
        if width:
            draw.rounded_rectangle((500, y + 5, 500 + width, y + 65), radius=16, fill=color)
        _text(draw, (1640, y + 10), f"{round(percent * 100)}%", 28, bold=True)
    p = _progress(t, 1.5, 0.55)
    draw.line((170, 800, 170 + round(1540 * p), 800), fill=RED, width=7)
    _text(draw, (1420, 820), "$0 LEFT", 42, RED_LIGHT, bold=True)


def _empty(draw: ImageDraw.ImageDraw, t: float) -> None:
    p = _progress(t, 0.45, 1.15)
    _panel(draw, (330, 360, 1590, 770), outline=(52, 65, 85))
    _text(draw, (420, 425), "AVAILABLE BALANCE", 34, MUTED, bold=True)
    _text(draw, (420, 515), f"${max(0, round(4200 * (1 - p))):,.2f}", 112, bold=True)
    draw.rounded_rectangle((420, 680, 1480, 694), radius=7, fill=PANEL_LIGHT)
    draw.rounded_rectangle((420, 680, 420 + round(1060 * p), 694), radius=7, fill=RED)
    _text(draw, (930, 715), "PAYCHECK EXHAUSTED", 30, RED_LIGHT, bold=True)


def _transfer(draw: ImageDraw.ImageDraw, t: float) -> None:
    _panel(draw, (180, 380, 760, 730))
    _panel(draw, (1160, 380, 1740, 730), outline=(76, 55, 140))
    _text(draw, (245, 440), "CHECKING", 34, MUTED, bold=True)
    _text(draw, (1225, 440), "INDEX FUND", 34, PURPLE_LIGHT, bold=True)
    _text(draw, (365, 545), "90%", 78, bold=True)
    _text(draw, (1325, 545), "+10%", 78, GREEN_LIGHT, bold=True)
    draw.line((760, 575, 1160, 575), fill=(76, 55, 140), width=8)
    x = round(_lerp(770, 1150, _progress(t, 0.45, 1.25)))
    draw.ellipse((x - 36, 539, x + 36, 611), fill=PURPLE)
    draw.polygon(((1132, 550), (1168, 575), (1132, 600)), fill=PURPLE_LIGHT)
    _text(draw, (820, 655), "AUTOMATIC", 32, bold=True)
    _text(draw, (820, 705), "EVERY PAYDAY", 28, PURPLE_LIGHT, bold=True)


def _index(draw: ImageDraw.ImageDraw, t: float) -> None:
    _panel(draw, (150, 330, 1770, 870))
    baseline = 800
    for index, height in enumerate((110, 180, 260, 350, 470, 620)):
        actual = round(height * _progress(t, 0.30 + index * 0.10, 0.90))
        x = 260 + index * 230
        draw.rounded_rectangle((x, baseline - actual, x + 150, baseline), radius=16, fill=PURPLE)
    draw.line((230, baseline, 1660, baseline), fill=(71, 85, 105), width=3)
    _text(draw, (260, 825), "REGULAR CONTRIBUTIONS", 30, PURPLE_LIGHT, bold=True)
    _text(draw, (1400, 825), "TIME  →", 34, bold=True)


def _compound(draw: ImageDraw.ImageDraw, t: float) -> None:
    _panel(draw, (150, 330, 1770, 870))
    points: list[tuple[int, int]] = []
    for index, size in enumerate((36, 48, 64, 86, 116, 156)):
        actual = max(8, round(size * _progress(t, 0.30 + index * 0.14, 0.70)))
        x = 300 + index * 250
        y = 770 - actual
        points.append((x + actual // 2, y + actual // 2))
        draw.ellipse((x, y, x + actual, y + actual), fill=PURPLE)
        _text(draw, (x + actual // 2, 815), f"Y{index + 1}", 23, PURPLE_LIGHT, bold=True, anchor="mm")
    draw.line(points, fill=GREEN, width=8, joint="curve")
    _text(draw, (960, 410), "CONTRIBUTIONS + RETURNS + TIME", 38, bold=True, anchor="mm")


def _comparison(draw: ImageDraw.ImageDraw, t: float) -> None:
    p = _progress(t, 0.45, 0.8)
    _panel(draw, (180, 380, 880, 790), (63, 23, 32), (127, 29, 29))
    _panel(draw, (1040, 380, 1740, 790), (15, 47, 42), (6, 95, 70))
    _text(draw, (530, 445), "SPEND FIRST", 44, RED_LIGHT, bold=True, anchor="mm")
    _text(draw, (1390, 445), "PAY SELF FIRST", 44, GREEN_LIGHT, bold=True, anchor="mm")
    _text(draw, (530, 610), "$0 LEFT", 74, bold=True, anchor="mm")
    _text(draw, (1390, 610), f"{round(10 * p)}% INVESTED", 74, bold=True, anchor="mm")
    draw.line((960, 370, 960, 810), fill=(71, 85, 105), width=4)


def _subscribe(draw: ImageDraw.ImageDraw, t: float) -> None:
    pulse = 1 + 0.035 * math.sin(t * 4)
    width, height = round(1000 * pulse), round(260 * pulse)
    left, top = (OUTPUT_WIDTH - width) // 2, 420 - (height - 260) // 2
    draw.rounded_rectangle((left, top, left + width, top + height), radius=46, fill=PURPLE)
    _text(draw, (960, top + 90), "SUBSCRIBE", 82, bold=True, anchor="mm")
    _text(draw, (960, top + 190), "BUILD THE NEXT STEP", 35, (237, 233, 254), bold=True, anchor="mm")
    draw.rounded_rectangle((700, 735, 700 + round(520 * _progress(t, 0.75, 1.0)), 745), radius=5, fill=GREEN)


RENDERERS = {
    "paycheck_split": _paycheck,
    "expense_breakdown": _expenses,
    "empty_balance": _empty,
    "recurring_transfer": _transfer,
    "index_growth": _index,
    "compound_growth": _compound,
    "pay_self_comparison": _comparison,
    "subscribe_cta": _subscribe,
}


def render_frame(template_id: str, duration_seconds: float, time_seconds: float) -> Image.Image:
    template = TEMPLATE_BY_ID.get(template_id)
    if template is None:
        raise HTTPException(status_code=422, detail="Unknown finance motion template")
    image = _background().copy()
    draw = _common(image, template)
    RENDERERS[template_id](draw, time_seconds)
    fade_seconds = max(0.15, min(0.35, duration_seconds / 6))
    visibility = min(_clamp(time_seconds / fade_seconds), _clamp((duration_seconds - time_seconds) / fade_seconds))
    return Image.blend(Image.new("RGB", image.size, BG_TOP), image, visibility) if visibility < 1 else image


def ffmpeg_encoder_command(ffmpeg: str, output_path: Path) -> list[str]:
    return [
        ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24", "-s", f"{OUTPUT_WIDTH}x{OUTPUT_HEIGHT}", "-r", str(OUTPUT_FPS),
        "-i", "-", "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path),
    ]


def _compact_error(value: bytes | str | None) -> str:
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    meaningful = [line for line in lines if not line.startswith(("ffmpeg version", "built with", "configuration:", "libav"))]
    return " ".join(meaningful[-6:])[-1200:] or "Unknown encoder error"


def _encode_frames(ffmpeg: str, template: MotionTemplate, duration_seconds: float, output_path: Path) -> None:
    process = subprocess.Popen(ffmpeg_encoder_command(ffmpeg, output_path), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    frame_count = max(1, math.ceil(duration_seconds * OUTPUT_FPS))
    try:
        assert process.stdin is not None
        for index in range(frame_count):
            process.stdin.write(render_frame(template.template_id, duration_seconds, min(duration_seconds, index / OUTPUT_FPS)).tobytes())
        process.stdin.close()
        code = process.wait(timeout=RENDER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        raise HTTPException(status_code=504, detail="Finance motion render timed out") from exc
    except BrokenPipeError as exc:
        process.kill()
        process.wait()
        error = _compact_error(process.stderr.read() if process.stderr else None)
        raise HTTPException(status_code=500, detail=f"Finance motion encoder stopped unexpectedly: {error}") from exc
    finally:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
    if code != 0:
        error = _compact_error(process.stderr.read() if process.stderr else None)
        raise HTTPException(status_code=500, detail=f"Finance motion encoder failed: {error}")


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def render_finance_motion(scene: Scene, template_id: str | None = None) -> GeneratedMotion:
    template = TEMPLATE_BY_ID.get(template_id or "")
    if template is None:
        template, _confidence, _reason = suggest_template(scene)
    ffmpeg = shutil.which(FFMPEG_NAME)
    if ffmpeg is None:
        raise HTTPException(status_code=422, detail="FFmpeg is required to encode Finance Motion Studio videos.")
    duration = round(max(1.0, float(scene.duration_seconds)), 3)
    asset_directory = project_directory(scene.project_id) / "assets"
    asset_directory.mkdir(parents=True, exist_ok=True)
    stem = asset_directory / f"scene-{scene.scene_number:03d}-finance-{safe_component(template.template_id)}"
    media_path = stem.with_suffix(".mp4")
    preview_path = Path(f"{stem}-poster.jpg")
    temporary_media = Path(f"{media_path}.part.mp4")
    temporary_preview = Path(f"{preview_path}.part.jpg")
    temporary_media.unlink(missing_ok=True)
    temporary_preview.unlink(missing_ok=True)
    try:
        _encode_frames(ffmpeg, template, duration, temporary_media)
        poster_time = min(max(0.8, duration * 0.55), max(0.0, duration - 0.03))
        render_frame(template.template_id, duration, poster_time).save(temporary_preview, format="JPEG", quality=92, optimize=True)
        temporary_media.replace(media_path)
        temporary_preview.replace(preview_path)
    except HTTPException:
        temporary_media.unlink(missing_ok=True)
        temporary_preview.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temporary_media.unlink(missing_ok=True)
        temporary_preview.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Finance motion render failed: {type(exc).__name__}: {exc}") from exc
    media_relative = media_path.resolve().relative_to(MEDIA_ROOT).as_posix()
    preview_relative = preview_path.resolve().relative_to(MEDIA_ROOT).as_posix()
    return GeneratedMotion(
        template=template,
        media_path=media_path,
        preview_path=preview_path,
        media_relative_path=media_relative,
        preview_relative_path=preview_relative,
        media_url=public_media_url(media_relative),
        preview_url=public_media_url(preview_relative),
        content_type="video/mp4",
        size_bytes=media_path.stat().st_size,
        checksum_sha256=_checksum(media_path),
        duration_seconds=duration,
    )
