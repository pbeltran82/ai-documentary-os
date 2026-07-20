from __future__ import annotations

from PIL import Image

from app.services.visuals import (
    ExecutionMode,
    QualityMetrics,
    SourceMode,
    VisualFamily,
    build_visual_plan,
    choose_visual_strategy,
    evaluate_visual_quality,
    install_visual_architecture,
    measure_edge_density,
    visual_architecture_installed,
    visual_plan_payload,
)
from app.services.visuals.scene_intent import analyze_scene_intent


def test_human_environment_defaults_to_real_asset_first() -> None:
    plan = build_visual_plan(
        narration="A worker checks her phone while walking through a crowded station.",
        visual_intent="Observe the person in a real environment, not a diagram.",
        scene_key="scene-1",
    )

    assert plan.strategy.family == VisualFamily.CINEMATIC_REAL_WORLD
    assert plan.strategy.source_mode == SourceMode.REAL_FOOTAGE
    assert plan.asset.execution_mode == ExecutionMode.ASSET_FIRST
    assert plan.asset.preferred_media_type == "video"
    assert plan.asset.fallback_media_type == "photo"
    assert plan.strategy.requires_subject is True
    assert plan.strategy.text_budget_words <= 5
    assert plan.shot.depth_layers >= 3


def test_interface_scene_prefers_observational_real_footage() -> None:
    plan = build_visual_plan(
        narration="The recommendation algorithm ranks the feed after every scroll and click.",
        visual_intent="Over-the-shoulder phone observation.",
        scene_key="scene-2",
    )

    assert plan.strategy.family == VisualFamily.INTERFACE_OBSERVATIONAL
    assert plan.strategy.source_mode == SourceMode.REAL_FOOTAGE
    assert plan.asset.execution_mode == ExecutionMode.ASSET_FIRST
    assert plan.strategy.max_labels <= 1


def test_data_explainer_reserves_procedural_rendering() -> None:
    plan = build_visual_plan(
        narration="A chart compares the ranking score, probability, rate, and model estimate.",
        scene_key="scene-data",
    )

    assert plan.strategy.family == VisualFamily.DATA_EXPLAINER
    assert plan.strategy.source_mode == SourceMode.PROCEDURAL_GRAPHIC
    assert plan.asset.execution_mode == ExecutionMode.EXACT_VISUAL
    assert plan.asset.fallback_media_type is None


def test_repeated_data_scene_is_rerouted_away_from_slide_repetition() -> None:
    intent = analyze_scene_intent(
        "A chart compares the ranking score, probability, rate, and model estimate."
    )
    first = choose_visual_strategy(intent)
    second = choose_visual_strategy(intent, [first.family])

    assert first.family == VisualFamily.DATA_EXPLAINER
    assert second.family == VisualFamily.EDITORIAL_SYMBOLIC
    assert second.source_mode == SourceMode.PHOTOGRAPHY


def test_shot_plan_is_deterministic_for_same_scene() -> None:
    first = build_visual_plan(
        narration="A person pauses at a glowing screen in a dark room.",
        scene_key="project-7-scene-3",
    )
    second = build_visual_plan(
        narration="A person pauses at a glowing screen in a dark room.",
        scene_key="project-7-scene-3",
    )

    assert first == second


def test_visual_plan_payload_is_json_safe() -> None:
    plan = build_visual_plan(
        narration="A family watches a phone together in their living room.",
        scene_key="payload-scene",
    )
    payload = visual_plan_payload(plan)

    assert payload["strategy"]["family"] == "cinematic_real_world"
    assert payload["strategy"]["source_mode"] == "real_footage"
    assert payload["asset"]["execution_mode"] == "asset_first"
    assert payload["shot"]["camera_move"]


def test_quality_gate_rejects_slide_like_frame() -> None:
    plan = build_visual_plan(
        narration="A viewer watches a recommendation feed on a phone.",
        scene_key="scene-quality",
    )
    decision = evaluate_visual_quality(
        QualityMetrics(
            text_words=38,
            label_count=8,
            panel_count=5,
            arrow_count=6,
            centered_elements=7,
            subject_count=0,
            depth_layers=1,
            motion_cues=0,
            empty_space_ratio=0.68,
        ),
        plan.strategy,
    )

    assert decision.accepted is False
    assert decision.score < 72
    assert decision.retry_family is not None
    assert any("slide" in reason for reason in decision.reasons)


def test_edge_density_measurement_distinguishes_empty_frame() -> None:
    empty = Image.new("RGB", (1920, 1080), (8, 10, 18))
    assert measure_edge_density(empty) < 0.02


def test_runtime_registration_is_idempotent_and_renders_cinematic_frame() -> None:
    from app.services import tech_behavior_motion as tech
    from app.services.visuals.cinematic_renderer import render_behavioral_twin

    install_visual_architecture()
    install_visual_architecture()

    assert visual_architecture_installed() is True
    assert tech.RENDERERS["behavioral_twin"] is render_behavioral_twin

    frame = tech.render_frame(
        "behavioral_twin",
        duration_seconds=4.0,
        time_seconds=2.0,
        style_id="editorial_documentary",
    )
    assert frame.size == (1920, 1080)
    assert measure_edge_density(frame) > 0.02
