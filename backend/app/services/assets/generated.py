from __future__ import annotations

from fastapi import HTTPException

from ...schemas import AssetCandidate
from .common import ProviderSpec


def search(
    _query: str,
    _media_type: str,
    _per_page: int,
) -> tuple[list[AssetCandidate], int | None]:
    raise HTTPException(
        status_code=422,
        detail="Finance Motion Studio generates exact scene graphics instead of searching stock media.",
    )


SPEC = ProviderSpec(
    name="generated",
    label="Finance Motion Studio",
    media_types=("video",),
    env_key=None,
    setup_hint="Built in. Generates project-owned 1080p motion graphics locally with FFmpeg.",
    source_url="http://localhost:5173",
    search=search,
)
