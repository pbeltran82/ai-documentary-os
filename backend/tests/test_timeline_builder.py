from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models import Asset, Project, Scene
from app.schemas import TimelineStyleUpdate
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

    def make_scene(
        self,
        project: Project,
        *,
        scene_id: int,
        scene_number: int,
        start: float,
        duration: float,
        media_type: str,
    ) -> Scene:
        scene = Scene(
            id=scene_id,
            project_id=project.id,
            scene_number=scene_number,
            start_seconds=start,
            end_seconds=start + duration,
            duration_seconds=duration,
            narration=f"Narration for scene {scene_number}.",
            visual_intent="Stock chart growth",
            search_keywords=["stock chart"],
            preferred_asset_type="stock_video" if media_type == "video" else "stock_image",
            asset_status="ready",
        )
        extension = ".mp4" if media_type == "video" else ".jpg"
        local_path = f"project-0001/assets/scene-{scene_number:03d}-test{extension}"
        asset_file = self.media_root / local_path
        asset_file.parent.mkdir(parents=True, exist_ok=True)
        asset_file.write_bytes(b"local-media")
        asset = Asset(
            id=20 + scene_number,
            scene_id=scene_id,
            provider="pixabay",
            provider_asset_id=f"asset-{scene_number}",
            media_type=media_type,
            source_url=f"https://example.com/source/{scene_number}",
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
        return scene

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
        project.scenes = [
            self.make_scene(
                project,
                scene_id=10,
                scene_number=1,
                start=0,
                duration=5,
                media_type=media_type,
            )
        ]
        return project

    def test_video_plan_loops_trims_normalizes_and_adds_edge_fades(self) -> None:
        project = self.make_project("video")
        with patch.object(
            timeline_builder,
            "ffmpeg_executable",
            return_value="/opt/homebrew/bin/ffmpeg",
        ):
            plan = timeline_builder.write_timeline_plan(project)

        self.assertTrue(plan["ready"])
        self.assertEqual(plan["schema_version"], "0.3")
        self.assertEqual(plan["clip_count"], 1)
        self.assertEqual(plan["runtime_seconds"], 5)
        self.assertIn("-stream_loop", plan["command"])
        filter_graph = plan["command"][plan["command"].index("-filter_complex") + 1]
        self.assertIn("trim=duration=5.000", filter_graph)
        self.assertIn("scale=1920:1080", filter_graph)
        self.assertIn("fade=t=in:st=0:d=0.350", filter_graph)
        self.assertIn("fade=t=out:st=4.650:d=0.350", filter_graph)
        self.assertIn("[v0]null[outv]", filter_graph)

        timeline_dir = self.media_root / "project-0001" / "timeline"
        self.assertTrue((timeline_dir / "render-plan.json").is_file())
        self.assertTrue((timeline_dir / "render.sh").is_file())
        saved = json.loads((timeline_dir / "render-plan.json").read_text())
        self.assertIn("native motion", saved["clips"][0]["assembly_action"])
        self.assertEqual(saved["settings"]["transition_style"], "crossfade")

    def test_photo_plan_uses_gentle_zoom(self) -> None:
        project = self.make_project("photo")
        with patch.object(timeline_builder, "ffmpeg_executable", return_value="ffmpeg"):
            plan = timeline_builder.build_timeline_plan(project)

        self.assertIn("-loop", plan["command"])
        self.assertIn("-framerate", plan["command"])
        self.assertNotIn("-stream_loop", plan["command"])
        filter_graph = plan["command"][plan["command"].index("-filter_complex") + 1]
        self.assertIn("zoompan=z='1.0+0.08*on/", filter_graph)
        self.assertEqual(plan["clips"][0]["motion_effect"], "zoom_in")
        self.assertIn("gentle zoom in", plan["clips"][0]["assembly_action"])

    def test_crossfade_preserves_exact_timeline_runtime(self) -> None:
        project = self.make_project("video")
        project.scenes.append(
            self.make_scene(
                project,
                scene_id=11,
                scene_number=2,
                start=5,
                duration=5,
                media_type="photo",
            )
        )
        style = TimelineStyleUpdate(
            transition_style="crossfade",
            transition_duration_seconds=0.35,
            photo_motion="alternate",
            edge_fade_seconds=0.35,
        )

        with patch.object(timeline_builder, "ffmpeg_executable", return_value="ffmpeg"):
            plan = timeline_builder.build_timeline_plan(project, style)

        self.assertEqual(plan["runtime_seconds"], 10)
        self.assertEqual(plan["clips"][0]["processed_duration_seconds"], 5.35)
        self.assertEqual(plan["clips"][0]["transition_duration_seconds"], 0.35)
        self.assertEqual(plan["clips"][1]["motion_effect"], "zoom_out")
        filter_graph = plan["command"][plan["command"].index("-filter_complex") + 1]
        self.assertIn("trim=duration=5.350", filter_graph)
        self.assertIn(
            "xfade=transition=fade:duration=0.350:offset=5.000",
            filter_graph,
        )
        self.assertEqual(plan["command"][plan["command"].index("-t") + 1], "10.000")

    def test_fade_black_and_clean_cut_generate_distinct_graphs(self) -> None:
        project = self.make_project("video")
        project.scenes.append(
            self.make_scene(
                project,
                scene_id=11,
                scene_number=2,
                start=5,
                duration=3,
                media_type="video",
            )
        )

        with patch.object(timeline_builder, "ffmpeg_executable", return_value="ffmpeg"):
            fade_plan = timeline_builder.build_timeline_plan(
                project,
                TimelineStyleUpdate(transition_style="fade_black"),
            )
            cut_plan = timeline_builder.build_timeline_plan(
                project,
                TimelineStyleUpdate(transition_style="cut"),
            )

        fade_graph = fade_plan["command"][fade_plan["command"].index("-filter_complex") + 1]
        cut_graph = cut_plan["command"][cut_plan["command"].index("-filter_complex") + 1]
        self.assertIn("xfade=transition=fadeblack", fade_graph)
        self.assertIn("concat=n=2:v=1:a=0", cut_graph)
        self.assertNotIn("xfade=", cut_graph)

    def test_style_is_persisted_and_reloaded(self) -> None:
        project = self.make_project("photo")
        saved = timeline_builder.save_timeline_style(
            project.id,
            TimelineStyleUpdate(
                transition_style="cut",
                photo_motion="static",
                edge_fade_seconds=0,
            ),
        )
        loaded = timeline_builder.load_timeline_style(project.id)

        self.assertEqual(saved, loaded)
        self.assertEqual(loaded["transition_style"], "cut")
        self.assertEqual(loaded["transition_duration_seconds"], 0)
        self.assertEqual(loaded["photo_motion"], "static")

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
