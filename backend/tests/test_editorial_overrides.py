from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.services.visuals.editorial_overrides import (
    apply_scene_override,
    exact_template_override,
    forces_asset_first,
)
from app.services.visuals.visual_pipeline import build_visual_plan


class EditorialOverrideTests(unittest.TestCase):
    def _scene(self, number: int):
        return SimpleNamespace(
            id=number,
            project_id=1,
            scene_number=number,
            narration="Placeholder narration",
            visual_intent="",
            search_keywords=(),
            project=SimpleNamespace(title="How Algorithms Shape Your Attention"),
        )

    def _base_plan(self):
        return build_visual_plan(
            narration="Placeholder narration",
            visual_intent="",
            scene_key="editorial-override-test",
        )

    def test_locked_hyperframes_template_map(self) -> None:
        expected = {
            2: "attention_auction",
            8: "behavior_prediction_engine",
            10: "consequence_map",
            12: "algorithm_chose_you",
            13: "machine_choice_cta",
        }
        for scene_number, template_id in expected.items():
            with self.subTest(scene_number=scene_number):
                scene = self._scene(scene_number)
                plan = apply_scene_override(scene, self._base_plan())
                self.assertEqual(exact_template_override(scene), template_id)
                self.assertEqual(plan.asset.execution_mode.value, "exact_visual")

    def test_scene_four_is_released_from_hyperframes_to_real_media(self) -> None:
        scene = self._scene(4)
        plan = apply_scene_override(scene, self._base_plan())
        self.assertTrue(forces_asset_first(scene))
        self.assertEqual(plan.asset.execution_mode.value, "asset_first")
        self.assertIn("person face beside data profile screen", plan.asset.search_terms)

    def test_personalized_feed_brief_rejects_literal_food(self) -> None:
        scene = self._scene(9)
        plan = apply_scene_override(scene, self._base_plan())
        self.assertIn("personalized social media feed on smartphone", plan.asset.search_terms)
        self.assertIn("food", plan.asset.avoid_terms)
        self.assertIn("meal", plan.asset.avoid_terms)

    def test_unrelated_projects_receive_no_override(self) -> None:
        scene = self._scene(9)
        scene.project.title = "Another Documentary"
        plan = self._base_plan()
        self.assertIs(apply_scene_override(scene, plan), plan)
        self.assertIsNone(exact_template_override(scene))
        self.assertFalse(forces_asset_first(scene))


if __name__ == "__main__":
    unittest.main()
