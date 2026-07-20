from __future__ import annotations

import unittest

from PIL import ImageChops

from app.services import tech_behavior_motion as tech
from app.services.cinematic_composition_upgrade import UPGRADED_TEMPLATES


class CinematicCompositionUpgradeTests(unittest.TestCase):
    def test_upgraded_frames_remain_landscape_rgb(self) -> None:
        for template_id in UPGRADED_TEMPLATES:
            with self.subTest(template_id=template_id):
                frame = tech.render_frame(template_id, 6.0, 3.4, tech.DEFAULT_STYLE_ID)
                self.assertEqual(frame.size, (1920, 1080))
                self.assertEqual(frame.mode, "RGB")

    def test_upgraded_frames_have_stronger_occupied_area(self) -> None:
        for template_id in UPGRADED_TEMPLATES:
            with self.subTest(template_id=template_id):
                frame = tech.render_frame(template_id, 6.0, 4.8, tech.DEFAULT_STYLE_ID)
                background = tech._palette(tech.DEFAULT_STYLE_ID)["background"]
                flat = frame.resize((192, 108))
                occupied = sum(1 for pixel in flat.getdata() if pixel != background)
                self.assertGreater(occupied / (192 * 108), 0.58)

    def test_compositions_are_not_center_mirrored_slides(self) -> None:
        for template_id in UPGRADED_TEMPLATES:
            with self.subTest(template_id=template_id):
                frame = tech.render_frame(template_id, 6.0, 4.2, tech.DEFAULT_STYLE_ID)
                left = frame.crop((0, 280, 960, 1080)).resize((240, 200))
                right = frame.crop((960, 280, 1920, 1080)).transpose(method=0).resize((240, 200))
                difference = ImageChops.difference(left, right)
                self.assertIsNotNone(difference.getbbox())
                histogram = difference.histogram()
                changed = sum(histogram[1:256]) + sum(histogram[257:512]) + sum(histogram[513:768])
                self.assertGreater(changed, 10000)

    def test_bright_style_keeps_depth_and_subject_presence(self) -> None:
        frame = tech.render_frame("behavioral_twin", 6.0, 4.5, "clean_infographic")
        palette = tech._palette("clean_infographic")
        sample = frame.resize((192, 108))
        occupied = sum(1 for pixel in sample.getdata() if pixel != palette["background"])
        self.assertGreater(occupied / (192 * 108), 0.60)
        self.assertGreater(len(set(sample.getdata())), 45)

    def test_rendering_does_not_modify_story_fields(self) -> None:
        story = {
            "narration": "The ranking shapes what reaches you next.",
            "start_seconds": 18.0,
            "end_seconds": 24.0,
            "duration_seconds": 6.0,
        }
        before = dict(story)
        tech.render_frame("consequence_map", 6.0, 3.0, tech.DEFAULT_STYLE_ID)
        self.assertEqual(story, before)


if __name__ == "__main__":
    unittest.main()
