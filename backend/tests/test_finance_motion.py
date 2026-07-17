from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageChops, ImageDraw

from app.models import Project, Scene
from app.services import finance_motion_composition as composition
from app.services.finance_motion_choreography import (
    DEFAULT_STYLE_ID,
    OUTPUT_HEIGHT,
    OUTPUT_WIDTH,
    STYLES,
    TEMPLATES,
    ffmpeg_encoder_command,
    render_frame,
    storyboard_beats,
    style_catalog,
    suggest_template,
)


class FinanceMotionTests(unittest.TestCase):
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

    def test_empty_balance_scene_gets_exact_template(self) -> None:
        template, confidence, reason = suggest_template(
            self.scene("Spoiler alert: there is never anything left. The balance is zero.")
        )
        self.assertEqual(template.template_id, "empty_balance")
        self.assertGreaterEqual(confidence, 0.68)
        self.assertIn("Matched", reason)

    def test_automatic_investing_scene_gets_transfer_template(self) -> None:
        template, _confidence, _reason = suggest_template(
            self.scene(
                "Route ten percent automatically into an index fund every payday.",
                "A recurring automatic transfer from checking into an investment account.",
            )
        )
        self.assertEqual(template.template_id, "recurring_transfer")

    def test_compounding_scene_gets_growth_template(self) -> None:
        template, _confidence, _reason = suggest_template(
            self.scene("Compound interest builds an invisible wealth machine for your future self.")
        )
        self.assertEqual(template.template_id, "compound_growth")

    def test_every_template_renders_a_portable_1080p_frame(self) -> None:
        for template in TEMPLATES:
            with self.subTest(template=template.template_id):
                frame = render_frame(template.template_id, 4, 1.5, DEFAULT_STYLE_ID)
                self.assertEqual(frame.size, (OUTPUT_WIDTH, OUTPUT_HEIGHT))
                self.assertEqual(frame.mode, "RGB")

    def test_semantic_templates_have_distinct_compositions(self) -> None:
        signatures: set[str] = set()
        for template in TEMPLATES:
            frame = render_frame(template.template_id, 4, 2.0, "clean_infographic")
            sample = frame.resize((96, 54))
            signatures.add(hashlib.sha256(sample.tobytes()).hexdigest())
            self.assertGreater(len(set(sample.getdata())), 35)
        self.assertEqual(len(signatures), len(TEMPLATES))

    def test_all_house_styles_render_and_are_visually_distinct(self) -> None:
        frames = [
            render_frame("paycheck_split", 4, 2.0, style.style_id)
            for style in STYLES
        ]
        for frame in frames:
            self.assertEqual(frame.size, (OUTPUT_WIDTH, OUTPUT_HEIGHT))
            self.assertEqual(frame.mode, "RGB")
        self.assertIsNotNone(ImageChops.difference(frames[0], frames[1]).getbbox())
        self.assertIsNotNone(ImageChops.difference(frames[1], frames[2]).getbbox())

    def test_style_catalog_exposes_three_house_styles(self) -> None:
        catalog = style_catalog()
        self.assertEqual(len(catalog), 3)
        self.assertEqual(DEFAULT_STYLE_ID, "premium_motion")
        self.assertTrue(all(len(item["swatches"]) == 4 for item in catalog))

    def test_storyboard_beats_are_ordered_and_scene_specific(self) -> None:
        beats = storyboard_beats("recurring_transfer", 7)
        self.assertEqual([beat["label"] for beat in beats], ["PAYDAY", "AUTO-TRANSFER", "CONFIRMED"])
        times = [float(beat["time_seconds"]) for beat in beats]
        self.assertEqual(times, sorted(times))
        self.assertTrue(all(0 < value < 7 for value in times))

    def test_storyboard_keyframes_show_real_choreography_progression(self) -> None:
        beats = storyboard_beats("paycheck_split", 7)
        frames = [
            render_frame("paycheck_split", 7, float(beat["time_seconds"]), DEFAULT_STYLE_ID)
            for beat in beats
        ]
        self.assertIsNotNone(ImageChops.difference(frames[0], frames[1]).getbbox())
        self.assertIsNotNone(ImageChops.difference(frames[1], frames[2]).getbbox())

    def test_end_card_uses_a_slim_red_subscribe_and_blue_like_action(self) -> None:
        canvas = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (255, 255, 255))
        composition._cta_composed(ImageDraw.Draw(canvas), 2.5)
        pixels = list(canvas.getdata())
        self.assertGreater(pixels.count(composition.SUBSCRIBE_RED), 5000)
        self.assertGreater(pixels.count(composition.LIKE_BLUE), 2000)

        red_rows = [
            y
            for y in range(350, 700)
            for x in range(1040, 1800)
            if canvas.getpixel((x, y)) == composition.SUBSCRIBE_RED
        ]
        self.assertLess(max(red_rows) - min(red_rows), 120)

    def test_like_action_arrives_on_the_final_cta_beat(self) -> None:
        early = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (255, 255, 255))
        final = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (255, 255, 255))
        composition._cta_composed(ImageDraw.Draw(early), 0.7)
        composition._cta_composed(ImageDraw.Draw(final), 2.5)
        self.assertEqual(list(early.getdata()).count(composition.LIKE_BLUE), 0)
        self.assertGreater(list(final.getdata()).count(composition.LIKE_BLUE), 2000)

        beats = storyboard_beats("subscribe_cta", 7)
        self.assertEqual(beats[-1]["label"], "LIKE + SUBSCRIBE")

    def test_exports_leave_the_footer_safe_area_unbranded(self) -> None:
        for style in STYLES:
            with self.subTest(style=style.style_id):
                frame = render_frame("paycheck_split", 4, 2, style.style_id)
                safe_area = frame.crop((80, 930, 1840, 1010)).convert("L")
                bright_content = safe_area.point(
                    lambda value: 255 if value >= 225 else 0,
                    mode="1",
                )
                self.assertIsNone(bright_content.getbbox())

    def test_paycheck_template_has_real_motion_between_keyframes(self) -> None:
        early = render_frame("paycheck_split", 4, 0.45, DEFAULT_STYLE_ID)
        settled = render_frame("paycheck_split", 4, 2.0, DEFAULT_STYLE_ID)
        self.assertIsNotNone(ImageChops.difference(early, settled).getbbox())

    def test_encoder_uses_raw_frames_not_optional_drawtext_filter(self) -> None:
        command = ffmpeg_encoder_command("ffmpeg", Path("output.mp4"))
        rendered = " ".join(command)
        self.assertIn("rawvideo", rendered)
        self.assertIn("rgb24", rendered)
        self.assertNotIn("drawtext", rendered)
        self.assertNotIn("-vf", command)

    def test_unknown_template_and_style_are_rejected(self) -> None:
        with self.assertRaises(HTTPException):
            render_frame("not-a-template", 4, 1, DEFAULT_STYLE_ID)
        with self.assertRaises(HTTPException):
            render_frame("paycheck_split", 4, 1, "not-a-style")
        with self.assertRaises(HTTPException):
            storyboard_beats("not-a-template", 4)


if __name__ == "__main__":
    unittest.main()
