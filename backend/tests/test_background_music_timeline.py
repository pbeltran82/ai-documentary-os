from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from app.routers.timeline import format_music_defaults
from app.services import background_music_timeline as music


class BackgroundMusicTimelineTests(unittest.TestCase):
    def test_regular_and_shorts_receive_distinct_safe_defaults(self) -> None:
        regular = format_music_defaults(SimpleNamespace(video_format="youtube"))
        shorts = format_music_defaults(SimpleNamespace(video_format="shorts"))

        self.assertEqual(regular["music_gain_db"], -22.0)
        self.assertEqual(regular["music_fade_seconds"], 1.5)
        self.assertEqual(shorts["music_gain_db"], -24.0)
        self.assertEqual(shorts["music_ducking_db"], -9.0)
        self.assertEqual(shorts["music_fade_seconds"], 0.6)

    def test_music_settings_are_clamped_to_safe_ranges(self) -> None:
        normalized = music.normalize_timeline_style(
            {
                "music_enabled": True,
                "music_gain_db": -4,
                "music_ducking_db": -40,
                "music_fade_seconds": 99,
            }
        )
        self.assertTrue(normalized["music_enabled"])
        self.assertEqual(normalized["music_gain_db"], -10.0)
        self.assertEqual(normalized["music_ducking_db"], -18.0)
        self.assertEqual(normalized["music_fade_seconds"], 8.0)

    def test_music_filter_loops_to_runtime_with_gain_and_fades(self) -> None:
        chain = music._music_filter(
            3,
            48.7,
            {
                "music_gain_db": -24.0,
                "music_fade_seconds": 0.6,
            },
            "music_bed",
        )
        self.assertIn("[3:a]", chain)
        self.assertIn("volume=-24dB", chain)
        self.assertIn("atrim=duration=48.700", chain)
        self.assertIn("afade=t=in:st=0:d=0.600", chain)
        self.assertIn("afade=t=out:st=48.100:d=0.600", chain)
        self.assertTrue(chain.endswith("[music_bed]"))

    def test_narration_mix_uses_sidechain_ducking_and_limiter(self) -> None:
        original = music._original_build_filter_graph
        music._original_build_filter_graph = lambda *args, **kwargs: "[9:a]anull[outa]"
        try:
            graph = music.build_filter_graph(
                [],
                30.0,
                {
                    "music_gain_db": -22.0,
                    "music_ducking_db": -8.0,
                    "music_fade_seconds": 1.5,
                },
                voiceover_input_index=9,
                music_input_index=10,
            )
        finally:
            music._original_build_filter_graph = original

        self.assertIn("[narration_raw]asplit=2", graph)
        self.assertIn("sidechaincompress", graph)
        self.assertIn("[narration_mix][ducked_music]amix", graph)
        self.assertIn("alimiter=limit=0.95[outa]", graph)

    def test_music_command_adds_looped_input_and_audio_output(self) -> None:
        original = music._original_build_ffmpeg_command
        music._original_build_ffmpeg_command = lambda *args, **kwargs: [
            "ffmpeg",
            "-filter_complex",
            "[v0]null[outv]",
            "-map",
            "[outv]",
            "-an",
            "output.mp4",
        ]
        try:
            command = music.build_ffmpeg_command(
                [{"duration_seconds": 10.0}],
                Path("output.mp4"),
                style={
                    "music_enabled": True,
                    "music_gain_db": -22.0,
                    "music_ducking_db": -8.0,
                    "music_fade_seconds": 1.5,
                },
                runtime_seconds=10.0,
                music={"source_file": "/tmp/music.mp3"},
            )
        finally:
            music._original_build_ffmpeg_command = original

        self.assertIn("-stream_loop", command)
        self.assertIn("/tmp/music.mp3", command)
        self.assertNotIn("-an", command)
        self.assertIn("[outa]", command)
        self.assertIn("aac", command)

    def test_disabled_music_preserves_original_command(self) -> None:
        original = music._original_build_ffmpeg_command
        expected = ["ffmpeg", "-an", "output.mp4"]
        music._original_build_ffmpeg_command = lambda *args, **kwargs: list(expected)
        try:
            command = music.build_ffmpeg_command(
                [],
                Path("output.mp4"),
                style={"music_enabled": False},
                music={"source_file": "/tmp/music.mp3"},
            )
        finally:
            music._original_build_ffmpeg_command = original
        self.assertEqual(command, expected)


if __name__ == "__main__":
    unittest.main()
