from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Asset, Project, Scene
from ..schemas import AssetSelect
from ..services import finance_motion as finance_engine
from ..services import hyperframes_renderer
from ..services.manifest_events import refresh_project_manifests
from ..services.media_library import public_media_url, resolve_media_path
from ..services.visuals import (
    ExecutionMode,
    VisualFamily,
    build_scene_visual_plan,
    build_visual_plan,
    visual_plan_payload,
)
from ..services.visuals.asset_first_executor import search_architecture_candidates
from ..services.visuals.diversity_guard import (
    VisualDiversityGuard,
    choose_unused_exact_template,
)
from .assets import select_asset, update_project_asset_status
from .finance_motion import generate_exact_visual

router = APIRouter(tags=["visual-architecture"])

_FINANCE_TERMS = {
    "account", "balance", "budget", "compound", "expense", "finance", "fund",
    "income", "index", "invest", "investment", "market", "money", "paycheck",
    "rent", "salary", "saving", "savings", "wealth",
}


def _scene(scene_id: int, db: Session) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


def _project(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _project_plans(project: Project):
    recent_families = []
    recent_compositions = []
    planned = []
    for scene in project.scenes:
        plan = build_visual_plan(
            narration=str(scene.narration or ""),
            visual_intent=str(scene.visual_intent or ""),
            search_keywords=tuple(scene.search_keywords or ()),
            scene_key=f"project-{scene.project_id}-scene-{scene.scene_number}",
            recent_families=recent_families,
            recent_compositions=recent_compositions,
        )
        planned.append((scene, plan))
        recent_families.append(plan.strategy.family)
        recent_compositions.append(plan.shot.composition)
    return planned


def _candidate_payload(candidate, *, preview_fallback: bool = False) -> AssetSelect:
    values = candidate.model_dump()
    if preview_fallback:
        values["download_url"] = candidate.preview_url
    return AssetSelect.model_validate(values)


def _candidate_payloads(candidate) -> list[tuple[str, AssetSelect]]:
    payloads = [("original", _candidate_payload(candidate))]
    if (
        candidate.media_type == "photo"
        and candidate.preview_url.startswith(("https://", "http://"))
        and candidate.preview_url != candidate.download_url
    ):
        payloads.append(("preview_fallback", _candidate_payload(candidate, preview_fallback=True)))
    return payloads


def _candidate_responses(scene: Scene, plan, per_page: int):
    media_types = [plan.asset.preferred_media_type]
    if plan.asset.fallback_media_type and plan.asset.fallback_media_type not in media_types:
        media_types.append(plan.asset.fallback_media_type)
    return [
        search_architecture_candidates(scene, plan, media_type, per_page)
        for media_type in media_types
    ]


def _select_asset_first(
    scene: Scene,
    plan,
    per_page: int,
    db: Session,
    guard: VisualDiversityGuard,
):
    responses = _candidate_responses(scene, plan, per_page)
    attempted: set[tuple[str, str]] = set()
    download_failures: list[dict[str, str]] = []
    candidate_count = 0
    diversity_rejections = 0

    for response in responses:
        for candidate in response.candidates:
            identity = (candidate.provider, candidate.provider_asset_id)
            if identity in attempted:
                continue
            attempted.add(identity)
            if guard.rejects_candidate(candidate):
                diversity_rejections += 1
                continue
            candidate_count += 1

            for source_kind, payload in _candidate_payloads(candidate):
                try:
                    asset = select_asset(scene.id, payload, db)
                except HTTPException as exc:
                    download_failures.append(
                        {
                            "provider": candidate.provider,
                            "provider_asset_id": candidate.provider_asset_id,
                            "source_kind": source_kind,
                            "detail": str(exc.detail),
                        }
                    )
                    continue
                guard.register_asset(
                    asset.provider,
                    asset.provider_asset_id,
                    asset.download_url or candidate.download_url,
                    asset.media_type,
                )
                return asset, candidate, response, download_failures, diversity_rejections

    if candidate_count == 0:
        suffix = (
            f" {diversity_rejections} otherwise viable candidates were rejected as repeated "
            "or overly repetitive within this project."
            if diversity_rejections
            else ""
        )
        raise HTTPException(
            status_code=422,
            detail=(
                "No defensible real visual survived the architecture brief, provider, rights, "
                f"concept, quality, and diversity gates.{suffix}"
            ),
        )

    last_details = "; ".join(
        f"{failure['provider']}:{failure['source_kind']} {failure['detail']}"
        for failure in download_failures[-4:]
    )
    raise HTTPException(
        status_code=502,
        detail=(
            f"Could not download any of {candidate_count} ranked visual candidates. "
            "The executor tried alternate candidates, fallback media types, and preview "
            f"sources automatically. Last errors: {last_details}"
        ),
    )


def _resolve_ffmpeg_binary() -> str | None:
    configured = str(getattr(finance_engine, "FFMPEG_NAME", "") or "").strip()
    candidates = [
        configured,
        shutil.which(configured) if configured else None,
        shutil.which("ffmpeg"),
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg",
    ]
    for value in candidates:
        if not value:
            continue
        path = Path(value).expanduser()
        if path.is_file():
            return str(path.resolve())
        discovered = shutil.which(str(value))
        if discovered:
            return discovered
    return None


def _exact_visual_route(scene: Scene, plan) -> tuple[str, str | None]:
    """Choose the procedural renderer explicitly; never fall back to topic guessing."""
    terms = {
        word
        for value in (
            str(scene.narration or ""),
            str(scene.visual_intent or ""),
            *[str(item) for item in (scene.search_keywords or ())],
        )
        for word in value.lower().replace("/", " ").replace("-", " ").split()
    }
    if plan.strategy.family == VisualFamily.CONCLUSION_CTA:
        return "tech_behavior_motion", "machine_choice_cta"
    if plan.strategy.family == VisualFamily.DATA_EXPLAINER:
        if terms & _FINANCE_TERMS:
            return "finance_motion", None
        return "tech_behavior_motion", "behavior_prediction_engine"
    return "tech_behavior_motion", None


def _store_hyperframes_asset(scene: Scene, family_id: str, template_id: str, db: Session) -> Asset:
    rendered = hyperframes_renderer.render_scene(scene, family_id, template_id)
    asset = db.scalar(select(Asset).where(Asset.scene_id == scene.id))
    old_paths: set[str] = set()
    if asset is None:
        asset = Asset(scene_id=scene.id)
        db.add(asset)
    else:
        old_paths = {asset.local_path, asset.local_preview_path}

    media_url = public_media_url(rendered.media_relative_path)
    values = {
        "provider": "hyperframes",
        "provider_asset_id": f"hyperframes-{template_id}-scene-{scene.id}",
        "media_type": "video",
        "source_url": f"local://hyperframes/{family_id}/{template_id}",
        "preview_url": media_url,
        "download_url": media_url,
        "remote_download_url": "",
        "creator": "AI Documentary OS + HyperFrames",
        "creator_url": "https://github.com/heygen-com/hyperframes",
        "width": rendered.width,
        "height": rendered.height,
        "duration_seconds": rendered.duration_seconds,
        "license_name": "Project-owned generated media",
        "license_url": "",
        "attribution": "Generated locally from an AI Documentary OS HTML composition with HyperFrames.",
        "local_path": rendered.media_relative_path,
        "local_preview_path": rendered.preview_relative_path,
        "content_type": "video/mp4",
        "file_size_bytes": rendered.size_bytes,
        "checksum_sha256": rendered.checksum_sha256,
        "downloaded_at": datetime.now(timezone.utc),
    }
    for field, value in values.items():
        setattr(asset, field, value)
    scene.selected_asset = asset
    scene.asset_status = "ready"
    update_project_asset_status(scene.project)
    db.commit()
    db.refresh(asset)

    new_paths = {rendered.media_relative_path, rendered.preview_relative_path}
    for path_value in old_paths - new_paths:
        path = resolve_media_path(path_value)
        if path is not None:
            path.unlink(missing_ok=True)
    return asset


def _execute_scene(
    scene: Scene,
    plan,
    per_page: int,
    db: Session,
    guard: VisualDiversityGuard | None = None,
) -> dict[str, object]:
    guard = guard or VisualDiversityGuard.from_project(scene.project)
    if plan.asset.execution_mode == ExecutionMode.ASSET_FIRST:
        asset, candidate, response, download_failures, diversity_rejections = _select_asset_first(
            scene, plan, per_page, db, guard
        )
        return {
            "scene_id": scene.id,
            "scene_number": scene.scene_number,
            "status": "completed",
            "execution_mode": plan.asset.execution_mode.value,
            "visual_family": plan.strategy.family.value,
            "provider": asset.provider,
            "media_type": asset.media_type,
            "provider_asset_id": asset.provider_asset_id,
            "director_score": candidate.director_score,
            "providers_searched": response.providers_searched,
            "search_queries": response.search_queries,
            "download_failures_before_success": download_failures,
            "diversity_rejections_before_success": diversity_rejections,
            "reason": plan.asset.reason,
        }

    ffmpeg = _resolve_ffmpeg_binary()
    if ffmpeg is not None:
        finance_engine.FFMPEG_NAME = ffmpeg
    family_id, preferred_template = _exact_visual_route(scene, plan)
    template_id = choose_unused_exact_template(family_id, preferred_template, guard)

    renderer = "legacy_exact_visual"
    if (
        hyperframes_renderer.enabled()
        and template_id is not None
        and hyperframes_renderer.supports(family_id, template_id)
    ):
        try:
            asset = _store_hyperframes_asset(scene, family_id, template_id, db)
            renderer = "hyperframes"
        except Exception:
            asset = generate_exact_visual(
                scene_id=scene.id,
                family_id=family_id,
                template_id=template_id,
                style_id=None,
                defer_manifest=True,
                db=db,
            )
            renderer = "legacy_fallback"
    else:
        asset = generate_exact_visual(
            scene_id=scene.id,
            family_id=family_id,
            template_id=template_id,
            style_id=None,
            defer_manifest=True,
            db=db,
        )
    guard.register_exact(family_id, template_id or "auto")
    return {
        "scene_id": scene.id,
        "scene_number": scene.scene_number,
        "status": "completed",
        "execution_mode": plan.asset.execution_mode.value,
        "visual_family": plan.strategy.family.value,
        "exact_family_id": family_id,
        "exact_template_id": template_id,
        "exact_renderer": renderer,
        "provider": asset.provider,
        "media_type": asset.media_type,
        "provider_asset_id": asset.provider_asset_id,
        "reason": plan.asset.reason,
    }


@router.get("/scenes/{scene_id}/visual-architecture-plan")
def scene_visual_architecture_plan(
    scene_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    scene = _scene(scene_id, db)
    return {
        "scene_id": scene.id,
        "scene_number": scene.scene_number,
        "plan": visual_plan_payload(build_scene_visual_plan(scene)),
    }


@router.get("/projects/{project_id}/visual-architecture-plan")
def project_visual_architecture_plan(
    project_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    project = _project(project_id, db)
    entries = [
        {
            "scene_id": scene.id,
            "scene_number": scene.scene_number,
            "plan": visual_plan_payload(plan),
        }
        for scene, plan in _project_plans(project)
    ]
    asset_first = sum(
        entry["plan"]["asset"]["execution_mode"] == ExecutionMode.ASSET_FIRST.value
        for entry in entries
    )
    return {
        "project_id": project.id,
        "project_title": project.title,
        "scene_count": len(entries),
        "asset_first_count": asset_first,
        "exact_visual_count": len(entries) - asset_first,
        "scenes": entries,
    }


@router.post("/scenes/{scene_id}/visual-architecture-execute")
def execute_scene_visual_architecture(
    scene_id: int,
    replace_existing: bool = Query(default=False),
    per_page: int = Query(default=6, ge=3, le=12),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    scene = _scene(scene_id, db)
    if scene.selected_asset is not None and not replace_existing:
        return {
            "scene_id": scene.id,
            "scene_number": scene.scene_number,
            "status": "skipped",
            "reason": "A visual is already attached. Set replace_existing=true to redirect it.",
        }
    plan = build_scene_visual_plan(scene)
    guard = VisualDiversityGuard.from_project(scene.project, ignore_existing=replace_existing)
    result = _execute_scene(scene, plan, per_page, db, guard)
    refresh_project_manifests(db.get_bind(), [scene.project_id])
    result["plan"] = visual_plan_payload(plan)
    return result


@router.post("/projects/{project_id}/visual-architecture-execute")
def execute_project_visual_architecture(
    project_id: int,
    replace_existing: bool = Query(default=False),
    per_page: int = Query(default=6, ge=3, le=12),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    project = _project(project_id, db)
    entries: list[dict[str, object]] = []
    completed = skipped = failed = 0
    guard = VisualDiversityGuard.from_project(project, ignore_existing=replace_existing)

    for scene, plan in _project_plans(project):
        if scene.selected_asset is not None and not replace_existing:
            skipped += 1
            entries.append(
                {
                    "scene_id": scene.id,
                    "scene_number": scene.scene_number,
                    "status": "skipped",
                    "execution_mode": plan.asset.execution_mode.value,
                    "visual_family": plan.strategy.family.value,
                    "reason": "Existing visual preserved.",
                }
            )
            continue
        try:
            entries.append(_execute_scene(scene, plan, per_page, db, guard))
            completed += 1
        except HTTPException as exc:
            failed += 1
            entries.append(
                {
                    "scene_id": scene.id,
                    "scene_number": scene.scene_number,
                    "status": "failed",
                    "execution_mode": plan.asset.execution_mode.value,
                    "visual_family": plan.strategy.family.value,
                    "reason": str(exc.detail),
                }
            )

    refresh_project_manifests(db.get_bind(), [project.id])
    return {
        "project_id": project.id,
        "project_title": project.title,
        "scene_count": len(project.scenes),
        "completed": completed,
        "skipped": skipped,
        "failed": failed,
        "entries": entries,
        "diversity": {
            "unique_asset_count": len(guard.asset_ids),
            "unique_exact_template_count": len(guard.exact_templates),
        },
    }
