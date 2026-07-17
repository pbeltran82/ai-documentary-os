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
from app.services.finance_motion import ffmpeg_encoder_command
from app.services.video_format import (
    SHORTS_FORMAT,
    YOUTUBE_FORMAT,
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

    def test_landscape_frame_is_preserved_and_shorts_gets_vertical_reflow(self) -> None:
        source = self.sample_frame()
        youtube = format_exact_visual_frame(source, YOUTUBE_FORMAT)
        shorts = format_exact_visual_frame(
            source,
            SHORTS_FORMAT,
            "character_explainer",
            "paycheck_arrival",
        )

        self.assertEqual(youtube.size, (1920, 1080))
        self.assertEqual(youtube.tobytes(), source.tobytes())
        self.assertEqual(shorts.size, (1080, 1920))
        self.assertEqual(shorts.mode, "RGB")
        self.assertGreater(len(set(shorts.resize((54, 96)).getdata())), 25)
        # Both story halves survive the vertical reflow.
        self.assertGreater(shorts.crop((80, 360, 1000, 1040)).getbbox()[2], 800)
        self.assertGreater(shorts.crop((80, 1150, 1000, 1830)).getbbox()[2], 800)

    def test_encoder_accepts_vertical_raw_frame_dimensions(self) -> None:
        command = ffmpeg_encoder_command("ffmpeg", Path("short.mp4"), 1080, 1920)
        self.assertEqual(command[command.index("-s") + 1], "1080x1920")

    def test_three_column_tech_story_becomes_three_intact_shorts_panels(self) -> None:
        source = Image.new("RGB", (1920, 1080), (8, 16, 28))
        draw = ImageDraw.Draw(source)
        draw.rectangle((65, 340, 640, 999), fill=(220, 45, 55))
        draw.rectangle((662, 340, 1238, 999), fill=(35, 205, 105))
        draw.rectangle((1277, 340, 1853, 999), fill=(45, 105, 230))

        shorts = format_exact_visual_frame(
            source,
            SHORTS_FORMAT,
            "tech_behavior_motion",
            "algorithm_chose_you",
        )

        self.assertEqual(shorts.getpixel((540, 560)), (220, 45, 55))
        self.assertEqual(shorts.getpixel((540, 1080)), (35, 205, 105))
        self.assertEqual(shorts.getpixel((540, 1600)), (45, 105, 230))

    def test_tech_terminal_cta_keeps_subscribe_and_like_together(self) -> None:
        source = Image.new("RGB", (1920, 1080), (8, 16, 28))
        draw = ImageDraw.Draw(source)
        subscribe = (246, 42, 63)
        like = (45, 139, 224)
        draw.rectangle((620, 865, 980, 965), fill=subscribe)
        draw.rectangle((1080, 865, 1350, 965), fill=like)

        shorts = format_exact_visual_frame(
            source,
            SHORTS_FORMAT,
            "tech_behavior_motion",
            "machine_choice_cta",
        )

        bottom = shorts.crop((34, 1372, 1046, 1874))
        colors = bottom.getcolors(maxcolors=bottom.width * bottom.height) or []
        counts = {color: count for count, color in colors}
        self.assertGreater(counts.get(subscribe, 0), 20_000)
        self.assertGreater(counts.get(like, 0), 15_000)

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
