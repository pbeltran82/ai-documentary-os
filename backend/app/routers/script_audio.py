from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Project, Scene
from ..services.documentary_script_generation import (
    ScriptGenerationError,
    generate_openai_script,
    update_script_draft,
)
from ..services.narration_synthesis import NarrationSynthesisError, synthesize_narration
from ..services.render_invalidation import invalidate_render_artifacts
from ..services.script_approval import approve_script, list_script_revisions
from ..services.script_audio_pipeline import (
    build_local_script_draft,
    build_narration_plan,
    load_narration_plan,
    load_script,
)

router = APIRouter(prefix="/projects/{project_id}/production", tags=["script-audio"])


class ScriptGenerateRequest(BaseModel):
    provider: Literal["local-outline", "openai"] = "local-outline"
    angle: str = Field(default="", max_length=3000)
    research_notes: str = Field(default="", max_length=100_000)
    target_scene_seconds: float = Field(default=8.0, ge=4.0, le=30.0)
    replace_scenes: bool = False


class ScriptUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    thesis: str | None = Field(default=None, max_length=5000)
    segments: list[dict[str, Any]] | None = None
    editor_notes: str = Field(default="", max_length=5000)
    replace_scenes: bool = False


class ScriptApproveRequest(BaseModel):
    notes: str = Field(default="", max_length=5000)
    replace_scenes: bool = True


class NarrationPlanRequest(BaseModel):
    provider: Literal["openai", "local-test"] = "openai"
    voice_id: str = Field(default="alloy", min_length=1, max_length=120)
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0)


class NarrationSynthesizeRequest(BaseModel):
    scene_numbers: list[int] = Field(default_factory=list, max_length=500)
    force: bool = False
    retime_scenes: bool = True


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


@router.get("/script/revisions")
def get_script_revisions(
    project_id: int,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    _project_or_404(project_id, db)
    return list_script_revisions(project_id)


@router.post("/script/generate")
def generate_script(
    project_id: int,
    payload: ScriptGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    project = _project_or_404(project_id, db)
    current = load_script(project_id)
    try:
        if payload.provider == "openai":
            script = generate_openai_script(
                project,
                angle=payload.angle,
                research_notes=payload.research_notes,
                target_scene_seconds=payload.target_scene_seconds,
                previous_revision=int(current.get("revision", 0)) if current else 0,
            )
        else:
            script = build_local_script_draft(
                project,
                angle=payload.angle,
                target_scene_seconds=payload.target_scene_seconds,
            )
            script["research_notes"] = payload.research_notes.strip()
    except ScriptGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    project.status = "script"
    db.commit()
    if payload.replace_scenes:
        _apply_script_to_scenes(project, script, db)
        script["scenes_applied"] = True
    else:
        script["scenes_applied"] = False
    return script


@router.put("/script")
def update_script(
    project_id: int,
    payload: ScriptUpdateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    project = _project_or_404(project_id, db)
    current = load_script(project_id)
    if current is None:
        raise HTTPException(status_code=404, detail="No generated script exists for this project")
    try:
        script = update_script_draft(
            project,
            current,
            title=payload.title,
            thesis=payload.thesis,
            segments=payload.segments,
            editor_notes=payload.editor_notes,
        )
    except ScriptGenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    project.status = "script"
    db.commit()
    if payload.replace_scenes:
        _apply_script_to_scenes(project, script, db)
        script["scenes_applied"] = True
    else:
        script["scenes_applied"] = False
    return script


@router.post("/script/approve")
def approve_project_script(
    project_id: int,
    payload: ScriptApproveRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    project = _project_or_404(project_id, db)
    try:
        script = approve_script(project_id, notes=payload.notes)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    project.status = "script_approved"
    db.commit()
    if payload.replace_scenes:
        _apply_script_to_scenes(project, script, db)
        project.status = "script_approved"
        db.commit()
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
    if script.get("status") != "approved":
        raise HTTPException(
            status_code=409,
            detail="Approve the project script before planning narration audio",
        )
    return build_narration_plan(
        project,
        script,
        provider=payload.provider,
        voice_id=payload.voice_id,
        speaking_rate=payload.speaking_rate,
    )


@router.post("/narration/synthesize")
def synthesize_project_narration(
    project_id: int,
    payload: NarrationSynthesizeRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    project = _project_or_404(project_id, db)
    script = load_script(project_id)
    if script is None or script.get("status") != "approved":
        raise HTTPException(
            status_code=409,
            detail="Approve the project script before synthesizing narration",
        )
    selected = {int(number) for number in payload.scene_numbers if int(number) > 0}
    try:
        return synthesize_narration(
            project,
            db,
            scene_numbers=selected or None,
            force=payload.force,
            retime_scenes=payload.retime_scenes,
        )
    except NarrationSynthesisError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
