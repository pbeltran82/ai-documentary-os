from __future__ import annotations

import math
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from ..models import Scene
from . import finance_motion as engine
from . import finance_motion_polish as polish
from .media_library import MEDIA_ROOT, project_directory, public_media_url, safe_component


@dataclass(frozen=True)
class MotionStyle:
    style_id: str
    label: str
    description: str
    swatches: tuple[str, ...]


@dataclass(frozen=True)
class ArtDirectedMotion:
    template: engine.MotionTemplate
    style: MotionStyle
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


STYLES = (
    MotionStyle(
        "clean_infographic",
        "Clean Infographic",
        "Crisp hierarchy, cool neutrals, precise charts, and minimal decoration.",
        ("#f8fafc", "#38bdf8", "#10b981", "#334155"),
    ),
    MotionStyle(
        "premium_motion",
        "Premium Motion",
        "Deeper gradients, luminous accents, layered depth, and richer cinematic energy.",
        ("#8b5cf6", "#22d3ee", "#34d399", "#111827"),
    ),
    MotionStyle(
        "editorial_documentary",
        "Editorial Documentary",
        "Restrained contrast, warm highlights, subtle grain, and a serious documentary finish.",
        ("#d6a85f", "#334155", "#0f172a", "#e2e8f0"),
    ),
)
STYLE_BY_ID = {style.style_id: style for style in STYLES}
DEFAULT_STYLE_ID = "premium_motion"

TEMPLATES = polish.TEMPLATES
OUTPUT_WIDTH = polish.OUTPUT_WIDTH
OUTPUT_HEIGHT = polish.OUTPUT_HEIGHT
template_catalog = polish.template_catalog
suggest_template = polish.suggest_template
ffmpeg_encoder_command = polish.ffmpeg_encoder_command


def style_catalog() -> list[dict[str, object]]:
    return [
        {
            "style_id": style.style_id,
            "label": style.label,
            "description": style.description,
            "swatches": list(style.swatches),
        }
        for style in STYLES
    ]


def _resolve_style(style_id: str | None) -> MotionStyle:
    resolved = STYLE_BY_ID.get(style_id or DEFAULT_STYLE_ID)
    if resolved is None:
        raise HTTPException(status_code=422, detail="Unknown finance motion style")
    return resolved


def _clamp_byte(value: float) -> int:
    return max(0, min(255, round(value)))


def _tint(
    image: Image.Image,
    color: tuple[int, int, int],
    strength: float,
) -> Image.Image:
    overlay = Image.new("RGB", image.size, color)
    return Image.blend(image, overlay, max(0.0, min(1.0, strength)))


def _overlay_from_pixels(
    pixels: list[tuple[int, int, int, int]],
    width: int,
    height: int,
) -> Image.Image:
    image = Image.new("RGBA", (width, height))
    image.putdata(pixels)
    return image.resize((OUTPUT_WIDTH, OUTPUT_HEIGHT), Image.Resampling.BICUBIC)


@lru_cache(maxsize=8)
def _premium_static_overlay() -> Image.Image:
    small_width, small_height = 240, 135
    pixels: list[tuple[int, int, int, int]] = []
    glows = (
        (0.18, 0.10, 0.48, (124, 58, 237), 105),
        (0.86, 0.18, 0.42, (34, 211, 238), 72),
        (0.72, 0.82, 0.38, (52, 211, 153), 48),
    )
    for y in range(small_height):
        ny = y / max(1, small_height - 1)
        for x in range(small_width):
            nx = x / max(1, small_width - 1)
            red = green = blue = alpha = 0.0
            for cx, cy, radius, color, maximum_alpha in glows:
                distance = math.hypot(nx - cx, ny - cy)
                influence = max(0.0, 1.0 - distance / radius) ** 2
                red += color[0] * influence
                green += color[1] * influence
                blue += color[2] * influence
                alpha += maximum_alpha * influence
            pixels.append(
                (
                    _clamp_byte(red),
                    _clamp_byte(green),
                    _clamp_byte(blue),
                    _clamp_byte(alpha),
                )
            )
    return _overlay_from_pixels(pixels, small_width, small_height)


@lru_cache(maxsize=8)
def _clean_static_overlay() -> Image.Image:
    overlay = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, OUTPUT_WIDTH, OUTPUT_HEIGHT), fill=(5, 23, 42, 18))
    for x in range(0, OUTPUT_WIDTH, 240):
        draw.line((x, 280, x, 900), fill=(56, 189, 248, 14), width=1)
    for y in range(320, 901, 145):
        draw.line((80, y, OUTPUT_WIDTH - 80, y), fill=(148, 163, 184, 12), width=1)
    draw.rounded_rectangle((86, 82, 98, 270), radius=6, fill=(56, 189, 248, 120))
    return overlay


@lru_cache(maxsize=8)
def _editorial_static_overlay() -> Image.Image:
    small_width, small_height = 240, 135
    pixels: list[tuple[int, int, int, int]] = []
    for y in range(small_height):
        ny = y / max(1, small_height - 1)
        for x in range(small_width):
            nx = x / max(1, small_width - 1)
            edge = min(nx, ny, 1 - nx, 1 - ny)
            vignette = max(0.0, 1.0 - edge / 0.26)
            warm = max(0.0, 1.0 - math.hypot(nx - 0.18, ny - 0.22) / 0.48)
            grain = ((x * 37 + y * 61) % 17) / 16
            pixels.append(
                (
                    _clamp_byte(182 * warm),
                    _clamp_byte(116 * warm),
                    _clamp_byte(45 * warm),
                    _clamp_byte(22 + 52 * vignette + 10 * grain),
                )
            )
    return _overlay_from_pixels(pixels, small_width, small_height)


def _apply_clean(image: Image.Image, t: float) -> Image.Image:
    image = ImageEnhance.Contrast(image).enhance(1.08)
    image = ImageEnhance.Color(image).enhance(0.92)
    frame = Image.alpha_composite(image.convert("RGBA"), _clean_static_overlay())
    draw = ImageDraw.Draw(frame)
    progress = (0.5 + 0.5 * math.sin(t * 1.8)) * 0.65 + 0.2
    draw.rounded_rectangle(
        (130, 884, 130 + round(640 * progress), 892),
        radius=4,
        fill=(56, 189, 248, 150),
    )
    for index in range(4):
        x = 1620 + index * 42
        draw.ellipse((x, 120, x + 12, 132), fill=(52, 211, 153, 125))
    return frame.convert("RGB")


def _apply_premium(image: Image.Image, t: float) -> Image.Image:
    image = ImageEnhance.Color(image).enhance(1.22)
    image = ImageEnhance.Contrast(image).enhance(1.07)
    frame = Image.alpha_composite(image.convert("RGBA"), _premium_static_overlay())
    glow_layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow_layer)
    for index, (base_x, base_y, color) in enumerate(
        (
            (1540, 280, (34, 211, 238, 90)),
            (360, 760, (139, 92, 246, 105)),
            (1390, 780, (52, 211, 153, 72)),
        )
    ):
        phase = t * (0.8 + index * 0.17) + index * 1.7
        x = base_x + round(70 * math.sin(phase))
        y = base_y + round(38 * math.cos(phase * 0.9))
        radius = 46 + round(12 * math.sin(phase * 1.3))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(24))
    frame = Image.alpha_composite(frame, glow_layer)
    beam = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    beam_draw = ImageDraw.Draw(beam)
    offset = round(120 * math.sin(t * 0.55))
    beam_draw.polygon(
        ((1180 + offset, 0), (1490 + offset, 0), (920 + offset, 1080), (650 + offset, 1080)),
        fill=(124, 58, 237, 18),
    )
    return Image.alpha_composite(frame, beam.filter(ImageFilter.GaussianBlur(10))).convert("RGB")


def _apply_editorial(image: Image.Image, t: float) -> Image.Image:
    image = ImageEnhance.Color(image).enhance(0.68)
    image = ImageEnhance.Contrast(image).enhance(1.12)
    image = _tint(image, (18, 24, 38), 0.08)
    frame = Image.alpha_composite(image.convert("RGBA"), _editorial_static_overlay())
    draw = ImageDraw.Draw(frame)
    draw.rectangle((52, 52, OUTPUT_WIDTH - 52, OUTPUT_HEIGHT - 52), outline=(226, 232, 240, 24), width=2)
    light_x = round(160 + (OUTPUT_WIDTH - 320) * ((math.sin(t * 0.28) + 1) / 2))
    draw.rectangle((light_x, 70, light_x + 2, 900), fill=(214, 168, 95, 42))
    for y in range(330, 900, 118):
        alpha = 12 + ((y * 13) % 9)
        draw.line((110, y, OUTPUT_WIDTH - 110, y), fill=(226, 232, 240, alpha), width=1)
    return frame.convert("RGB")


STYLE_RENDERERS = {
    "clean_infographic": _apply_clean,
    "premium_motion": _apply_premium,
    "editorial_documentary": _apply_editorial,
}


def render_frame(
    template_id: str,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    style = _resolve_style(style_id)
    frame = polish.render_frame(template_id, duration_seconds, time_seconds)
    styled = STYLE_RENDERERS[style.style_id](frame, time_seconds)
    fade_seconds = max(0.15, min(0.35, duration_seconds / 6))
    visibility = min(
        engine._clamp(time_seconds / fade_seconds),
        engine._clamp((duration_seconds - time_seconds) / fade_seconds),
    )
    if visibility < 1:
        return Image.blend(
            Image.new("RGB", styled.size, engine.BG_TOP),
            styled,
            visibility,
        )
    return styled


def styled_background(
    style_id: str,
    time_seconds: float = 2.0,
) -> Image.Image:
    style = _resolve_style(style_id)
    return STYLE_RENDERERS[style.style_id](polish._background().copy(), time_seconds)


def _encode_frames(
    ffmpeg: str,
    template: engine.MotionTemplate,
    style: MotionStyle,
    duration_seconds: float,
    output_path: Path,
) -> None:
    process = subprocess.Popen(
        ffmpeg_encoder_command(ffmpeg, output_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    frame_count = max(1, math.ceil(duration_seconds * engine.OUTPUT_FPS))
    code = -1
    try:
        assert process.stdin is not None
        for index in range(frame_count):
            process.stdin.write(
                render_frame(
                    template.template_id,
                    duration_seconds,
                    min(duration_seconds, index / engine.OUTPUT_FPS),
                    style.style_id,
                ).tobytes()
            )
        process.stdin.close()
        code = process.wait(timeout=engine.RENDER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        raise HTTPException(status_code=504, detail="Finance motion render timed out") from exc
    except BrokenPipeError as exc:
        process.kill()
        process.wait()
        error = engine._compact_error(process.stderr.read() if process.stderr else None)
        raise HTTPException(
            status_code=500,
            detail=f"Finance motion encoder stopped unexpectedly: {error}",
        ) from exc
    finally:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
    if code != 0:
        error = engine._compact_error(process.stderr.read() if process.stderr else None)
        raise HTTPException(
            status_code=500,
            detail=f"Finance motion encoder failed: {error}",
        )


def render_finance_motion(
    scene: Scene,
    template_id: str | None = None,
    style_id: str | None = None,
) -> ArtDirectedMotion:
    template = engine.TEMPLATE_BY_ID.get(template_id or "")
    if template is None:
        template, _confidence, _reason = suggest_template(scene)
    style = _resolve_style(style_id)
    ffmpeg = shutil.which(engine.FFMPEG_NAME)
    if ffmpeg is None:
        raise HTTPException(
            status_code=422,
            detail="FFmpeg is required to encode Finance Motion Studio videos.",
        )

    duration = round(max(1.0, float(scene.duration_seconds)), 3)
    asset_directory = project_directory(scene.project_id) / "assets"
    asset_directory.mkdir(parents=True, exist_ok=True)
    stem = asset_directory / (
        f"scene-{scene.scene_number:03d}-finance-"
        f"{safe_component(template.template_id)}-{safe_component(style.style_id)}"
    )
    media_path = stem.with_suffix(".mp4")
    preview_path = Path(f"{stem}-poster.jpg")
    temporary_media = Path(f"{media_path}.part.mp4")
    temporary_preview = Path(f"{preview_path}.part.jpg")
    temporary_media.unlink(missing_ok=True)
    temporary_preview.unlink(missing_ok=True)

    try:
        _encode_frames(ffmpeg, template, style, duration, temporary_media)
        poster_time = min(max(0.8, duration * 0.55), max(0.0, duration - 0.03))
        render_frame(
            template.template_id,
            duration,
            poster_time,
            style.style_id,
        ).save(temporary_preview, format="JPEG", quality=93, optimize=True)
        temporary_media.replace(media_path)
        temporary_preview.replace(preview_path)
    except HTTPException:
        temporary_media.unlink(missing_ok=True)
        temporary_preview.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temporary_media.unlink(missing_ok=True)
        temporary_preview.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Finance motion render failed: {type(exc).__name__}: {exc}",
        ) from exc

    media_relative = media_path.resolve().relative_to(MEDIA_ROOT).as_posix()
    preview_relative = preview_path.resolve().relative_to(MEDIA_ROOT).as_posix()
    return ArtDirectedMotion(
        template=template,
        style=style,
        media_path=media_path,
        preview_path=preview_path,
        media_relative_path=media_relative,
        preview_relative_path=preview_relative,
        media_url=public_media_url(media_relative),
        preview_url=public_media_url(preview_relative),
        content_type="video/mp4",
        size_bytes=media_path.stat().st_size,
        checksum_sha256=engine._checksum(media_path),
        duration_seconds=duration,
    )
