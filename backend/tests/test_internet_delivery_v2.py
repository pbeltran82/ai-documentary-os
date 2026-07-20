from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.services import cartoon_documentary as cartoon
from app.services import internet_attention_delivery_v2 as delivery
from app.services import internet_attention_visuals as internet
from app.services import media_quality_assurance as media_qa
from app.services import regular_transition_polish as transitions
from app.services import rendered_semantic_quality_assurance as rendered_qa


def scene(number: int = 1, duration: float = 38.4, stored_beats: int = 0):
    project = SimpleNamespace(
        id=22,
        title="How the Internet Changed Human Attention",
        topic="Internet, smartphones, notifications, algorithms, and attention",
        audience="General audience",
        tone="Balanced",
        visual_style="Technology documentary",
        scenes=[],
    )
    beats = [
        {
            "relative_start_seconds": i * duration / max(1, stored_beats),
            "relative_end_seconds": (i + 1) * duration / max(1, stored_beats),
            "visual_intent": f"Beat {i + 1}",
        }
        for i in range(stored_beats)
    ]
    value = SimpleNamespace(
        project=project,
        project_id=project.id,
        scene_number=number,
        duration_seconds=duration,
        narration="The internet moved from desktops into smartphones, feeds, and notifications.",
        visual_intent="Show the early web, search, smartphones, algorithms, and attention.",
        search_keywords=["internet", "attention", "smartphone"],
        animation_plan={"visual_beats": beats},
    )
    project.scenes = [value]
    return value


class InternetDeliveryV2Tests(unittest.TestCase):
    def test_long_scene_gets_contiguous_delivery_windows(self):
        beats = delivery.effective_visual_beats(scene())
        self.assertEqual(len(beats), 7)
        self.assertEqual(beats[0]["relative_start_seconds"], 0.0)
        self.assertEqual(beats[-1]["relative_end_seconds"], 38.4)
        self.assertTrue(all(a["relative_end_seconds"] == b["relative_start_seconds"] for a, b in zip(beats, beats[1:], strict=False)))

    def test_scene_arcs_avoid_repeat_and_land_conclusion(self):
        second = delivery.beat_template_sequence(scene(2, 36.3), "internet_early_web")
        final = delivery.beat_template_sequence(scene(7, 43.3))
        self.assertEqual(second[0], "internet_search_growth")
        self.assertGreaterEqual(len(set(second)), 4)
        self.assertTrue(all(a != b for a, b in zip(second, second[1:], strict=False)))
        self.assertEqual(final[-1], "internet_attention_choice")

    def test_renderer_changes_actual_pixels_between_windows(self):
        value = scene()
        first = internet.render_planned_frame(value, "internet_early_web", 38.4, 2.0)
        second = internet.render_planned_frame(value, "internet_early_web", 38.4, 9.0)
        self.assertNotEqual(first.tobytes(), second.tobytes())

    def test_clean_cuts_and_output_helpers(self):
        self.assertTrue(internet.INTERNET_TEMPLATE_IDS <= transitions.DOCUMENTARY_TEMPLATE_IDS)
        black = bytes([0]) * (64 * 36)
        dark_art = bytes([18]) * (64 * 36)
        white = bytes([255]) * (64 * 36)
        self.assertTrue(rendered_qa.is_black_signature(black))
        self.assertFalse(rendered_qa.is_black_signature(dark_art))
        self.assertEqual(rendered_qa.signature_cluster_count([black, black, white]), 2)

    def test_guards_are_installed_last(self):
        self.assertIs(internet._visual_beats, delivery.effective_visual_beats)
        self.assertIs(internet._beat_state, delivery.beat_state)
        self.assertIs(cartoon.render_planned_frame, internet.render_planned_frame)
        self.assertIs(media_qa.evaluate_quality, rendered_qa.evaluate_quality)


if __name__ == "__main__":
    unittest.main()
