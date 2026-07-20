from __future__ import annotations

import unittest

from app.models import Project, Scene
from app.services.exact_visuals import (
    FINANCE_FAMILY_ID,
    TECH_FAMILY_ID,
    recommend_family,
)


class ExactVisualRoutingTests(unittest.TestCase):
    def project(self, topic: str) -> Project:
        return Project(
            id=41,
            title="Routing Test",
            topic=topic,
            target_minutes=2,
            audience="General audience",
            tone="Investigative",
            visual_style="Cinematic documentary",
            video_format="youtube",
            status="storyboard",
        )

    def scene(self, project: Project, narration: str, visual_intent: str) -> Scene:
        scene = Scene(
            id=7,
            project_id=project.id,
            scene_number=1,
            start_seconds=0,
            end_seconds=18,
            duration_seconds=18,
            narration=narration,
            visual_intent=visual_intent,
            search_keywords=[],
            preferred_asset_type="stock_video",
            asset_status="missing",
        )
        scene.project = project
        project.scenes = [scene]
        return scene

    def test_mars_robotics_documentary_never_falls_back_to_finance(self) -> None:
        project = self.project("AI robots evacuate humanity to Mars")
        scene = self.scene(
            project,
            "Robotic fleets carry survivors off-planet while autonomous systems deploy life-support habitats on Mars.",
            "Cinematic spacecraft, maintenance drones, Martian habitat diagrams, and survivor silhouettes.",
        )

        family_id, confidence, reason = recommend_family(scene)

        self.assertEqual(family_id, TECH_FAMILY_ID)
        self.assertGreaterEqual(confidence, 0.8)
        self.assertIn("space", reason.lower())

    def test_explicit_investing_mechanism_still_routes_to_finance(self) -> None:
        project = self.project("Automatic investing")
        scene = self.scene(
            project,
            "An automatic transfer moves part of every paycheck into a low-cost index fund.",
            "Show the paycheck splitting between expenses and an investment account with a growth chart.",
        )

        family_id, confidence, _reason = recommend_family(scene)

        self.assertEqual(family_id, FINANCE_FAMILY_ID)
        self.assertGreaterEqual(confidence, 0.68)

    def test_ambiguous_non_finance_scene_uses_neutral_tech_family(self) -> None:
        project = self.project("A documentary about institutional change")
        scene = self.scene(
            project,
            "The record remains incomplete, but the consequences continue to shape public decisions.",
            "Use an archival timeline, evidence cards, and restrained systems diagrams.",
        )

        family_id, _confidence, reason = recommend_family(scene)

        self.assertEqual(family_id, TECH_FAMILY_ID)
        self.assertIn("finance", reason.lower())


if __name__ == "__main__":
    unittest.main()
