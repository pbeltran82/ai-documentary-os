from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Asset, Scene
from ..schemas import (
    AssetRead,
    AssetSearchResponse,
    AssetSelect,
    ProviderStatusResponse,
)
from ..services.assets import PROVIDERS
from ..services.assets.common import public_search_url

router = APIRouter(tags=["assets"])


def get_scene_or_404(scene_id: int, db: Session) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


def default_query(scene: Scene) -> str:
    keywords = [keyword.strip() for keyword in scene.search_keywords if keyword.strip()]
    if keywords:
        return " ".join(keywords[:5])
    if scene.visual_intent.strip():
        return scene.visual_intent.strip()
    return scene.narration.strip()


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

    candidates, remaining = provider_spec.search(
        search_query,
        media_type,
        per_page,
    )
    return AssetSearchResponse(
        provider=provider,
        configured=True,
        query=search_query,
        media_type=media_type,
        source_url=source_url,
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
    if provider.track_selection is not None:
        provider.track_selection(payload.provider_asset_id)

    asset = db.scalar(select(Asset).where(Asset.scene_id == scene_id))
    values = payload.model_dump()
    if asset is None:
        asset = Asset(scene_id=scene_id, **values)
        db.add(asset)
    else:
        for field, value in values.items():
            setattr(asset, field, value)

    scene.asset_status = "selected"
    scene.project.status = "assets"
    db.commit()
    db.refresh(asset)
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
    if asset is not None:
        db.delete(asset)
    scene.asset_status = "missing"
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
