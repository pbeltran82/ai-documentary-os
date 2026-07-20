from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from app.models import Project
from app.services import cartoon_art_polish_v52 as v52
from app.services import cartoon_art_polish_v61 as v61
from app.services import media_library
from app.services import script_audio_pipeline as pipeline


class StoryClockRegressionTests(unittest.TestCase):
    def test_shorts_narration_plan_is_independent_and_under_sixty_seconds(self) -> None:
        project = Project(
            id=91,
            title="Moving Civilization to Mars",
            topic="How humanity could build a permanent Mars settlement",
            target_minutes=3,
            audience="General audience",
            tone="Investigative",
            visual_style="Cartoon documentary",
            video_format="shorts",
            status="script_approved",
        )
        segments = []
        for number in range(1, 13):
            segments.append(
                {
                    "segment_id": f"source-{number}",
                    "scene_number": number,
                    "act": "Mechanism",
                    "narration": (
                        "Moving people to Mars requires transport, shelter, power, food, governance, "
                        "and reliable life support. Each system must work before families can arrive."
                    ),
                }
            )
        script = {"revision": 3, "segments": segments}

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch.object(media_library, "MEDIA_ROOT", root),
                patch.object(pipeline, "MEDIA_ROOT", root),
            ):
                plan = pipeline.build_narration_plan(
                    project,
                    script,
                    provider="local-test",
                    voice_id="alloy",
                    speaking_rate=1.0,
                )

        self.assertEqual(plan["story_mode"], "shorts")
        self.assertLessEqual(plan["segment_count"], 7)
        self.assertGreaterEqual(plan["segment_count"], 5)
        self.assertLessEqual(plan["estimated_runtime_seconds"], 60.0)
        self.assertEqual(
            plan["selected_scene_numbers"],
            [segment["scene_number"] for segment in plan["segments"]],
        )

    def test_route_progress_does_not_reset_at_visual_beat_boundary(self) -> None:
        scene = SimpleNamespace(
            scene_number=4,
            narration="A spacecraft travels from Earth to Mars.",
            visual_intent="Earth to Mars route",
            search_keywords=["earth", "mars", "spacecraft", "route"],
            duration_seconds=10.0,
            animation_plan={
                "visual_beats": [
                    {
                        "relative_start_seconds": 0.0,
                        "relative_end_seconds": 5.0,
                        "visual_intent": "Earth to Mars route departure",
                    },
                    {
                        "relative_start_seconds": 5.0,
                        "relative_end_seconds": 10.0,
                        "visual_intent": "Earth to Mars route arrival",
                    },
                ]
            },
        )
        captured: list[float] = []

        def fake_route(progress: float, variant: int) -> Image.Image:
            del variant
            captured.append(progress)
            return Image.new("RGB", (1920, 1080))

        with patch.object(v52, "_route", side_effect=fake_route):
            v61.render_planned_frame(scene, "route_map", 10.0, 4.9)
            v61.render_planned_frame(scene, "route_map", 10.0, 5.1)

        self.assertEqual(len(captured), 2)
        self.assertGreater(captured[1], captured[0])
        self.assertGreater(captured[1], 0.5)


if __name__ == "__main__":
    unittest.main()
