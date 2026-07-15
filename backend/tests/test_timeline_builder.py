from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models import Asset, Project, Scene
from app.services import media_library, timeline_builder
from app.services.render_invalidation import invalidate_render_artifacts


class TimelineBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.media_root = Path(self.temporary.name)
        self.media_patch = patch.object(media_library, "MEDIA_ROOT", self.media_root)
        self.timeline_patch = patch.object(timeline_builder, "MEDIA_ROOT", self.media_root)
        self.media_patch.start()
        self.timeline_patch.start()

    def tearDown(self) -> None:
        self.timeline_patch.stop()
        self.media_patch.stop()
        self.temporary.cleanup()

    def make_project(self, media_type: str = "video") -> Project:
        project = Project(
            id=1,
            title="Compound Blueprint",
            topic="Compound growth",
            target_minutes=8,
            audience="General audience",
            tone="Cinematic",
            visual_style="Cinematic documentary",
            status="timeline",
        )
        scene = Scene(
            id=10,
            project_id=1,
            scene_number=1,
            start_seconds=0,
            end_seconds=5,
            duration_seconds=5,
            narration="Time changes everything.",
            visual_intent="Stock chart growth",
            search_keywords=["stock chart"],
            preferred_asset_type="stock_video" if media_type == "video" else "stock_image",
            asset_status="ready",
        )
        extension = ".mp4" if media_type == "video" else ".jpg"
        local_path = f"project-0001/assets/scene-001-test{extension}"
        asset_file = self.media_root / local_path
        asset_file.parent.mkdir(parents=True, exist_ok=True)
        asset_file.write_bytes(b"local-media")
        asset = Asset(
            id=20,
            scene_id=10,
            provider="pixabay",
            provider_asset_id="asset-1",
            media_type=media_type,
            source_url="https://example.com/source",
            preview_url="http://localhost:8000/media/preview.jpg",
            download_url=f"http://localhost:8000/media/{local_path}",
            remote_download_url="https://example.com/remote",
            creator="Creator",
            creator_url="https://example.com/creator",
            width=1920,
            height=1080,
            duration_seconds=12 if media_type == "video" else None,
            license_name="Test License",
            license_url="https://example.com/license",
            attribution="Creator attribution",
            local_path=local_path,
            local_preview_path=local_path,
            content_type="video/mp4" if media_type == "video" else "image/jpeg",
            file_size_bytes=11,
            checksum_sha256="0" * 64,
        )
        scene.selected_asset = asset
        project.scenes = [scene]
        return project

    def test_video_plan_loops_trims_normalizes_and_concatenates(self) -> None:
        project = self.make_project("video")
        with patch.object(
            timeline_builder,
            "ffmpeg_executable",
            return_value="/opt/homebrew/bin/ffmpeg",
        ):
            plan = timeline_builder.write_timeline_plan(project)

        self.assertTrue(plan["ready"])
        self.assertEqual(plan["clip_count"], 1)
        self.assertEqual(plan["runtime_seconds"], 5)
        self.assertIn("-stream_loop", plan["command"])
        filter_graph = plan["command"][plan["command"].index("-filter_complex") + 1]
        self.assertIn("trim=duration=5.000", filter_graph)
        self.assertIn("scale=1920:1080", filter_graph)
        self.assertIn("concat=n=1:v=1:a=0", filter_graph)

        timeline_dir = self.media_root / "project-0001" / "timeline"
        self.assertTrue((timeline_dir / "render-plan.json").is_file())
        self.assertTrue((timeline_dir / "render.sh").is_file())
        saved = json.loads((timeline_dir / "render-plan.json").read_text())
        self.assertEqual(saved["clips"][0]["assembly_action"], "Loop if needed, trim to 5s, fit 16:9")

    def test_photo_plan_uses_image_loop_input(self) -> None:
        project = self.make_project("photo")
        with patch.object(timeline_builder, "ffmpeg_executable", return_value="ffmpeg"):
            plan = timeline_builder.build_timeline_plan(project)

        self.assertIn("-loop", plan["command"])
        self.assertIn("-framerate", plan["command"])
        self.assertNotIn("-stream_loop", plan["command"])
        self.assertEqual(plan["clips"][0]["assembly_action"], "Hold for 5s, fit 16:9")

    def test_missing_asset_blocks_render_plan(self) -> None:
        project = self.make_project("video")
        project.scenes[0].selected_asset = None
        project.scenes[0].asset_status = "missing"

        plan = timeline_builder.write_timeline_plan(project)

        self.assertFalse(plan["ready"])
        self.assertEqual(plan["clip_count"], 0)
        self.assertEqual(plan["missing_scenes"][0]["scene_number"], 1)
        self.assertEqual(plan["command"], [])

    def test_timeline_change_invalidates_stale_render_files(self) -> None:
        timeline_dir = self.media_root / "project-0001" / "timeline"
        timeline_dir.mkdir(parents=True, exist_ok=True)
        for filename in ("first-cut.mp4", "render-plan.json", "render.sh"):
            (timeline_dir / filename).write_text("stale")

        invalidate_render_artifacts(1)

        self.assertFalse((timeline_dir / "first-cut.mp4").exists())
        self.assertFalse((timeline_dir / "render-plan.json").exists())
        self.assertFalse((timeline_dir / "render.sh").exists())


if __name__ == "__main__":
    unittest.main()
