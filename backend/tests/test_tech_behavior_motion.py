from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageChops, ImageDraw

from app.models import Project, Scene
from app.services import exact_visuals
from app.services import engagement_cta
from app.services import tech_behavior_motion as tech
from app.services import tech_behavior_truthful as truthful


class TechBehaviorMotionTests(unittest.TestCase):
    def scene(self, narration: str, visual_intent: str = "") -> Scene:
        project = Project(
            id=2,
            title="The Algorithm Chose You",
            topic="AI prediction and behavioral modeling",
            target_minutes=1,
            audience="General audience",
            tone="Tense documentary",
            visual_style="Cinematic technology documentary",
            status="assets",
        )
        scene = Scene(
            id=12,
            project_id=2,
            scene_number=2,
            start_seconds=6,
            end_seconds=12,
            duration_seconds=6,
            narration=narration,
            visual_intent=visual_intent,
            search_keywords=[],
            preferred_asset_type="stock_video",
            asset_status="missing",
        )
        scene.project = project
        project.scenes = [scene]
        return scene

    def project_scenes(self, narrations: list[str]) -> list[Scene]:
        project = Project(
            id=22,
            title="Behavioral Ranking",
            topic="AI prediction and behavioral modeling",
            target_minutes=1,
            audience="General audience",
            tone="Tense documentary",
            visual_style="Cinematic technology documentary",
            status="assets",
        )
        project.scenes = [
            Scene(
                id=100 + index,
                project_id=project.id,
                scene_number=index,
                start_seconds=(index - 1) * 6,
                end_seconds=index * 6,
                duration_seconds=6,
                narration=narration,
                visual_intent="",
                search_keywords=[],
                preferred_asset_type="stock_video",
                asset_status="missing",
            )
            for index, narration in enumerate(narrations, 1)
        ]
        for scene in project.scenes:
            scene.project = project
        return project.scenes

    def test_catalog_exposes_six_tech_templates(self) -> None:
        catalog = tech.template_catalog()
        self.assertEqual(len(catalog), 7)
        self.assertEqual(
            {item["template_id"] for item in catalog},
            {
                "algorithm_chose_you",
                "behavior_prediction_engine",
                "life_event_timeline",
                "digital_footprint_collector",
                "behavioral_twin",
                "machine_choice_explainer",
                "machine_choice_cta",
            },
        )

    def test_family_catalog_exposes_three_modular_visual_systems(self) -> None:
        catalog = exact_visuals.family_catalog()
        self.assertEqual(len(catalog), 3)
        self.assertEqual(
            {item["family_id"] for item in catalog},
            {
                exact_visuals.FINANCE_FAMILY_ID,
                exact_visuals.CHARACTER_FAMILY_ID,
                exact_visuals.TECH_FAMILY_ID,
            },
        )

    def test_algorithm_documentary_scenes_route_to_tech_motion(self) -> None:
        examples = (
            "A silent algorithm decided you would watch this exact video today.",
            "Artificial intelligence is predicting human behavior.",
            "Researchers estimated job changes, sickness, and mortality from a digital footprint.",
            "Every scroll, every pause, and every deleted draft becomes a signal.",
            "Those signals create a digital twin designed to anticipate what you do next.",
            "Did you choose to watch this, or did the machine choose the moment?",
        )
        for narration in examples:
            with self.subTest(narration=narration):
                family_id, confidence, reason = exact_visuals.recommend_family(
                    self.scene(narration)
                )
                self.assertEqual(family_id, exact_visuals.TECH_FAMILY_ID)
                self.assertGreaterEqual(confidence, 0.60)
                self.assertTrue(
                    "algorithmic behavior" in reason
                    or "Technology, prediction" in reason
                )

    def test_finance_and_character_regression_routing_remains_intact(self) -> None:
        finance_family, _confidence, _reason = exact_visuals.recommend_family(
            self.scene("Compound interest grows inside a low-cost S&P 500 index fund.")
        )
        character_family, _confidence, _reason = exact_visuals.recommend_family(
            self.scene("Most people get paid, pay rent, buy groceries, and go out.")
        )
        self.assertEqual(finance_family, exact_visuals.FINANCE_FAMILY_ID)
        self.assertEqual(character_family, exact_visuals.CHARACTER_FAMILY_ID)

    def test_template_recommendations_match_the_script_concepts(self) -> None:
        cases = (
            ("A silent algorithm ranked this exact video for you today.", "algorithm_chose_you"),
            ("Artificial intelligence is predicting human behavior better than humans can.", "behavior_prediction_engine"),
            ("The model estimates job changes, health events, and mortality across a timeline.", "life_event_timeline"),
            ("Your digital footprint collects every scroll and click.", "digital_footprint_collector"),
            ("Those signals create a behavioral digital twin of you.", "behavioral_twin"),
            ("Did you choose, or did the machine choose? Subscribe if you are awake.", "machine_choice_cta"),
        )
        for narration, expected in cases:
            with self.subTest(template=expected):
                template, confidence, _reason = tech.suggest_template(self.scene(narration))
                self.assertEqual(template.template_id, expected)
                self.assertGreater(confidence, 0.50)

    def test_cta_is_reserved_for_the_terminal_scene(self) -> None:
        scenes = self.project_scenes(
            [
                "Did you choose, or did the machine choose the moment?",
                "Did you choose, or did the machine choose the moment? Like and subscribe.",
            ]
        )

        early, _confidence, _reason = tech.suggest_template(scenes[0])
        terminal, _confidence, _reason = tech.suggest_template(scenes[1])

        self.assertEqual(early.template_id, "machine_choice_explainer")
        self.assertEqual(terminal.template_id, "machine_choice_cta")

    def test_project_sequence_avoids_recent_exact_template_repeats(self) -> None:
        scenes = self.project_scenes(
            [
                "This exact video would reach you through a recommendation system.",
                "Artificial intelligence predicts behavior from every signal.",
                "Your digital footprint collects every scroll and click.",
                "Life records estimate job changes and future health events.",
                "Artificial intelligence predicts behavior from every signal.",
                "Your digital footprint collects every scroll and click.",
                "Those signals create a behavioral twin of you.",
                "A recommendation system ranked the opportunity.",
                "Did you choose, or did the machine choose the moment?",
                "Systems that learn how to navigate us create a behavioral version of you.",
                "Did you choose, or did the machine choose the moment? Like and subscribe.",
            ]
        )
        selected = [tech.suggest_template(scene)[0].template_id for scene in scenes]

        for index, template_id in enumerate(selected):
            with self.subTest(scene=index + 1, template=template_id):
                self.assertNotIn(template_id, selected[max(0, index - 3):index])
        self.assertNotIn("machine_choice_cta", selected[:-1])
        self.assertEqual(selected[-1], "machine_choice_cta")

    def test_behavioral_twin_uses_finished_clothed_characters(self) -> None:
        palette = tech._palette(tech.DEFAULT_STYLE_ID)
        character_palette = truthful.tech_character_palette(palette)
        canvas = Image.new("RGB", (tech.OUTPUT_WIDTH, tech.OUTPUT_HEIGHT), palette["background"])

        truthful._truthful_behavioral_twin(ImageDraw.Draw(canvas), 0.78, palette)

        pixels = list(canvas.getdata())
        self.assertGreater(pixels.count(character_palette["skin"]), 1200)
        self.assertGreater(pixels.count(character_palette["denim"]), 900)
        self.assertGreater(pixels.count(character_palette["denim_alt"]), 900)

    def test_tech_end_card_uses_shared_red_subscribe_and_blue_like_actions(self) -> None:
        palette = tech._palette(tech.DEFAULT_STYLE_ID)
        canvas = Image.new("RGB", (tech.OUTPUT_WIDTH, tech.OUTPUT_HEIGHT), palette["background"])

        tech._machine_choice_cta(ImageDraw.Draw(canvas), 0.92, palette)

        pixels = list(canvas.getdata())
        self.assertGreater(pixels.count(engagement_cta.SUBSCRIBE_RED), 3500)
        self.assertGreater(pixels.count(engagement_cta.LIKE_BLUE), 1500)
        final_bar_bottom = (
            tech.MACHINE_CHOICE_BAR_START_Y
            + 6 * tech.MACHINE_CHOICE_BAR_STEP_Y
            + tech.MACHINE_CHOICE_BAR_HEIGHT
        )
        self.assertGreaterEqual(tech.MACHINE_CHOICE_LABEL_Y - final_bar_bottom, 35)

    def test_all_tech_templates_render_distinct_1080p_frames(self) -> None:
        signatures: set[str] = set()
        for template in tech.TEMPLATES:
            with self.subTest(template=template.template_id):
                frame = tech.render_frame(
                    template.template_id,
                    6,
                    3.2,
                    tech.DEFAULT_STYLE_ID,
                )
                self.assertEqual(frame.size, (1920, 1080))
                self.assertEqual(frame.mode, "RGB")
                sample = frame.resize((96, 54))
                self.assertGreater(len(set(sample.getdata())), 40)
                signatures.add(hashlib.sha256(sample.tobytes()).hexdigest())
        self.assertEqual(len(signatures), len(tech.TEMPLATES))

    def test_all_three_house_styles_work_with_tech_templates(self) -> None:
        frames = [
            tech.render_frame("behavioral_twin", 6, 3.1, style.style_id)
            for style in tech.STYLES
        ]
        self.assertEqual(len(frames), 3)
        self.assertIsNotNone(ImageChops.difference(frames[0], frames[1]).getbbox())
        self.assertIsNotNone(ImageChops.difference(frames[1], frames[2]).getbbox())

    def test_storyboard_beats_change_the_rendered_story(self) -> None:
        beats = tech.storyboard_beats("behavior_prediction_engine", 6)
        frames = [
            tech.render_frame(
                "behavior_prediction_engine",
                6,
                float(beat["time_seconds"]),
                tech.DEFAULT_STYLE_ID,
            )
            for beat in beats
        ]
        self.assertEqual(len(beats), 3)
        self.assertLess(float(beats[0]["time_seconds"]), float(beats[1]["time_seconds"]))
        self.assertLess(float(beats[1]["time_seconds"]), float(beats[2]["time_seconds"]))
        self.assertIsNotNone(ImageChops.difference(frames[0], frames[1]).getbbox())
        self.assertIsNotNone(ImageChops.difference(frames[1], frames[2]).getbbox())

    def test_exports_keep_footer_safe_area_unbranded(self) -> None:
        frame = tech.render_frame(
            "algorithm_chose_you",
            6,
            3.0,
            "clean_infographic",
        )
        safe_area = frame.crop((80, 975, 1840, 1040)).convert("L")
        bright_content = safe_area.point(
            lambda value: 255 if value >= 235 else 0,
            mode="1",
        )
        self.assertIsNone(bright_content.getbbox())

    def test_encoder_remains_portable(self) -> None:
        command = tech.ffmpeg_encoder_command("ffmpeg", Path("output.mp4"))
        rendered = " ".join(command)
        self.assertIn("rawvideo", rendered)
        self.assertIn("rgb24", rendered)
        self.assertNotIn("drawtext", rendered)
        self.assertNotIn("-vf", command)

    def test_unknown_tech_template_is_rejected(self) -> None:
        with self.assertRaises(HTTPException):
            tech.render_frame("unknown-template", 6, 2)


if __name__ == "__main__":
    unittest.main()
