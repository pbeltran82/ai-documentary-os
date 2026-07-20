from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Project, Scene
from ..schemas import AssetSelect
from ..services import finance_motion as finance_engine
from ..services.manifest_events import refresh_project_manifests
from ..services.visuals import (
    ExecutionMode,
    build_scene_visual_plan,
    build_visual_plan,
    visual_plan_payload,
)
from ..services.visuals.asset_first_executor import search_architecture_candidates
from .assets import select_asset
from .finance_motion import generate_exact_visual

router = APIRouter(tags=["visual-architecture"])


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
        payloads.append(
            ("preview_fallback", _candidate_payload(candidate, preview_fallback=True))
        )
    return payloads


def _candidate_responses(scene: Scene, plan, per_page: int):
    media_types = [plan.asset.preferred_media_type]
    if (
        plan.asset.fallback_media_type
        and plan.asset.fallback_media_type not in media_types
    ):
        media_types.append(plan.asset.fallback_media_type)
    return [
        search_architecture_candidates(scene, plan, media_type, per_page)
        for media_type in media_types
    ]


def _select_asset_first(scene: Scene, plan, per_page: int, db: Session):
    responses = _candidate_responses(scene, plan, per_page)
    attempted: set[tuple[str, str]] = set()
    download_failures: list[dict[str, str]] = []
    candidate_count = 0

    for response in responses:
        for candidate in response.candidates:
            identity = (candidate.provider, candidate.provider_asset_id)
            if identity in attempted:
                continue
            attempted.add(identity)
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
                return asset, candidate, response, download_failures

    if candidate_count == 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "No defensible real visual survived the architecture brief, provider, "
                "rights, concept, quality, and diversity gates."
            ),
        )

    last_details = "; ".join(
        (
            f"{failure['provider']}:{failure['source_kind']} "
            f"{failure['detail']}"
        )
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


def _execute_scene(scene: Scene, plan, per_page: int, db: Session) -> dict[str, object]:
    if plan.asset.execution_mode == ExecutionMode.ASSET_FIRST:
        asset, candidate, response, download_failures = _select_asset_first(
            scene,
            plan,
            per_page,
            db,
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
            "reason": plan.asset.reason,
        }

    ffmpeg = _resolve_ffmpeg_binary()
    if ffmpeg is not None:
        finance_engine.FFMPEG_NAME = ffmpeg
    asset = generate_exact_visual(
        scene_id=scene.id,
        family_id=None,
        template_id=None,
        style_id=None,
        defer_manifest=True,
        db=db,
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
    result = _execute_scene(scene, plan, per_page, db)
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
            entries.append(_execute_scene(scene, plan, per_page, db))
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
    }
