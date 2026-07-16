from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.services import media_library, voiceover


async def byte_stream(*chunks: bytes):
    for chunk in chunks:
        yield chunk


class VoiceoverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.media_root = Path(self.temporary.name)
        self.media_patch = patch.object(media_library, "MEDIA_ROOT", self.media_root)
        self.voiceover_patch = patch.object(voiceover, "MEDIA_ROOT", self.media_root)
        self.media_patch.start()
        self.voiceover_patch.start()

    def tearDown(self) -> None:
        self.voiceover_patch.stop()
        self.media_patch.stop()
        self.temporary.cleanup()

    def test_audio_upload_is_atomic_hashed_probed_and_reloadable(self) -> None:
        with (
            patch.object(voiceover, "ffprobe_executable", return_value="ffprobe"),
            patch.object(voiceover, "probe_duration", return_value=5.125),
        ):
            metadata = asyncio.run(
                voiceover.save_voiceover(
                    1,
                    "compound-voiceover.mp3",
                    "audio/mpeg",
                    byte_stream(b"voice", b"over"),
                )
            )

        self.assertEqual(metadata["duration_seconds"], 5.125)
        self.assertEqual(metadata["file_size_bytes"], 9)
        self.assertEqual(len(metadata["checksum_sha256"]), 64)
        self.assertEqual(
            metadata["relative_path"],
            "project-0001/audio/narration.mp3",
        )
        self.assertTrue(
            (self.media_root / "project-0001" / "audio" / "narration.mp3").is_file()
        )
        self.assertTrue(
            (self.media_root / "project-0001" / "audio" / "narration.json").is_file()
        )

        loaded = voiceover.load_voiceover(1)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded["original_filename"], "compound-voiceover.mp3")
        self.assertTrue(loaded["source_file"].endswith("narration.mp3"))

        voiceover.remove_voiceover(1)
        self.assertIsNone(voiceover.load_voiceover(1))

    def test_unsupported_audio_format_is_rejected(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            voiceover.choose_extension("notes.txt", "text/plain")
        self.assertEqual(raised.exception.status_code, 415)

    def test_empty_upload_is_rejected_without_leaving_partial_files(self) -> None:
        with patch.object(voiceover, "ffprobe_executable", return_value="ffprobe"):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(
                    voiceover.save_voiceover(
                        1,
                        "empty.wav",
                        "audio/wav",
                        byte_stream(),
                    )
                )

        self.assertEqual(raised.exception.status_code, 422)
        audio_dir = self.media_root / "project-0001" / "audio"
        self.assertFalse(any(audio_dir.glob("*.part")))


if __name__ == "__main__":
    unittest.main()
