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

    def test_research_plan_uses_computer_performance_methods(self) -> None:
        plan = director.build_animation_plan(
            self.scene("Researchers type the data into a computer dashboard and inspect the evidence.")
        )
        self.assertEqual(plan["pose_sequence"], ["look", "type", "swipe", "point"])
        self.assertIn("computer", plan["props"])

    def test_investigative_question_has_thinking_arc(self) -> None:
        plan = director.build_animation_plan(
            self.scene("Why did this mystery endure? Consider the evidence.")
        )
        self.assertEqual(plan["pose_sequence"], ["look", "think", "confused", "nod"])

    def test_myth_correction_rejects_then_affirms(self) -> None:
        plan = director.build_animation_plan(
            self.scene("This popular myth is not true. The verified record tells a different story.")
        )
        self.assertEqual(plan["pose_sequence"], ["point", "shake_head", "swipe", "nod"])

    def test_trigger_words_do_not_match_inside_unrelated_words(self) -> None:
        plan = director.build_animation_plan(
            self.scene("A different story emerges from the archive.")
        )
        self.assertNotEqual(plan["pose_sequence"], ["receive", "point", "recoil", "slump"])

    def test_uncertainty_plan_uses_shrug_without_losing_resolution(self) -> None:
        plan = director.build_animation_plan(
            self.scene("Perhaps the cause is still unknown, but one fact is clear.")
        )
        self.assertEqual(plan["pose_sequence"], ["look", "confused", "shrug", "point"])

    def test_urgent_plan_uses_run_as_a_story_beat(self) -> None:
        plan = director.build_animation_plan(
            self.scene("The rescue team had to race quickly toward the signal.")
        )
        self.assertEqual(plan["pose_sequence"], ["walk", "run", "point", "celebrate"])

    def test_introduction_plan_greets_then_settles(self) -> None:
        plan = director.build_animation_plan(
            self.scene("Welcome. Meet the scientist who changed the field.")
        )
        self.assertEqual(plan["pose_sequence"], ["walk", "wave", "point", "idle"])

    def test_generated_plans_use_current_character_studio_version(self) -> None:
        plan = director.build_animation_plan(self.scene("A person considers a difficult choice."))
        self.assertEqual(plan["version"], "1.9.3")

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

    def test_runtime_uses_editable_performance_timing(self) -> None:
        runtime._ACTIVE_PLAN = {
            "pose_sequence": ["look", "think", "point", "nod"],
            "expression_sequence": ["neutral", "curious", "focused", "confident"],
            "animation_beats": {
                "anticipation": 0.7,
                "action": 0.1,
                "overshoot": 0.1,
                "recovery": 0.1,
            },
        }
        runtime.character._CURRENT_TIME = 3.0
        runtime.character._CURRENT_DURATION = 6.0
        with patch.object(runtime, "_ORIGINAL_PERSON") as person:
            runtime._planned_person(MagicMock(), (100, 100), {}, pose="idle", mood="neutral")
        self.assertEqual(person.call_args.kwargs["pose"], "look")
        self.assertEqual(person.call_args.kwargs["mood"], "neutral")
        runtime._ACTIVE_PLAN = None

    def test_invalid_performance_timing_falls_back_to_equal_segments(self) -> None:
        position = runtime._sequence_position(0.6, 4, {"only": 1.0})
        self.assertAlmostEqual(position, 2.4)

    def test_review_frame_activates_saved_direction_and_restores_runtime(self) -> None:
        scene = self.scene("Anything")
        scene.animation_plan = {
            "pose_sequence": ["think", "nod"],
            "expression_sequence": ["curious", "confident"],
        }
        runtime._ACTIVE_PLAN = {"pose_sequence": ["idle"]}
        observed_plan = None

        def capture(*_args, **_kwargs):
            nonlocal observed_plan
            observed_plan = runtime._ACTIVE_PLAN
            return MagicMock()

        with patch.object(runtime.character, "render_frame", side_effect=capture):
            runtime.render_planned_frame(scene, "paycheck_arrival", 6.0, 3.0, "premium_motion")

        self.assertEqual(observed_plan, scene.animation_plan)
        self.assertEqual(runtime._ACTIVE_PLAN, {"pose_sequence": ["idle"]})
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
