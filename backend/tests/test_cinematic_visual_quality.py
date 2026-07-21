from __future__ import annotations

import unittest

from app.services.cinematic_visual_quality import (
    PROCESS_DIAGRAM,
    SlideQualitySignals,
    choose_cinematic_template,
    layout_family,
    shorten_headline,
    slide_likeness,
)
from app.services.tech_behavior_motion import TEMPLATE_BY_ID


class CinematicVisualQualityTests(unittest.TestCase):
    def test_no_more_than_two_consecutive_layouts(self) -> None:
        scored = [
            (100, TEMPLATE_BY_ID["behavioral_twin"]),
            (90, TEMPLATE_BY_ID["profile_forecast"]),
            (80, TEMPLATE_BY_ID["digital_footprint_collector"]),
        ]
        _score, selected = choose_cinematic_template(
            scored,
            ["behavioral_twin", "profile_forecast"],
        )
        self.assertNotEqual(layout_family(selected.template_id), "editorial_hero")

    def test_process_diagram_remains_a_minority_when_alternatives_exist(self) -> None:
        scored = [
            (100, TEMPLATE_BY_ID["behavior_prediction_engine"]),
            (95, TEMPLATE_BY_ID["signal_feedback_loop"]),
            (90, TEMPLATE_BY_ID["attention_auction"]),
        ]
        _score, selected = choose_cinematic_template(
            scored,
            ["behavior_prediction_engine", "behavioral_twin", "signal_feedback_loop"],
        )
        self.assertNotEqual(layout_family(selected.template_id), PROCESS_DIAGRAM)

    def test_slide_likeness_rejects_sparse_centered_text_heavy_scene(self) -> None:
        result = slide_likeness(
            SlideQualitySignals(
                text_density=1.0,
                empty_space_ratio=0.95,
                centered_symmetry=1.0,
                repeated_layout=1.0,
                subject_presence=0.05,
                depth_layering=0.05,
                motion_richness=0.05,
            )
        )
        self.assertTrue(result.rejected)
        self.assertGreaterEqual(result.score, 0.58)
        self.assertIn("too much text", result.reasons)

    def test_editorial_scene_passes_quality_gate(self) -> None:
        result = slide_likeness(
            SlideQualitySignals(
                text_density=0.15,
                empty_space_ratio=0.22,
                centered_symmetry=0.10,
                repeated_layout=0.0,
                subject_presence=0.92,
                depth_layering=0.88,
                motion_richness=0.82,
            )
        )
        self.assertFalse(result.rejected)

    def test_headline_shortening_does_not_mutate_script_content(self) -> None:
        narration = (
            "Every scroll, every pause, and every abandoned draft becomes another "
            "behavioral signal used to predict what you may do next."
        )
        headline = shorten_headline(narration)
        self.assertEqual(
            narration,
            "Every scroll, every pause, and every abandoned draft becomes another "
            "behavioral signal used to predict what you may do next.",
        )
        self.assertLessEqual(len(headline.split()), 7)
        self.assertLessEqual(len(headline), 54)

    def test_quality_selection_does_not_touch_timing_or_narration_fields(self) -> None:
        scene_snapshot = {
            "narration": "The algorithm ranked the opportunity.",
            "start_seconds": 12.0,
            "end_seconds": 18.0,
            "duration_seconds": 6.0,
        }
        before = dict(scene_snapshot)
        choose_cinematic_template(
            [(100, TEMPLATE_BY_ID["algorithm_chose_you"])],
            [],
        )
        self.assertEqual(scene_snapshot, before)


if __name__ == "__main__":
    unittest.main()
