from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services import opening_frame_polish as opening
from app.services import timeline_builder


class OpeningFramePolishTests(unittest.TestCase):
    def generated_clip(self, *, input_index: int = 0) -> dict:
        return {
            "input_index": input_index,
            "provider": "generated",
            "exact_visual_family_id": "tech_behavior_motion",
            "exact_visual_template_id": "transport_scene",
            "duration_seconds": 5.0,
            "processed_duration_seconds": 5.0,
            "source_duration_seconds": 5.0,
            "source_width": 1920,
            "source_height": 1080,
            "output_width": 1920,
            "output_height": 1080,
            "video_format": "youtube",
            "media_type": "video",
            "motion_effect": "static",
        }

    def test_first_generated_exact_visual_gets_three_frame_safety_trim(self) -> None:
        graph = opening.normalized_video_filter(self.generated_clip(), 5.0)

        # Normal generated trim is 0.120s. The opening receives three more
        # frames at 30fps, so frame zero starts at the first authored image.
        self.assertIn("trim=start=0.220:duration=4.660", graph)
        self.assertIn("setpts=(PTS-STARTPTS)*1.072961", graph)
        self.assertNotIn("fade=t=in", graph)

    def test_later_generated_clip_keeps_existing_edge_treatment(self) -> None:
        clip = self.generated_clip(input_index=1)
        with patch.object(
            opening,
            "_previous_normalized_video_filter",
            return_value="previous-filter",
        ) as previous:
            graph = opening.normalized_video_filter(clip, 5.0)

        self.assertEqual(graph, "previous-filter")
        previous.assert_called_once_with(clip, 5.0)

    def test_authored_opening_disables_project_edge_fade(self) -> None:
        clips = [self.generated_clip()]
        style = {"video_format": "youtube", "edge_fade_seconds": 0.35}
        with patch.object(
            opening,
            "_previous_build_filter_graph",
            return_value="graph",
        ) as previous:
            graph = opening.build_filter_graph(clips, 5.0, style)

        self.assertEqual(graph, "graph")
        resolved = previous.call_args.args[2]
        self.assertEqual(resolved["edge_fade_seconds"], 0.0)
        self.assertEqual(style["edge_fade_seconds"], 0.35)

    def test_stock_opening_preserves_saved_edge_fade(self) -> None:
        clip = self.generated_clip()
        clip["provider"] = "pixabay"
        clip["exact_visual_family_id"] = None
        style = {"video_format": "youtube", "edge_fade_seconds": 0.35}
        with patch.object(
            opening,
            "_previous_build_filter_graph",
            return_value="graph",
        ) as previous:
            opening.build_filter_graph([clip], 5.0, style)

        resolved = previous.call_args.args[2]
        self.assertEqual(resolved["edge_fade_seconds"], 0.35)

    def test_release_guard_is_installed_last(self) -> None:
        self.assertIs(timeline_builder.normalized_video_filter, opening.normalized_video_filter)
        self.assertIs(timeline_builder.build_filter_graph, opening.build_filter_graph)


if __name__ == "__main__":
    unittest.main()
