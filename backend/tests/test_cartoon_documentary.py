from __future__ import annotations

import unittest

from app.models import Scene
from app.services import cartoon_documentary as cartoon
from app.services import cartoon_documentary_patch as patch
from app.services import exact_visuals


class CartoonDocumentaryTests(unittest.TestCase):
    def scene(self, *, narration: str, visual_intent: str, animation_plan=None) -> Scene:
        return Scene(
            project_id=1,
            scene_number=1,
            start_seconds=0,
            end_seconds=10,
            duration_seconds=10,
            narration=narration,
            visual_intent=visual_intent,
            search_keywords=[],
            preferred_asset_type="generated",
            asset_status="missing",
            animation_plan=animation_plan or {},
        )

    def test_mars_story_uses_cartoon_documentary_template(self) -> None:
        scene = self.scene(
            narration="Families board robotic transports before leaving Earth for Mars.",
            visual_intent="A crowded evacuation platform and spacecraft launch.",
        )
        template, _confidence, _reason = exact_visuals.suggest_template(
            scene,
            exact_visuals.TECH_FAMILY_ID,
        )
        self.assertIn(template.template_id, cartoon.TEMPLATE_BY_ID)

    def test_algorithm_story_keeps_existing_tech_templates(self) -> None:
        scene = self.scene(
            narration="The recommendation algorithm ranks every click and pause.",
            visual_intent="A digital profile becomes a behavioral prediction.",
        )
        template, _confidence, _reason = exact_visuals.suggest_template(
            scene,
            exact_visuals.TECH_FAMILY_ID,
        )
        self.assertNotIn(template.template_id, cartoon.TEMPLATE_BY_ID)

    def test_visual_beats_can_change_composition_inside_scene(self) -> None:
        scene = self.scene(
            narration="The evacuation moves from Earth to a new habitat on Mars.",
            visual_intent="Show the journey and construction.",
            animation_plan={
                "visual_beats": [
                    {
                        "relative_start_seconds": 0,
                        "relative_end_seconds": 5,
                        "visual_intent": "Earth and Mars with a travel route",
                    },
                    {
                        "relative_start_seconds": 5,
                        "relative_end_seconds": 10,
                        "visual_intent": "Robots build a life support habitat",
                    },
                ]
            },
        )
        first = cartoon._beat_for_time(scene, 2.5)
        second = cartoon._beat_for_time(scene, 7.5)
        self.assertIn("route", first["visual_intent"].lower())
        self.assertIn("habitat", second["visual_intent"].lower())
        first_template = cartoon.suggest_template(scene, first["visual_intent"])[0]
        second_template = cartoon.suggest_template(scene, second["visual_intent"])[0]
        self.assertEqual(first_template.template_id, "route_map")
        self.assertEqual(second_template.template_id, "habitat_build")

    def test_preview_frame_is_full_hd(self) -> None:
        frame = patch.render_frame(
            exact_visuals.TECH_FAMILY_ID,
            "crowd_focus",
            5,
            2.5,
        )
        self.assertEqual(frame.size, (1920, 1080))


if __name__ == "__main__":
    unittest.main()
