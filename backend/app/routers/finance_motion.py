from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Asset, Scene
from ..schemas import AssetRead
from ..services import finance_motion_composition as _finance_motion_composition
from ..services.finance_motion_art import (
    DEFAULT_STYLE_ID,
    render_finance_motion,
    render_frame,
    style_catalog,
    suggest_template,
    template_catalog,
)
from ..services.media_library import resolve_media_path
from .assets import update_project_asset_status

router = APIRouter(tags=["finance-motion"])


def get_scene_or_404(scene_id: int, db: Session) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.get("/scenes/{scene_id}/finance-motion-suggestion")
def finance_motion_suggestion(
    scene_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    scene = get_scene_or_404(scene_id, db)
    template, confidence, reason = suggest_template(scene)
    return {
        "recommended": {
            "template_id": template.template_id,
            "label": template.label,
            "description": template.description,
            "confidence": confidence,
            "reason": reason,
        },
        "templates": template_catalog(),
        "styles": style_catalog(),
        "default_style_id": DEFAULT_STYLE_ID,
    }


@router.get("/scenes/{scene_id}/finance-motion-preview")
def finance_motion_preview(
    scene_id: int,
    template_id: str | None = Query(default=None, max_length=80),
    style_id: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
) -> Response:
    scene = get_scene_or_404(scene_id, db)
    resolved_template = template_id
    if not resolved_template:
        resolved_template, _confidence, _reason = suggest_template(scene)
        resolved_template = resolved_template.template_id
    duration = max(1.0, float(scene.duration_seconds))
    preview_time = min(max(0.8, duration * 0.55), max(0.0, duration - 0.03))
    frame = render_frame(
        resolved_template,
        duration,
        preview_time,
        style_id or DEFAULT_STYLE_ID,
    )
    output = BytesIO()
    frame.save(output, format="PNG", optimize=True)
    return Response(
        content=output.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/scenes/{scene_id}/finance-motion", response_model=AssetRead)
def generate_finance_motion(
    scene_id: int,
    template_id: str | None = Query(default=None, max_length=80),
    style_id: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
) -> Asset:
    scene = get_scene_or_404(scene_id, db)
    generated = render_finance_motion(scene, template_id, style_id)
    asset = db.scalar(select(Asset).where(Asset.scene_id == scene_id))
    old_paths: set[str] = set()
    if asset is None:
        asset = Asset(scene_id=scene_id)
        scene.selected_asset = asset
        db.add(asset)
    else:
        old_paths = {asset.local_path, asset.local_preview_path}

    now = datetime.now(timezone.utc)
    values = {
        "provider": "generated",
        "provider_asset_id": (
            f"finance-{generated.template.template_id}-{generated.style.style_id}-scene-{scene.id}"
        ),
        "media_type": "video",
        "source_url": (
            f"local://finance-motion/{generated.template.template_id}/{generated.style.style_id}"
        ),
        "preview_url": generated.preview_url,
        "download_url": generated.media_url,
        "remote_download_url": "",
        "creator": "AI Documentary OS",
        "creator_url": "",
        "width": 1920,
        "height": 1080,
        "duration_seconds": generated.duration_seconds,
        "license_name": "Project-owned generated media",
        "license_url": "",
        "attribution": (
            "Generated locally by AI Documentary OS Finance Motion Studio · "
            f"Visual Composition v1.2 · {generated.style.label}"
        ),
        "local_path": generated.media_relative_path,
        "local_preview_path": generated.preview_relative_path,
        "content_type": generated.content_type,
        "file_size_bytes": generated.size_bytes,
        "checksum_sha256": generated.checksum_sha256,
        "downloaded_at": now,
    }
    for field, value in values.items():
        setattr(asset, field, value)

    scene.selected_asset = asset
    scene.asset_status = "ready"
    update_project_asset_status(scene.project)
    try:
        db.commit()
    except Exception:
        db.rollback()
        for path_value in {generated.media_relative_path, generated.preview_relative_path}:
            path = resolve_media_path(path_value)
            if path is not None:
                path.unlink(missing_ok=True)
        raise

    db.refresh(asset)
    new_paths = {generated.media_relative_path, generated.preview_relative_path}
    for path_value in old_paths - new_paths:
        path = resolve_media_path(path_value)
        if path is not None:
            path.unlink(missing_ok=True)
    return asset
