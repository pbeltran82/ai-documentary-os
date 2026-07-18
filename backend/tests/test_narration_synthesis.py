from __future__ import annotations

import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import Mock, patch

from app.models import Project
from app.services import media_library
from app.services import narration_synthesis as synthesis
from app.services import script_approval
from app.services import script_audio_pipeline as pipeline


class NarrationSynthesisTests(unittest.TestCase):
    def project(self) -> Project:
        return Project(
            id=23,
            title="A System in Motion",
            topic="How small rules create large outcomes",
            target_minutes=1,
            audience="General audience",
            tone="Investigative",
            visual_style="Cinematic documentary",
            video_format="youtube",
            status="planning",
        )

    def test_approval_snapshots_the_script_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch.object(media_library, "MEDIA_ROOT", root),
                patch.object(pipeline, "MEDIA_ROOT", root),
                patch.object(script_approval, "MEDIA_ROOT", root),
            ):
                pipeline.build_local_script_draft(self.project(), target_scene_seconds=12)
                approved = script_approval.approve_script(23, notes="Editorially approved")
                revisions = script_approval.list_script_revisions(23)

        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["approval_notes"], "Editorially approved")
        self.assertEqual(len(revisions), 1)
        self.assertEqual(revisions[0]["revision"], 1)

    def test_local_adapter_writes_measured_wav_and_is_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch.object(media_library, "MEDIA_ROOT", root),
                patch.object(pipeline, "MEDIA_ROOT", root),
                patch.object(script_approval, "MEDIA_ROOT", root),
                patch.object(synthesis, "MEDIA_ROOT", root),
            ):
                project = self.project()
                script = pipeline.build_local_script_draft(project, target_scene_seconds=20)
                script_approval.approve_script(project.id)
                pipeline.build_narration_plan(
                    project,
                    script,
                    provider="local-test",
                    voice_id="test",
                    speaking_rate=1.0,
                )
                first = synthesis.synthesize_narration(
                    project,
                    Mock(),
                    scene_numbers={1},
                    retime_scenes=False,
                )
                second = synthesis.synthesize_narration(
                    project,
                    Mock(),
                    scene_numbers={1},
                    retime_scenes=False,
                )

        segment = first["segments"][0]
        self.assertEqual(segment["status"], "complete")
        self.assertGreater(segment["actual_duration_seconds"], 0)
        self.assertEqual(len(segment["checksum_sha256"]), 64)
        self.assertEqual(first["last_run"]["completed"], 1)
        self.assertEqual(second["last_run"]["skipped"], 1)

    def test_streamed_wav_sentinel_uses_actual_payload_duration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "streamed.wav"
            sample_rate = 48_000
            seconds = 2
            payload = b"\x00\x00" * sample_rate * seconds
            fmt = struct.pack("<HHIIHH", 1, 1, sample_rate, sample_rate * 2, 2, 16)
            content = (
                b"RIFF"
                + struct.pack("<I", 0xFFFFFFFF)
                + b"WAVE"
                + b"fmt "
                + struct.pack("<I", len(fmt))
                + fmt
                + b"data"
                + struct.pack("<I", 0xFFFFFFFF)
                + payload
            )
            path.write_bytes(content)

            duration = synthesis._wav_duration(path)

        self.assertEqual(duration, 2.0)


if __name__ == "__main__":
    unittest.main()
