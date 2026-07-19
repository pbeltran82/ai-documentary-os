from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.routers import timeline as timeline_router
from app.services import media_quality_assurance as base
from app.services import media_quality_assurance_v2 as qa
from app.services import render_invalidation


class MediaQualityAssuranceTests(unittest.TestCase):
    def project(self, video_format: str = "youtube") -> SimpleNamespace:
        return SimpleNamespace(id=7, title="Mars", video_format=video_format)

    def metadata(self, video_format: str = "youtube") -> dict:
        width, height = ((1080, 1920) if video_format == "shorts" else (1920, 1080))
        return {
            "container_duration_seconds": 10.0,
            "video_duration_seconds": 10.0,
            "audio_duration_seconds": 10.0,
            "width": width,
            "height": height,
            "fps": 30.0,
            "frame_count": 300,
            "video_codec": "h264",
            "pixel_format": "yuv420p",
            "audio_codec": "aac",
            "audio_sample_rate": 48000,
            "has_video": True,
            "has_audio": True,
            "size_bytes": 2048,
        }

    def plan(self) -> dict:
        return {
            "runtime_seconds": 10.0,
            "voiceover": {"duration_seconds": 10.0},
            "clips": [],
        }

    def evaluate(
        self,
        *,
        video_format: str = "youtube",
        black_segments: list[dict[str, float]] | None = None,
        repeated_pairs: list[dict] | None = None,
    ) -> list[dict]:
        return qa.evaluate_quality(
            project=self.project(video_format),
            plan=self.plan(),
            metadata=self.metadata(video_format),
            black_segments=black_segments or [],
            freeze_segments=[],
            audio_peak_db=-3.5,
            repeated_pairs=repeated_pairs or [],
        )

    def test_black_detector_uses_separate_pixel_and_picture_thresholds(self) -> None:
        completed = SimpleNamespace(stderr="")
        with patch.object(base, "_run", return_value=completed) as run:
            black, freezes = qa.scan_video_events(Path("render.mp4"), 10.0, "ffmpeg")

        self.assertEqual(black, [])
        self.assertEqual(freezes, [])
        filter_value = run.call_args.args[0][run.call_args.args[0].index("-vf") + 1]
        self.assertIn("pix_th=0.10", filter_value)
        self.assertIn("pic_th=0.98", filter_value)
        self.assertNotIn("pix_th=0.98", filter_value)

    def test_immediate_opening_passes_without_black_frames(self) -> None:
        checks = self.evaluate(video_format="shorts")
        opening = next(check for check in checks if check["id"] == "immediate_opening")
        self.assertEqual(opening["status"], "pass")
        self.assertNotIn("shorts_immediate_hook", {check["id"] for check in checks})

    def test_brief_opening_black_is_review_not_release_hold(self) -> None:
        checks = self.evaluate(
            video_format="shorts",
            black_segments=[
                {"start_seconds": 0.0, "end_seconds": 0.067, "duration_seconds": 0.067}
            ],
        )
        opening = next(check for check in checks if check["id"] == "immediate_opening")
        self.assertEqual(opening["status"], "warn")

    def test_long_opening_black_fails_every_delivery_format(self) -> None:
        checks = self.evaluate(
            video_format="youtube",
            black_segments=[
                {"start_seconds": 0.0, "end_seconds": 0.4, "duration_seconds": 0.4}
            ],
        )
        opening = next(check for check in checks if check["id"] == "immediate_opening")
        self.assertEqual(opening["status"], "fail")

    def test_internal_black_flash_is_major_failure(self) -> None:
        checks = self.evaluate(
            black_segments=[
                {"start_seconds": 4.0, "end_seconds": 4.04, "duration_seconds": 0.04}
            ],
        )
        internal = next(check for check in checks if check["id"] == "internal_black_frames")
        self.assertEqual(internal["status"], "fail")
        self.assertEqual(internal["metrics"]["count"], 1)

    def test_repeated_documentary_template_can_hold_release(self) -> None:
        checks = self.evaluate(
            repeated_pairs=[
                {
                    "first_scene_number": 1,
                    "second_scene_number": 2,
                    "first_template_id": "transport_scene",
                    "second_template_id": "transport_scene",
                    "similarity": 0.999,
                    "same_documentary_template": True,
                }
            ],
        )
        repeated = next(check for check in checks if check["id"] == "adjacent_scene_similarity")
        self.assertEqual(repeated["status"], "fail")

    def test_render_endpoint_attaches_automatic_qa_report(self) -> None:
        project = self.project()
        report = {"verdict": "PASS", "checks": []}
        with (
            patch.object(timeline_router, "get_project_or_404", return_value=project),
            patch.object(timeline_router, "render_first_cut", return_value={"message": "rendered"}) as render,
            patch.object(timeline_router, "analyze_timeline_render", return_value=report) as analyze,
        ):
            result = timeline_router.render_timeline(7, None, db=object())

        self.assertIs(result["qa_report"], report)
        render.assert_called_once_with(project, None)
        analyze.assert_called_once_with(project)

    def test_render_invalidation_removes_stale_qa_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project_dir = Path(temporary) / "project-0007"
            timeline_dir = project_dir / "timeline"
            timeline_dir.mkdir(parents=True)
            for filename in ("first-cut.mp4", "render-plan.json", "qa-report.json"):
                (timeline_dir / filename).write_text("stale", encoding="utf-8")

            with patch.object(render_invalidation, "project_directory", return_value=project_dir):
                render_invalidation.invalidate_render_artifacts(7)

            self.assertFalse((timeline_dir / "first-cut.mp4").exists())
            self.assertFalse((timeline_dir / "render-plan.json").exists())
            self.assertFalse((timeline_dir / "qa-report.json").exists())


if __name__ == "__main__":
    unittest.main()
