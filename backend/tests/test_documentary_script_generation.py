from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.models import Project
from app.services import documentary_script_generation as generation
from app.services import media_library
from app.services import script_audio_pipeline as pipeline


class DocumentaryScriptGenerationTests(unittest.TestCase):
    def project(self) -> Project:
        return Project(
            id=31,
            title="The Invisible Engine",
            topic="How recommendation systems shape attention",
            target_minutes=2,
            audience="General audience",
            tone="Investigative",
            visual_style="Cinematic technology documentary",
            video_format="youtube",
            status="planning",
        )

    def generated_payload(self) -> dict:
        return {
            "title": "The Invisible Engine",
            "thesis": "Small signals become systems that influence what people notice next.",
            "segments": [
                {
                    "act": act,
                    "narration": f"This is the {act.lower()} beat, showing how one signal changes the next decision.",
                    "visual_intent": f"Show a distinct visual for the {act.lower()} beat.",
                    "search_keywords": [act, "recommendation systems"],
                }
                for act in ("Hook", "Context", "Mechanism", "Evidence", "Conclusion")
            ],
        }

    def test_normalization_persists_scene_ready_script(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch.object(media_library, "MEDIA_ROOT", root),
                patch.object(pipeline, "MEDIA_ROOT", root),
                patch.object(generation, "_production_directory", lambda project_id: root / f"project-{project_id:04d}" / "production"),
            ):
                script = generation.normalize_generated_script(
                    self.project(),
                    self.generated_payload(),
                    provider="openai",
                    model="test-model",
                    angle="Follow signal to consequence.",
                    research_notes="Only conceptual claims are verified.",
                    target_scene_seconds=8,
                    previous_revision=2,
                )

        self.assertEqual(script["revision"], 3)
        self.assertEqual(script["status"], "draft")
        self.assertEqual(len(script["segments"]), 5)
        self.assertEqual(script["segments"][0]["scene_number"], 1)
        self.assertGreater(script["estimated_runtime_seconds"], 0)

    def test_openai_adapter_reads_strict_response_output(self) -> None:
        response_body = {
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(self.generated_payload()),
                        }
                    ]
                }
            ]
        }
        response = Mock()
        response.read.return_value = json.dumps(response_body).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
                patch.object(generation, "urlopen", return_value=response),
                patch.object(generation, "_production_directory", lambda project_id: root / f"project-{project_id:04d}" / "production"),
            ):
                script = generation.generate_openai_script(
                    self.project(),
                    research_notes="No precise statistics supplied.",
                    previous_revision=1,
                )

        self.assertEqual(script["provider"], "openai")
        self.assertEqual(script["revision"], 2)
        self.assertEqual(script["segments"][-1]["act"], "Conclusion")

    def test_manual_edit_creates_new_draft_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(generation, "_production_directory", lambda project_id: root / f"project-{project_id:04d}" / "production"):
                current = generation.normalize_generated_script(
                    self.project(),
                    self.generated_payload(),
                    provider="openai",
                    model="test-model",
                    angle="",
                    research_notes="",
                    target_scene_seconds=8,
                    previous_revision=0,
                )
                edited_segments = list(current["segments"])
                edited_segments[0] = {
                    **edited_segments[0],
                    "narration": "A stronger opening line creates immediate tension and a clear question.",
                }
                updated = generation.update_script_draft(
                    self.project(),
                    current,
                    thesis="A revised thesis.",
                    segments=edited_segments,
                    editor_notes="Tightened the hook.",
                )

        self.assertEqual(updated["revision"], 2)
        self.assertEqual(updated["status"], "draft")
        self.assertEqual(updated["thesis"], "A revised thesis.")
        self.assertEqual(updated["editor_notes"], "Tightened the hook.")


if __name__ == "__main__":
    unittest.main()
