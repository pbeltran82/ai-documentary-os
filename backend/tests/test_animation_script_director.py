from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from PIL import Image, ImageChops

from app.models import Scene
from app.services import animation_script_director as director
from app.services import animation_script_runtime as runtime
from app.services import character_camera_director as camera_director
from app.services import character_performance_library as library


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
        self.assertEqual(plan["pose_sequence"], ["step_in", "wave", "point", "idle"])

    def test_paycheck_infographic_uses_grounded_step_in(self) -> None:
        plan = director.build_animation_plan(
            self.scene("A paycheck arrives and the first 10 percent goes to your future self.")
        )
        self.assertEqual(
            plan["pose_sequence"],
            ["step_in", "receive", "point", "relaxed"],
        )
        self.assertIn("point briefly", plan["character_action"])

    def test_saved_generated_paycheck_plan_upgrades_to_the_released_hold(self) -> None:
        scene = self.scene("A paycheck arrives and funds your future self.")
        scene.animation_plan = {
            "version": "1.9.6",
            "character_action": (
                "Receive the paycheck, anticipate the choice, separate ten percent, "
                "and point to the future account."
            ),
            "pose_sequence": ["step_in", "receive", "point", "celebrate"],
        }

        plan = director.ensure_animation_plan(scene)

        self.assertEqual(
            plan["pose_sequence"],
            ["step_in", "receive", "point", "relaxed"],
        )
        self.assertIs(scene.animation_plan, plan)

    def test_hand_edited_paycheck_plan_is_not_rewritten(self) -> None:
        scene = self.scene("A paycheck arrives and funds your future self.")
        scene.animation_plan = {
            "version": "manual",
            "character_action": "Hold this custom performance.",
            "pose_sequence": ["step_in", "receive", "point", "celebrate"],
        }

        plan = director.ensure_animation_plan(scene)

        self.assertEqual(plan["pose_sequence"][-1], "celebrate")

    def test_generated_plans_use_current_character_studio_version(self) -> None:
        plan = director.build_animation_plan(self.scene("A person considers a difficult choice."))
        self.assertEqual(plan["version"], "1.9.6")

    def test_reusable_performance_library_exposes_directing_patterns(self) -> None:
        catalog = library.preset_catalog()
        self.assertEqual(len(catalog), 7)
        self.assertEqual(
            {item["preset_id"] for item in catalog},
            {"investigate", "research", "correct_myth", "uncertainty", "urgent_action", "welcome", "explain"},
        )

    def test_preset_plan_is_an_independent_editable_copy(self) -> None:
        first = library.plan_from_preset("investigate")
        first["pose_sequence"].append("celebrate")
        second = library.plan_from_preset("investigate")
        self.assertNotIn("celebrate", second["pose_sequence"])
        self.assertEqual(second["preset_id"], "investigate")

    def test_default_scene_uses_reusable_explain_preset(self) -> None:
        plan = director.build_animation_plan(self.scene("A clear chronological account follows."))
        self.assertEqual(plan["preset_id"], "explain")

    def test_every_preset_has_executable_camera_direction(self) -> None:
        for preset in library.preset_catalog():
            with self.subTest(preset=preset["preset_id"]):
                motion = preset["camera_motion"]
                self.assertIn(motion["mode"], {"push_in", "pull_back", "track", "drift", "settle"})
                self.assertGreater(motion["intensity"], 0)

    def test_camera_direction_changes_framing_without_changing_dimensions(self) -> None:
        source = Image.new("RGB", (320, 180))
        source.putdata([(x % 256, y % 256, (x + y) % 256) for y in range(180) for x in range(320)])
        directed = camera_director.apply_camera_direction(
            source,
            {"mode": "push_in", "intensity": 0.7, "focus": [0.65, 0.45]},
            0.8,
        )
        self.assertEqual(directed.size, source.size)
        self.assertIsNotNone(ImageChops.difference(source, directed).getbbox())

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

    def test_authored_actor_keeps_its_role_specific_pose(self) -> None:
        runtime._ACTIVE_PLAN = {
            "pose_sequence": ["celebrate"],
            "expression_sequence": ["happy"],
        }
        try:
            with patch.object(runtime, "_ORIGINAL_PERSON") as person:
                runtime._planned_person(
                    MagicMock(),
                    (100, 100),
                    {},
                    pose="slump",
                    mood="sad",
                    performance_role="authored",
                )
            self.assertEqual(person.call_args.kwargs["pose"], "slump")
            self.assertEqual(person.call_args.kwargs["mood"], "sad")
            self.assertNotIn("performance_role", person.call_args.kwargs)
        finally:
            runtime._ACTIVE_PLAN = None

    def test_locomotion_transition_does_not_crossfade_two_rigs(self) -> None:
        from PIL import ImageDraw

        runtime._ACTIVE_PLAN = {
            "pose_sequence": ["walk", "receive", "point", "celebrate"],
            "expression_sequence": ["neutral", "focused", "confident", "happy"],
            "animation_beats": {
                "anticipation": 0.15,
                "action": 0.35,
                "overshoot": 0.15,
                "recovery": 0.35,
            },
        }
        runtime.character._CURRENT_TIME = 1.44
        runtime.character._CURRENT_DURATION = 10.0
        canvas = Image.new("RGBA", (320, 240), (0, 0, 0, 0))
        try:
            with patch.object(runtime, "_ORIGINAL_PERSON") as person:
                runtime._planned_person(
                    ImageDraw.Draw(canvas),
                    (120, 200),
                    {},
                    pose="idle",
                    mood="neutral",
                )
            self.assertEqual(person.call_count, 1)
            self.assertEqual(person.call_args.kwargs["pose"], "walk")
        finally:
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
