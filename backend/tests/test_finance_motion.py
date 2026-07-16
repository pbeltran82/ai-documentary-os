from __future__ import annotations

import unittest

from fastapi import HTTPException

from app.models import Project, Scene
from app.services.finance_motion import TEMPLATES, build_filter_chain, suggest_template


class FinanceMotionTests(unittest.TestCase):
    def scene(self, narration: str, visual_intent: str = "") -> Scene:
        project = Project(
            id=1,
            title="Compound Blueprint",
            topic="Personal finance",
            target_minutes=1,
            audience="General audience",
            tone="Cinematic",
            visual_style="Cinematic documentary",
            status="assets",
        )
        scene = Scene(
            id=3,
            project_id=1,
            scene_number=3,
            start_seconds=14,
            end_seconds=18,
            duration_seconds=4,
            narration=narration,
            visual_intent=visual_intent,
            search_keywords=[],
            preferred_asset_type="stock_video",
            asset_status="missing",
        )
        scene.project = project
        project.scenes = [scene]
        return scene

    def test_empty_balance_scene_gets_exact_template(self) -> None:
        template, confidence, reason = suggest_template(
            self.scene("Spoiler alert: there is never anything left. The balance is zero.")
        )
        self.assertEqual(template.template_id, "empty_balance")
        self.assertGreaterEqual(confidence, 0.68)
        self.assertIn("Matched", reason)

    def test_automatic_investing_scene_gets_transfer_template(self) -> None:
        template, _confidence, _reason = suggest_template(
            self.scene("Route ten percent automatically into an index fund every payday.")
        )
        self.assertEqual(template.template_id, "recurring_transfer")

    def test_compounding_scene_gets_growth_template(self) -> None:
        template, _confidence, _reason = suggest_template(
            self.scene("Compound interest builds an invisible wealth machine for your future self.")
        )
        self.assertEqual(template.template_id, "compound_growth")

    def test_every_template_builds_a_1080p_safe_filter_chain(self) -> None:
        for template in TEMPLATES:
            with self.subTest(template=template.template_id):
                chain = build_filter_chain(template.template_id, 4)
                self.assertIn("drawtext", chain)
                self.assertIn("fade=t=in", chain)
                self.assertTrue(chain.endswith("format=yuv420p"))

    def test_unknown_template_is_rejected(self) -> None:
        with self.assertRaises(HTTPException):
            build_filter_chain("not-a-template", 4)


if __name__ == "__main__":
    unittest.main()
