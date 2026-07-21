from __future__ import annotations

import hashlib
from collections.abc import Sequence

from .types import (
    CameraMove,
    Composition,
    SceneIntent,
    ShotPlan,
    ShotType,
    VisualFamily,
    VisualStrategy,
)


def _pick(values: tuple, seed: str):
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return values[int.from_bytes(digest[:4], "big") % len(values)]


def plan_shot(
    intent: SceneIntent,
    strategy: VisualStrategy,
    scene_key: str,
    recent_compositions: Sequence[Composition | str] = (),
) -> ShotPlan:
    family = strategy.family
    shot_options = {
        VisualFamily.CINEMATIC_REAL_WORLD: (
            ShotType.CLOSE_UP,
            ShotType.MEDIUM,
            ShotType.WIDE,
            ShotType.OVER_SHOULDER,
        ),
        VisualFamily.INTERFACE_OBSERVATIONAL: (
            ShotType.OVER_SHOULDER,
            ShotType.INSERT,
            ShotType.EXTREME_CLOSE_UP,
        ),
        VisualFamily.DATA_EXPLAINER: (ShotType.OVERHEAD, ShotType.WIDE),
        VisualFamily.TIMELINE_HISTORICAL: (ShotType.WIDE, ShotType.INSERT),
        VisualFamily.COMPARISON_CONTRAST: (ShotType.MEDIUM, ShotType.WIDE),
        VisualFamily.CONCLUSION_CTA: (ShotType.WIDE, ShotType.MEDIUM),
        VisualFamily.EDITORIAL_SYMBOLIC: (ShotType.WIDE, ShotType.MEDIUM, ShotType.CLOSE_UP),
    }[family]
    composition_options = {
        VisualFamily.CINEMATIC_REAL_WORLD: (
            Composition.LEFT_WEIGHTED,
            Composition.RIGHT_WEIGHTED,
            Composition.FRAME_WITHIN_FRAME,
            Composition.DIAGONAL,
        ),
        VisualFamily.INTERFACE_OBSERVATIONAL: (
            Composition.FRAME_WITHIN_FRAME,
            Composition.DIAGONAL,
            Composition.RIGHT_WEIGHTED,
        ),
        VisualFamily.DATA_EXPLAINER: (
            Composition.DIAGONAL,
            Composition.SPLIT_DEPTH,
        ),
        VisualFamily.TIMELINE_HISTORICAL: (
            Composition.DIAGONAL,
            Composition.LEFT_WEIGHTED,
        ),
        VisualFamily.COMPARISON_CONTRAST: (
            Composition.SPLIT_DEPTH,
            Composition.DIAGONAL,
        ),
        VisualFamily.CONCLUSION_CTA: (
            Composition.LAYERED_CENTER,
            Composition.LEFT_WEIGHTED,
        ),
        VisualFamily.EDITORIAL_SYMBOLIC: (
            Composition.DIAGONAL,
            Composition.SPLIT_DEPTH,
            Composition.RIGHT_WEIGHTED,
        ),
    }[family]
    movement_options = {
        VisualFamily.CINEMATIC_REAL_WORLD: (
            CameraMove.SLOW_PUSH,
            CameraMove.LATERAL_DRIFT,
            CameraMove.PARALLAX_REVEAL,
        ),
        VisualFamily.INTERFACE_OBSERVATIONAL: (
            CameraMove.SLOW_PUSH,
            CameraMove.CONTROLLED_PAN,
        ),
        VisualFamily.DATA_EXPLAINER: (
            CameraMove.LOCKED_TENSION,
            CameraMove.CONTROLLED_PAN,
        ),
        VisualFamily.TIMELINE_HISTORICAL: (
            CameraMove.CONTROLLED_PAN,
            CameraMove.PULL_BACK,
        ),
        VisualFamily.COMPARISON_CONTRAST: (
            CameraMove.LATERAL_DRIFT,
            CameraMove.LOCKED_TENSION,
        ),
        VisualFamily.CONCLUSION_CTA: (
            CameraMove.PULL_BACK,
            CameraMove.SLOW_PUSH,
        ),
        VisualFamily.EDITORIAL_SYMBOLIC: (
            CameraMove.PARALLAX_REVEAL,
            CameraMove.SLOW_PUSH,
        ),
    }[family]

    composition = _pick(composition_options, f"{scene_key}:composition")
    recent = tuple(Composition(value) for value in recent_compositions[-2:])
    if recent.count(composition) >= 1 and len(composition_options) > 1:
        index = (composition_options.index(composition) + 1) % len(composition_options)
        composition = composition_options[index]

    focal = (
        intent.subject_terms[0]
        if intent.subject_terms
        else intent.concept_terms[0]
        if intent.concept_terms
        else "human consequence"
    )
    secondary = tuple(dict.fromkeys((*intent.action_terms, *intent.concept_terms)))[:3]
    setting = intent.setting_terms[0] if intent.setting_terms else "contextual environment"
    foreground = "soft practical foreground object or silhouette"
    background = setting if family != VisualFamily.DATA_EXPLAINER else "subtle evidence field"
    atmosphere = {
        "urgent": "high contrast, compressed space, directional light",
        "ominous": "low-key light, haze, restrained highlights",
        "hopeful": "warm edge light, open depth, gentle movement",
        "reflective": "soft falloff, negative space around the subject",
        "curious": "controlled contrast, layered discovery, quiet motion",
    }[intent.emotional_tone]

    return ShotPlan(
        shot_type=_pick(shot_options, f"{scene_key}:shot"),
        composition=composition,
        camera_move=_pick(movement_options, f"{scene_key}:move"),
        focal_subject=focal,
        secondary_subjects=secondary,
        foreground=foreground,
        background=background,
        atmosphere=atmosphere,
        depth_layers=max(3, strategy.minimum_depth_layers),
    )
