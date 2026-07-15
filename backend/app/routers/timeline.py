from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Project, Scene
from ..schemas import TimelinePlanResponse
from ..services.timeline_builder import render_first_cut, write_timeline_plan

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
    db: Session = Depends(get_db),
) -> dict:
    project = get_project_or_404(project_id, db)
    return write_timeline_plan(project)


@router.post(
    "/{project_id}/timeline/render",
    response_model=TimelinePlanResponse,
)
def render_timeline(
    project_id: int,
    db: Session = Depends(get_db),
) -> dict:
    project = get_project_or_404(project_id, db)
    result = render_first_cut(project)
    project.status = "timeline"
    db.commit()
    return result
