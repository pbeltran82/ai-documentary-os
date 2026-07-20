from __future__ import annotations

from collections.abc import Sequence

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
    """Build one stable plan that any renderer or asset provider can execute."""
    intent = analyze_scene_intent(narration, visual_intent, search_keywords)
    strategy = choose_visual_strategy(intent, recent_families)
    shot = plan_shot(intent, strategy, scene_key, recent_compositions)
    return VisualPlan(intent=intent, strategy=strategy, shot=shot)


def build_scene_visual_plan(scene) -> VisualPlan:
    """Adapter for SQLAlchemy Scene without coupling the architecture to models."""
    return build_visual_plan(
        narration=str(scene.narration or ""),
        visual_intent=str(scene.visual_intent or ""),
        search_keywords=tuple(scene.search_keywords or ()),
        scene_key=f"project-{scene.project_id}-scene-{scene.scene_number}",
    )
