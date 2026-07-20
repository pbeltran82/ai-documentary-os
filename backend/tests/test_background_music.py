from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import background_music_timeline as music
from app.services import timeline_builder as base


class BackgroundMusicTimelineTests(unittest.TestCase):
    def test_music_defaults_are_restrained_and_disabled(self) -> None:
        style = music.normalize_timeline_style(None)
        self.assertFalse(style["music_enabled"])
        self.assertEqual(style["music_gain_db"], -22.0)
        self.assertEqual(style["music_ducking_db"], -8.0)
        self.assertEqual(style["music_fade_seconds"], 1.5)

    def test_partial_style_updates_preserve_existing_music_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "style.json"
            path.write_text(
                json.dumps(
                    {
                        "transition_style": "cut",
                        "transition_duration_seconds": 0,
                        "photo_motion": "editorial",
                        "edge_fade_seconds": 0,
                        "music_enabled": True,
                        "music_gain_db": -24,
                        "music_ducking_db": -10,
                        "music_fade_seconds": 2,
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(base, "timeline_style_path", return_value=path):
                saved = music.save_timeline_style(
                    7,
                    {
                        "transition_style": "crossfade",
                        "transition_duration_seconds": 0.35,
                    },
                )

            self.assertTrue(saved["music_enabled"])
            self.assertEqual(saved["music_gain_db"], -24.0)
            self.assertEqual(saved["music_ducking_db"], -10.0)
            self.assertEqual(saved["transition_style"], "crossfade")

    def test_narration_music_graph_uses_sidechain_ducking_and_limiter(self) -> None:
        with patch.object(
            music,
            "_original_build_filter_graph",
            return_value="video[outv];narration[outa]",
        ):
            graph = music.build_filter_graph(
                [],
                30.0,
                {
                    "music_gain_db": -22,
                    "music_ducking_db": -8,
                    "music_fade_seconds": 1.5,
                },
                voiceover_input_index=2,
                music_input_index=3,
            )

        self.assertIn("volume=-22dB", graph)
        self.assertIn("afade=t=in", graph)
        self.assertIn("afade=t=out", graph)
        self.assertIn("sidechaincompress", graph)
        self.assertIn("amix=inputs=2", graph)
        self.assertIn("alimiter=limit=0.95[outa]", graph)
        self.assertNotIn("narration[outa]", graph)

    def test_music_only_command_loops_track_and_maps_audio(self) -> None:
        original = [
            "ffmpeg",
            "-i",
            "scene.mp4",
            "-filter_complex",
            "video[outv]",
            "-map",
            "[outv]",
            "-an",
            "output.mp4",
        ]
        with (
            patch.object(music, "_original_build_ffmpeg_command", return_value=original.copy()),
            patch.object(music, "build_filter_graph", return_value="video[outv];music[outa]"),
        ):
            command = music.build_ffmpeg_command(
                [{"duration_seconds": 10.0}],
                Path("output.mp4"),
                "ffmpeg",
                voiceover=None,
                runtime_seconds=10.0,
                style={
                    "music_enabled": True,
                    "music_source_file": "/tmp/music.mp3",
                    "music_gain_db": -22,
                    "music_ducking_db": -8,
                    "music_fade_seconds": 1.5,
                },
            )

        self.assertIn("-stream_loop", command)
        loop_index = command.index("-stream_loop")
        self.assertEqual(command[loop_index : loop_index + 4], ["-stream_loop", "-1", "-i", "/tmp/music.mp3"])
        self.assertNotIn("-an", command)
        self.assertIn("[outa]", command)
        self.assertIn("aac", command)

    def test_disabled_music_keeps_established_command_unchanged(self) -> None:
        original = ["ffmpeg", "-filter_complex", "video[outv]", "-an", "output.mp4"]
        with patch.object(music, "_original_build_ffmpeg_command", return_value=original.copy()):
            command = music.build_ffmpeg_command(
                [],
                Path("output.mp4"),
                "ffmpeg",
                runtime_seconds=10.0,
                style={"music_enabled": False, "music_source_file": "/tmp/music.mp3"},
            )
        self.assertEqual(command, original)


if __name__ == "__main__":
    unittest.main()
