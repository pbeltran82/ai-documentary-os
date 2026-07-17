from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Project
from app.routers.projects import update_project
from app.schemas import ProjectCreate, ProjectUpdate
from app.services import exact_visuals
from app.services.finance_motion import ffmpeg_encoder_command
from app.services.native_shorts import COMPOSITIONS
from app.services.video_format import (
    SHORTS_FORMAT,
    YOUTUBE_FORMAT,
    exact_visual_source_time,
    format_exact_visual_frame,
    normalize_video_format,
    video_format_catalog,
    video_format_profile,
)


class VideoFormatTests(unittest.TestCase):
    def sample_frame(self) -> Image.Image:
        frame = Image.new("RGB", (1920, 1080), (8, 16, 28))
        draw = ImageDraw.Draw(frame)
        draw.rectangle((60, 45, 1860, 270), fill=(21, 62, 76))
        draw.rectangle((60, 300, 1040, 1020), fill=(45, 105, 135))
        draw.rectangle((880, 300, 1860, 1020), fill=(190, 91, 74))
        draw.text((120, 120), "DOCUMENTARY TITLE", fill=(245, 248, 250))
        return frame

    def test_project_schema_defaults_existing_work_to_youtube(self) -> None:
        project = ProjectCreate(title="Test film", topic="A documentary topic")
        self.assertEqual(project.video_format, YOUTUBE_FORMAT)

    def test_catalog_exposes_exact_delivery_dimensions(self) -> None:
        catalog = {item["format_id"]: item for item in video_format_catalog()}
        self.assertEqual((catalog[YOUTUBE_FORMAT]["width"], catalog[YOUTUBE_FORMAT]["height"]), (1920, 1080))
        self.assertEqual((catalog[SHORTS_FORMAT]["width"], catalog[SHORTS_FORMAT]["height"]), (1080, 1920))
        self.assertEqual(catalog[SHORTS_FORMAT]["aspect_ratio"], "9:16")

    def test_unknown_format_falls_back_safely(self) -> None:
        self.assertEqual(normalize_video_format("square"), YOUTUBE_FORMAT)
        self.assertEqual(video_format_profile(None).format_id, YOUTUBE_FORMAT)

    def test_landscape_frame_is_preserved_and_shorts_gets_native_composition(self) -> None:
        source = self.sample_frame()
        youtube = format_exact_visual_frame(
            source,
            YOUTUBE_FORMAT,
            "character_explainer",
            "paycheck_arrival",
            progress=0.82,
            title="A title that must not change landscape pixels",
        )
        shorts = format_exact_visual_frame(
            source,
            SHORTS_FORMAT,
            "character_explainer",
            "paycheck_arrival",
            progress=0.5,
            title="THE PAYCHECK ARRIVES",
            subtitle="The first decision happens before lifestyle spending.",
        )

        self.assertEqual(youtube.size, (1920, 1080))
        self.assertEqual(youtube.tobytes(), source.tobytes())
        self.assertEqual(shorts.size, (1080, 1920))
        self.assertEqual(shorts.mode, "RGB")
        self.assertGreater(len(set(shorts.resize((54, 96)).getdata())), 25)
        # Native mobile typography and one full-size hero occupy the safe area
        # without carrying the source panel's landscape chrome into Shorts.
        self.assertIsNotNone(shorts.crop((58, 130, 946, 380)).getbbox())
        self.assertIsNotNone(shorts.crop((58, 410, 946, 1458)).getbbox())
        self.assertIsNotNone(shorts.crop((58, 1490, 946, 1690)).getbbox())

    def test_encoder_accepts_vertical_raw_frame_dimensions(self) -> None:
        command = ffmpeg_encoder_command("ffmpeg", Path("short.mp4"), 1080, 1920)
        self.assertEqual(command[command.index("-s") + 1], "1080x1920")

    def test_shorts_holds_one_hero_instead_of_cycling_source_beats(self) -> None:
        source = Image.new("RGB", (1920, 1080), (8, 16, 28))
        draw = ImageDraw.Draw(source)
        draw.ellipse((1350, 410, 1790, 900), fill=(45, 105, 230))

        samples: list[Image.Image] = []
        for progress in (0.15, 0.50, 0.85):
            with self.subTest(progress=progress):
                shorts = format_exact_visual_frame(
                    source,
                    SHORTS_FORMAT,
                    "tech_behavior_motion",
                    "algorithm_chose_you",
                    progress=progress,
                    title="THE ALGORITHM CHOSE THE MOMENT",
                    subtitle="Thousands of possibilities. One ranked outcome.",
                )
                samples.append(shorts)
                blue_pixels = sum(
                    1
                    for red, green, blue in shorts.crop((70, 410, 1010, 1450)).getdata()
                    if blue > red * 1.5 and blue > green * 1.15
                )
                self.assertGreater(blue_pixels, 70_000)
        # Progress may move the camera gently, but it must not swap the hero.
        self.assertNotEqual(samples[0].tobytes(), samples[-1].tobytes())

    def test_shorts_uses_a_fixed_mature_source_state_only(self) -> None:
        duration = 8.0
        source_times = {
            exact_visual_source_time(SHORTS_FORMAT, duration, output_time)
            for output_time in (0.0, 2.0, 4.0, 7.9)
        }
        self.assertEqual(len(source_times), 1)
        self.assertAlmostEqual(source_times.pop(), 6.56)
        self.assertEqual(exact_visual_source_time(YOUTUBE_FORMAT, duration, 2.0), 2.0)
        self.assertEqual(exact_visual_source_time(YOUTUBE_FORMAT, duration, 7.9), 7.9)

    def test_shorts_does_not_reuse_source_grid_or_nested_card_border(self) -> None:
        source = Image.new("RGB", (1920, 1080), (8, 16, 28))
        draw = ImageDraw.Draw(source)
        grid = (40, 72, 108)
        for x in range(1275, 1855, 70):
            draw.line((x, 350, x, 980), fill=grid, width=2)
        for y in range(350, 981, 70):
            draw.line((1275, y, 1855, y), fill=grid, width=2)
        draw.ellipse((1400, 480, 1740, 860), fill=(45, 180, 230))

        shorts = format_exact_visual_frame(
            source,
            SHORTS_FORMAT,
            "tech_behavior_motion",
            "algorithm_chose_you",
            progress=0.5,
            title="ONE CLEAN IDEA",
            subtitle="The source grid should not become the Shorts background.",
        )
        exact_grid_pixels = sum(1 for color in shorts.getdata() if color == grid)
        self.assertLess(exact_grid_pixels, 120)

    def test_tech_terminal_cta_keeps_subscribe_and_like_together(self) -> None:
        source = Image.new("RGB", (1920, 1080), (8, 16, 28))
        draw = ImageDraw.Draw(source)
        subscribe = (220, 53, 69)
        like = (48, 126, 218)
        for progress in (0.25, 0.90):
            with self.subTest(progress=progress):
                shorts = format_exact_visual_frame(
                    source,
                    SHORTS_FORMAT,
                    "tech_behavior_motion",
                    "machine_choice_cta",
                    progress=progress,
                    title="WHO CHOSE THIS MOMENT?",
                    subtitle="You pressed play. The machine ranked the opportunity.",
                )
                colors = shorts.getcolors(maxcolors=shorts.width * shorts.height) or []
                counts = {color: count for count, color in colors}
                self.assertGreater(counts.get(subscribe, 0), 30_000)
                self.assertGreater(counts.get(like, 0), 15_000)

    def test_unknown_future_template_uses_native_single_hero_fallback(self) -> None:
        source = self.sample_frame()
        shorts = format_exact_visual_frame(
            source,
            SHORTS_FORMAT,
            "future_documentary_family",
            "new_template_added_later",
            progress=0.52,
            title="A NEW DOCUMENTARY IDEA",
            subtitle="Future templates receive a safe native vertical story automatically.",
        )
        self.assertEqual(shorts.size, (1080, 1920))
        self.assertGreater(len(set(shorts.resize((54, 96)).getdata())), 25)

    def test_every_current_exact_visual_has_a_semantic_shorts_mapping(self) -> None:
        current_templates = {
            (family_id, item["template_id"])
            for family_id in (
                exact_visuals.FINANCE_FAMILY_ID,
                exact_visuals.CHARACTER_FAMILY_ID,
                exact_visuals.TECH_FAMILY_ID,
            )
            for item in exact_visuals.template_catalog(family_id)
        }

        self.assertEqual(current_templates, current_templates & set(COMPOSITIONS))

    def test_project_format_update_persists_and_invalidates_old_render(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        project = Project(
            title="Vertical documentary",
            topic="A documentary made for Shorts",
            video_format="youtube",
        )
        session.add(project)
        session.commit()

        with patch("app.routers.projects.invalidate_render_artifacts") as invalidate:
            updated = update_project(
                project.id,
                ProjectUpdate(video_format="shorts"),
                session,
            )

        self.assertEqual(updated.video_format, "shorts")
        self.assertEqual(session.get(Project, project.id).video_format, "shorts")
        invalidate.assert_called_once_with(project.id)
        session.close()


if __name__ == "__main__":
    unittest.main()
