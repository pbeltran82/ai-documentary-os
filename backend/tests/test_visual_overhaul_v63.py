from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services import cartoon_documentary as cartoon
from app.services import cartoon_visual_overhaul_v63 as overhaul


class VisualOverhaulV63Tests(unittest.TestCase):
    def scene(self, template_id: str) -> SimpleNamespace:
        template = cartoon.TEMPLATE_BY_ID[template_id]
        return SimpleNamespace(
            narration=template.description,
            visual_intent=template.description,
            search_keywords=list(template.keywords),
            scene_number=3,
            animation_plan={},
            duration_seconds=12.0,
        )

    def test_every_general_template_uses_full_hd_layered_renderer(self) -> None:
        for template_id in cartoon.TEMPLATE_BY_ID:
            with self.subTest(template=template_id):
                image = overhaul.render_planned_frame(
                    self.scene(template_id),
                    template_id,
                    12.0,
                    6.0,
                )
                self.assertEqual(image.size, (1920, 1080))
                self.assertEqual(image.mode, "RGB")

    def test_known_templates_never_fall_back_to_legacy_renderer(self) -> None:
        with patch.object(
            overhaul.v62,
            "render_planned_frame",
            side_effect=AssertionError("legacy fallback used"),
        ):
            for template_id in cartoon.TEMPLATE_BY_ID:
                with self.subTest(template=template_id):
                    overhaul.render_planned_frame(
                        self.scene(template_id),
                        template_id,
                        12.0,
                        5.0,
                    )

    def test_route_has_distinct_departure_cruise_and_arrival_frames(self) -> None:
        frames = [
            overhaul._route_frame(progress, 2).resize((192, 108)).tobytes()
            for progress in (0.10, 0.42, 0.93)
        ]
        self.assertEqual(len(set(frames)), 3)

    def test_overhaul_is_the_installed_regular_renderer(self) -> None:
        self.assertIs(cartoon.render_planned_frame, overhaul.render_planned_frame)


if __name__ == "__main__":
    unittest.main()
