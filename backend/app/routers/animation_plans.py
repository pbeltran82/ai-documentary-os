from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Scene
from ..services.animation_script_director import build_animation_plan, ensure_animation_plan
from ..services.character_performance_library import plan_from_preset, preset_catalog

router = APIRouter(tags=["animation-script-director"])


@router.get("/character-studio/performance-presets")
def performance_presets() -> list[dict[str, Any]]:
    return preset_catalog()


def _scene(scene_id: int, db: Session) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.get("/scenes/{scene_id}/animation-plan")
def get_animation_plan(scene_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    scene = _scene(scene_id, db)
    plan = ensure_animation_plan(scene)
    db.commit()
    return plan


@router.post("/scenes/{scene_id}/animation-plan/regenerate")
def regenerate_animation_plan(scene_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    scene = _scene(scene_id, db)
    scene.animation_plan = build_animation_plan(scene)
    db.commit()
    return scene.animation_plan


@router.post("/scenes/{scene_id}/animation-plan/apply-preset/{preset_id}")
def apply_performance_preset(
    scene_id: int,
    preset_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    scene = _scene(scene_id, db)
    try:
        scene.animation_plan = plan_from_preset(preset_id)
    except KeyError as error:
        raise HTTPException(status_code=422, detail="Unknown Character Studio preset") from error
    db.commit()
    return scene.animation_plan


@router.put("/scenes/{scene_id}/animation-plan")
def update_animation_plan(
    scene_id: int,
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    scene = _scene(scene_id, db)
    required = {"character_action", "expression_sequence", "pose_sequence", "camera_direction"}
    missing = sorted(required - payload.keys())
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing animation plan fields: {', '.join(missing)}")
    payload["version"] = "1.9.4"
    scene.animation_plan = payload
    db.commit()
    return scene.animation_plan
