from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException

from ..models import Scene
from .media_library import MEDIA_ROOT, project_directory, public_media_url, safe_component

OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
OUTPUT_FPS = 30
FFMPEG_NAME = os.getenv("FFMPEG_BIN", "ffmpeg")
RENDER_TIMEOUT_SECONDS = int(os.getenv("FINANCE_MOTION_RENDER_TIMEOUT_SECONDS", "240"))


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
    MotionTemplate(
        "paycheck_split",
        "Paycheck Split",
        "Animate 10% moving to the future before expenses.",
        tuple("paycheck salary paid pay yourself first 10 percent future".split()),
        "PAY YOURSELF FIRST",
        "10% moves before lifestyle can spend it",
    ),
    MotionTemplate(
        "expense_breakdown",
        "Expense Breakdown",
        "Visualize rent, groceries, and lifestyle draining a paycheck.",
        tuple("rent groceries bills expenses spending checkout lifestyle".split()),
        "WHERE THE PAYCHECK GOES",
        "Rent. Groceries. Lifestyle. Then nothing.",
    ),
    MotionTemplate(
        "empty_balance",
        "Empty Balance",
        "Show an account falling to zero without weak stock metaphors.",
        tuple("empty zero nothing left balance declined wallet exhausted".split()),
        "NOTHING LEFT",
        "$0.00 after the spending cycle",
    ),
    MotionTemplate(
        "recurring_transfer",
        "Recurring Transfer",
        "Animate an automatic transfer into an investment account.",
        tuple("automatic route transfer recurring scheduled bill invest".split()),
        "AUTOMATE THE FIRST 10%",
        "Pay your future self like a required bill",
    ),
    MotionTemplate(
        "index_growth",
        "Index Fund Growth",
        "Show regular contributions building long-term market exposure.",
        tuple("s&p index fund market investing investment".split()),
        "LOW-COST INDEX FUND",
        "Small automatic deposits. Long-term market growth.",
    ),
    MotionTemplate(
        "compound_growth",
        "Compound Growth",
        "Show contributions accelerating through compounding.",
        tuple("compound interest wealth growth machine future".split()),
        "COMPOUNDING TAKES OVER",
        "Time turns consistency into acceleration",
    ),
    MotionTemplate(
        "pay_self_comparison",
        "Pay Yourself First",
        "Compare spending-first and investing-first money flows.",
        tuple("opposite pay yourself first spending wealthy".split()),
        "TWO DIFFERENT SYSTEMS",
        "Spend first vs. invest first",
    ),
    MotionTemplate(
        "subscribe_cta",
        "Blueprint CTA",
        "End with an animated subscribe and blueprint call to action.",
        tuple("subscribe blueprint follow channel".split()),
        "BUILD YOUR BLUEPRINT",
        "Subscribe for the next step",
    ),
)
TEMPLATE_BY_ID = {template.template_id: template for template in TEMPLATES}


def _words(value: str) -> set[str]:
    return {
        "".join(character for character in token.lower() if character.isalnum())
        for token in value.split()
    } - {""}


def template_catalog() -> list[dict[str, object]]:
    return [
        {
            "template_id": template.template_id,
            "label": template.label,
            "description": template.description,
        }
        for template in TEMPLATES
    ]


def suggest_template(scene: Scene) -> tuple[MotionTemplate, float, str]:
    context = " ".join(
        [scene.narration, scene.visual_intent, *scene.search_keywords]
    )
    context_words = _words(context)
    scored = [
        (len(context_words & set(template.keywords)), template)
        for template in TEMPLATES
    ]
    scored.sort(key=lambda item: (item[0], item[1].template_id), reverse=True)
    matched_count, template = scored[0]
    confidence = min(0.98, 0.50 + matched_count * 0.09)
    reason = (
        f"Matched {matched_count} finance concept keyword"
        f"{'s' if matched_count != 1 else ''} in the scene brief."
        if matched_count
        else "Selected as the safest general finance composition for this scene."
    )
    return template, round(confidence, 2), reason


def _escape_drawtext(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _expression(value: str | int | float) -> str:
    if isinstance(value, (int, float)):
        return str(value)
    escaped = value.replace("\\", "\\\\").replace(",", "\\,").replace("'", "\\'")
    return f"'{escaped}'"


def _text(
    value: str,
    x: str | int,
    y: str | int,
    size: int = 48,
    color: str = "white",
    alpha: str = "1",
) -> str:
    return (
        "drawtext=font='Sans':"
        f"text='{_escape_drawtext(value)}':expansion=none:"
        f"fontcolor={color}:fontsize={size}:x={_expression(x)}:y={_expression(y)}:"
        f"alpha='{alpha}'"
    )


def _box(
    x: str | int,
    y: str | int,
    width: str | int,
    height: str | int,
    color: str,
    enable: str | None = None,
) -> str:
    value = (
        f"drawbox=x={_expression(x)}:y={_expression(y)}:"
        f"w={_expression(width)}:h={_expression(height)}:color={color}:t=fill"
    )
    if enable:
        value += f":enable={_expression(enable)}"
    return value


def _common_filters(template: MotionTemplate) -> list[str]:
    return [
        "drawgrid=w=160:h=160:t=1:c=0xffffff@0.035",
        _box(110, 100, 8, 150, "0x8b5cf6@0.95"),
        _text(
            template.title,
            150,
            105,
            68,
            "white",
            "min(1,max(0,(t-0.10)/0.35))",
        ),
        _text(
            template.subtitle,
            150,
            195,
            31,
            "0xc4b5fd",
            "min(1,max(0,(t-0.35)/0.4))",
        ),
        _box(120, 940, 1680, 2, "0xffffff@0.18"),
        _text(
            "AI DOCUMENTARY OS  •  LOCAL MOTION",
            120,
            970,
            21,
            "0x94a3b8",
            "min(1,max(0,(t-0.7)/0.4))",
        ),
    ]


def build_filter_chain(template_id: str, duration_seconds: float) -> str:
    template = TEMPLATE_BY_ID.get(template_id)
    if template is None:
        raise HTTPException(status_code=422, detail="Unknown finance motion template")

    filters = _common_filters(template)
    if template_id == "paycheck_split":
        filters.extend(
            [
                _box(170, 420, 1580, 150, "0x111827@0.95"),
                _text("PAYCHECK", 220, 455, 38),
                _box(220, 570, "max(10,min(1260,(t-0.7)*650))", 72, "0x64748b@0.8"),
                _box(1480, 570, "max(10,min(220,(t-1.1)*220))", 72, "0x8b5cf6@0.95"),
                _text("90%  LIFE", 250, 582, 34, "white", "min(1,max(0,(t-1.0)/0.4))"),
                _text("10%", 1520, 582, 34, "white", "min(1,max(0,(t-1.25)/0.35))"),
                _text("FUTURE", 1490, 675, 28, "0xc4b5fd", "min(1,max(0,(t-1.45)/0.4))"),
            ]
        )
    elif template_id == "expense_breakdown":
        for index, (label, percent, color) in enumerate(
            (("RENT", 0.46, "0xef4444"), ("GROCERIES", 0.28, "0xf59e0b"), ("LIFESTYLE", 0.20, "0x64748b"))
        ):
            y_position = 400 + index * 150
            filters.extend(
                [
                    _text(label, 180, y_position - 8, 30, "white", f"min(1,max(0,(t-{0.45 + index * 0.2:.2f})/0.3))"),
                    _box(500, y_position, f"max(8,min({int(1080 * percent)},(t-{0.55 + index * 0.2:.2f})*500))", 55, f"{color}@0.9"),
                    _text(f"{int(percent * 100)}%", 1510, y_position + 7, 28, "white", f"min(1,max(0,(t-{0.85 + index * 0.2:.2f})/0.3))"),
                ]
            )
        filters.extend(
            [
                _box(160, 810, "max(10,min(1580,(t-1.7)*900))", 6, "0xef4444@0.9"),
                _text("$0 LEFT", 1420, 840, 42, "0xfca5a5", "min(1,max(0,(t-1.9)/0.3))"),
            ]
        )
    elif template_id == "empty_balance":
        filters.extend(
            [
                _box(330, 370, 1260, 390, "0x111827@0.98"),
                _text("AVAILABLE BALANCE", 420, 435, 34, "0x94a3b8", "min(1,max(0,(t-0.4)/0.4))"),
                _text("$0.00", 420, 520, 116, "white", "min(1,max(0,(t-0.8)/0.45))"),
                _box(420, 680, "max(10,min(1060,(t-1.0)*650))", 10, "0xef4444@0.9"),
                _text("PAYCHECK EXHAUSTED", 930, 705, 30, "0xfca5a5", "min(1,max(0,(t-1.5)/0.35))"),
            ]
        )
    elif template_id == "recurring_transfer":
        filters.extend(
            [
                _box(180, 390, 580, 330, "0x111827@0.98"),
                _box(1160, 390, 580, 330, "0x111827@0.98"),
                _text("CHECKING", 245, 445, 34, "0x94a3b8"),
                _text("INDEX FUND", 1225, 445, 34, "0xc4b5fd"),
                _text("90%", 365, 545, 78),
                _text("+10%", 1325, 545, 78, "0xa7f3d0", "min(1,max(0,(t-1.3)/0.4))"),
                _box("max(760,min(1140,760+(t-0.7)*300))", 540, 70, 70, "0x8b5cf6@0.95", "between(t,0.7,2.3)"),
                _text("AUTOMATIC", 820, 650, 32, "white", "min(1,max(0,(t-0.9)/0.4))"),
                _text("EVERY PAYDAY", 820, 700, 28, "0xc4b5fd", "min(1,max(0,(t-1.15)/0.4))"),
            ]
        )
    elif template_id == "index_growth":
        for index, height in enumerate((110, 180, 260, 350, 470, 620)):
            filters.append(
                _box(
                    260 + index * 230,
                    820 - height,
                    150,
                    f"max(8,min({height},(t-{0.45 + index * 0.12:.2f})*280))",
                    "0x8b5cf6@0.88",
                )
            )
        filters.extend(
            [
                _text("REGULAR CONTRIBUTIONS", 260, 845, 30, "0xc4b5fd", "min(1,max(0,(t-1.5)/0.4))"),
                _text("TIME  →", 1400, 845, 34, "white", "min(1,max(0,(t-1.8)/0.4))"),
            ]
        )
    elif template_id == "compound_growth":
        for index, size in enumerate((36, 48, 64, 86, 116, 156)):
            x_position = 300 + index * 250
            y_position = 770 - size
            filters.extend(
                [
                    _box(x_position, y_position, size, size, "0x8b5cf6@0.85", f"gte(t,{0.4 + index * 0.22:.2f})"),
                    _text(f"Y{index + 1}", x_position, y_position + size + 28, 23, "0xc4b5fd", f"min(1,max(0,(t-{0.45 + index * 0.22:.2f})/0.3))"),
                ]
            )
        filters.append(
            _text("CONTRIBUTIONS + RETURNS + TIME", 450, 410, 38, "white", "min(1,max(0,(t-1.4)/0.5))")
        )
    elif template_id == "pay_self_comparison":
        filters.extend(
            [
                _box(180, 390, 700, 390, "0x3f1720@0.94"),
                _box(1040, 390, 700, 390, "0x0f2f2a@0.94"),
                _text("SPEND FIRST", 300, 445, 44, "0xfca5a5"),
                _text("PAY SELF FIRST", 1150, 445, 44, "0xa7f3d0"),
                _text("$0 LEFT", 390, 590, 74, "white", "min(1,max(0,(t-0.9)/0.4))"),
                _text("10% INVESTED", 1170, 590, 74, "white", "min(1,max(0,(t-1.25)/0.4))"),
                _box(940, 380, 4, 420, "0xffffff@0.22"),
            ]
        )
    else:
        filters.extend(
            [
                _box(460, 410, 1000, 260, "0x8b5cf6@0.9"),
                _text("SUBSCRIBE", 690, 475, 82, "white", "min(1,max(0,(t-0.4)/0.4))"),
                _text("BUILD THE NEXT STEP", 720, 590, 35, "0xede9fe", "min(1,max(0,(t-0.9)/0.4))"),
                _box(700, 720, "max(10,min(520,(t-1.1)*360))", 8, "0xa7f3d0@0.95"),
            ]
        )

    fade_seconds = max(0.15, min(0.35, duration_seconds / 6))
    filters.extend(
        [
            f"fade=t=in:st=0:d={fade_seconds:.3f}",
            f"fade=t=out:st={max(0, duration_seconds - fade_seconds):.3f}:d={fade_seconds:.3f}",
            "format=yuv420p",
        ]
    )
    return ",".join(filters)


def _run(command: list[str], label: str) -> None:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=RENDER_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail=f"{label} timed out") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "Unknown FFmpeg error")[-1800:]
        raise HTTPException(status_code=500, detail=f"{label} failed: {detail}")


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
        raise HTTPException(status_code=422, detail="FFmpeg is required to generate finance motion graphics")

    duration = round(max(1.0, float(scene.duration_seconds)), 3)
    asset_directory = project_directory(scene.project_id) / "assets"
    asset_directory.mkdir(parents=True, exist_ok=True)
    identity = safe_component(template.template_id)
    stem = asset_directory / f"scene-{scene.scene_number:03d}-finance-{identity}"
    media_path = stem.with_suffix(".mp4")
    preview_path = Path(f"{stem}-poster.jpg")
    temporary_media = Path(f"{media_path}.part.mp4")
    temporary_preview = Path(f"{preview_path}.part.jpg")

    temporary_media.unlink(missing_ok=True)
    temporary_preview.unlink(missing_ok=True)
    _run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x080d19:s={OUTPUT_WIDTH}x{OUTPUT_HEIGHT}:r={OUTPUT_FPS}:d={duration:.3f}",
            "-vf",
            build_filter_chain(template.template_id, duration),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(temporary_media),
        ],
        "Finance motion render",
    )
    _run(
        [
            ffmpeg,
            "-y",
            "-ss",
            f"{min(0.8, duration / 2):.3f}",
            "-i",
            str(temporary_media),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(temporary_preview),
        ],
        "Finance motion poster render",
    )
    temporary_media.replace(media_path)
    temporary_preview.replace(preview_path)

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
