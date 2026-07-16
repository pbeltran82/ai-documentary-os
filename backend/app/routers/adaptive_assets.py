from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import VisualDirectorResponse
from .assets import direct_visual_search

router = APIRouter(tags=["assets"])


def _combined_remaining(*values: int | None) -> int | None:
    available = [value for value in values if value is not None]
    return min(available) if available else None


@router.get(
    "/scenes/{scene_id}/adaptive-visual-director",
    response_model=VisualDirectorResponse,
)
def adaptive_visual_search(
    scene_id: int,
    media_type: str = Query(default="video", pattern="^(video|photo)$"),
    per_page: int = Query(default=6, ge=3, le=12),
    db: Session = Depends(get_db),
) -> VisualDirectorResponse:
    """Prefer defensible video, then automatically fall back to motion-ready stills."""
    primary = direct_visual_search(
        scene_id=scene_id,
        media_type=media_type,
        provider="auto",
        per_page=per_page,
        db=db,
    )
    if media_type != "video" or primary.candidates:
        return primary

    fallback = direct_visual_search(
        scene_id=scene_id,
        media_type="photo",
        provider="auto",
        per_page=per_page,
        db=db,
    )
    searched_providers = list(
        dict.fromkeys([*primary.providers_searched, *fallback.providers_searched])
    )
    search_queries = list(dict.fromkeys([*primary.search_queries, *fallback.search_queries]))

    if not fallback.candidates:
        return VisualDirectorResponse(
            media_type=primary.media_type,
            shot_brief=primary.shot_brief,
            search_queries=search_queries,
            providers_searched=searched_providers,
            rate_limit_remaining=_combined_remaining(
                primary.rate_limit_remaining,
                fallback.rate_limit_remaining,
            ),
            rejected_count=max(primary.rejected_count, fallback.rejected_count),
            candidates=[],
        )

    motion_ready = [
        candidate.model_copy(
            update={
                "director_reasons": [
                    "Motion-ready still fallback after no defensible video survived",
                    *candidate.director_reasons,
                ][:3],
                "director_warnings": [
                    *candidate.director_warnings,
                    "Timeline Builder will apply editorial still motion",
                ][:3],
            }
        )
        for candidate in fallback.candidates
    ]
    return fallback.model_copy(
        update={
            "search_queries": search_queries,
            "providers_searched": searched_providers,
            "rate_limit_remaining": _combined_remaining(
                primary.rate_limit_remaining,
                fallback.rate_limit_remaining,
            ),
            "rejected_count": max(primary.rejected_count, fallback.rejected_count),
            "candidates": motion_ready,
        }
    )
