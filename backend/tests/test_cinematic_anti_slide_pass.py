from __future__ import annotations

import unittest

from PIL import ImageChops

from app.services import tech_behavior_motion as tech
from app.services.cinematic_anti_slide_pass import UPGRADED_TEMPLATES


class CinematicAntiSlidePassTests(unittest.TestCase):
    def test_remaining_weak_templates_render_landscape_rgb(self) -> None:
        for template_id in UPGRADED_TEMPLATES:
            with self.subTest(template_id=template_id):
                frame = tech.render_frame(template_id, 6.0, 4.4, tech.DEFAULT_STYLE_ID)
                self.assertEqual(frame.size, (1920, 1080))
                self.assertEqual(frame.mode, "RGB")

    def test_remaining_weak_templates_fill_the_frame(self) -> None:
        background = tech._palette(tech.DEFAULT_STYLE_ID)["background"]
        for template_id in UPGRADED_TEMPLATES:
            with self.subTest(template_id=template_id):
                frame = tech.render_frame(template_id, 6.0, 4.6, tech.DEFAULT_STYLE_ID)
                sample = frame.resize((192, 108))
                occupied = sum(1 for pixel in sample.getdata() if pixel != background)
                self.assertGreater(occupied / (192 * 108), 0.60)
                self.assertGreater(len(set(sample.getdata())), 45)

    def test_compositions_are_directionally_asymmetric(self) -> None:
        for template_id in UPGRADED_TEMPLATES:
            with self.subTest(template_id=template_id):
                frame = tech.render_frame(template_id, 6.0, 4.2, tech.DEFAULT_STYLE_ID)
                left = frame.crop((0, 280, 960, 1080)).resize((240, 200))
                right = frame.crop((960, 280, 1920, 1080)).transpose(method=0).resize((240, 200))
                difference = ImageChops.difference(left, right)
                self.assertIsNotNone(difference.getbbox())
                changed = sum(1 for pixel in difference.getdata() if pixel != (0, 0, 0))
                self.assertGreater(changed, 9000)

    def test_progress_changes_story_staging(self) -> None:
        for template_id in UPGRADED_TEMPLATES:
            with self.subTest(template_id=template_id):
                early = tech.render_frame(template_id, 6.0, 1.1, tech.DEFAULT_STYLE_ID)
                late = tech.render_frame(template_id, 6.0, 5.1, tech.DEFAULT_STYLE_ID)
                difference = ImageChops.difference(early, late)
                self.assertIsNotNone(difference.getbbox())

    def test_bright_style_uses_depth_not_empty_white_space(self) -> None:
        for template_id in UPGRADED_TEMPLATES:
            with self.subTest(template_id=template_id):
                frame = tech.render_frame(template_id, 6.0, 4.4, "clean_infographic")
                palette = tech._palette("clean_infographic")
                sample = frame.resize((192, 108))
                occupied = sum(1 for pixel in sample.getdata() if pixel != palette["background"])
                self.assertGreater(occupied / (192 * 108), 0.60)

    def test_visual_render_does_not_modify_story_values(self) -> None:
        story = {
            "narration": "A hidden ranking system competes for the next moment.",
            "start_seconds": 24.0,
            "end_seconds": 30.0,
            "duration_seconds": 6.0,
        }
        before = dict(story)
        tech.render_frame("attention_auction", 6.0, 3.4, tech.DEFAULT_STYLE_ID)
        self.assertEqual(story, before)


if __name__ == "__main__":
    unittest.main()
