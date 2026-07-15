from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Asset, Scene
from ..schemas import (
    AssetCandidate,
    AssetRead,
    AssetSearchResponse,
    AssetSelect,
    PexelsStatusResponse,
)

router = APIRouter(tags=["assets"])

PEXELS_API_BASE = "https://api.pexels.com"
SETUP_HINT = "Add PEXELS_API_KEY=your_key to backend/.env, then restart the app."


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


def public_search_url(query: str, media_type: str) -> str:
    encoded = quote(query.strip(), safe="")
    if media_type == "video":
        return f"https://www.pexels.com/search/videos/{encoded}/"
    return f"https://www.pexels.com/search/{encoded}/"


def pexels_request(path: str, params: dict[str, str | int]) -> tuple[dict[str, Any], int | None]:
    api_key = os.getenv("PEXELS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(SETUP_HINT)

    url = f"{PEXELS_API_BASE}{path}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "Authorization": api_key,
            "Accept": "application/json",
            "User-Agent": "AI-Documentary-OS/0.3",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
            remaining_value = response.headers.get("X-Ratelimit-Remaining")
            remaining = int(remaining_value) if remaining_value else None
            return payload, remaining
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=502,
            detail=f"Pexels request failed ({exc.code}): {detail[:300]}",
        ) from exc
    except URLError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach Pexels: {exc.reason}",
        ) from exc


def choose_video_file(video_files: list[dict[str, Any]]) -> dict[str, Any] | None:
    mp4_files = [
        item
        for item in video_files
        if item.get("file_type") == "video/mp4" and item.get("link")
    ]
    if not mp4_files:
        return None

    def score(item: dict[str, Any]) -> tuple[int, int, int]:
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        portrait_penalty = 1 if height > width else 0
        quality_penalty = 0 if item.get("quality") == "hd" else 1
        resolution_distance = abs(width - 1920) + abs(height - 1080)
        return portrait_penalty, quality_penalty, resolution_distance

    return min(mp4_files, key=score)


def normalize_video(item: dict[str, Any]) -> AssetCandidate | None:
    selected_file = choose_video_file(item.get("video_files") or [])
    if selected_file is None:
        return None
    user = item.get("user") or {}
    return AssetCandidate(
        provider="pexels",
        provider_asset_id=str(item["id"]),
        media_type="video",
        source_url=item.get("url") or "",
        preview_url=item.get("image") or "",
        download_url=selected_file.get("link") or "",
        creator=user.get("name") or "",
        creator_url=user.get("url") or "",
        width=int(selected_file.get("width") or item.get("width") or 0),
        height=int(selected_file.get("height") or item.get("height") or 0),
        duration_seconds=float(item.get("duration") or 0),
    )


def normalize_photo(item: dict[str, Any]) -> AssetCandidate:
    sources = item.get("src") or {}
    return AssetCandidate(
        provider="pexels",
        provider_asset_id=str(item["id"]),
        media_type="photo",
        source_url=item.get("url") or "",
        preview_url=sources.get("large") or sources.get("medium") or "",
        download_url=sources.get("original") or sources.get("large2x") or "",
        creator=item.get("photographer") or "",
        creator_url=item.get("photographer_url") or "",
        width=int(item.get("width") or 0),
        height=int(item.get("height") or 0),
        duration_seconds=None,
    )


@router.get("/providers/pexels/status", response_model=PexelsStatusResponse)
def pexels_status() -> PexelsStatusResponse:
    return PexelsStatusResponse(
        configured=bool(os.getenv("PEXELS_API_KEY", "").strip()),
        setup_hint=SETUP_HINT,
    )


@router.get(
    "/scenes/{scene_id}/asset-candidates",
    response_model=AssetSearchResponse,
)
def search_asset_candidates(
    scene_id: int,
    media_type: str = Query(default="video", pattern="^(video|photo)$"),
    query: str | None = Query(default=None, min_length=2, max_length=300),
    per_page: int = Query(default=12, ge=1, le=40),
    db: Session = Depends(get_db),
) -> AssetSearchResponse:
    scene = get_scene_or_404(scene_id, db)
    search_query = (query or default_query(scene)).strip()
    source_url = public_search_url(search_query, media_type)
    configured = bool(os.getenv("PEXELS_API_KEY", "").strip())

    if not configured:
        return AssetSearchResponse(
            configured=False,
            query=search_query,
            media_type=media_type,
            source_url=source_url,
            candidates=[],
        )

    if media_type == "video":
        payload, remaining = pexels_request(
            "/v1/videos/search",
            {
                "query": search_query,
                "orientation": "landscape",
                "size": "medium",
                "per_page": per_page,
            },
        )
        candidates = [
            candidate
            for candidate in (
                normalize_video(item) for item in payload.get("videos", [])
            )
            if candidate is not None
        ]
    else:
        payload, remaining = pexels_request(
            "/v1/search",
            {
                "query": search_query,
                "orientation": "landscape",
                "per_page": per_page,
            },
        )
        candidates = [normalize_photo(item) for item in payload.get("photos", [])]

    return AssetSearchResponse(
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
