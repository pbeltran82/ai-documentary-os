from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services import animation_script_runtime as runtime
from app.services import character_expressive as character
from app.services import character_pose_stability as pose_stability
from app.services import cinematic_character_polish as cinematic
from app.services import finance_motion_art as art
from app.services.visual_staging import CharacterPlacement


class CinematicCharacterPolishTests(unittest.TestCase):
    def test_default_motion_style_is_neutral_cinematic(self) -> None:
        style = art.STYLE_BY_ID["premium_motion"]
        self.assertEqual(style.label, "Cinematic Motion")
        self.assertNotIn("#8b5cf6", style.swatches)

    def test_background_has_no_graph_paper_line_at_160_pixels(self) -> None:
        background = cinematic._cinematic_background()
        row = 540
        left = background.getpixel((159, row))
        center = background.getpixel((160, row))
        right = background.getpixel((161, row))
        self.assertLessEqual(max(abs(left[i] - center[i]) for i in range(3)), 3)
        self.assertLessEqual(max(abs(center[i] - right[i]) for i in range(3)), 3)

    def test_open_hand_draws_four_fingers_and_one_thumb(self) -> None:
        draw = MagicMock()
        cinematic._polished_hand(draw, (100, 100), cinematic.TEAL, 1.0, open_hand=True)
        self.assertEqual(draw.line.call_count, 5)

    def test_closed_hand_keeps_visible_digit_definition(self) -> None:
        draw = MagicMock()
        cinematic._polished_hand(draw, (100, 100), cinematic.TEAL, 1.0, open_hand=False)
        self.assertEqual(draw.line.call_count, 5)

    def test_performance_arc_is_restrained_and_settles(self) -> None:
        character._CURRENT_DURATION = 10.0
        values = []
        for time_value in (0.0, 1.8, 2.6, 4.5, 6.5, 9.0):
            character._CURRENT_TIME = time_value
            values.append(cinematic._restrained_performance_pulse())
        self.assertLessEqual(max(abs(value) for value in values), 0.051)
        self.assertEqual(values[-1], 0.0)

    def test_unsupported_script_pose_keeps_template_pose(self) -> None:
        runtime._ACTIVE_PLAN = {
            "pose_sequence": ["recoil"],
            "expression_sequence": ["shocked"],
        }
        character._CURRENT_TIME = 3.0
        character._CURRENT_DURATION = 6.0
        try:
            with patch.object(runtime, "_ORIGINAL_PERSON") as person:
                pose_stability._stable_planned_person(
                    MagicMock(),
                    (100, 100),
                    {},
                    pose="phone",
                    mood="neutral",
                )
            self.assertEqual(person.call_args.kwargs["pose"], "phone")
            self.assertEqual(person.call_args.kwargs["mood"], "surprised")
        finally:
            runtime._ACTIVE_PLAN = None

    def test_wallet_anchor_stays_inside_character_gesture_reach(self) -> None:
        placement = CharacterPlacement(255, 840, 1.06, 1)
        wallet_x, wallet_y = cinematic._wallet_anchor(placement)
        self.assertLessEqual(abs(wallet_x - placement.center_x), round(120 * placement.scale))
        shoulder_y = placement.ground_y - round(175 * placement.scale)
        self.assertLessEqual(abs(wallet_y - shoulder_y), round(40 * placement.scale))

    def test_character_frame_contains_no_purple_halo_bias(self) -> None:
        frame = character.render_frame(
            "automatic_investing_habit",
            6.0,
            3.0,
            "premium_motion",
        )
        self.assertEqual(frame.size, (1920, 1080))
        crop = frame.crop((80, 330, 720, 930))
        purple_pixels = sum(
            1
            for red, green, blue in crop.getdata()
            if red > 75 and blue > red + 28 and blue > green + 18
        )
        self.assertLess(purple_pixels, 250)


if __name__ == "__main__":
    unittest.main()
