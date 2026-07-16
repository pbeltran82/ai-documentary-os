from __future__ import annotations

import unittest

from PIL import ImageChops, ImageDraw

from app.services import character_expressive as expressive
from app.services import exact_visuals


class ExpressiveCharacterTests(unittest.TestCase):
    def test_character_family_routes_through_expressive_renderer(self) -> None:
        self.assertIs(exact_visuals.character, expressive)

    def test_all_templates_render_across_house_styles(self) -> None:
        for template in expressive.CHARACTER_TEMPLATES:
            for style in expressive.STYLES:
                with self.subTest(template=template.template_id, style=style.style_id):
                    frame = expressive.render_frame(
                        template.template_id,
                        6.0,
                        3.0,
                        style.style_id,
                    )
                    self.assertEqual(frame.size, (1920, 1080))

    def test_performance_changes_between_story_beats(self) -> None:
        frame_a = expressive.render_frame(
            "empty_balance_reaction",
            6.0,
            0.9,
            "premium_motion",
        )
        frame_b = expressive.render_frame(
            "empty_balance_reaction",
            6.0,
            5.1,
            "premium_motion",
        )
        self.assertIsNotNone(ImageChops.difference(frame_a, frame_b).getbbox())

    def test_rig_draws_oversized_hands_and_shoes(self) -> None:
        from PIL import Image

        canvas = Image.new("RGB", (700, 700), (255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        palette = {
            "ink": (9, 14, 27),
            "person": (139, 92, 246),
            "person_alt": (34, 211, 238),
            "skin": (251, 191, 145),
            "accent": (34, 211, 238),
        }
        expressive._CURRENT_TIME = 0.75
        expressive._CURRENT_DURATION = 4.0
        expressive._expressive_person(
            draw,
            (350, 620),
            palette,
            scale=1.3,
            pose="celebrate",
            mood="happy",
        )
        body_pixels = sum(
            1
            for pixel in canvas.getdata()
            if pixel == palette["person"]
        )
        self.assertGreater(body_pixels, 3000)

    def test_blink_timing_changes_face_pixels(self) -> None:
        from PIL import Image

        palette = {
            "ink": (9, 14, 27),
            "person": (139, 92, 246),
            "person_alt": (34, 211, 238),
            "skin": (251, 191, 145),
            "accent": (34, 211, 238),
        }
        open_eye = Image.new("RGB", (240, 180), (255, 255, 255))
        expressive._CURRENT_TIME = 0.2
        expressive._expression(ImageDraw.Draw(open_eye), (120, 90), palette, 1.4, "neutral", 1)
        blink = Image.new("RGB", (240, 180), (255, 255, 255))
        expressive._CURRENT_TIME = 1.52
        expressive._expression(ImageDraw.Draw(blink), (120, 90), palette, 1.4, "neutral", 1)
        self.assertIsNotNone(ImageChops.difference(open_eye, blink).getbbox())


if __name__ == "__main__":
    unittest.main()
