from __future__ import annotations

import unittest

from PIL import ImageChops, ImageDraw

from app.services import character_expressive as expressive
from app.services import character_pose_stability
from app.services import exact_visuals


class ExpressiveCharacterTests(unittest.TestCase):
    def test_character_studio_animation_vocabulary_is_supported(self) -> None:
        expected = {
            "step_in", "walk", "run", "look", "think", "celebrate", "point", "wave",
            "shrug", "confused", "nod", "shake_head", "type", "swipe", "tap", "idle",
        }
        self.assertTrue(expected.issubset(character_pose_stability.SUPPORTED_POSES))

    def test_step_in_moves_once_and_settles_at_the_stage_anchor(self) -> None:
        from PIL import Image

        palette = {
            "ink": (9, 14, 27),
            "person": (139, 92, 246),
            "person_alt": (139, 92, 246),
            "skin": (251, 191, 145),
            "accent": (34, 211, 238),
        }

        def character_center(time_seconds: float) -> float:
            canvas = Image.new("RGB", (700, 700), (255, 255, 255))
            expressive._CURRENT_TIME = time_seconds
            expressive._CURRENT_DURATION = 6.0
            expressive._expressive_person(
                ImageDraw.Draw(canvas),
                (350, 620),
                palette,
                scale=1.2,
                pose="step_in",
            )
            body_x = [
                x
                for y in range(330, 650)
                for x in range(180, 520)
                if canvas.getpixel((x, y)) == palette["person"]
            ]
            return sum(body_x) / len(body_x)

        self.assertGreater(character_center(0.90) - character_center(0.03), 24)
        self.assertAlmostEqual(character_center(0.90), character_center(1.40), delta=1.5)

    def test_primary_and_alternate_characters_have_distinct_hair(self) -> None:
        from PIL import Image

        palette = {
            "ink": (9, 14, 27),
            "person": (34, 211, 238),
            "person_alt": (34, 211, 238),
            "skin": (251, 191, 145),
            "accent": (34, 211, 238),
        }
        heads = []
        for alternate in (False, True):
            canvas = Image.new("RGB", (700, 700), (255, 255, 255))
            expressive._CURRENT_TIME = 0.3
            expressive._CURRENT_DURATION = 4.0
            expressive._expressive_person(
                ImageDraw.Draw(canvas),
                (350, 620),
                palette,
                scale=1.3,
                pose="idle",
                alternate=alternate,
            )
            heads.append(canvas.crop((275, 205, 430, 365)))
        self.assertIsNotNone(ImageChops.difference(*heads).getbbox())

    def test_new_performance_methods_render_distinct_motion(self) -> None:
        from PIL import Image

        palette = {
            "ink": (9, 14, 27),
            "person": (139, 92, 246),
            "person_alt": (34, 211, 238),
            "skin": (251, 191, 145),
            "denim": (48, 86, 132),
            "accent": (34, 211, 238),
        }
        for pose in ("run", "look", "think", "wave", "shrug", "confused", "nod", "shake_head", "type", "swipe"):
            with self.subTest(pose=pose):
                frames = []
                for time_seconds in (0.15, 0.55):
                    canvas = Image.new("RGB", (700, 700), (255, 255, 255))
                    expressive._CURRENT_TIME = time_seconds
                    expressive._CURRENT_DURATION = 2.0
                    expressive._expressive_person(
                        ImageDraw.Draw(canvas), (350, 620), palette, scale=1.2, pose=pose
                    )
                    frames.append(canvas)
                self.assertIsNotNone(ImageChops.difference(*frames).getbbox())

    def test_walk_alternates_the_planted_foot(self) -> None:
        from PIL import Image

        palette = {
            "ink": (9, 14, 27),
            "person": (139, 92, 246),
            "person_alt": (34, 211, 238),
            "skin": (251, 191, 145),
            "denim": (48, 86, 132),
            "accent": (34, 211, 238),
        }

        def foot_bottoms(time_seconds: float) -> tuple[int, int]:
            canvas = Image.new("RGB", (700, 700), (255, 255, 255))
            expressive._CURRENT_TIME = time_seconds
            expressive._CURRENT_DURATION = 2.0
            expressive._expressive_person(
                ImageDraw.Draw(canvas),
                (350, 620),
                palette,
                scale=1.2,
                pose="walk",
            )
            pants = palette["denim"]
            left = [y for y in range(520, 680) for x in range(180, 350) if canvas.getpixel((x, y)) == pants]
            right = [y for y in range(520, 680) for x in range(350, 530) if canvas.getpixel((x, y)) == pants]
            return max(left), max(right)

        left_planted = foot_bottoms(0.25)
        right_planted = foot_bottoms(0.75)
        self.assertGreater(left_planted[0], left_planted[1])
        self.assertGreater(right_planted[1], right_planted[0])

    def test_head_has_one_ink_contour_without_a_shirt_colored_halo(self) -> None:
        from PIL import Image

        canvas = Image.new("RGB", (700, 700), (255, 255, 255))
        palette = {
            "ink": (9, 14, 27),
            "person": (67, 185, 166),
            "person_alt": (224, 174, 83),
            "skin": (238, 187, 145),
            "accent": (174, 235, 222),
            "hair": (35, 31, 29),
        }
        expressive._CURRENT_TIME = 0.4
        expressive._CURRENT_DURATION = 4.0
        expressive._expressive_person(
            ImageDraw.Draw(canvas),
            (350, 620),
            palette,
            scale=1.2,
            pose="idle",
        )
        head_crop = canvas.crop((295, 260, 415, 390))
        self.assertEqual(
            sum(1 for pixel in head_crop.getdata() if pixel == palette["person"]),
            0,
        )

    def test_outfit_separates_shirt_jeans_shoes_and_skin(self) -> None:
        from PIL import Image

        canvas = Image.new("RGB", (700, 700), (255, 255, 255))
        palette = {
            "ink": (9, 14, 27),
            "person": (67, 185, 166),
            "person_alt": (224, 174, 83),
            "skin": (238, 187, 145),
            "denim": (47, 84, 129),
            "denim_alt": (40, 72, 110),
            "shoe": (29, 37, 49),
            "accent": (174, 235, 222),
        }
        expressive._CURRENT_TIME = 0.4
        expressive._CURRENT_DURATION = 4.0
        expressive._expressive_person(
            ImageDraw.Draw(canvas),
            (350, 620),
            palette,
            scale=1.2,
            pose="idle",
        )
        pixels = list(canvas.getdata())
        self.assertGreater(pixels.count(palette["person"]), 3000)
        self.assertGreater(pixels.count(palette["denim"]), 1000)
        self.assertGreater(pixels.count(palette["shoe"]), 500)
        skin_below_head = sum(
            1
            for y in range(385, 650)
            for x in range(180, 520)
            if canvas.getpixel((x, y)) == palette["skin"]
        )
        self.assertGreater(skin_below_head, 500)

    def test_celebration_keeps_open_hands_out_of_stick_up_zone(self) -> None:
        from PIL import Image

        canvas = Image.new("RGB", (700, 700), (255, 255, 255))
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
            ImageDraw.Draw(canvas),
            (350, 620),
            palette,
            scale=1.3,
            pose="celebrate",
            mood="happy",
        )
        raised_outer_pixels = sum(
            1
            for y in range(0, 330)
            for x in (*range(0, 270), *range(430, 700))
            if canvas.getpixel((x, y)) == palette["person"]
        )
        self.assertLess(raised_outer_pixels, 20)

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
