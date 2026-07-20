from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from app.services import cartoon_visual_overhaul_v63 as v63
from app.services import cartoon_visual_overhaul_v64 as v64
from app.services import shorts_transition_polish as transition
from app.services import timeline_builder


class MarsReleaseGuardTests(unittest.TestCase):
    def test_final_mars_route_resolves_to_settlement_system(self) -> None:
        first = SimpleNamespace(scene_number=1)
        final = SimpleNamespace(
            scene_number=2,
            narration="The journey to Mars must become a permanent settlement.",
            visual_intent="Earth to Mars route and final arrival",
            search_keywords=["mars", "spacecraft"],
            animation_plan={},
        )
        project = SimpleNamespace(scenes=[first, final])
        first.project = project
        final.project = project
        settlement = Image.new("RGB", (8, 8), (10, 120, 40))
        route = Image.new("RGB", (8, 8), (40, 80, 160))

        with (
            patch.object(v63, "_process_frame", return_value=settlement) as process,
            patch.object(v63, "render_planned_frame", return_value=route) as previous,
        ):
            rendered = v64.render_planned_frame(final, "route_map", 10.0, 5.0)

        self.assertEqual(rendered.tobytes(), settlement.tobytes())
        process.assert_called_once()
        previous.assert_not_called()

    def test_nonfinal_route_remains_the_journey(self) -> None:
        first = SimpleNamespace(
            scene_number=1,
            narration="The spacecraft leaves Earth for Mars.",
            visual_intent="Earth to Mars route",
            search_keywords=["mars", "spacecraft"],
            animation_plan={},
        )
        final = SimpleNamespace(scene_number=2)
        project = SimpleNamespace(scenes=[first, final])
        first.project = project
        final.project = project
        route = Image.new("RGB", (8, 8), (40, 80, 160))

        with (
            patch.object(v63, "_process_frame") as process,
            patch.object(v63, "render_planned_frame", return_value=route) as previous,
        ):
            rendered = v64.render_planned_frame(first, "route_map", 10.0, 5.0)

        self.assertEqual(rendered.tobytes(), route.tobytes())
        process.assert_not_called()
        previous.assert_called_once()

    def test_native_shorts_exact_visuals_use_clean_cuts(self) -> None:
        clips = [
            {
                "duration_seconds": 5.0,
                "processed_duration_seconds": 5.0,
                "video_format": "shorts",
                "exact_visual_family_id": "tech_behavior_motion",
                "media_type": "video",
                "motion_effect": "static",
            },
            {
                "duration_seconds": 6.0,
                "processed_duration_seconds": 6.0,
                "video_format": "shorts",
                "exact_visual_family_id": "tech_behavior_motion",
                "media_type": "video",
                "motion_effect": "static",
            },
        ]
        style = timeline_builder.normalize_timeline_style(
            {
                "transition_style": "crossfade",
                "transition_duration_seconds": 0.35,
            }
        )

        timeline_builder.apply_edit_decisions(clips, style)

        self.assertEqual(clips[0]["transition_out"], "cut")
        self.assertEqual(clips[0]["transition_duration_seconds"], 0.0)
        self.assertEqual(clips[0]["processed_duration_seconds"], 5.0)
        self.assertIn("clean cut", clips[0]["assembly_action"])

    def test_native_shorts_filter_disables_edge_fades(self) -> None:
        clips = [{"exact_visual_family_id": "tech_behavior_motion"}]
        style = {
            "video_format": "shorts",
            "edge_fade_seconds": 0.35,
        }
        with patch.object(transition, "_original_build_filter_graph", return_value="graph") as original:
            result = transition.build_filter_graph(clips, 5.0, style)

        self.assertEqual(result, "graph")
        resolved_style = original.call_args.args[2]
        self.assertEqual(resolved_style["edge_fade_seconds"], 0.0)


if __name__ == "__main__":
    unittest.main()
