from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from app.services import cartoon_documentary as cartoon
from app.services import cartoon_shorts_story_v8 as shorts_v8
from app.services import cartoon_visual_overhaul_v65 as regular_v65
from app.services import exact_visuals as exact
from app.services import native_shorts as native


class MarsGroundedFinalPolishTests(unittest.TestCase):
    def test_short_dome_geometry_is_anchored_to_requested_base(self) -> None:
        left, top, right, base_y = 35, 625, 390, 1085
        box = shorts_v8._grounded_dome_box(left, top, right, base_y)
        self.assertEqual(box[:3], (left, top, right))
        self.assertEqual((box[1] + box[3]) // 2, base_y)

    def test_regular_dome_geometry_is_anchored_to_requested_base(self) -> None:
        left, top, right, base_y = 75, 405, 610, 760
        box = regular_v65._grounded_dome_box(left, top, right, base_y)
        self.assertEqual((box[1] + box[3]) // 2, base_y)

    def test_latest_short_renderers_own_people_and_settlement_beats(self) -> None:
        self.assertIs(
            native.RENDERERS[(exact.TECH_FAMILY_ID, "crowd_focus")],
            shorts_v8._community,
        )
        self.assertIs(
            native.RENDERERS[(exact.TECH_FAMILY_ID, "process_diagram")],
            shorts_v8._settlement,
        )
        self.assertIs(
            native.RENDERERS[(exact.TECH_FAMILY_ID, "habitat_build")],
            shorts_v8._habitat,
        )

    def test_short_community_and_settlement_are_visually_distinct(self) -> None:
        community = Image.new("RGB", (1080, 1530), (10, 24, 38))
        settlement = Image.new("RGB", (1080, 1530), (10, 24, 38))
        shorts_v8._community(community, 0.75, None)
        shorts_v8._settlement(settlement, 0.75, None)
        self.assertNotEqual(
            community.resize((108, 153)).tobytes(),
            settlement.resize((108, 153)).tobytes(),
        )

    def test_second_route_scene_becomes_arrival_not_another_route_map(self) -> None:
        first = SimpleNamespace(
            scene_number=1,
            animation_plan={"shorts_template_id": "route_map"},
            narration="Earth departure for Mars",
            visual_intent="route",
            search_keywords=["mars"],
        )
        second = SimpleNamespace(
            scene_number=2,
            animation_plan={"shorts_template_id": "route_map"},
            narration="Mars approach and landing preparation",
            visual_intent="route",
            search_keywords=["mars"],
        )
        final = SimpleNamespace(
            scene_number=3,
            animation_plan={"shorts_template_id": "process_diagram"},
            narration="The settlement becomes a city",
            visual_intent="settlement",
            search_keywords=["mars"],
        )
        project = SimpleNamespace(scenes=[first, second, final])
        for scene in project.scenes:
            scene.project = project

        arrival = Image.new("RGB", (8, 8), (170, 80, 50))
        route = Image.new("RGB", (8, 8), (40, 80, 160))
        with (
            patch.object(regular_v65, "_arrival_frame", return_value=arrival) as arrival_renderer,
            patch.object(regular_v65.v63, "_route_frame", return_value=route) as route_renderer,
        ):
            rendered = regular_v65.render_planned_frame(second, "route_map", 10.0, 5.0)

        self.assertEqual(rendered.tobytes(), arrival.tobytes())
        arrival_renderer.assert_called_once()
        route_renderer.assert_not_called()

    def test_first_route_scene_remains_the_single_abstract_journey(self) -> None:
        first = SimpleNamespace(
            scene_number=1,
            animation_plan={"shorts_template_id": "route_map"},
            narration="Earth departure for Mars",
            visual_intent="route",
            search_keywords=["mars"],
        )
        second = SimpleNamespace(
            scene_number=2,
            animation_plan={"shorts_template_id": "route_map"},
            narration="Mars arrival",
            visual_intent="route",
            search_keywords=["mars"],
        )
        final = SimpleNamespace(
            scene_number=3,
            animation_plan={"shorts_template_id": "process_diagram"},
            narration="Settlement",
            visual_intent="settlement",
            search_keywords=["mars"],
        )
        project = SimpleNamespace(scenes=[first, second, final])
        for scene in project.scenes:
            scene.project = project

        route = Image.new("RGB", (8, 8), (40, 80, 160))
        with (
            patch.object(regular_v65.v63, "_route_frame", return_value=route) as route_renderer,
            patch.object(regular_v65, "_arrival_frame") as arrival_renderer,
        ):
            rendered = regular_v65.render_planned_frame(first, "route_map", 10.0, 5.0)

        self.assertEqual(rendered.tobytes(), route.tobytes())
        route_renderer.assert_called_once()
        arrival_renderer.assert_not_called()

    def test_v65_is_the_installed_regular_renderer(self) -> None:
        self.assertIs(cartoon.render_planned_frame, regular_v65.render_planned_frame)


if __name__ == "__main__":
    unittest.main()
