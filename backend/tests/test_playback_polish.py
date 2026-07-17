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

    def test_short_subscribe_cta_holds_last_clear_frame_without_looping(self) -> None:
        clip = self.generated_clip(duration=4.0, processed=4.0)
        clip.update(
            {
                "source_duration_seconds": 1.75,
                "exact_visual_family_id": "finance_motion",
                "exact_visual_template_id": "subscribe_cta",
            }
        )

        chain = playback.normalized_video_filter(clip, 4.0)

        self.assertIn("tpad=stop_mode=clone", chain)
        self.assertIn("trim=duration=4.000", chain)
        self.assertNotIn("setpts=(PTS-STARTPTS)*", chain)

    def test_remote_video_keeps_original_normalization_path(self) -> None:
        clip = self.generated_clip()
        clip["provider"] = "pixabay"
        chain = playback.normalized_video_filter(clip, 4.35)
        self.assertIn("trim=duration=4.350", chain)
        self.assertNotIn("trim=start=", chain)

    def test_legacy_landscape_generated_visual_gets_ambient_shorts_frame(self) -> None:
        clip = self.generated_clip()
        clip.update(
            {
                "video_format": "shorts",
                "output_width": 1080,
                "output_height": 1920,
                "source_width": 1920,
                "source_height": 1080,
            }
        )
        chain = playback.normalized_video_filter(clip, 4.35)
        self.assertIn("split=2[generated_bg_0][generated_fg_0]", chain)
        self.assertIn("gblur=sigma=32", chain)
        self.assertIn("overlay=(W-w)/2:(H-h)/2", chain)

    def test_vertical_generated_visual_stays_safe_when_switching_back_to_youtube(self) -> None:
        clip = self.generated_clip()
        clip.update(
            {
                "video_format": "youtube",
                "output_width": 1920,
                "output_height": 1080,
                "source_width": 1080,
                "source_height": 1920,
            }
        )
        chain = playback.normalized_video_filter(clip, 4.35)
        self.assertIn("split=2[generated_bg_0][generated_fg_0]", chain)
        self.assertIn("scale=1920:1080:force_original_aspect_ratio=increase", chain)

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
