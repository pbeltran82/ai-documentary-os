from __future__ import annotations

import os
import re
from typing import Any, Callable

from fastapi import HTTPException

from .cinematic_renderer import (
    CINEMATIC_RENDERERS,
    cinematic_beat_indicator,
    cinematic_common,
)
from .types import ExecutionMode, VisualFamily
from .visual_pipeline import build_scene_visual_plan

_INSTALLED = False
_ORIGINAL_EXECUTE_SCENE: Callable[..., dict[str, object]] | None = None
_ORIGINAL_RENDER_EXACT_VISUAL: Callable[..., Any] | None = None
_WORD_RE = re.compile(r"[a-z0-9']+")

_TECH_RESCUE_TERMS = {
    "algorithm",
    "attention",
    "behavior",
    "behaviour",
    "choice",
    "click",
    "control",
    "data",
    "feed",
    "model",
    "predict",
    "prediction",
    "profile",
    "rank",
    "ranking",
    "recommend",
    "recommendation",
    "scroll",
    "signal",
    "system",
}
_RANKING_TERMS = {
    "rank",
    "ranks",
    "ranked",
    "ranking",
    "rankings",
    "recommend",
    "recommends",
    "recommended",
    "recommendation",
    "feed",
}
_SIGNAL_TERMS = {
    "signal",
    "signals",
    "feedback",
    "change",
    "changes",
    "changed",
    "prediction",
    "predict",
    "behavior",
    "behaviour",
}
_AUCTION_TERMS = {"attention", "auction", "bid", "bids", "advertiser", "advertising"}


def _scene_terms(scene) -> set[str]:
    selected = getattr(scene, "selected_asset", None)
    values = [
        str(getattr(scene, "narration", "") or ""),
        str(getattr(scene, "visual_intent", "") or ""),
        *[str(item) for item in (getattr(scene, "search_keywords", ()) or ())],
        str(getattr(selected, "provider_asset_id", "") or ""),
        str(getattr(selected, "source_url", "") or ""),
        str(getattr(selected, "local_path", "") or ""),
    ]
    return set(_WORD_RE.findall(" ".join(values).lower().replace("_", " ")))


def _template_for_plan(plan) -> str:
    family = plan.strategy.family
    intent = plan.intent
    if family == VisualFamily.CONCLUSION_CTA:
        return "machine_choice_cta"
    if family == VisualFamily.COMPARISON_CONTRAST:
        return "machine_choice_explainer"
    if family == VisualFamily.TIMELINE_HISTORICAL:
        return "life_event_timeline"
    if family == VisualFamily.INTERFACE_OBSERVATIONAL:
        if {"scroll", "click", "search", "digital"} & set(intent.action_terms + intent.concept_terms):
            return "digital_footprint_collector"
        return "algorithm_chose_you"
    if family == VisualFamily.DATA_EXPLAINER:
        return "behavior_prediction_engine"
    if family == VisualFamily.CINEMATIC_REAL_WORLD:
        return "digital_footprint_collector" if intent.interface_score else "behavioral_twin"
    return "behavioral_twin"


def _architectural_suggest_template(scene):
    from .. import tech_behavior_motion as tech

    plan = build_scene_visual_plan(scene)
    template_id = _template_for_plan(plan)
    template = tech.TEMPLATE_BY_ID[template_id]
    confidence = 0.9 if plan.intent.human_score + plan.intent.interface_score + plan.intent.data_score >= 2 else 0.78
    reason = (
        f"Visual Architecture selected {plan.strategy.family.value}; "
        f"{plan.strategy.reason} Shot: {plan.shot.shot_type.value}, "
        f"{plan.shot.composition.value}, {plan.shot.camera_move.value}."
    )
    return template, confidence, reason


def _eligible_for_hyperframes_rescue(scene, plan) -> bool:
    if plan.asset.execution_mode != ExecutionMode.ASSET_FIRST:
        return False
    terms = _scene_terms(scene)
    concept_terms = set(plan.intent.concept_terms)
    return bool(
        terms & _TECH_RESCUE_TERMS
        or plan.intent.interface_score
        or plan.intent.data_score
        or concept_terms & {"attention", "behavior", "prediction", "choice", "control", "technology"}
    )


def _rescue_template_for_scene(scene, plan) -> str:
    """Choose a distinct cinematic system when real-media search cannot defend a result."""
    terms = _scene_terms(scene)
    if terms & _RANKING_TERMS:
        return "machine_choice_explainer"
    if terms & _AUCTION_TERMS:
        return "attention_auction"
    if terms & _SIGNAL_TERMS:
        return "consequence_map"
    if plan.intent.interface_score:
        return "machine_choice_explainer"
    return "consequence_map"


def _is_legacy_tech_visual(scene) -> bool:
    selected = getattr(scene, "selected_asset", None)
    provider = str(getattr(selected, "provider", "") or "").lower()
    source_url = str(getattr(selected, "source_url", "") or "").lower()
    return provider == "generated" and source_url.startswith(
        "local://exact-visual/tech_behavior_motion/"
    )


def _is_hyperframes_visual(scene) -> bool:
    selected = getattr(scene, "selected_asset", None)
    provider = str(getattr(selected, "provider", "") or "").lower()
    source_url = str(getattr(selected, "source_url", "") or "").lower()
    return provider == "hyperframes" and source_url.startswith("local://hyperframes/")


def _run_hyperframes_rescue(
    scene,
    plan,
    db,
    guard,
    *,
    original_status: int,
    original_detail: str,
) -> dict[str, object]:
    from ...routers import visual_architecture as visual_router
    from .. import hyperframes_renderer
    from .diversity_guard import VisualDiversityGuard, choose_unused_exact_template

    active_guard = guard or VisualDiversityGuard()
    project = getattr(scene, "project", None)
    if project is not None:
        active_guard.merge(
            VisualDiversityGuard.from_project(project, ignore_scene_id=scene.id)
        )

    family_id = "tech_behavior_motion"
    preferred_template = _rescue_template_for_scene(scene, plan)
    template_id = choose_unused_exact_template(family_id, preferred_template, active_guard)
    if (
        not hyperframes_renderer.enabled()
        or template_id is None
        or not hyperframes_renderer.supports(family_id, template_id)
    ):
        raise HTTPException(status_code=original_status, detail=original_detail)

    try:
        asset = visual_router._store_hyperframes_asset(scene, family_id, template_id, db)
    except Exception as rescue_error:
        raise HTTPException(
            status_code=original_status,
            detail=(
                f"{original_detail} HyperFrames rescue also failed: "
                f"{type(rescue_error).__name__}: {rescue_error}"
            ),
        ) from rescue_error

    active_guard.register_exact(family_id, template_id)
    return {
        "scene_id": scene.id,
        "scene_number": scene.scene_number,
        "status": "completed",
        "execution_mode": ExecutionMode.EXACT_VISUAL.value,
        "fallback_from": ExecutionMode.ASSET_FIRST.value,
        "visual_family": plan.strategy.family.value,
        "exact_family_id": family_id,
        "exact_template_id": template_id,
        "exact_renderer": "hyperframes_rescue",
        "provider": asset.provider,
        "media_type": asset.media_type,
        "provider_asset_id": asset.provider_asset_id,
        "reason": (
            "A legacy tech diagram or failed real-asset search was redirected to a "
            "distinct project-owned HyperFrames composition."
        ),
        "asset_first_failure": original_detail,
    }


def _execute_scene_with_hyperframes_rescue(
    scene,
    plan,
    per_page: int,
    db,
    guard=None,
) -> dict[str, object]:
    if _ORIGINAL_EXECUTE_SCENE is None:
        raise RuntimeError("Visual Architecture execution wrapper is not installed")

    if _is_legacy_tech_visual(scene):
        return _run_hyperframes_rescue(
            scene,
            plan,
            db,
            guard,
            original_status=422,
            original_detail=(
                "Existing legacy Tech & Behavior Motion diagram scheduled for a "
                "HyperFrames cinematic upgrade."
            ),
        )

    if (
        _is_hyperframes_visual(scene)
        and plan.asset.execution_mode == ExecutionMode.ASSET_FIRST
    ):
        return _run_hyperframes_rescue(
            scene,
            plan,
            db,
            guard,
            original_status=422,
            original_detail=(
                "Existing HyperFrames Tech & Behavior Motion scene scheduled for a "
                "distinct cinematic redirect."
            ),
        )

    try:
        return _ORIGINAL_EXECUTE_SCENE(scene, plan, per_page, db, guard)
    except HTTPException as original_error:
        if original_error.status_code not in {422, 502} or not _eligible_for_hyperframes_rescue(scene, plan):
            raise
        return _run_hyperframes_rescue(
            scene,
            plan,
            db,
            guard,
            original_status=original_error.status_code,
            original_detail=str(original_error.detail),
        )


def _render_exact_visual_preserving_hyperframes(scene, *args, **kwargs):
    """Prevent the legacy Exact Visual renderer from silently replacing HyperFrames."""
    selected = getattr(scene, "selected_asset", None)
    provider = str(getattr(selected, "provider", "") or "").lower()
    allow_override = os.getenv("ALLOW_LEGACY_REPLACE_HYPERFRAMES", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if provider == "hyperframes" and not allow_override:
        raise HTTPException(
            status_code=409,
            detail=(
                "This scene already has a protected HyperFrames asset. Use Visual Architecture "
                "to redirect it, or explicitly set ALLOW_LEGACY_REPLACE_HYPERFRAMES=1."
            ),
        )
    if _ORIGINAL_RENDER_EXACT_VISUAL is None:
        raise RuntimeError("Exact Visual protection wrapper is not installed")
    return _ORIGINAL_RENDER_EXACT_VISUAL(scene, *args, **kwargs)


def install_visual_architecture() -> None:
    """Install the shared cinematic system and safe HyperFrames integration hooks."""
    global _INSTALLED, _ORIGINAL_EXECUTE_SCENE, _ORIGINAL_RENDER_EXACT_VISUAL

    from .. import tech_behavior_motion as tech
    from ...routers import finance_motion as finance_router
    from ...routers import visual_architecture as visual_router

    tech.RENDERERS.update(CINEMATIC_RENDERERS)
    tech._common = cinematic_common
    tech._beat_indicator = cinematic_beat_indicator
    tech.suggest_template = _architectural_suggest_template

    if _ORIGINAL_EXECUTE_SCENE is None:
        _ORIGINAL_EXECUTE_SCENE = visual_router._execute_scene
        visual_router._execute_scene = _execute_scene_with_hyperframes_rescue

    if _ORIGINAL_RENDER_EXACT_VISUAL is None:
        _ORIGINAL_RENDER_EXACT_VISUAL = finance_router.render_exact_visual
        finance_router.render_exact_visual = _render_exact_visual_preserving_hyperframes

    _INSTALLED = True


def visual_architecture_installed() -> bool:
    return _INSTALLED
