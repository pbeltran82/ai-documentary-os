from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Project, Scene
from ..services.render_invalidation import invalidate_render_artifacts
from ..services.script_audio_pipeline import (
    build_local_script_draft,
    build_narration_plan,
    load_narration_plan,
    load_script,
)

router = APIRouter(prefix="/projects/{project_id}/production", tags=["script-audio"])


class ScriptGenerateRequest(BaseModel):
    provider: Literal["local-outline"] = "local-outline"
    angle: str = Field(default="", max_length=3000)
    target_scene_seconds: float = Field(default=8.0, ge=4.0, le=30.0)
    replace_scenes: bool = False


class NarrationPlanRequest(BaseModel):
    provider: str = Field(default="openai", min_length=2, max_length=80)
    voice_id: str = Field(default="alloy", min_length=1, max_length=120)
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0)


def _project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _apply_script_to_scenes(project: Project, script: dict[str, Any], db: Session) -> None:
    db.execute(delete(Scene).where(Scene.project_id == project.id))
    for item in script.get("segments", []):
        db.add(
            Scene(
                project_id=project.id,
                scene_number=int(item["scene_number"]),
                start_seconds=float(item["start_seconds"]),
                end_seconds=float(item["end_seconds"]),
                duration_seconds=float(item["estimated_duration_seconds"]),
                narration=str(item["narration"]),
                visual_intent=str(item["visual_intent"]),
                search_keywords=list(item.get("search_keywords", []))[:20],
                preferred_asset_type="stock_video",
                asset_status="missing",
            )
        )
    project.status = "scripted"
    db.commit()
    invalidate_render_artifacts(project.id)


@router.get("/script")
def get_script(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    _project_or_404(project_id, db)
    script = load_script(project_id)
    if script is None:
        raise HTTPException(status_code=404, detail="No generated script exists for this project")
    return script


@router.post("/script/generate")
def generate_script(
    project_id: int,
    payload: ScriptGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    project = _project_or_404(project_id, db)
    script = build_local_script_draft(
        project,
        angle=payload.angle,
        target_scene_seconds=payload.target_scene_seconds,
    )
    if payload.replace_scenes:
        _apply_script_to_scenes(project, script, db)
        script["scenes_applied"] = True
    else:
        script["scenes_applied"] = False
    return script


@router.get("/narration")
def get_narration_plan(
    project_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _project_or_404(project_id, db)
    plan = load_narration_plan(project_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No narration plan exists for this project")
    return plan


@router.post("/narration/plan")
def plan_narration(
    project_id: int,
    payload: NarrationPlanRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    project = _project_or_404(project_id, db)
    script = load_script(project_id)
    if script is None:
        raise HTTPException(
            status_code=409,
            detail="Generate a project script before planning narration audio",
        )
    return build_narration_plan(
        project,
        script,
        provider=payload.provider,
        voice_id=payload.voice_id,
        speaking_rate=payload.speaking_rate,
    )
