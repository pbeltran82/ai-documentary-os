from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch as mock_patch

from PIL import Image

from app.services import cartoon_documentary as cartoon
from app.services import cartoon_documentary_patch as patch
from app.services import internet_attention_release_guard as release_guard
from app.services import internet_attention_visuals as internet
from app.services.semantic_visual_quality_assurance import semantic_checks


class InternetAttentionGeneralizationTests(unittest.TestCase):
    def project(self, *, topic: str | None = None):
        project = SimpleNamespace(
            title="How the Internet Changed Human Attention",
            topic=topic
            or "Explain how the internet, smartphones, notifications, and recommendation systems changed human attention.",
            audience="General audience",
            tone="Balanced and cinematic",
            visual_style="Modern technology documentary",
            video_format="youtube",
            scenes=[],
        )
        return project

    def scene(self, number: int = 3, *, project=None, beats: int = 8):
        project = project or self.project()
        visual_beats = [
            {
                "beat_number": index + 1,
                "relative_start_seconds": index * 5.0,
                "relative_end_seconds": (index + 1) * 5.0,
                "visual_intent": intent,
            }
            for index, intent in enumerate(
                (
                    "Smartphone adoption timeline",
                    "Phone moves from desk to pocket",
                    "Recommendation algorithm ranks cards",
                    "Notifications arrive during a concentration task",
                    "Research evidence distinguishes immediate effects",
                    "Student and worker switch between tabs",
                    "People change notification settings",
                    "A city remains connected while people choose when to look",
                )[:beats]
            )
        ]
        scene = SimpleNamespace(
            narration=(
                "Smartphones made the internet constant. Recommendation systems select what appears next, "
                "notifications interrupt attention, and people switch among tabs and apps."
            ),
            visual_intent=(
                "Sequence showing smartphone adoption, algorithmic feeds, notifications, research evidence, "
                "fragmented daily behavior, and intentional settings."
            ),
            search_keywords=["smartphone", "attention", "algorithm", "notification"],
            scene_number=number,
            animation_plan={"visual_beats": visual_beats},
            duration_seconds=max(5.0, beats * 5.0),
            project=project,
            project_id=1,
        )
        project.scenes.append(scene)
        return scene

    def test_internet_project_uses_dedicated_cartoon_family(self) -> None:
        scene = self.scene()

        self.assertTrue(internet.is_internet_attention(scene))
        self.assertTrue(patch._use_cartoon(scene))
        template, confidence, reason = cartoon.suggest_template(scene)
        self.assertIn(template.template_id, internet.INTERNET_TEMPLATE_IDS)
        self.assertGreaterEqual(confidence, 0.72)
        self.assertIn("Internet", reason)

    def test_unknown_non_mars_project_cannot_enter_mars_cartoon_stack(self) -> None:
        project = SimpleNamespace(
            title="A History of Paper",
            topic="How paper changed record keeping and public knowledge",
            audience="General audience",
            tone="Historical",
            visual_style="Archival",
            scenes=[],
        )
        scene = SimpleNamespace(
            narration="Paper made records easier to preserve.",
            visual_intent="Archival documents and a printing workshop.",
            search_keywords=["paper", "documents"],
            scene_number=1,
            animation_plan={"visual_beats": [{"visual_intent": "Printing workshop"}]},
            duration_seconds=20.0,
            project=project,
        )

        self.assertFalse(internet.is_mars_documentary(scene))
        self.assertFalse(patch._use_cartoon(scene))

    def test_mars_project_preserves_reference_renderer(self) -> None:
        project = SimpleNamespace(
            title="Building a City on Mars",
            topic="Transport, habitats, governance, and settlement on Mars",
            audience="General audience",
            tone="Cinematic",
            visual_style="Cartoon documentary",
            scenes=[],
        )
        scene = SimpleNamespace(
            narration="A Mars habitat needs life support.",
            visual_intent="Build a dome and attached airlock on Mars.",
            search_keywords=["mars", "habitat"],
            scene_number=2,
            animation_plan={"visual_beats": []},
            duration_seconds=20.0,
            project=project,
        )

        self.assertTrue(internet.is_mars_documentary(scene))
        self.assertTrue(patch._use_cartoon(scene))

    def test_long_scene_resolves_to_multiple_subject_specific_beats(self) -> None:
        scene = self.scene(beats=8)
        sequence = internet.beat_template_sequence(scene)

        self.assertEqual(len(sequence), 8)
        self.assertGreaterEqual(len(set(sequence)), 4)
        self.assertTrue(set(sequence).issubset(internet.INTERNET_TEMPLATE_IDS))
        self.assertTrue(set(sequence).isdisjoint(internet.MARS_CARTOON_TEMPLATE_IDS))
        self.assertTrue(all(left != right for left, right in zip(sequence, sequence[1:])))

    def test_renderer_changes_composition_across_visual_beats(self) -> None:
        scene = self.scene(beats=4)
        first = cartoon.render_planned_frame(scene, "internet_smartphone_shift", 20.0, 1.0)
        second = cartoon.render_planned_frame(scene, "internet_smartphone_shift", 20.0, 11.0)

        self.assertIsInstance(first, Image.Image)
        self.assertEqual(first.mode, "RGB")
        self.assertEqual(first.size, (1920, 1080))
        self.assertEqual(second.size, (1920, 1080))
        self.assertNotEqual(first.tobytes(), second.tobytes())

    def test_regeneration_replaces_stale_mars_template_identity(self) -> None:
        scene = self.scene(number=2, beats=6)
        sentinel = object()
        with mock_patch.object(
            release_guard,
            "_original_render_cartoon_documentary",
            return_value=sentinel,
        ) as original:
            result = release_guard.render_cartoon_documentary(
                scene,
                "habitat_build",
                "clean_editorial",
            )

        self.assertIs(result, sentinel)
        resolved_template_id = original.call_args.args[1]
        self.assertIn(resolved_template_id, internet.INTERNET_TEMPLATE_IDS)
        self.assertNotEqual(resolved_template_id, "habitat_build")

    def test_semantic_qa_holds_internet_project_with_mars_templates(self) -> None:
        project = self.project()
        self.scene(project=project, beats=6)
        plan = {
            "clips": [
                {
                    "provider": "generated",
                    "scene_number": 1,
                    "exact_visual_template_id": "habitat_build",
                    "source_url": "local://exact-visual/tech_behavior_motion/habitat_build/youtube",
                    "visual_intent": "Mars habitat community",
                    "narration": "The internet became constant.",
                }
            ]
        }

        checks = {check["id"]: check for check in semantic_checks(project, plan)}
        self.assertEqual(checks["semantic_visual_alignment"]["status"], "fail")
        self.assertEqual(checks["semantic_visual_alignment"]["severity"], "blocker")

    def test_semantic_qa_passes_dedicated_family_and_beat_coverage(self) -> None:
        project = self.project()
        for number in range(1, 8):
            self.scene(number=number, project=project, beats=6)
        plan = {
            "clips": [
                {
                    "provider": "generated",
                    "scene_number": number,
                    "exact_visual_template_id": internet.SCENE_ARCS[number][0],
                    "source_url": f"local://exact-visual/tech_behavior_motion/{internet.SCENE_ARCS[number][0]}/youtube",
                    "visual_intent": "Internet and attention composition",
                    "narration": "Internet attention story",
                }
                for number in range(1, 8)
            ]
        }

        checks = {check["id"]: check for check in semantic_checks(project, plan)}
        self.assertEqual(checks["semantic_visual_alignment"]["status"], "pass")
        self.assertEqual(checks["semantic_visual_beat_coverage"]["status"], "pass")
        self.assertEqual(checks["semantic_template_diversity"]["status"], "pass")

    def test_topic_aware_renderer_is_installed_last(self) -> None:
        self.assertIs(cartoon.render_planned_frame, internet.render_planned_frame)
        self.assertIs(cartoon.render_cartoon_documentary, release_guard.render_cartoon_documentary)
        self.assertIs(cartoon.suggest_template, internet.suggest_template)
        self.assertIs(patch._use_cartoon, internet._use_cartoon)


if __name__ == "__main__":
    unittest.main()
