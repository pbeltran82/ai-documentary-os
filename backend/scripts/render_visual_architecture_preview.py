from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

# Importing the application installs the visual architecture exactly as production does.
from app import main as _app_main  # noqa: F401
from app.services import tech_behavior_motion as tech
from app.services.visuals.quality_gate import measure_edge_density

OUTPUT_DIR = Path("visual-architecture-preview")
TEMPLATES = (
    "algorithm_chose_you",
    "behavior_prediction_engine",
    "life_event_timeline",
    "digital_footprint_collector",
    "behavioral_twin",
    "machine_choice_explainer",
    "machine_choice_cta",
)
DURATION_SECONDS = 4.0
POSTER_TIME = 2.4
PREVIEW_FPS = 12


def render_posters() -> list[Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    report: dict[str, object] = {"templates": {}}

    for template_id in TEMPLATES:
        image = tech.render_frame(
            template_id,
            DURATION_SECONDS,
            POSTER_TIME,
            "editorial_documentary",
        )
        path = OUTPUT_DIR / f"{template_id}.jpg"
        image.save(path, format="JPEG", quality=94, optimize=True)
        paths.append(path)
        report["templates"][template_id] = {
            "width": image.width,
            "height": image.height,
            "edge_density": measure_edge_density(image),
            "mode": image.mode,
        }

    (OUTPUT_DIR / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return paths


def build_contact_sheet(paths: list[Path]) -> Path:
    thumb_width = 640
    thumb_height = 360
    label_height = 48
    columns = 2
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), (8, 10, 16))
    draw = ImageDraw.Draw(sheet)

    for index, path in enumerate(paths):
        row, column = divmod(index, columns)
        x = column * thumb_width
        y = row * (thumb_height + label_height)
        image = Image.open(path).convert("RGB").resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        sheet.paste(image, (x, y))
        draw.rectangle((x, y + thumb_height, x + thumb_width, y + thumb_height + label_height), fill=(12, 16, 25))
        draw.text((x + 18, y + thumb_height + 15), path.stem.replace("_", " ").upper(), fill=(235, 239, 246))

    output = OUTPUT_DIR / "contact-sheet.jpg"
    sheet.save(output, format="JPEG", quality=92, optimize=True)
    return output


def render_motion_montage() -> Path | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None

    output = OUTPUT_DIR / "motion-montage.mp4"
    process = subprocess.Popen(
        [
            ffmpeg,
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            "1920x1080",
            "-r",
            str(PREVIEW_FPS),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    assert process.stdin is not None
    segment_seconds = 2.0
    frames_per_segment = round(segment_seconds * PREVIEW_FPS)
    try:
        for template_id in TEMPLATES:
            for frame_index in range(frames_per_segment):
                local_progress = frame_index / max(1, frames_per_segment - 1)
                time_seconds = local_progress * DURATION_SECONDS
                frame = tech.render_frame(
                    template_id,
                    DURATION_SECONDS,
                    time_seconds,
                    "editorial_documentary",
                ).convert("RGB")
                process.stdin.write(frame.tobytes())
        process.stdin.close()
        code = process.wait(timeout=180)
    except Exception:
        process.kill()
        process.wait()
        raise

    if code != 0:
        error = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        raise RuntimeError(f"ffmpeg failed: {error[-4000:]}")
    return output


def main() -> None:
    posters = render_posters()
    contact_sheet = build_contact_sheet(posters)
    montage = render_motion_montage()
    print(f"Rendered {len(posters)} posters")
    print(f"Contact sheet: {contact_sheet}")
    print(f"Motion montage: {montage or 'ffmpeg unavailable'}")


if __name__ == "__main__":
    main()
