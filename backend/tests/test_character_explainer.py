from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from fastapi import HTTPException
from PIL import ImageChops

from app.models import Project, Scene
from app.services import character_staging as character
from app.services import exact_visuals
from app.services import visual_staging


class CharacterExplainerTests(unittest.TestCase):
    def scene(self, narration: str, visual_intent: str = "") -> Scene:
        project = Project(
            id=1,
            title="Compound Blueprint",
            topic="Personal finance",
            target_minutes=1,
            audience="General audience",
            tone="Cinematic",
            visual_style="Cinematic documentary",
            status="assets",
        )
        scene = Scene(
            id=3,
            project_id=1,
            scene_number=3,
            start_seconds=14,
            end_seconds=18,
            duration_seconds=4,
            narration=narration,
            visual_intent=visual_intent,
            search_keywords=[],
            preferred_asset_type="stock_video",
            asset_status="missing",
        )
        scene.project = project
        project.scenes = [scene]
        return scene

    def test_catalog_exposes_five_character_templates(self) -> None:
        catalog = character.template_catalog()
        self.assertEqual(len(catalog), 5)
        self.assertEqual(
            {item["template_id"] for item in catalog},
            {
                "paycheck_arrival",
                "spend_first",
                "empty_balance_reaction",
                "pay_self_character_comparison",
                "automatic_investing_habit",
            },
        )

    def test_behavior_scenes_route_to_character_explainer(self) -> None:
        examples = (
            "The first ten percent of your paycheck belongs to your future self.",
            "Most people get paid, pay their rent, buy groceries, and go out.",
            "Spoiler alert: there is never anything left.",
            "Wealthy people do the exact opposite. They pay themselves first.",
            "Treat that ten percent like a bill you legally have to pay.",
        )
        for narration in examples:
            with self.subTest(narration=narration):
                family_id, confidence, reason = exact_visuals.recommend_family(
                    self.scene(narration)
                )
                self.assertEqual(family_id, exact_visuals.CHARACTER_FAMILY_ID)
                self.assertGreaterEqual(confidence, 0.62)
                self.assertIn("Human behavior", reason)

    def test_system_scenes_remain_finance_motion(self) -> None:
        examples = (
            "Route ten percent automatically into a low-cost S&P 500 index fund.",
            "Compound interest is already working for you.",
            "Subscribe to build your blueprint.",
        )
        for narration in examples:
            with self.subTest(narration=narration):
                family_id, confidence, _reason = exact_visuals.recommend_family(
                    self.scene(narration)
                )
                self.assertEqual(family_id, exact_visuals.FINANCE_FAMILY_ID)
                self.assertGreaterEqual(confidence, 0.58)

    def test_character_template_recommendations_match_behavior(self) -> None:
        cases = (
            ("When your paycheck hits, pay your future self first.", "paycheck_arrival"),
            ("Pay rent, buy groceries, go out, and spend first.", "spend_first"),
            ("There is nothing left and the card is declined.", "empty_balance_reaction"),
            ("Wealthy people do the exact opposite and pay themselves first.", "pay_self_character_comparison"),
            ("Treat automatic investing like a bill and build the habit.", "automatic_investing_habit"),
        )
        for narration, expected in cases:
            with self.subTest(template=expected):
                template, confidence, _reason = character.suggest_template(
                    self.scene(narration)
                )
                self.assertEqual(template.template_id, expected)
                self.assertGreater(confidence, 0.50)

    def test_all_character_templates_render_distinct_1080p_frames(self) -> None:
        signatures: set[str] = set()
        for template in character.CHARACTER_TEMPLATES:
            with self.subTest(template=template.template_id):
                frame = character.render_frame(
                    template.template_id,
                    4,
                    2.1,
                    character.DEFAULT_STYLE_ID,
                )
                self.assertEqual(frame.size, (1920, 1080))
                self.assertEqual(frame.mode, "RGB")
                sample = frame.resize((96, 54))
                self.assertGreater(len(set(sample.getdata())), 40)
                signatures.add(hashlib.sha256(sample.tobytes()).hexdigest())
        self.assertEqual(len(signatures), len(character.CHARACTER_TEMPLATES))

    def test_all_three_house_styles_work_with_characters(self) -> None:
        frames = [
            character.render_frame("paycheck_arrival", 4, 2.0, style.style_id)
            for style in character.STYLES
        ]
        self.assertEqual(len(frames), 3)
        self.assertIsNotNone(ImageChops.difference(frames[0], frames[1]).getbbox())
        self.assertIsNotNone(ImageChops.difference(frames[1], frames[2]).getbbox())

    def test_character_animation_changes_across_story_beats(self) -> None:
        beats = character.storyboard_beats("spend_first", 4)
        frames = [
            character.render_frame(
                "spend_first",
                4,
                float(beat["time_seconds"]),
                character.DEFAULT_STYLE_ID,
            )
            for beat in beats
        ]
        self.assertEqual(len(beats), 3)
        self.assertIsNotNone(ImageChops.difference(frames[0], frames[1]).getbbox())
        self.assertIsNotNone(ImageChops.difference(frames[1], frames[2]).getbbox())
        self.assertLess(float(beats[0]["time_seconds"]), float(beats[1]["time_seconds"]))
        self.assertLess(float(beats[1]["time_seconds"]), float(beats[2]["time_seconds"]))

    def test_every_character_staging_plan_protects_the_face(self) -> None:
        for template in character.CHARACTER_TEMPLATES:
            with self.subTest(template=template.template_id):
                plan = visual_staging.staging_plan(template.template_id)
                self.assertTrue(plan.is_face_safe())

    def test_face_pixels_remain_visible_in_previously_occluded_templates(self) -> None:
        for template_id in ("spend_first", "automatic_investing_habit"):
            beats = character.storyboard_beats(template_id, 4)
            left, top, right, bottom = visual_staging.face_safe_zone(template_id)
            crop_box = (left - 22, top - 22, right + 22, bottom + 22)
            for style in character.STYLES:
                for beat in beats:
                    with self.subTest(
                        template=template_id,
                        style=style.style_id,
                        beat=beat["label"],
                    ):
                        frame = character.render_frame(
                            template_id,
                            4,
                            float(beat["time_seconds"]),
                            style.style_id,
                        )
                        crop = frame.crop(crop_box)
                        skin_like = sum(
                            1
                            for red, green, blue in crop.getdata()
                            if red >= 175
                            and green >= 110
                            and blue >= 70
                            and red > green
                            and green >= blue
                        )
                        self.assertGreater(skin_like, 350)

    def test_character_exports_keep_footer_safe_area_unbranded(self) -> None:
        frame = character.render_frame(
            "paycheck_arrival",
            4,
            2.0,
            "clean_infographic",
        )
        safe_area = frame.crop((80, 930, 1840, 1010)).convert("L")
        bright_content = safe_area.point(
            lambda value: 255 if value >= 235 else 0,
            mode="1",
        )
        self.assertIsNone(bright_content.getbbox())

    def test_encoder_remains_portable(self) -> None:
        command = character.ffmpeg_encoder_command("ffmpeg", Path("output.mp4"))
        rendered = " ".join(command)
        self.assertIn("rawvideo", rendered)
        self.assertIn("rgb24", rendered)
        self.assertNotIn("drawtext", rendered)
        self.assertNotIn("-vf", command)

    def test_unknown_family_and_template_are_rejected(self) -> None:
        with self.assertRaises(HTTPException):
            exact_visuals.template_catalog("unknown-family")
        with self.assertRaises(HTTPException):
            character.render_frame("unknown-template", 4, 1)


if __name__ == "__main__":
    unittest.main()
