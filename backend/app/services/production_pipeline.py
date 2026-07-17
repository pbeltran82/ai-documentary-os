from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import Project, Scene
from .animation_script_director import build_animation_plan
from .media_library import project_directory
from .voiceover import load_voiceover


def _ready_visual(scene: Scene) -> bool:
    asset = scene.selected_asset
    return bool(
        asset
        and scene.asset_status == "ready"
        and asset.local_path
    )


def _stage(
    stage_id: str,
    label: str,
    complete: int,
    total: int,
    description: str,
) -> dict[str, Any]:
    if total <= 0:
        status = "blocked"
    elif complete >= total:
        status = "complete"
    elif complete > 0:
        status = "in_progress"
    else:
        status = "ready"
    return {
        "stage_id": stage_id,
        "label": label,
        "status": status,
        "complete": complete,
        "total": total,
        "percent": round((complete / total) * 100) if total else 0,
        "description": description,
    }


def build_pipeline_status(project: Project) -> dict[str, Any]:
    scenes = list(project.scenes)
    total = len(scenes)
    directed = sum(bool(scene.animation_plan) for scene in scenes)
    visual_ready = sum(_ready_visual(scene) for scene in scenes)
    narration = load_voiceover(project.id)
    timeline_dir = project_directory(project.id) / "timeline"
    manifest_ready = (timeline_dir / "manifest.json").is_file()
    plan_ready = (timeline_dir / "render-plan.json").is_file()
    render_ready = (timeline_dir / "first-cut.mp4").is_file()

    stages = [
        _stage("direction", "Direct scenes", directed, total, "Create editable performance and camera direction for every scene."),
        _stage("visuals", "Generate visuals", visual_ready, total, "Attach a rights-aware visual or generated exact visual to every timeline slot."),
        _stage("narration", "Attach narration", 1 if narration else 0, 1, "Add the final voiceover and verify its duration."),
        _stage("assembly", "Assemble timeline", int(manifest_ready) + int(plan_ready), 2, "Build the manifest and machine-readable FFmpeg render plan."),
        _stage("render", "Render first cut", 1 if render_ready else 0, 1, "Render the complete narrated documentary preview."),
    ]

    missing_direction = [scene.id for scene in scenes if not scene.animation_plan]
    missing_visuals = [scene.id for scene in scenes if not _ready_visual(scene)]
    if not total:
        next_action = "Create or import documentary scenes."
    elif missing_direction:
        next_action = f"Prepare direction for {len(missing_direction)} scene(s)."
    elif missing_visuals:
        next_action = f"Generate or select visuals for {len(missing_visuals)} scene(s)."
    elif not narration:
        next_action = "Attach the final narration audio."
    elif not (manifest_ready and plan_ready):
        next_action = "Build the timeline manifest and render plan."
    elif not render_ready:
        next_action = "Render the narrated first cut."
    else:
        next_action = "Review the completed first cut and approve export."

    return {
        "version": "2.0.0-alpha.1",
        "project_id": project.id,
        "project_title": project.title,
        "status": "complete" if render_ready else "in_progress" if total else "blocked",
        "scene_count": total,
        "visual_coverage_percent": round((visual_ready / total) * 100) if total else 0,
        "stages": stages,
        "missing_direction_scene_ids": missing_direction,
        "missing_visual_scene_ids": missing_visuals,
        "narration_attached": narration is not None,
        "next_action": next_action,
    }


def prepare_project_direction(project: Project) -> dict[str, Any]:
    prepared: list[int] = []
    for scene in project.scenes:
        if not scene.animation_plan:
            scene.animation_plan = build_animation_plan(scene)
            prepared.append(scene.id)
    status = build_pipeline_status(project)
    status["prepared_scene_ids"] = prepared
    return status
