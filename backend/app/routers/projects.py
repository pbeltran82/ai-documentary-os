from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Project, Scene
from ..schemas import ProjectCreate, ProjectDetail, ProjectRead, ProjectUpdate
from ..services.media_library import remove_project_directory
from ..services.narration_synthesis import repair_existing_narration_timings
from ..services.render_invalidation import invalidate_render_artifacts

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    statement = select(Project).order_by(Project.updated_at.desc())
    return list(db.scalars(statement).all())


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.video_format != payload.video_format:
        project.video_format = payload.video_format
        db.commit()
        db.refresh(project)
        invalidate_render_artifacts(project_id)
    return project


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    statement = (
        select(Project)
        .options(selectinload(Project.scenes).selectinload(Scene.selected_asset))
        .where(Project.id == project_id)
    )
    project = db.scalar(statement)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Recover projects persisted with the streamed-WAV 0xFFFFFFFF duration bug
    # before Pydantic validates the response's 60-second per-scene limit.
    if any(float(scene.duration_seconds) > 60.0 for scene in project.scenes):
        repair_existing_narration_timings(project, db)

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)) -> Response:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    remove_project_directory(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
