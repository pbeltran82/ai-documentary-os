from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.models import Scene
from app.services import animation_script_director as director
from app.services import animation_script_runtime as runtime


class AnimationScriptDirectorTests(unittest.TestCase):
    def scene(self, narration: str) -> Scene:
        return Scene(
            id=1,
            project_id=1,
            scene_number=1,
            start_seconds=0,
            end_seconds=6,
            duration_seconds=6,
            narration=narration,
            visual_intent="",
            search_keywords=[],
            animation_plan={},
        )

    def test_empty_balance_plan_has_reaction_arc(self) -> None:
        plan = director.build_animation_plan(self.scene("There is nothing left. The balance is zero."))
        self.assertEqual(plan["pose_sequence"], ["phone", "tap", "recoil", "slump"])
        self.assertIn("shocked", plan["expression_sequence"])
        self.assertIn("phone", plan["props"])

    def test_automatic_plan_directs_one_time_setup(self) -> None:
        plan = director.build_animation_plan(self.scene("Set it once and invest automatically every payday."))
        self.assertEqual(plan["pose_sequence"][0], "tap")
        self.assertIn("calendar", plan["props"])

    def test_ensure_plan_preserves_manual_direction(self) -> None:
        scene = self.scene("Anything")
        scene.animation_plan = {"version": "manual", "pose_sequence": ["celebrate"]}
        self.assertEqual(director.ensure_animation_plan(scene)["version"], "manual")

    def test_runtime_uses_saved_pose_and_expression(self) -> None:
        runtime._ACTIVE_PLAN = {
            "pose_sequence": ["walk", "slump"],
            "expression_sequence": ["neutral", "shocked"],
        }
        runtime.character._CURRENT_TIME = 5.0
        runtime.character._CURRENT_DURATION = 6.0
        with patch.object(runtime, "_ORIGINAL_PERSON") as person:
            runtime._planned_person(MagicMock(), (100, 100), {}, pose="idle", mood="neutral")
        self.assertEqual(person.call_args.kwargs["pose"], "slump")
        self.assertEqual(person.call_args.kwargs["mood"], "surprised")
        runtime._ACTIVE_PLAN = None

    def test_timing_segments_sum_to_one(self) -> None:
        plan = director.build_animation_plan(self.scene("A person receives a paycheck."))
        self.assertAlmostEqual(sum(plan["animation_beats"].values()), 1.0)

    def test_plan_exposes_editable_direction_contract(self) -> None:
        plan = director.build_animation_plan(self.scene("A person considers a difficult choice."))
        for field in (
            "character_action",
            "expression_sequence",
            "pose_sequence",
            "props",
            "camera_direction",
            "animation_beats",
            "transition_intention",
        ):
            self.assertIn(field, plan)


if __name__ == "__main__":
    unittest.main()
