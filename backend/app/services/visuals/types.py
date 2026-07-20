from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VisualFamily(str, Enum):
    CINEMATIC_REAL_WORLD = "cinematic_real_world"
    EDITORIAL_SYMBOLIC = "editorial_symbolic"
    INTERFACE_OBSERVATIONAL = "interface_observational"
    DATA_EXPLAINER = "data_explainer"
    TIMELINE_HISTORICAL = "timeline_historical"
    COMPARISON_CONTRAST = "comparison_contrast"
    CONCLUSION_CTA = "conclusion_cta"


class RealismLevel(str, Enum):
    REALISTIC = "realistic"
    CINEMATIC_STYLIZED = "cinematic_stylized"
    EDITORIAL_GRAPHIC = "editorial_graphic"


class SourceMode(str, Enum):
    REAL_FOOTAGE = "real_footage"
    PHOTOGRAPHY = "photography"
    HYBRID_COMPOSITE = "hybrid_composite"
    RENDERED_INTERFACE = "rendered_interface"
    PROCEDURAL_GRAPHIC = "procedural_graphic"


class ExecutionMode(str, Enum):
    ASSET_FIRST = "asset_first"
    EXACT_VISUAL = "exact_visual"


class ShotType(str, Enum):
    EXTREME_CLOSE_UP = "extreme_close_up"
    CLOSE_UP = "close_up"
    MEDIUM = "medium"
    WIDE = "wide"
    OVER_SHOULDER = "over_shoulder"
    OVERHEAD = "overhead"
    INSERT = "insert"


class Composition(str, Enum):
    LEFT_WEIGHTED = "left_weighted"
    RIGHT_WEIGHTED = "right_weighted"
    DIAGONAL = "diagonal"
    LAYERED_CENTER = "layered_center"
    SPLIT_DEPTH = "split_depth"
    FRAME_WITHIN_FRAME = "frame_within_frame"


class CameraMove(str, Enum):
    SLOW_PUSH = "slow_push"
    LATERAL_DRIFT = "lateral_drift"
    PARALLAX_REVEAL = "parallax_reveal"
    CONTROLLED_PAN = "controlled_pan"
    LOCKED_TENSION = "locked_tension"
    PULL_BACK = "pull_back"


@dataclass(frozen=True)
class SceneIntent:
    subject_terms: tuple[str, ...]
    action_terms: tuple[str, ...]
    setting_terms: tuple[str, ...]
    concept_terms: tuple[str, ...]
    human_score: int
    environmental_score: int
    interface_score: int
    data_score: int
    comparison_score: int
    historical_score: int
    emotional_tone: str
    closing: bool


@dataclass(frozen=True)
class VisualStrategy:
    family: VisualFamily
    realism: RealismLevel
    source_mode: SourceMode
    text_budget_words: int
    max_labels: int
    requires_subject: bool
    minimum_depth_layers: int
    reason: str


@dataclass(frozen=True)
class ShotPlan:
    shot_type: ShotType
    composition: Composition
    camera_move: CameraMove
    focal_subject: str
    secondary_subjects: tuple[str, ...]
    foreground: str
    background: str
    atmosphere: str
    depth_layers: int


@dataclass(frozen=True)
class AssetDirective:
    execution_mode: ExecutionMode
    preferred_media_type: str
    fallback_media_type: str | None
    overlay_mode: str
    search_terms: tuple[str, ...]
    avoid_terms: tuple[str, ...]
    allow_generated_still: bool
    reason: str


@dataclass(frozen=True)
class VisualPlan:
    intent: SceneIntent
    strategy: VisualStrategy
    shot: ShotPlan
    asset: AssetDirective


@dataclass(frozen=True)
class QualityMetrics:
    text_words: int = 0
    label_count: int = 0
    panel_count: int = 0
    arrow_count: int = 0
    centered_elements: int = 0
    subject_count: int = 0
    depth_layers: int = 1
    motion_cues: int = 0
    empty_space_ratio: float = 0.0
    edge_density: float = 0.0


@dataclass(frozen=True)
class QualityDecision:
    accepted: bool
    score: int
    reasons: tuple[str, ...]
    retry_family: VisualFamily | None = None
