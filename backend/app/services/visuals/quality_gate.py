from __future__ import annotations

from PIL import Image, ImageFilter

from .types import QualityDecision, QualityMetrics, VisualFamily, VisualStrategy


def measure_edge_density(image: Image.Image) -> float:
    """Estimate whether a frame contains enough visual structure to avoid emptiness."""
    sample = image.convert("L").resize((192, 108), Image.Resampling.BILINEAR)
    edges = sample.filter(ImageFilter.FIND_EDGES)
    histogram = edges.histogram()
    active = sum(histogram[24:])
    total = max(1, sample.width * sample.height)
    return round(active / total, 4)


def evaluate_visual_quality(
    metrics: QualityMetrics,
    strategy: VisualStrategy,
) -> QualityDecision:
    """Reject slide-like frames before they become final documentary assets."""
    score = 100
    reasons: list[str] = []

    if metrics.text_words > strategy.text_budget_words:
        overflow = metrics.text_words - strategy.text_budget_words
        score -= min(30, overflow * 4)
        reasons.append("on-screen text exceeds the visual family's text budget")
    if metrics.label_count > strategy.max_labels:
        score -= min(22, (metrics.label_count - strategy.max_labels) * 6)
        reasons.append("too many explanatory labels")
    if metrics.panel_count >= 3:
        score -= min(24, (metrics.panel_count - 2) * 8)
        reasons.append("repeated panels make the composition resemble a slide")
    if metrics.arrow_count >= 3:
        score -= min(18, (metrics.arrow_count - 2) * 5)
        reasons.append("too many arrows are carrying the story")
    if metrics.centered_elements >= 4:
        score -= min(18, (metrics.centered_elements - 3) * 5)
        reasons.append("the layout is overly centered and presentation-like")
    if strategy.requires_subject and metrics.subject_count < 1:
        score -= 28
        reasons.append("the scene needs a clear visual subject")
    if metrics.depth_layers < strategy.minimum_depth_layers:
        score -= 18
        reasons.append("the scene lacks foreground, subject, and background separation")
    if metrics.motion_cues < 1:
        score -= 10
        reasons.append("the scene has no meaningful motion direction")
    if metrics.empty_space_ratio > 0.58:
        score -= 18
        reasons.append("too much unstructured empty space")
    if metrics.edge_density and metrics.edge_density < 0.035:
        score -= 12
        reasons.append("the frame is visually underdeveloped")

    accepted = score >= 72 and not (
        strategy.requires_subject and metrics.subject_count < 1
    )
    retry_family = None
    if not accepted:
        retry_family = (
            VisualFamily.CINEMATIC_REAL_WORLD
            if strategy.family in {VisualFamily.DATA_EXPLAINER, VisualFamily.INTERFACE_OBSERVATIONAL}
            else VisualFamily.EDITORIAL_SYMBOLIC
        )
    return QualityDecision(
        accepted=accepted,
        score=max(0, score),
        reasons=tuple(reasons),
        retry_family=retry_family,
    )
