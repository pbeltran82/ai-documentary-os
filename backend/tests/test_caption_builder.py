from __future__ import annotations

import unittest

from app.models import Scene
from app.services.caption_builder import MAX_LINE_CHARACTERS, build_srt, caption_chunks


class CaptionBuilderTests(unittest.TestCase):
    def scene(
        self,
        scene_number: int,
        start: float,
        end: float,
        narration: str,
    ) -> Scene:
        return Scene(
            id=scene_number,
            project_id=1,
            scene_number=scene_number,
            start_seconds=start,
            end_seconds=end,
            duration_seconds=end - start,
            narration=narration,
            visual_intent="",
            search_keywords=[],
            preferred_asset_type="stock_video",
            asset_status="missing",
        )

    def test_caption_chunks_respect_reading_time(self) -> None:
        narration = (
            "Every scroll, every pause, and every abandoned draft becomes "
            "another signal in the model that predicts what happens next."
        )
        chunks = caption_chunks(narration, 6.0)

        self.assertGreaterEqual(len(chunks), 2)
        self.assertLessEqual(len(chunks), 5)
        self.assertEqual(" ".join(chunks), narration)

    def test_srt_uses_scene_timing_and_phone_readable_lines(self) -> None:
        scenes = [
            self.scene(
                1,
                0,
                4,
                "The algorithm ranked thousands of possibilities before this video reached you.",
            ),
            self.scene(
                2,
                4,
                9,
                "Your visible action sits beside a much larger field of hidden machine scores.",
            ),
        ]

        content, cue_count = build_srt(scenes)

        self.assertGreaterEqual(cue_count, 2)
        self.assertIn("00:00:00,000 -->", content)
        self.assertIn("--> 00:00:09,000", content)
        text_lines = [
            line
            for line in content.splitlines()
            if line and not line.isdigit() and " --> " not in line
        ]
        self.assertTrue(all(len(line) <= MAX_LINE_CHARACTERS for line in text_lines))


if __name__ == "__main__":
    unittest.main()
