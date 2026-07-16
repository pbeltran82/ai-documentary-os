from __future__ import annotations

import unittest

from app.services import finance_motion_truthful as finance
from app.services import timeline_playback_polish as playback


class PlaybackPolishTests(unittest.TestCase):
    def generated_clip(self, duration: float = 4.0, processed: float = 4.35) -> dict:
        return {
            "input_index": 0,
            "provider": "generated",
            "media_type": "video",
            "duration_seconds": duration,
            "processed_duration_seconds": processed,
            "transition_duration_seconds": max(0.0, processed - duration),
        }

    def style(self) -> dict:
        return {
            "transition_style": "crossfade",
            "transition_duration_seconds": 0.35,
            "photo_motion": "editorial",
            "edge_fade_seconds": 0.35,
        }

    def test_generated_video_filter_skips_burned_in_dark_edges(self) -> None:
        clip = self.generated_clip()
        chain = playback.normalized_video_filter(clip, 4.35)
        self.assertIn("trim=start=", chain)
        self.assertIn("setpts=(PTS-STARTPTS)*", chain)
        self.assertNotIn("trim=duration=4.350,setpts=PTS-STARTPTS", chain)
        self.assertIn("fps=30", chain)

    def test_short_generated_scene_uses_proportional_safe_trim(self) -> None:
        clip = self.generated_clip(duration=2.0, processed=2.35)
        self.assertEqual(playback.generated_edge_trim_seconds(clip), 0.05)

    def test_remote_video_keeps_original_normalization_path(self) -> None:
        clip = self.generated_clip()
        clip["provider"] = "pixabay"
        chain = playback.normalized_video_filter(clip, 4.35)
        self.assertIn("trim=duration=4.350", chain)
        self.assertNotIn("trim=start=", chain)

    def test_narration_filter_targets_finished_web_loudness(self) -> None:
        graph = playback.build_filter_graph(
            [self.generated_clip(duration=4.0, processed=4.0)],
            4.0,
            self.style(),
            voiceover_input_index=1,
        )
        self.assertIn("loudnorm=I=-16:TP=-1.5:LRA=11", graph)
        self.assertIn("apad=whole_dur=4.000", graph)

    def test_compound_growth_does_not_claim_a_fake_percentage(self) -> None:
        self.assertEqual(finance.COMPOUND_STATUS_LABEL, "ILLUSTRATIVE GROWTH PATH")
        self.assertNotIn("%", finance.COMPOUND_STATUS_LABEL)
        frame = finance.render_frame(
            "compound_growth",
            6.0,
            4.8,
            "premium_motion",
        )
        self.assertEqual(frame.size, (1920, 1080))


if __name__ == "__main__":
    unittest.main()
