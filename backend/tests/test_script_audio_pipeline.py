from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models import Project
from app.services import media_library
from app.services import script_audio_pipeline as pipeline


class ScriptAudioPipelineTests(unittest.TestCase):
    def project(self) -> Project:
        return Project(
            id=17,
            title="The Hidden System",
            topic="How automated systems shape everyday decisions",
            target_minutes=2,
            audience="General audience",
            tone="Investigative",
            visual_style="Cinematic technology documentary",
            video_format="youtube",
            status="planning",
        )

    def test_script_artifact_is_structured_and_persistent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch.object(media_library, "MEDIA_ROOT", root),
                patch.object(pipeline, "MEDIA_ROOT", root),
            ):
                script = pipeline.build_local_script_draft(
                    self.project(),
                    angle="Follow the evidence from signal to consequence.",
                    target_scene_seconds=10,
                )
                loaded = pipeline.load_script(17)

        self.assertEqual(script["schema_version"], "1.0")
        self.assertEqual(script["provider"], "local-outline")
        self.assertGreaterEqual(len(script["segments"]), len(pipeline.ACT_BLUEPRINTS))
        self.assertEqual(loaded["segments"][0]["segment_id"], script["segments"][0]["segment_id"])
        self.assertGreater(script["estimated_runtime_seconds"], 0)

    def test_narration_plan_has_stable_scene_level_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch.object(media_library, "MEDIA_ROOT", root),
                patch.object(pipeline, "MEDIA_ROOT", root),
            ):
                project = self.project()
                script = pipeline.build_local_script_draft(project, target_scene_seconds=12)
                plan = pipeline.build_narration_plan(
                    project,
                    script,
                    provider="openai",
                    voice_id="alloy",
                    speaking_rate=1.0,
                )
                loaded = pipeline.load_narration_plan(project.id)

        self.assertEqual(plan["segment_count"], len(script["segments"]))
        self.assertEqual(plan["status"], "planned")
        self.assertTrue(plan["segments"][0]["relative_path"].endswith(".wav"))
        self.assertEqual(loaded["segments"][0]["status"], "planned")
        self.assertEqual(loaded["voice_id"], "alloy")


if __name__ == "__main__":
    unittest.main()
