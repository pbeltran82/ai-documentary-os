from __future__ import annotations

import unittest

from PIL import Image, ImageDraw

from app.services import character_explainer as base
from app.services import character_staging_clean as clean
from app.services.visual_staging import CharacterPlacement


class CharacterHaloRegressionTests(unittest.TestCase):
    def test_character_stage_does_not_draw_full_body_colored_oval(self) -> None:
        background = (245, 245, 245)
        image = Image.new("RGB", (600, 600), background)
        draw = ImageDraw.Draw(image)
        placement = CharacterPlacement(center_x=300, ground_y=520, scale=1.0)

        clean._character_stage_clean(
            draw,
            placement,
            base._palette("premium_motion"),
            pose="idle",
        )

        # This point sat inside the old 200x290 colored silhouette ellipse but
        # outside the figure itself. It must remain untouched background now.
        self.assertEqual(image.getpixel((205, 360)), background)

        # The face and body are still drawn, proving the test is not passing on
        # an empty frame.
        self.assertNotEqual(image.getpixel((300, 275)), background)

    def test_exact_visual_character_frames_use_clean_staging(self) -> None:
        frame = clean.render_frame(
            "automatic_investing_habit",
            4,
            2.1,
            "premium_motion",
        )
        self.assertEqual(frame.size, (1920, 1080))
        self.assertEqual(frame.mode, "RGB")


if __name__ == "__main__":
    unittest.main()
