from __future__ import annotations

"""Bind the diverse Shorts narration plan to scene and exact-visual selection."""

from typing import Any

from . import cartoon_documentary as cartoon
from . import exact_visuals as exact
from . import shorts_story_clock as clock
from .video_format import SHORTS_FORMAT, project_video_format

_previous_exact_suggest = exact.suggest_template


def _manifest_templates(project) -> tuple[list[int], dict[int, str]]:
    manifest = clock._shorts_manifest(project)
    if manifest is None:
        return [], {}
    order = clock._selected_numbers(manifest)
    templates = {
        int(item.get("scene_number", 0)): str(item.get("template_id") or "")
        for item in manifest.get("segments", [])
        if int(item.get("scene_number", 0)) > 0
    }
    return order, templates


def _mark_selection(project, selected: set[int]) -> None:
    """Persist selected order and forced semantic role on every scene plan."""
    order, templates = _manifest_templates(project)
    order_index = {number: index + 1 for index, number in enumerate(order)}
    for scene in project.scenes:
        plan = dict(scene.animation_plan or {})
        is_selected = scene.scene_number in selected
        plan["shorts_selected"] = is_selected
        plan["shorts_story_order"] = order_index.get(scene.scene_number) if is_selected else None
        forced = templates.get(scene.scene_number, "") if is_selected else ""
        if forced in cartoon.TEMPLATE_BY_ID:
            plan["shorts_template_id"] = forced
        else:
            plan.pop("shorts_template_id", None)
        scene.animation_plan = plan


def _forced_template(scene) -> str:
    if project_video_format(scene) != SHORTS_FORMAT:
        return ""
    plan = dict(getattr(scene, "animation_plan", None) or {})
    candidate = str(plan.get("shorts_template_id") or "")
    return candidate if candidate in cartoon.TEMPLATE_BY_ID else ""


def suggest_template(scene, family_id: str):
    forced = _forced_template(scene)
    if family_id == exact.TECH_FAMILY_ID and forced:
        return (
            cartoon.TEMPLATE_BY_ID[forced],
            1.0,
            f"The independent Shorts story plan requires the {forced} visual role.",
        )
    return _previous_exact_suggest(scene, family_id)


clock._mark_selection = _mark_selection
exact.suggest_template = suggest_template
