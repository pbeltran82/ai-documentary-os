from __future__ import annotations

from dataclasses import replace

from .types import (
    AssetDirective,
    CameraMove,
    Composition,
    ExecutionMode,
    RealismLevel,
    ShotPlan,
    ShotType,
    SourceMode,
    VisualFamily,
    VisualPlan,
    VisualStrategy,
)

_PROJECT_TITLE = "how algorithms shape your attention"

# This is an approved editorial map, not a narration-keyword heuristic. It keeps
# the working renderer stable while allowing the director to lock meaning-critical
# scenes to concrete real-world briefs or exact HyperFrames systems.
_SCENE_OVERRIDES: dict[int, dict[str, object]] = {
    1: {
        "mode": "asset_first",
        "search_terms": (
            "person opening smartphone app notifications",
            "multiple app notifications competing on phone",
            "close up smartphone notification screen",
        ),
        "preferred_media_type": "video",
        "focal_subject": "person opening an app on a smartphone",
    },
    2: {"mode": "exact_visual", "template_id": "attention_auction"},
    3: {
        "mode": "asset_first",
        "search_terms": (
            "person scrolling smartphone over shoulder",
            "close up finger interacting with phone feed",
            "smartphone user pausing on social media video",
        ),
        "preferred_media_type": "video",
        "focal_subject": "person interacting with a recommendation feed",
    },
    4: {
        "mode": "asset_first",
        "search_terms": (
            "person face beside data profile screen",
            "human using phone with algorithm data overlay",
            "person compared with digital behavioral profile",
        ),
        "preferred_media_type": "video",
        "focal_subject": "human beside an abstract behavioral model",
    },
    6: {
        "mode": "asset_first",
        "search_terms": (
            "macro finger scrolling smartphone feed",
            "finger pausing and replaying phone video",
            "close up thumb scrolling social media",
        ),
        "preferred_media_type": "video",
        "focal_subject": "finger pausing on a smartphone feed",
    },
    7: {
        "mode": "asset_first",
        "search_terms": (
            "behavioral data profile forming on screen",
            "digital identity data points around person",
            "person silhouette with data visualization",
        ),
        "preferred_media_type": "video",
        "focal_subject": "behavioral signals forming a digital profile",
    },
    8: {"mode": "exact_visual", "template_id": "behavior_prediction_engine"},
    9: {
        "mode": "asset_first",
        "search_terms": (
            "personalized social media feed on smartphone",
            "recommendation feed adapting on phone screen",
            "person scrolling customized video feed",
        ),
        "preferred_media_type": "video",
        "focal_subject": "personalized recommendation feed adapting",
        "avoid_terms": (
            "food",
            "meal",
            "restaurant",
            "animal feed",
            "livestock feed",
        ),
    },
    10: {"mode": "exact_visual", "template_id": "consequence_map"},
    11: {
        "mode": "asset_first",
        "search_terms": (
            "multiple notifications competing for attention",
            "person surrounded by phone alerts and screens",
            "digital advertising attention competition",
        ),
        "preferred_media_type": "video",
        "focal_subject": "notifications and screens competing for attention",
    },
    12: {"mode": "exact_visual", "template_id": "algorithm_chose_you"},
    13: {"mode": "exact_visual", "template_id": "machine_choice_cta"},
}


def _matches_project(scene) -> bool:
    project = getattr(scene, "project", None)
    title = str(getattr(project, "title", "") or "").strip().lower()
    return title == _PROJECT_TITLE


def scene_override(scene) -> dict[str, object] | None:
    if not _matches_project(scene):
        return None
    return _SCENE_OVERRIDES.get(int(getattr(scene, "scene_number", 0) or 0))


def exact_template_override(scene) -> str | None:
    override = scene_override(scene)
    if not override or override.get("mode") != "exact_visual":
        return None
    return str(override.get("template_id") or "") or None


def forces_asset_first(scene) -> bool:
    override = scene_override(scene)
    return bool(override and override.get("mode") == "asset_first")


def apply_scene_override(scene, plan: VisualPlan) -> VisualPlan:
    override = scene_override(scene)
    if not override:
        return plan

    mode = str(override["mode"])
    if mode == "exact_visual":
        template_id = str(override["template_id"])
        family = (
            VisualFamily.CONCLUSION_CTA
            if template_id == "machine_choice_cta"
            else VisualFamily.DATA_EXPLAINER
        )
        strategy = VisualStrategy(
            family=family,
            realism=RealismLevel.EDITORIAL_GRAPHIC,
            source_mode=SourceMode.PROCEDURAL_GRAPHIC,
            text_budget_words=10,
            max_labels=5,
            requires_subject=False,
            minimum_depth_layers=3,
            reason=f"Approved editorial map locks this scene to {template_id}.",
        )
        asset = replace(
            plan.asset,
            execution_mode=ExecutionMode.EXACT_VISUAL,
            preferred_media_type="video",
            fallback_media_type=None,
            overlay_mode="native_explainer",
            allow_generated_still=False,
            reason=f"Approved editorial map requires HyperFrames template {template_id}.",
        )
        return replace(plan, strategy=strategy, asset=asset)

    search_terms = tuple(str(value) for value in override.get("search_terms", ()))
    extra_avoid = tuple(str(value) for value in override.get("avoid_terms", ()))
    asset = AssetDirective(
        execution_mode=ExecutionMode.ASSET_FIRST,
        preferred_media_type=str(override.get("preferred_media_type") or "video"),
        fallback_media_type="photo",
        overlay_mode="restrained_editorial_overlay",
        search_terms=search_terms,
        avoid_terms=tuple(dict.fromkeys((*plan.asset.avoid_terms, *extra_avoid))),
        allow_generated_still=True,
        reason="Approved editorial brief replaces weak narration-keyword search terms.",
    )
    shot = ShotPlan(
        shot_type=ShotType.OVER_SHOULDER,
        composition=Composition.FRAME_WITHIN_FRAME,
        camera_move=CameraMove.SLOW_PUSH,
        focal_subject=str(override.get("focal_subject") or plan.shot.focal_subject),
        secondary_subjects=(),
        foreground="human hand, phone edge, or practical foreground layer",
        background="credible everyday digital environment",
        atmosphere="restrained documentary contrast with subtle technology context",
        depth_layers=3,
    )
    strategy = VisualStrategy(
        family=VisualFamily.CINEMATIC_REAL_WORLD,
        realism=RealismLevel.REALISTIC,
        source_mode=SourceMode.REAL_FOOTAGE,
        text_budget_words=0,
        max_labels=0,
        requires_subject=True,
        minimum_depth_layers=3,
        reason="Approved editorial brief requires a concrete observable real-world shot.",
    )
    return replace(plan, strategy=strategy, shot=shot, asset=asset)
