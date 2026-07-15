from __future__ import annotations

import logging

from sqlalchemy import event, select
from sqlalchemy.orm import Session, selectinload

from ..models import Asset, Project, Scene
from .media_library import write_timeline_manifest
from .render_invalidation import invalidate_render_artifacts

logger = logging.getLogger(__name__)
MANIFEST_PROJECT_IDS = "documentary_os_manifest_project_ids"


@event.listens_for(Session, "after_flush")
def collect_manifest_project_ids(session: Session, _flush_context) -> None:
    project_ids: set[int] = set(session.info.get(MANIFEST_PROJECT_IDS, set()))

    for item in session.new.union(session.dirty).union(session.deleted):
        if isinstance(item, Project) and item.id is not None:
            project_ids.add(item.id)
        elif isinstance(item, Scene) and item.project_id is not None:
            project_ids.add(item.project_id)
        elif isinstance(item, Asset):
            scene = item.scene
            if scene is not None and scene.project_id is not None:
                project_ids.add(scene.project_id)

    if project_ids:
        session.info[MANIFEST_PROJECT_IDS] = project_ids


@event.listens_for(Session, "after_rollback")
def clear_manifest_project_ids(session: Session) -> None:
    session.info.pop(MANIFEST_PROJECT_IDS, None)


@event.listens_for(Session, "after_commit")
def refresh_timeline_manifests(session: Session) -> None:
    project_ids = session.info.pop(MANIFEST_PROJECT_IDS, set())
    if not project_ids:
        return

    try:
        bind = session.get_bind()
        with Session(bind=bind) as manifest_db:
            for project_id in sorted(project_ids):
                statement = (
                    select(Project)
                    .options(
                        selectinload(Project.scenes).selectinload(Scene.selected_asset)
                    )
                    .where(Project.id == project_id)
                )
                project = manifest_db.scalar(statement)
                if project is not None:
                    invalidate_render_artifacts(project_id)
                    write_timeline_manifest(project)
    except Exception:
        logger.exception("Could not refresh timeline manifest after database commit")
