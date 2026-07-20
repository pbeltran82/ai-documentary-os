from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from app.services import cartoon_documentary as cartoon
from app.services import cartoon_visual_overhaul_v63 as v63
from app.services import cartoon_visual_overhaul_v65 as v65
from app.services import cartoon_visual_overhaul_v66 as v66
from app.services import regular_transition_polish as regular_transition
from app.services import timeline_builder


class RegularReleaseQATests(unittest.TestCase):
    def documentary_clip(
        self,
        *,
        duration: float,
        template_id: str,
        video_format: str = "youtube",
    ) -> dict:
        return {
            "duration_seconds": duration,
            "processed_duration_seconds": duration + 0.24,
            "video_format": video_format,
            "exact_visual_family_id": "tech_behavior_motion",
            "exact_visual_template_id": template_id,
            "media_type": "video",
            "motion_effect": "static",
            "transition_out": "fade_black",
            "transition_duration_seconds": 0.24,
            "assembly_action": "",
        }

    def test_regular_documentary_boundary_uses_clean_cut(self) -> None:
        clips = [
            self.documentary_clip(duration=5.0, template_id="transport_scene"),
            self.documentary_clip(duration=6.0, template_id="habitat_build"),
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

    def test_non_documentary_exact_visual_retains_existing_transition(self) -> None:
        clips = [
            self.documentary_clip(duration=5.0, template_id="algorithm_chose_you"),
            self.documentary_clip(duration=6.0, template_id="behavior_prediction_engine"),
        ]
        style = timeline_builder.normalize_timeline_style(None)

        with patch.object(regular_transition, "_previous_apply_edit_decisions"):
            regular_transition.apply_edit_decisions(clips, style)

        self.assertEqual(clips[0]["transition_out"], "fade_black")
        self.assertEqual(clips[0]["transition_duration_seconds"], 0.24)

    def test_shorts_boundary_is_not_modified_by_regular_guard(self) -> None:
        clips = [
            self.documentary_clip(
                duration=5.0,
                template_id="transport_scene",
                video_format="shorts",
            ),
            self.documentary_clip(
                duration=6.0,
                template_id="habitat_build",
                video_format="shorts",
            ),
        ]
        clips[0]["assembly_action"] = "shorts contract"
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
            patch.object(v66, "_previous_render_planned_frame", return_value=fallback) as previous,
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
            patch.object(v66, "_previous_render_planned_frame", return_value=fallback) as previous,
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

    def test_v66_extends_v65_public_renderer_contract(self) -> None:
        self.assertIs(v65.render_planned_frame, v66.render_planned_frame)
        self.assertIs(cartoon.render_planned_frame, v65.render_planned_frame)


if __name__ == "__main__":
    unittest.main()
