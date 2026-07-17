from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Project
from ..services.production_pipeline import build_pipeline_status, prepare_project_direction

router = APIRouter(tags=["production-pipeline"])


def _project(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/production-pipeline")
def production_pipeline(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    return build_pipeline_status(_project(project_id, db))


@router.post("/projects/{project_id}/production-pipeline/prepare")
def prepare_production_pipeline(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    status = prepare_project_direction(_project(project_id, db))
    db.commit()
    return status
