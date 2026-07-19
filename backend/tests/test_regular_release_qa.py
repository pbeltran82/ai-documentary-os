from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from app.services import cartoon_visual_overhaul_v63 as v63
from app.services import cartoon_visual_overhaul_v65 as v65
from app.services import cartoon_visual_overhaul_v66 as v66
from app.services import regular_transition_polish as regular_transition
from app.services import timeline_builder


class RegularReleaseQATests(unittest.TestCase):
    def test_regular_exact_visual_boundary_uses_clean_cut(self) -> None:
        clips = [
            {
                "duration_seconds": 5.0,
                "processed_duration_seconds": 5.24,
                "video_format": "youtube",
                "exact_visual_family_id": "tech_behavior_motion",
                "media_type": "video",
                "motion_effect": "static",
                "transition_out": "fade_black",
                "transition_duration_seconds": 0.24,
                "assembly_action": "",
            },
            {
                "duration_seconds": 6.0,
                "processed_duration_seconds": 6.0,
                "video_format": "youtube",
                "exact_visual_family_id": "tech_behavior_motion",
                "media_type": "video",
                "motion_effect": "static",
                "transition_out": "cut",
                "transition_duration_seconds": 0.0,
                "assembly_action": "",
            },
        ]
        style = timeline_builder.normalize_timeline_style(
            {
                "transition_style": "crossfade",
                "transition_duration_seconds": 0.35,
            }
        )

        with patch.object(regular_transition, "_previous_apply_edit_decisions") as previous:
            regular_transition.apply_edit_decisions(clips, style)

        previous.assert_called_once()
        self.assertEqual(clips[0]["transition_out"], "cut")
        self.assertEqual(clips[0]["transition_duration_seconds"], 0.0)
        self.assertEqual(clips[0]["processed_duration_seconds"], 5.0)
        self.assertIn("clean cut", clips[0]["assembly_action"])

    def test_shorts_boundary_is_not_modified_by_regular_guard(self) -> None:
        clips = [
            {
                "duration_seconds": 5.0,
                "processed_duration_seconds": 5.0,
                "video_format": "shorts",
                "exact_visual_family_id": "tech_behavior_motion",
                "media_type": "video",
                "motion_effect": "static",
                "transition_out": "cut",
                "transition_duration_seconds": 0.0,
                "assembly_action": "shorts contract",
            },
            {
                "duration_seconds": 6.0,
                "processed_duration_seconds": 6.0,
                "video_format": "shorts",
                "exact_visual_family_id": "tech_behavior_motion",
                "media_type": "video",
                "motion_effect": "static",
                "transition_out": "cut",
                "transition_duration_seconds": 0.0,
                "assembly_action": "",
            },
        ]
        style = timeline_builder.normalize_timeline_style(None)

        with patch.object(regular_transition, "_previous_apply_edit_decisions"):
            regular_transition.apply_edit_decisions(clips, style)

        self.assertEqual(clips[0]["assembly_action"], "shorts contract")

    def test_second_adjacent_transport_uses_logistics_renderer(self) -> None:
        first = SimpleNamespace(scene_number=1, animation_plan={})
        second = SimpleNamespace(scene_number=2, animation_plan={})
        project = SimpleNamespace(scenes=[first, second])
        first.project = project
        second.project = project
        logistics = Image.new("RGB", (8, 8), (20, 120, 180))
        fallback = Image.new("RGB", (8, 8), (180, 100, 20))

        def selected(scene, template_id):
            return "transport_scene"

        with (
            patch.object(v63, "_selected_template", side_effect=selected),
            patch.object(v66, "_logistics_frame", return_value=logistics) as logistics_frame,
            patch.object(v65, "render_planned_frame", return_value=fallback) as previous,
        ):
            rendered = v66.render_planned_frame(
                second,
                "transport_scene",
                10.0,
                5.0,
            )

        self.assertEqual(rendered.tobytes(), logistics.tobytes())
        logistics_frame.assert_called_once()
        previous.assert_not_called()

    def test_first_transport_keeps_boarding_renderer(self) -> None:
        first = SimpleNamespace(scene_number=1, animation_plan={})
        second = SimpleNamespace(scene_number=2, animation_plan={})
        project = SimpleNamespace(scenes=[first, second])
        first.project = project
        second.project = project
        fallback = Image.new("RGB", (8, 8), (180, 100, 20))

        with (
            patch.object(v63, "_selected_template", return_value="transport_scene"),
            patch.object(v66, "_logistics_frame") as logistics_frame,
            patch.object(v65, "render_planned_frame", return_value=fallback) as previous,
        ):
            rendered = v66.render_planned_frame(
                first,
                "transport_scene",
                10.0,
                5.0,
            )

        self.assertEqual(rendered.tobytes(), fallback.tobytes())
        logistics_frame.assert_not_called()
        previous.assert_called_once()


if __name__ == "__main__":
    unittest.main()
