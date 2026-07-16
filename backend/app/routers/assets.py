from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Asset, Project, Scene
from ..schemas import (
    AssetRead,
    AssetSearchResponse,
    AssetSelect,
    ProviderStatusResponse,
    ShotBrief,
    TimelineManifestResponse,
    VisualDirectorResponse,
    VisualFeedbackCreate,
    VisualFeedbackRead,
    VisualFeedbackReset,
)
from ..services.assets import PROVIDERS
from ..services.assets.common import public_search_url
from ..services.assets.search_intelligence import build_search_plan
from ..services.media_library import (
    download_candidate,
    resolve_media_path,
    write_timeline_manifest,
)
from ..services.visual_director import (
    build_shot_brief,
    director_shortlist,
    provider_priority,
)
from ..services.visual_feedback import (
    clear_scene_feedback,
    record_rejection,
    scene_feedback,
)

router = APIRouter(tags=["assets"])


def get_scene_or_404(scene_id: int, db: Session) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def default_query(scene: Scene) -> str:
    keywords = [keyword.strip() for keyword in scene.search_keywords if keyword.strip()]
    if keywords:
        return ", ".join(keywords[:5])
    if scene.visual_intent.strip():
        return scene.visual_intent.strip()
    return scene.narration.strip()


def update_project_asset_status(project: Project) -> None:
    if project.scenes and all(
        scene.asset_status == "ready" and scene.selected_asset is not None
        for scene in project.scenes
    ):
        project.status = "timeline"
    else:
        project.status = "assets"


@router.get("/providers/status", response_model=list[ProviderStatusResponse])
def provider_statuses() -> list[ProviderStatusResponse]:
    return [
        ProviderStatusResponse(
            provider=provider.name,
            label=provider.label,
            configured=provider.configured,
            requires_key=provider.env_key is not None,
            supports_media_types=list(provider.media_types),
            setup_hint=provider.setup_hint,
            source_url=provider.source_url,
        )
        for provider in PROVIDERS.values()
    ]


@router.get(
    "/scenes/{scene_id}/shot-brief",
    response_model=ShotBrief,
)
def get_shot_brief(
    scene_id: int,
    media_type: str = Query(default="video", pattern="^(video|photo)$"),
    db: Session = Depends(get_db),
) -> ShotBrief:
    scene = get_scene_or_404(scene_id, db)
    return build_shot_brief(scene, media_type)


@router.get(
    "/scenes/{scene_id}/visual-director",
    response_model=VisualDirectorResponse,
)
def direct_visual_search(
    scene_id: int,
    media_type: str = Query(default="video", pattern="^(video|photo)$"),
    provider: str = Query(
        default="auto",
        pattern="^(auto|pixabay|unsplash|wikimedia|nasa|pexels)$",
    ),
    per_page: int = Query(default=6, ge=3, le=12),
    db: Session = Depends(get_db),
) -> VisualDirectorResponse:
    scene = get_scene_or_404(scene_id, db)
    brief = build_shot_brief(scene, media_type)
    configured = [
        name
        for name, spec in PROVIDERS.items()
        if spec.configured and media_type in spec.media_types
    ]

    if provider == "auto":
        provider_names = provider_priority(media_type, brief, configured)
    else:
        provider_spec = PROVIDERS[provider]
        if media_type not in provider_spec.media_types:
            raise HTTPException(
                status_code=422,
                detail=f"{provider_spec.label} does not support {media_type} search.",
            )
        if not provider_spec.configured:
            raise HTTPException(
                status_code=422,
                detail=f"{provider_spec.label} is not configured.",
            )
        provider_names = [provider]

    all_candidates = []
    remaining_values: list[int] = []
    searched_providers: list[str] = []
    queries = brief.query_variants[:2]

    for provider_name in provider_names:
        provider_spec = PROVIDERS[provider_name]
        provider_succeeded = False
        provider_queries = (
            queries[:1]
            if provider == "auto" and provider_name == "wikimedia"
            else queries
        )
        for focused_query in provider_queries:
            try:
                candidates, remaining = provider_spec.search(
                    focused_query,
                    media_type,
                    max(6, per_page),
                )
            except HTTPException:
                if provider != "auto":
                    raise
                continue
            provider_succeeded = True
            all_candidates.extend(
                candidate.model_copy(update={"query_variant": focused_query})
                for candidate in candidates
            )
            if remaining is not None:
                remaining_values.append(remaining)
        if provider_succeeded:
            searched_providers.append(provider_name)

    feedback = scene_feedback(scene.project_id, scene.id)
    rejected_ids = {
        (str(item.get("provider") or ""), str(item.get("provider_asset_id") or ""))
        for item in feedback
    }
    candidates = director_shortlist(
        scene,
        brief,
        all_candidates,
        rejected_ids,
        per_page,
    )

    return VisualDirectorResponse(
        media_type=media_type,
        shot_brief=brief,
        search_queries=queries,
        providers_searched=searched_providers,
        rate_limit_remaining=min(remaining_values) if remaining_values else None,
        rejected_count=len(feedback),
        candidates=candidates,
    )


@router.post(
    "/scenes/{scene_id}/visual-feedback",
    response_model=VisualFeedbackRead,
)
def reject_visual_candidate(
    scene_id: int,
    payload: VisualFeedbackCreate,
    db: Session = Depends(get_db),
) -> VisualFeedbackRead:
    scene = get_scene_or_404(scene_id, db)
    record = record_rejection(
        scene.project_id,
        scene.id,
        payload.provider,
        payload.provider_asset_id,
        payload.reason,
    )
    return VisualFeedbackRead(**record)


@router.delete(
    "/scenes/{scene_id}/visual-feedback",
    response_model=VisualFeedbackReset,
)
def reset_visual_feedback(
    scene_id: int,
    db: Session = Depends(get_db),
) -> VisualFeedbackReset:
    scene = get_scene_or_404(scene_id, db)
    removed = clear_scene_feedback(scene.project_id, scene.id)
    return VisualFeedbackReset(removed=removed)


@router.get(
    "/scenes/{scene_id}/asset-candidates",
    response_model=AssetSearchResponse,
)
def search_asset_candidates(
    scene_id: int,
    provider: str = Query(
        default="pixabay",
        pattern="^(pixabay|unsplash|wikimedia|nasa|pexels)$",
    ),
    media_type: str = Query(default="video", pattern="^(video|photo)$"),
    query: str | None = Query(default=None, min_length=2, max_length=300),
    per_page: int = Query(default=12, ge=1, le=30),
    db: Session = Depends(get_db),
) -> AssetSearchResponse:
    scene = get_scene_or_404(scene_id, db)
    provider_spec = PROVIDERS[provider]
    if media_type not in provider_spec.media_types:
        raise HTTPException(
            status_code=422,
            detail=f"{provider_spec.label} does not support {media_type} search.",
        )

    search_query = (query or default_query(scene)).strip()
    source_url = public_search_url(provider, search_query, media_type)
    if not provider_spec.configured:
        return AssetSearchResponse(
            provider=provider,
            configured=False,
            query=search_query,
            media_type=media_type,
            source_url=source_url,
            candidates=[],
        )

    search_plan = build_search_plan(
        search_query,
        scene.search_keywords,
        scene.visual_intent,
        media_type,
        max_queries=3,
    )
    searched_batches: list[tuple[int, str, list]] = []
    remaining_values: list[int] = []

    for position, focused_query in enumerate(search_plan):
        candidates, remaining = provider_spec.search(
            focused_query,
            media_type,
            per_page,
        )
        searched_batches.append((position, focused_query, candidates))
        if remaining is not None:
            remaining_values.append(remaining)

    _position, selected_query, candidates = max(
        searched_batches,
        key=lambda item: (len(item[2]), -item[0]),
    )
    candidates = candidates[:per_page]
    remaining = min(remaining_values) if remaining_values else None

    return AssetSearchResponse(
        provider=provider,
        configured=True,
        query=selected_query,
        media_type=media_type,
        source_url=public_search_url(provider, selected_query, media_type),
        rate_limit_remaining=remaining,
        candidates=candidates,
    )


@router.put(
    "/scenes/{scene_id}/selected-asset",
    response_model=AssetRead,
)
def select_asset(
    scene_id: int,
    payload: AssetSelect,
    db: Session = Depends(get_db),
) -> Asset:
    scene = get_scene_or_404(scene_id, db)
    provider = PROVIDERS.get(payload.provider)
    if provider is None:
        raise HTTPException(status_code=422, detail="Unknown asset provider")

    local_files = download_candidate(scene, payload)
    new_paths = {
        local_files.media.relative_path,
        local_files.preview.relative_path,
    }
    try:
        if provider.track_selection is not None:
            provider.track_selection(payload.provider_asset_id)
    except Exception:
        for relative_path in new_paths:
            path = resolve_media_path(relative_path)
            if path is not None:
                path.unlink(missing_ok=True)
        raise

    asset = db.scalar(select(Asset).where(Asset.scene_id == scene_id))
    old_paths: tuple[str, str] = ("", "")
    values = payload.model_dump()
    remote_download_url = values["download_url"]
    values.update(
        {
            "preview_url": local_files.preview.public_url,
            "download_url": local_files.media.public_url,
        }
    )

    if asset is None:
        asset = Asset(scene_id=scene_id, **values)
        scene.selected_asset = asset
        db.add(asset)
    else:
        old_paths = (asset.local_path, asset.local_preview_path)
        for field, value in values.items():
            setattr(asset, field, value)
        scene.selected_asset = asset

    asset.remote_download_url = remote_download_url
    asset.local_path = local_files.media.relative_path
    asset.local_preview_path = local_files.preview.relative_path
    asset.content_type = local_files.media.content_type
    asset.file_size_bytes = local_files.media.size_bytes
    asset.checksum_sha256 = local_files.media.checksum_sha256
    asset.downloaded_at = datetime.now(timezone.utc)

    scene.asset_status = "ready"
    update_project_asset_status(scene.project)
    try:
        db.commit()
    except Exception:
        db.rollback()
        for relative_path in new_paths:
            if relative_path not in set(old_paths):
                path = resolve_media_path(relative_path)
                if path is not None:
                    path.unlink(missing_ok=True)
        raise
    db.refresh(asset)
    for relative_path in set(old_paths):
        if relative_path and relative_path not in new_paths:
            path = resolve_media_path(relative_path)
            if path is not None:
                path.unlink(missing_ok=True)
    write_timeline_manifest(scene.project)
    return asset


@router.delete(
    "/scenes/{scene_id}/selected-asset",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_selected_asset(
    scene_id: int,
    db: Session = Depends(get_db),
) -> Response:
    scene = get_scene_or_404(scene_id, db)
    asset = db.scalar(select(Asset).where(Asset.scene_id == scene_id))
    paths = None if asset is None else (asset.local_path, asset.local_preview_path)
    if asset is not None:
        scene.selected_asset = None
    scene.asset_status = "missing"
    update_project_asset_status(scene.project)
    db.commit()

    if paths is not None:
        for relative_path in set(paths):
            path = resolve_media_path(relative_path)
            if path is not None:
                path.unlink(missing_ok=True)
    write_timeline_manifest(scene.project)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/projects/{project_id}/timeline-manifest",
    response_model=TimelineManifestResponse,
)
def generate_timeline_manifest(
    project_id: int,
    db: Session = Depends(get_db),
) -> TimelineManifestResponse:
    project = get_project_or_404(project_id, db)
    relative_path, public_url, manifest = write_timeline_manifest(project)
    return TimelineManifestResponse(
        project_id=project.id,
        relative_path=relative_path,
        public_url=public_url,
        manifest=manifest,
    )
