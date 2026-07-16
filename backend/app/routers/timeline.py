from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Project, Scene
from ..schemas import TimelinePlanResponse, TimelineStyleUpdate
from ..services.render_invalidation import invalidate_render_artifacts
from ..services.timeline_builder import render_first_cut, write_timeline_plan
from ..services.voiceover import remove_voiceover, save_voiceover

router = APIRouter(prefix="/projects", tags=["timeline"])


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


@router.post(
    "/{project_id}/timeline/render",
    response_model=TimelinePlanResponse,
)
def render_timeline(
    project_id: int,
    payload: TimelineStyleUpdate | None = None,
    db: Session = Depends(get_db),
) -> dict:
    project = get_project_or_404(project_id, db)
    return render_first_cut(project, payload)
