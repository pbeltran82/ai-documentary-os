from __future__ import annotations

import logging
from collections.abc import Iterable

from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from ..models import Asset, Project, Scene
from .media_library import write_timeline_manifest
from .render_invalidation import invalidate_render_artifacts

logger = logging.getLogger(__name__)
MANIFEST_PROJECT_IDS = "documentary_os_manifest_project_ids"
DEFER_MANIFEST_REFRESH = "documentary_os_defer_manifest_refresh"


def refresh_project_manifests(bind: Engine, project_ids: Iterable[int]) -> None:
    """Invalidate renders and rewrite manifests once for the supplied projects."""
    normalized_ids = sorted({int(project_id) for project_id in project_ids})
    if not normalized_ids:
        return

    with Session(bind=bind) as manifest_db:
        for project_id in normalized_ids:
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


def defer_manifest_refresh(session: Session) -> None:
    """Mark one database transaction as part of a larger visual batch."""
    session.info[DEFER_MANIFEST_REFRESH] = True


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
    session.info.pop(DEFER_MANIFEST_REFRESH, None)


@event.listens_for(Session, "after_commit")
def refresh_timeline_manifests(session: Session) -> None:
    project_ids = session.info.pop(MANIFEST_PROJECT_IDS, set())
    deferred = bool(session.info.pop(DEFER_MANIFEST_REFRESH, False))
    if not project_ids or deferred:
        return

    try:
        refresh_project_manifests(session.get_bind(), project_ids)
    except Exception:
        logger.exception("Could not refresh timeline manifest after database commit")
