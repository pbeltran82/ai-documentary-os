from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import selectinload

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Project, Scene  # noqa: E402
from app.routers.visual_architecture import (  # noqa: E402
    execute_project_visual_architecture,
    project_visual_architecture_plan,
)
from app.services.assets import PROVIDERS  # noqa: E402
from app.services.media_library import MEDIA_ROOT, resolve_media_path  # noqa: E402
from app.services.timeline_playback_polish import render_first_cut  # noqa: E402

OUTPUT_DIR = BACKEND_DIR / "asset-first-e2e-output"
REPORT_PATH = OUTPUT_DIR / "report.json"
CONTACT_SHEET_PATH = OUTPUT_DIR / "contact-sheet.jpg"


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def _probe(video_path: Path) -> dict[str, object]:
    payload = json.loads(
        _run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=width,height,r_frame_rate,codec_name:format=duration,size",
                "-of",
                "json",
                str(video_path),
            ]
        ).stdout
    )
    video_stream = next(
        stream for stream in payload.get("streams", []) if stream.get("width")
    )
    format_data = payload.get("format", {})
    return {
        "width": int(video_stream.get("width", 0)),
        "height": int(video_stream.get("height", 0)),
        "fps": str(video_stream.get("r_frame_rate", "")),
        "codec": str(video_stream.get("codec_name", "")),
        "duration_seconds": round(float(format_data.get("duration", 0)), 3),
        "size_bytes": int(format_data.get("size", 0)),
    }


def _contact_sheet(video_path: Path, duration: float) -> list[str]:
    frame_dir = OUTPUT_DIR / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    timestamps = [
        max(0.15, duration * 0.12),
        max(0.3, duration * 0.34),
        max(0.45, duration * 0.58),
        max(0.6, duration * 0.82),
    ]
    frame_paths: list[Path] = []
    for index, timestamp in enumerate(timestamps, start=1):
        path = frame_dir / f"frame-{index}.jpg"
        _run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(path),
            ]
        )
        frame_paths.append(path)

    thumb_width, thumb_height = 960, 540
    sheet = Image.new("RGB", (thumb_width * 2, thumb_height * 2 + 96), (8, 10, 16))
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(frame_paths):
        frame = Image.open(path).convert("RGB")
        frame.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        x = (index % 2) * thumb_width + (thumb_width - frame.width) // 2
        y = (index // 2) * thumb_height + 48 + (thumb_height - frame.height) // 2
        sheet.paste(frame, (x, y))
        draw.text((x + 18, y + 16), f"FRAME {index + 1}", fill=(255, 255, 255))
    draw.text((28, 16), "ASSET-FIRST VISUAL ARCHITECTURE · END-TO-END 16:9 TEST", fill=(255, 255, 255))
    sheet.save(CONTACT_SHEET_PATH, "JPEG", quality=92, optimize=True)
    return [path.relative_to(OUTPUT_DIR).as_posix() for path in frame_paths]


def _seed_project(session) -> Project:
    project = Project(
        title="Asset-First Architecture E2E",
        topic="How technology observes the world and shapes human attention",
        target_minutes=1,
        audience="General audience",
        tone="Cinematic, credible, reflective",
        visual_style="Real documentary footage and photography with restrained graphics",
        video_format="youtube",
        status="storyboard",
    )
    session.add(project)
    session.flush()

    definitions = [
        {
            "duration": 4.0,
            "narration": (
                "From orbit, Earth at night reveals a living network of cities, "
                "roads, and human activity without a single diagram."
            ),
            "visual_intent": (
                "A cinematic satellite photograph of Earth at night, with city lights "
                "and atmospheric depth filling the frame."
            ),
            "keywords": ["earth at night", "city lights", "satellite", "orbit"],
        },
        {
            "duration": 4.0,
            "narration": (
                "Historical records from the Apollo era show how cameras turned a distant "
                "world into a human place."
            ),
            "visual_intent": (
                "An archival Apollo astronaut photograph on the Moon, authentic and cinematic."
            ),
            "keywords": ["Apollo 11", "astronaut moon", "NASA archive", "historical photograph"],
        },
        {
            "duration": 4.0,
            "narration": (
                "A person checks a smartphone in a dark room while an unseen recommendation "
                "system studies every pause and scroll."
            ),
            "visual_intent": (
                "Real over-the-shoulder documentary footage of a person using a smartphone "
                "in a believable room, shallow depth of field."
            ),
            "keywords": ["person smartphone", "phone screen", "dark room", "over shoulder"],
        },
        {
            "duration": 4.0,
            "narration": (
                "A chart compares ranking score, probability, rate, and model estimate so the "
                "relationship can be explained precisely."
            ),
            "visual_intent": "A restrained data explainer with one clear relationship and minimal text.",
            "keywords": ["ranking score", "probability", "model estimate", "chart"],
        },
    ]

    cursor = 0.0
    for number, definition in enumerate(definitions, start=1):
        duration = float(definition["duration"])
        scene = Scene(
            project_id=project.id,
            scene_number=number,
            start_seconds=cursor,
            end_seconds=cursor + duration,
            duration_seconds=duration,
            narration=str(definition["narration"]),
            visual_intent=str(definition["visual_intent"]),
            search_keywords=list(definition["keywords"]),
            preferred_asset_type="stock_video",
            asset_status="missing",
        )
        session.add(scene)
        cursor += duration

    session.commit()
    session.refresh(project)
    return project


def _reload_project(session, project_id: int) -> Project:
    statement = (
        select(Project)
        .options(selectinload(Project.scenes).selectinload(Scene.selected_asset))
        .where(Project.id == project_id)
    )
    project = session.scalar(statement)
    if project is None:
        raise RuntimeError("Seeded project disappeared")
    return project


def _remove_failed_scenes(session, project: Project, failed_scene_ids: set[int]) -> Project:
    if failed_scene_ids:
        for scene in list(project.scenes):
            if scene.id in failed_scene_ids:
                session.delete(scene)
        session.commit()

    project = _reload_project(session, project.id)
    cursor = 0.0
    for number, scene in enumerate(project.scenes, start=1):
        scene.scene_number = number
        scene.start_seconds = cursor
        cursor += float(scene.duration_seconds)
        scene.end_seconds = cursor
    session.commit()
    return _reload_project(session, project.id)


def main() -> None:
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        project = _seed_project(session)
        plan = project_visual_architecture_plan(project.id, session)
        execution = execute_project_visual_architecture(
            project.id,
            replace_existing=True,
            per_page=8,
            db=session,
        )

        successful_asset_entries = [
            entry
            for entry in execution["entries"]
            if entry.get("status") == "completed"
            and entry.get("execution_mode") == "asset_first"
        ]
        successful_exact_entries = [
            entry
            for entry in execution["entries"]
            if entry.get("status") == "completed"
            and entry.get("execution_mode") == "exact_visual"
        ]
        failed_ids = {
            int(entry["scene_id"])
            for entry in execution["entries"]
            if entry.get("status") == "failed"
        }

        if not successful_asset_entries:
            raise RuntimeError(
                "Asset-first executor did not attach any real public media; "
                f"execution={json.dumps(execution, indent=2)}"
            )

        project = _reload_project(session, project.id)
        project = _remove_failed_scenes(session, project, failed_ids)
        if not project.scenes:
            raise RuntimeError("No successful scenes remained for the render test")

        rendered = render_first_cut(
            project,
            {
                "transition_style": "crossfade",
                "transition_duration_seconds": 0.28,
                "photo_motion": "editorial",
                "edge_fade_seconds": 0.25,
            },
        )
        output_path = resolve_media_path(str(rendered["output_relative_path"]))
        if output_path is None or not output_path.is_file():
            raise RuntimeError("Timeline renderer did not create the first-cut video")

        copied_video = OUTPUT_DIR / "asset-first-sample.mp4"
        shutil.copy2(output_path, copied_video)
        probe = _probe(copied_video)
        if probe["width"] != 1920 or probe["height"] != 1080:
            raise RuntimeError(f"Unexpected render dimensions: {probe}")
        if probe["duration_seconds"] < 3.5:
            raise RuntimeError(f"Rendered sample is too short: {probe}")

        frames = _contact_sheet(copied_video, float(probe["duration_seconds"]))
        selected_assets = [
            {
                "scene_number": scene.scene_number,
                "provider": scene.selected_asset.provider if scene.selected_asset else None,
                "media_type": scene.selected_asset.media_type if scene.selected_asset else None,
                "creator": scene.selected_asset.creator if scene.selected_asset else None,
                "license_name": scene.selected_asset.license_name if scene.selected_asset else None,
                "source_url": scene.selected_asset.source_url if scene.selected_asset else None,
                "local_path": scene.selected_asset.local_path if scene.selected_asset else None,
            }
            for scene in project.scenes
        ]
        report = {
            "status": "passed",
            "media_root": str(MEDIA_ROOT),
            "configured_providers": [
                name for name, provider in PROVIDERS.items() if provider.configured
            ],
            "plan": plan,
            "execution": execution,
            "successful_asset_first_count": len(successful_asset_entries),
            "successful_exact_visual_count": len(successful_exact_entries),
            "removed_failed_scene_ids": sorted(failed_ids),
            "render": probe,
            "selected_assets": selected_assets,
            "contact_sheet": CONTACT_SHEET_PATH.name,
            "frames": frames,
        }
        REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
