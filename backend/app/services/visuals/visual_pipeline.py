from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict

from .asset_director import build_asset_directive
from .scene_intent import analyze_scene_intent
from .shot_planner import plan_shot
from .types import Composition, VisualFamily, VisualPlan
from .visual_strategy import choose_visual_strategy


def build_visual_plan(
    *,
    narration: str,
    visual_intent: str = "",
    search_keywords: tuple[str, ...] | list[str] = (),
    scene_key: str = "scene",
    recent_families: Sequence[VisualFamily | str] = (),
    recent_compositions: Sequence[Composition | str] = (),
) -> VisualPlan:
    """Build one stable plan that renderers and real-asset providers can execute."""
    intent = analyze_scene_intent(narration, visual_intent, search_keywords)
    strategy = choose_visual_strategy(intent, recent_families)
    shot = plan_shot(intent, strategy, scene_key, recent_compositions)
    asset = build_asset_directive(
        intent,
        strategy,
        shot,
        narration=narration,
        visual_intent=visual_intent,
        search_keywords=search_keywords,
    )
    return VisualPlan(intent=intent, strategy=strategy, shot=shot, asset=asset)


def build_scene_visual_plan(scene) -> VisualPlan:
    """Adapter for SQLAlchemy Scene without coupling the architecture to models."""
    return build_visual_plan(
        narration=str(scene.narration or ""),
        visual_intent=str(scene.visual_intent or ""),
        search_keywords=tuple(scene.search_keywords or ()),
        scene_key=f"project-{scene.project_id}-scene-{scene.scene_number}",
    )


def visual_plan_payload(plan: VisualPlan) -> dict[str, object]:
    """Return a JSON-safe architecture plan for API and production reporting."""
    payload = asdict(plan)
    payload["strategy"]["family"] = plan.strategy.family.value
    payload["strategy"]["realism"] = plan.strategy.realism.value
    payload["strategy"]["source_mode"] = plan.strategy.source_mode.value
    payload["shot"]["shot_type"] = plan.shot.shot_type.value
    payload["shot"]["composition"] = plan.shot.composition.value
    payload["shot"]["camera_move"] = plan.shot.camera_move.value
    payload["asset"]["execution_mode"] = plan.asset.execution_mode.value
    return payload
