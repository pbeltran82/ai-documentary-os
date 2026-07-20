from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Project, Scene
from ..schemas import TimelinePlanResponse, TimelineStyleUpdate
from ..services.background_music import (
    load_background_music,
    remove_background_music,
    save_background_music,
)
from ..services.background_music_timeline import (
    load_timeline_style,
    render_first_cut,
    save_timeline_style,
    write_timeline_plan,
)
from ..services.release_quality_assurance import analyze_timeline_render, load_qa_report
from ..services.render_invalidation import invalidate_render_artifacts
from ..services.voiceover import remove_voiceover, save_voiceover

router = APIRouter(prefix="/projects", tags=["timeline"])


class BackgroundMusicSettingsUpdate(BaseModel):
    music_enabled: bool | None = None
    music_gain_db: float | None = Field(default=None, ge=-36, le=-10)
    music_ducking_db: float | None = Field(default=None, ge=-18, le=0)
    music_fade_seconds: float | None = Field(default=None, ge=0, le=8)


def get_project_or_404(project_id: int, db: Session) -> Project:
    statement = (
        select(Project)
        .options(selectinload(Project.scenes).selectinload(Scene.selected_asset))
        .where(Project.id == project_id)
    )
    project = db.scalar(statement)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def background_music_state(project_id: int) -> dict:
    settings = load_timeline_style(project_id)
    return {
        "background_music": load_background_music(project_id),
        "settings": {
            "music_enabled": bool(settings.get("music_enabled", False)),
            "music_gain_db": float(settings.get("music_gain_db", -22.0)),
            "music_ducking_db": float(settings.get("music_ducking_db", -8.0)),
            "music_fade_seconds": float(settings.get("music_fade_seconds", 1.5)),
        },
    }


def format_music_defaults(project: Project) -> dict:
    if str(project.video_format) == "shorts":
        return {
            "music_enabled": True,
            "music_gain_db": -24.0,
            "music_ducking_db": -9.0,
            "music_fade_seconds": 0.6,
        }
    return {
        "music_enabled": True,
        "music_gain_db": -22.0,
        "music_ducking_db": -8.0,
        "music_fade_seconds": 1.5,
    }


@router.post(
    "/{project_id}/timeline/plan",
    response_model=TimelinePlanResponse,
)
def create_timeline_plan(
    project_id: int,
    payload: TimelineStyleUpdate | None = None,
    db: Session = Depends(get_db),
) -> dict:
    project = get_project_or_404(project_id, db)
    if payload is not None:
        invalidate_render_artifacts(project_id)
    return write_timeline_plan(project, payload)


@router.put(
    "/{project_id}/timeline/narration",
    response_model=TimelinePlanResponse,
)
async def upload_narration(
    project_id: int,
    request: Request,
    filename: str = Query(min_length=1, max_length=255),
    db: Session = Depends(get_db),
) -> dict:
    project = get_project_or_404(project_id, db)
    content_type = request.headers.get("content-type", "application/octet-stream")
    await save_voiceover(project_id, filename, content_type, request.stream())
    invalidate_render_artifacts(project_id)
    return write_timeline_plan(project)


@router.delete(
    "/{project_id}/timeline/narration",
    response_model=TimelinePlanResponse,
)
def delete_narration(
    project_id: int,
    db: Session = Depends(get_db),
) -> dict:
    project = get_project_or_404(project_id, db)
    remove_voiceover(project_id)
    invalidate_render_artifacts(project_id)
    return write_timeline_plan(project)


@router.get("/{project_id}/timeline/music")
def get_timeline_music(
    project_id: int,
    db: Session = Depends(get_db),
) -> dict:
    get_project_or_404(project_id, db)
    return background_music_state(project_id)


@router.put("/{project_id}/timeline/music")
async def upload_timeline_music(
    project_id: int,
    request: Request,
    filename: str = Query(min_length=1, max_length=255),
    db: Session = Depends(get_db),
) -> dict:
    project = get_project_or_404(project_id, db)
    content_type = request.headers.get("content-type", "application/octet-stream")
    await save_background_music(project_id, filename, content_type, request.stream())
    save_timeline_style(project_id, format_music_defaults(project))
    invalidate_render_artifacts(project_id)
    return background_music_state(project_id)


@router.patch("/{project_id}/timeline/music")
def update_timeline_music(
    project_id: int,
    payload: BackgroundMusicSettingsUpdate,
    db: Session = Depends(get_db),
) -> dict:
    get_project_or_404(project_id, db)
    save_timeline_style(project_id, payload)
    invalidate_render_artifacts(project_id)
    return background_music_state(project_id)


@router.delete("/{project_id}/timeline/music")
def delete_timeline_music(
    project_id: int,
    db: Session = Depends(get_db),
) -> dict:
    get_project_or_404(project_id, db)
    remove_background_music(project_id)
    save_timeline_style(project_id, {"music_enabled": False})
    invalidate_render_artifacts(project_id)
    return background_music_state(project_id)


@router.post("/{project_id}/timeline/render")
def render_timeline(
    project_id: int,
    payload: TimelineStyleUpdate | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Render the first cut, then automatically produce its PASS/HOLD report."""
    project = get_project_or_404(project_id, db)
    plan = render_first_cut(project, payload)
    plan["qa_report"] = analyze_timeline_render(project)
    return plan


@router.post("/{project_id}/timeline/qa")
def run_timeline_quality_assurance(
    project_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Inspect the rendered first cut and persist a release QA report."""
    project = get_project_or_404(project_id, db)
    return analyze_timeline_render(project)


@router.get("/{project_id}/timeline/qa")
def get_timeline_quality_assurance(
    project_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Return the most recently generated release QA report."""
    get_project_or_404(project_id, db)
    return load_qa_report(project_id)
