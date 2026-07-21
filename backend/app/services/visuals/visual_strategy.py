from __future__ import annotations

from collections.abc import Sequence

from .types import (
    RealismLevel,
    SceneIntent,
    SourceMode,
    VisualFamily,
    VisualStrategy,
)


def choose_visual_strategy(
    intent: SceneIntent,
    recent_families: Sequence[VisualFamily | str] = (),
) -> VisualStrategy:
    """Choose a reusable documentary visual family and source mode.

    Human, environmental, interface, historical, comparison, and metaphor scenes
    prefer real footage or photography. Procedural graphics are reserved for
    narration that truly depends on quantities, a process, or the final CTA.
    """
    recent = tuple(VisualFamily(value) for value in recent_families[-2:])

    if intent.closing:
        family = VisualFamily.CONCLUSION_CTA
        reason = "The scene resolves the story, so it needs a thesis-led cinematic close."
    elif intent.comparison_score >= 2:
        family = VisualFamily.COMPARISON_CONTRAST
        reason = "The narration explicitly contrasts alternatives or states."
    elif intent.historical_score >= 2 and intent.data_score >= 1:
        family = VisualFamily.TIMELINE_HISTORICAL
        reason = "Historical evidence and time progression are central to the scene."
    elif intent.human_score + intent.environmental_score >= 2:
        family = VisualFamily.CINEMATIC_REAL_WORLD
        reason = "A human subject in a recognizable environment can carry the idea visually."
    elif intent.interface_score >= 2:
        family = VisualFamily.INTERFACE_OBSERVATIONAL
        reason = "The scene is about behavior around a device or platform experience."
    elif intent.data_score >= 3:
        family = VisualFamily.DATA_EXPLAINER
        reason = "The narration depends on quantities, ranking, or process relationships."
    else:
        family = VisualFamily.EDITORIAL_SYMBOLIC
        reason = "A real-world metaphor can express the abstract idea without turning it into a slide."

    if family == VisualFamily.DATA_EXPLAINER and recent.count(VisualFamily.DATA_EXPLAINER) >= 1:
        family = VisualFamily.EDITORIAL_SYMBOLIC
        reason = "A repeated explainer layout was rerouted to an asset-led metaphor for pacing variety."
    elif len(recent) == 2 and recent[0] == recent[1] == family:
        family = (
            VisualFamily.EDITORIAL_SYMBOLIC
            if family != VisualFamily.EDITORIAL_SYMBOLIC
            else VisualFamily.CINEMATIC_REAL_WORLD
        )
        reason = "The composition family was changed to prevent three visually similar scenes in a row."

    settings = {
        VisualFamily.CINEMATIC_REAL_WORLD: (
            RealismLevel.REALISTIC,
            SourceMode.REAL_FOOTAGE,
            5,
            0,
            True,
            3,
        ),
        VisualFamily.EDITORIAL_SYMBOLIC: (
            RealismLevel.REALISTIC,
            SourceMode.PHOTOGRAPHY,
            6,
            1,
            True,
            3,
        ),
        VisualFamily.INTERFACE_OBSERVATIONAL: (
            RealismLevel.REALISTIC,
            SourceMode.REAL_FOOTAGE,
            5,
            1,
            True,
            3,
        ),
        VisualFamily.DATA_EXPLAINER: (
            RealismLevel.EDITORIAL_GRAPHIC,
            SourceMode.PROCEDURAL_GRAPHIC,
            10,
            4,
            False,
            2,
        ),
        VisualFamily.TIMELINE_HISTORICAL: (
            RealismLevel.REALISTIC,
            SourceMode.PHOTOGRAPHY,
            7,
            2,
            True,
            3,
        ),
        VisualFamily.COMPARISON_CONTRAST: (
            RealismLevel.REALISTIC,
            SourceMode.HYBRID_COMPOSITE,
            6,
            1,
            True,
            3,
        ),
        VisualFamily.CONCLUSION_CTA: (
            RealismLevel.CINEMATIC_STYLIZED,
            SourceMode.PROCEDURAL_GRAPHIC,
            9,
            1,
            True,
            3,
        ),
    }
    realism, source_mode, text_budget, max_labels, requires_subject, depth = settings[family]
    return VisualStrategy(
        family=family,
        realism=realism,
        source_mode=source_mode,
        text_budget_words=text_budget,
        max_labels=max_labels,
        requires_subject=requires_subject,
        minimum_depth_layers=depth,
        reason=reason,
    )
