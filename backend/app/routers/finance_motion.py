from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Asset, Project, Scene
from ..schemas import AssetRead
from ..services import finance_motion_truthful as _finance_motion_truthful
from ..services.exact_visuals import (
    CHARACTER_FAMILY_ID,
    DEFAULT_STYLE_ID,
    FINANCE_FAMILY_ID,
    TECH_FAMILY_ID,
    family_catalog,
    recommend_family,
    render_exact_visual,
    render_frame,
    storyboard_beats,
    style_catalog,
    suggest_template,
    template_catalog,
)
from ..services.manifest_events import defer_manifest_refresh, refresh_project_manifests
from ..services.media_library import resolve_media_path
from .assets import update_project_asset_status

router = APIRouter(tags=["exact-visuals"])


FAMILY_LABELS = {
    FINANCE_FAMILY_ID: "Finance Motion",
    CHARACTER_FAMILY_ID: "Character Explainer",
    TECH_FAMILY_ID: "Tech & Behavior Motion",
}
FAMILY_SLUGS = {
    FINANCE_FAMILY_ID: "finance",
    CHARACTER_FAMILY_ID: "character",
    TECH_FAMILY_ID: "tech",
}


def get_scene_or_404(scene_id: int, db: Session) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


def _resolved_family_id(scene: Scene, family_id: str | None) -> str:
    if family_id:
        if family_id not in FAMILY_LABELS:
            raise HTTPException(status_code=422, detail="Unknown exact visual family")
        return family_id
    recommended, _confidence, _reason = recommend_family(scene)
    return recommended


def _resolved_template_id(
    scene: Scene,
    family_id: str,
    template_id: str | None,
) -> str:
    if template_id:
        return template_id
    template, _confidence, _reason = suggest_template(scene, family_id)
    return template.template_id


@router.get("/scenes/{scene_id}/finance-motion-suggestion")
def exact_visual_suggestion(
    scene_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    scene = get_scene_or_404(scene_id, db)
    family_id, family_confidence, family_reason = recommend_family(scene)
    family_items = family_catalog()
    family_by_id = {str(item["family_id"]): item for item in family_items}
    recommended_templates: dict[str, dict[str, object]] = {}
    templates_by_family: dict[str, list[dict[str, object]]] = {}
    for item in family_items:
        current_family = str(item["family_id"])
        template, confidence, reason = suggest_template(scene, current_family)
        recommended_templates[current_family] = {
            "template_id": template.template_id,
            "label": template.label,
            "description": template.description,
            "confidence": confidence,
            "reason": reason,
        }
        templates_by_family[current_family] = template_catalog(current_family)

    return {
        "recommended_family": {
            **family_by_id[family_id],
            "confidence": family_confidence,
            "reason": family_reason,
        },
        "recommended": recommended_templates[family_id],
        "recommended_by_family": recommended_templates,
        "families": family_items,
        "templates": templates_by_family[family_id],
        "templates_by_family": templates_by_family,
        "styles": style_catalog(),
        "default_style_id": DEFAULT_STYLE_ID,
    }


@router.get("/scenes/{scene_id}/finance-motion-storyboard")
def exact_visual_storyboard(
    scene_id: int,
    family_id: str | None = Query(default=None, max_length=80),
    template_id: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    scene = get_scene_or_404(scene_id, db)
    resolved_family = _resolved_family_id(scene, family_id)
    resolved_template = _resolved_template_id(scene, resolved_family, template_id)
    duration = max(1.0, float(scene.duration_seconds))
    return {
        "family_id": resolved_family,
        "template_id": resolved_template,
        "duration_seconds": duration,
        "beats": storyboard_beats(resolved_family, resolved_template, duration),
    }


@router.get("/scenes/{scene_id}/finance-motion-preview")
def exact_visual_preview(
    scene_id: int,
    family_id: str | None = Query(default=None, max_length=80),
    template_id: str | None = Query(default=None, max_length=80),
    style_id: str | None = Query(default=None, max_length=80),
    time_seconds: float | None = Query(default=None, ge=0, le=300),
    db: Session = Depends(get_db),
) -> Response:
    scene = get_scene_or_404(scene_id, db)
    resolved_family = _resolved_family_id(scene, family_id)
    resolved_template = _resolved_template_id(scene, resolved_family, template_id)
    duration = max(1.0, float(scene.duration_seconds))
    preview_time = (
        min(duration - 0.03, max(0.0, float(time_seconds)))
        if time_seconds is not None
        else min(max(0.8, duration * 0.55), max(0.0, duration - 0.03))
    )
    frame = render_frame(
        resolved_family,
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
def generate_exact_visual(
    scene_id: int,
    family_id: str | None = Query(default=None, max_length=80),
    template_id: str | None = Query(default=None, max_length=80),
    style_id: str | None = Query(default=None, max_length=80),
    defer_manifest: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> Asset:
    scene = get_scene_or_404(scene_id, db)
    resolved_family = _resolved_family_id(scene, family_id)
    generated = render_exact_visual(
        scene,
        resolved_family,
        template_id,
        style_id,
    )
    asset = db.scalar(select(Asset).where(Asset.scene_id == scene_id))
    old_paths: set[str] = set()
    if asset is None:
        asset = Asset(scene_id=scene_id)
        scene.selected_asset = asset
        db.add(asset)
    else:
        old_paths = {asset.local_path, asset.local_preview_path}

    family_label = FAMILY_LABELS[resolved_family]
    family_slug = FAMILY_SLUGS[resolved_family]
    now = datetime.now(timezone.utc)
    values = {
        "provider": "generated",
        "provider_asset_id": (
            f"{family_slug}-{generated.template.template_id}-"
            f"{generated.style.style_id}-scene-{scene.id}"
        ),
        "media_type": "video",
        "source_url": (
            f"local://exact-visual/{resolved_family}/"
            f"{generated.template.template_id}/{generated.style.style_id}"
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
            "Generated locally by AI Documentary OS Exact Visual Studio v1.8.0 · "
            f"{family_label} · {generated.style.label}"
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
    if defer_manifest:
        defer_manifest_refresh(db)
    try:
        db.commit()
    except Exception:
        db.rollback()
        for path_value in {
            generated.media_relative_path,
            generated.preview_relative_path,
        }:
            path = resolve_media_path(path_value)
            if path is not None:
                path.unlink(missing_ok=True)
        raise

    db.refresh(asset)
    new_paths = {
        generated.media_relative_path,
        generated.preview_relative_path,
    }
    for path_value in old_paths - new_paths:
        path = resolve_media_path(path_value)
        if path is not None:
            path.unlink(missing_ok=True)
    return asset


@router.post("/projects/{project_id}/exact-visual-batch/finalize")
def finalize_exact_visual_batch(
    project_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    refresh_project_manifests(db.get_bind(), [project_id])
    return {
        "project_id": project_id,
        "status": "finalized",
        "message": "Timeline render invalidated and project manifest refreshed once.",
    }
