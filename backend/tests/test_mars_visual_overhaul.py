from __future__ import annotations

import unittest
from types import SimpleNamespace

from PIL import Image

from app.models import Project
from app.services import cartoon_documentary as cartoon
from app.services import cartoon_visual_overhaul_v62 as overhaul
from app.services import exact_visuals
from app.services import script_audio_pipeline as pipeline
from app.services.cartoon_scene_graph import LayerStack, draw_airlock


class MarsVisualOverhaulTests(unittest.TestCase):
    def shorts_project(self) -> Project:
        return Project(
            id=91,
            title="Mars Short",
            topic="Building a permanent civilization on Mars",
            target_minutes=1,
            audience="General audience",
            tone="Investigative",
            visual_style="Cartoon documentary",
            video_format="shorts",
            status="script_approved",
        )

    def script_segments(self) -> list[dict[str, object]]:
        acts = (
            ("Hook", "A launch window opens a one-way journey from Earth to Mars."),
            ("Context", "Evacuation transports must board people through one safe corridor."),
            ("Mechanism", "Habitats need air, power, food, and life support before arrival."),
            ("Evidence", "Researchers turn data and evidence into an operating plan."),
            ("Complication", "A council must decide the rules, authority, and accountability."),
            ("Consequence", "Families and ordinary people must be able to form a community."),
            ("Conclusion", "Transport, habitat, and governance connect into a permanent settlement."),
            ("Conclusion", "The future city survives only when every system works together."),
        )
        return [
            {
                "segment_id": f"segment-{index}",
                "scene_number": index,
                "act": act,
                "narration": narration,
                "visual_intent": narration,
                "search_keywords": ["mars", act.lower()],
            }
            for index, (act, narration) in enumerate(acts, start=1)
        ]

    def test_foreground_airlock_occludes_actor_layer(self) -> None:
        stack = LayerStack((400, 400))
        draw_airlock(
            stack,
            (80, 40, 320, 360),
            opening=0.0,
            panel_fill=(81, 92, 103),
        )
        actors = stack.draw("actors")
        actors.rectangle((175, 130, 225, 300), fill=(255, 0, 0))
        image = stack.composite((230, 230, 230))
        self.assertNotEqual(image.getpixel((200, 210)), (255, 0, 0))
        self.assertEqual(image.getpixel((200, 210)), (81, 92, 103))

    def test_shorts_selector_uses_unique_roles_and_one_route(self) -> None:
        selected, story_mode = pipeline._narration_source_segments(
            self.shorts_project(),
            {"segments": self.script_segments()},
        )
        templates = [str(item["shorts_template_id"]) for item in selected]
        self.assertEqual(story_mode, "shorts")
        self.assertGreaterEqual(len(templates), pipeline.SHORTS_MIN_SCENES)
        self.assertEqual(len(templates), len(set(templates)))
        self.assertLessEqual(templates.count("route_map"), 1)
        self.assertEqual(templates[-1], "process_diagram")

    def test_manifest_persists_selected_template_roles(self) -> None:
        source, _mode = pipeline._narration_source_segments(
            self.shorts_project(),
            {"segments": self.script_segments()},
        )
        self.assertTrue(all(item.get("shorts_template_id") for item in source))
        self.assertNotEqual(source[0]["shorts_template_id"], source[-1]["shorts_template_id"])

    def test_forced_short_template_wins_exact_visual_suggestion(self) -> None:
        project = self.shorts_project()
        scene = SimpleNamespace(
            project=project,
            narration="Mars systems",
            visual_intent="Mars systems",
            search_keywords=["mars"],
            animation_plan={"shorts_template_id": "council_scene"},
            scene_number=5,
        )
        template, confidence, _reason = exact_visuals.suggest_template(
            scene,
            exact_visuals.TECH_FAMILY_ID,
        )
        self.assertEqual(template.template_id, "council_scene")
        self.assertEqual(confidence, 1.0)

    def test_regular_transport_has_no_legacy_wall_seam_columns(self) -> None:
        image = overhaul._transport_frame(0.55, 0).convert("RGB")
        self.assertEqual(image.size, (1920, 1080))
        pixels = image.load()

        def longest_dark_run(x: int) -> int:
            longest = current = 0
            for y in range(120, 740):
                red, green, blue = pixels[x, y]
                dark = red < 42 and green < 48 and blue < 60
                current = current + 1 if dark else 0
                longest = max(longest, current)
            return longest

        # These columns cross the broad wall regions where the old renderer drew
        # floor-to-ceiling construction seams. Real airlock edges are centered and
        # intentionally excluded from this assertion.
        for x in (340, 560, 1360, 1580):
            with self.subTest(x=x):
                self.assertLess(longest_dark_run(x), 120)

    def test_rebuilt_habitat_and_transport_are_rgb(self) -> None:
        for image in (overhaul._transport_frame(0.5, 1), overhaul._habitat_frame(0.5, 1)):
            self.assertIsInstance(image, Image.Image)
            self.assertEqual(image.mode, "RGB")
            self.assertEqual(image.size, (cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT))


if __name__ == "__main__":
    unittest.main()
