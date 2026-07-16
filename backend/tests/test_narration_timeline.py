from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models import Asset, Project, Scene
from app.services import media_library, timeline_builder


class NarratedTimelineTests(unittest.TestCase):
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

    def make_project(self) -> Project:
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
            narration="Most people underestimate the power of time.",
            visual_intent="Stock chart growth",
            search_keywords=["stock chart"],
            preferred_asset_type="stock_video",
            asset_status="ready",
        )
        local_path = "project-0001/assets/scene-001-test.mp4"
        asset_file = self.media_root / local_path
        asset_file.parent.mkdir(parents=True, exist_ok=True)
        asset_file.write_bytes(b"video")
        scene.selected_asset = Asset(
            id=20,
            scene_id=10,
            provider="pixabay",
            provider_asset_id="asset-1",
            media_type="video",
            source_url="https://example.com/source",
            preview_url="http://localhost:8000/media/preview.jpg",
            download_url=f"http://localhost:8000/media/{local_path}",
            remote_download_url="https://example.com/remote",
            creator="Creator",
            creator_url="https://example.com/creator",
            width=1920,
            height=1080,
            duration_seconds=12,
            license_name="Test License",
            license_url="https://example.com/license",
            attribution="Creator attribution",
            local_path=local_path,
            local_preview_path=local_path,
            content_type="video/mp4",
            file_size_bytes=5,
            checksum_sha256="0" * 64,
        )
        project.scenes = [scene]
        return project

    def voiceover(self, duration: float) -> dict:
        audio_file = self.media_root / "project-0001" / "audio" / "narration.mp3"
        audio_file.parent.mkdir(parents=True, exist_ok=True)
        audio_file.write_bytes(b"audio")
        return {
            "original_filename": "voiceover.mp3",
            "relative_path": "project-0001/audio/narration.mp3",
            "public_url": "http://localhost:8000/media/project-0001/audio/narration.mp3",
            "content_type": "audio/mpeg",
            "file_size_bytes": 5,
            "checksum_sha256": "1" * 64,
            "duration_seconds": duration,
            "uploaded_at": "2026-07-15T00:00:00+00:00",
            "source_file": str(audio_file),
        }

    def test_aligned_voiceover_adds_aac_audio_to_render_command(self) -> None:
        project = self.make_project()
        with (
            patch.object(timeline_builder, "ffmpeg_executable", return_value="ffmpeg"),
            patch.object(timeline_builder, "load_voiceover", return_value=self.voiceover(5.1)),
        ):
            plan = timeline_builder.build_timeline_plan(project)

        self.assertEqual(plan["alignment_status"], "aligned")
        self.assertEqual(plan["settings"]["audio"], "narration")
        self.assertIn("-c:a", plan["command"])
        self.assertIn("aac", plan["command"])
        filter_graph = plan["command"][plan["command"].index("-filter_complex") + 1]
        self.assertIn("apad=whole_dur=5.000", filter_graph)
        self.assertIn("atrim=duration=5.000", filter_graph)
        self.assertIn("[outa]", filter_graph)

    def test_long_voiceover_produces_explicit_trim_warning(self) -> None:
        project = self.make_project()
        with patch.object(timeline_builder, "load_voiceover", return_value=self.voiceover(7.25)):
            plan = timeline_builder.build_timeline_plan(project)

        self.assertEqual(plan["alignment_status"], "longer")
        self.assertEqual(plan["duration_delta_seconds"], 2.25)
        self.assertIn("trimmed", plan["alignment_message"])

    def test_missing_voiceover_keeps_silent_render_available(self) -> None:
        project = self.make_project()
        with (
            patch.object(timeline_builder, "ffmpeg_executable", return_value="ffmpeg"),
            patch.object(timeline_builder, "load_voiceover", return_value=None),
        ):
            plan = timeline_builder.build_timeline_plan(project)

        self.assertTrue(plan["ready"])
        self.assertEqual(plan["alignment_status"], "missing")
        self.assertEqual(plan["settings"]["audio"], "none")
        self.assertIn("-an", plan["command"])


if __name__ == "__main__":
    unittest.main()
