from __future__ import annotations

import unittest

from PIL import ImageChops

from app.models import Project, Scene
from app.services import exact_visuals
from app.services import tech_behavior_truthful as tech


class TruthfulTechRoutingTests(unittest.TestCase):
    def scene(self, narration: str, visual_intent: str = "") -> Scene:
        project = Project(
            id=2,
            title="The Algorithm Chose You",
            topic="AI prediction and behavioral modeling",
            target_minutes=1,
            audience="General audience",
            tone="Tense documentary",
            visual_style="Cinematic technology documentary",
            status="assets",
        )
        scene = Scene(
            id=21,
            project_id=2,
            scene_number=11,
            start_seconds=56,
            end_seconds=61,
            duration_seconds=5,
            narration=narration,
            visual_intent=visual_intent,
            search_keywords=[],
            preferred_asset_type="stock_video",
            asset_status="missing",
        )
        scene.project = project
        project.scenes = [scene]
        return scene

    def test_human_navigation_scene_prefers_real_footage_editorially(self) -> None:
        family_id, confidence, reason = exact_visuals.recommend_family(
            self.scene("We didn't build AI only to help us navigate the world.")
        )
        self.assertEqual(family_id, exact_visuals.TECH_FAMILY_ID)
        self.assertEqual(confidence, 0.64)
        self.assertIn("prefer strong real footage", reason)

        template, _confidence, _reason = tech.suggest_template(
            self.scene("We didn't build AI only to help us navigate the world.")
        )
        self.assertEqual(template.template_id, "machine_choice_cta")

    def test_system_navigating_us_routes_to_behavioral_twin(self) -> None:
        scene = self.scene("We also built systems that learn how to navigate us.")
        family_id, confidence, reason = exact_visuals.recommend_family(scene)
        self.assertEqual(family_id, exact_visuals.TECH_FAMILY_ID)
        self.assertGreaterEqual(confidence, 0.80)
        self.assertIn("algorithmic behavior", reason)

        template, template_confidence, template_reason = tech.suggest_template(scene)
        self.assertEqual(template.template_id, "behavioral_twin")
        self.assertGreaterEqual(template_confidence, 0.90)
        self.assertIn("navigate us", template_reason)

    def test_prediction_language_beats_raw_collection_signals(self) -> None:
        template, confidence, reason = tech.suggest_template(
            self.scene(
                "AI predicts behavior from every scroll, pause, click, and abandoned draft."
            )
        )
        self.assertEqual(template.template_id, "behavior_prediction_engine")
        self.assertGreaterEqual(confidence, 0.90)
        self.assertIn("predicts behavior", reason)

    def test_confidence_states_use_qualitative_labels(self) -> None:
        self.assertEqual(
            tech.prediction_confidence_state(0.0),
            ("LOW CONFIDENCE", "NOT ENOUGH SIGNALS", 0.18),
        )
        updating = tech.prediction_confidence_state(0.35)
        self.assertEqual(updating[0], "MODEL UPDATING")
        self.assertEqual(updating[1], "EVIDENCE ACCUMULATING")
        high = tech.prediction_confidence_state(1.0)
        self.assertEqual(high, ("HIGH CONFIDENCE", "ILLUSTRATIVE MODEL OUTPUT", 0.92))

    def test_truthful_storyboard_still_changes_across_beats(self) -> None:
        beats = tech.storyboard_beats("behavior_prediction_engine", 6)
        frames = [
            tech.render_frame(
                "behavior_prediction_engine",
                6,
                float(beat["time_seconds"]),
                "premium_motion",
            )
            for beat in beats
        ]
        self.assertIsNotNone(ImageChops.difference(frames[0], frames[1]).getbbox())
        self.assertIsNotNone(ImageChops.difference(frames[1], frames[2]).getbbox())


if __name__ == "__main__":
    unittest.main()
