from __future__ import annotations

from .media_library import project_directory


def invalidate_render_artifacts(project_id: int) -> None:
    timeline_directory = project_directory(project_id) / "timeline"
    for filename in ("first-cut.mp4", "captions.srt", "render-plan.json", "render.sh"):
        (timeline_directory / filename).unlink(missing_ok=True)
