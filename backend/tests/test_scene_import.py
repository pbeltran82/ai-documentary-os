from __future__ import annotations

import unittest

from app.routers.scenes import parse_structured_scene_plan


class StructuredSceneImportTests(unittest.TestCase):
    def test_imports_labeled_scene_fields_without_polluting_narration(self) -> None:
        text = """Scene 01
00:00–00:05
Narration: Most people underestimate the power of time.
Visual intent: Calendar pages and long-term market growth
Search terms: calendar time lapse, investment growth, stock chart
Preferred visual: Stock video
Asset status: Missing

Scene 02
00:05–00:10
Narration: Compound growth rewards patience and consistency.
Visual intent: Coins accumulating beside a rising line chart
Search keywords: compound interest; savings growth; line chart
Preferred visual: AI image
Asset status: Selected
"""

        scenes = parse_structured_scene_plan(text, target_scene_seconds=5)

        self.assertEqual(len(scenes), 2)
        self.assertEqual(
            scenes[0].narration,
            "Most people underestimate the power of time.",
        )
        self.assertEqual(scenes[0].duration_seconds, 5)
        self.assertEqual(
            scenes[0].visual_intent,
            "Calendar pages and long-term market growth",
        )
        self.assertEqual(
            scenes[0].search_keywords,
            ["calendar time lapse", "investment growth", "stock chart"],
        )
        self.assertEqual(scenes[0].preferred_asset_type, "stock_video")
        self.assertEqual(scenes[0].asset_status, "missing")
        self.assertEqual(scenes[1].preferred_asset_type, "ai_image")
        self.assertEqual(scenes[1].asset_status, "selected")

    def test_accepts_markdown_scene_labels(self) -> None:
        text = """## Scene 01 — Opening
**00:00-00:04**
- **Voiceover:** Time is the most powerful ingredient in compounding.
- **Visual intent:** A calendar dissolving into a rising investment chart.
- **Keywords:** calendar, compound growth, investing
- **Asset type:** Chart / graphic
- **Status:** Ready
"""

        scenes = parse_structured_scene_plan(text, target_scene_seconds=5)

        self.assertEqual(len(scenes), 1)
        self.assertEqual(
            scenes[0].narration,
            "Time is the most powerful ingredient in compounding.",
        )
        self.assertEqual(scenes[0].duration_seconds, 4)
        self.assertEqual(scenes[0].preferred_asset_type, "chart")
        self.assertEqual(scenes[0].asset_status, "ready")

    def test_plain_narration_is_not_misclassified(self) -> None:
        text = "Most people underestimate the power of time and consistency."
        self.assertEqual(parse_structured_scene_plan(text, 5), [])


if __name__ == "__main__":
    unittest.main()
