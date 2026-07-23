from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException

from app.database_safety import assert_destructive_database_is_safe
from app.services.hyperframes_renderer import _composition_html, supports
from app.services.visuals import build_visual_plan
from app.services.visuals.diversity_guard import (
    VisualDiversityGuard,
    canonical_url,
    choose_unused_exact_template,
)
from app.services.visuals.runtime import (
    _eligible_for_hyperframes_rescue,
    _render_exact_visual_preserving_hyperframes,
    _rescue_template_for_scene,
)


class Phase123VisualPipelineTests(unittest.TestCase):
    def test_destructive_reset_rejects_normal_user_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "documentary_os.db"
            with self.assertRaises(RuntimeError):
                assert_destructive_database_is_safe(
                    f"sqlite:///{path}", purpose="regression test"
                )

    def test_destructive_reset_accepts_e2e_database(self) -> None:
        with tempfile.TemporaryDirectory(prefix="documentary-e2e-") as directory:
            path = Path(directory) / "asset-first-e2e.db"
            resolved = assert_destructive_database_is_safe(
                f"sqlite:///{path}", purpose="regression test"
            )
            self.assertEqual(resolved, path.resolve())

    def test_duplicate_asset_identity_is_rejected(self) -> None:
        guard = VisualDiversityGuard()
        guard.register_asset("pixabay", "42", "https://cdn.example/a.mp4?token=1", "video")
        candidate = SimpleNamespace(
            provider="pixabay",
            provider_asset_id="42",
            download_url="https://cdn.example/other.mp4",
            preview_url="",
        )
        self.assertTrue(guard.rejects_candidate(candidate))

    def test_duplicate_media_url_ignores_query_tokens(self) -> None:
        self.assertEqual(
            canonical_url("https://cdn.example/a.mp4?token=one"),
            canonical_url("https://cdn.example/a.mp4?token=two"),
        )

    def test_exact_visual_rotation_avoids_repeated_template(self) -> None:
        guard = VisualDiversityGuard()
        guard.register_exact("tech_behavior_motion", "behavior_prediction_engine")
        selected = choose_unused_exact_template(
            "tech_behavior_motion", "behavior_prediction_engine", guard
        )
        self.assertEqual(selected, "algorithm_chose_you")

    def test_hyperframes_adapter_is_limited_to_pilot_templates(self) -> None:
        self.assertTrue(
            supports("tech_behavior_motion", "behavior_prediction_engine")
        )
        self.assertTrue(supports("tech_behavior_motion", "machine_choice_cta"))
        self.assertTrue(supports("tech_behavior_motion", "consequence_map"))
        self.assertTrue(supports("tech_behavior_motion", "machine_choice_explainer"))
        self.assertFalse(supports("finance_motion", "compound_growth"))

    def test_hyperframes_templates_are_visually_distinct_and_unbranded(self) -> None:
        scene = SimpleNamespace(
            narration="The system predicts what will keep your attention.",
            visual_intent="A cinematic explanation of an algorithm ranking behavior.",
        )
        templates = (
            "machine_choice_cta",
            "behavior_prediction_engine",
            "algorithm_chose_you",
            "consequence_map",
            "machine_choice_explainer",
        )
        documents = {
            template: _composition_html(scene, template, 5.0, 1920, 1080)
            for template in templates
        }

        self.assertEqual(len(set(documents.values())), len(templates))
        for template, document in documents.items():
            self.assertIn(f'data-template="{template}"', document)
            self.assertNotIn("Exact Visual · HyperFrames", document)
            self.assertNotIn("deterministic HTML motion", document)
            self.assertLess(document.count("<h1>"), 2)

        self.assertIn("forecast-orb", documents["behavior_prediction_engine"])
        self.assertIn("rank-card", documents["algorithm_chose_you"])
        self.assertIn("choice-path", documents["machine_choice_cta"])
        self.assertIn("consequence-system", documents["consequence_map"])
        self.assertIn("scoring-system", documents["machine_choice_explainer"])

    def test_search_terms_reject_weak_narration_glue(self) -> None:
        plan = build_visual_plan(
            narration=(
                "Every time it only needs a result, whether you skip or replay, "
                "the next thing changes."
            ),
            visual_intent=(
                "Observe a real person interacting with a recommendation feed on a phone."
            ),
            search_keywords=("every time", "only needs", "skip replay"),
            scene_key="semantic-search-regression",
        )
        joined = " ".join(plan.asset.search_terms)
        for weak in ("every", "time", "only", "needs", "result", "whether", "skip", "replay"):
            self.assertNotIn(weak, joined.split())
        self.assertTrue(
            any(
                phrase in joined
                for phrase in (
                    "person using smartphone",
                    "social media feed",
                    "phone screen over shoulder",
                )
            ),
            joined,
        )

    def test_failed_tech_asset_search_routes_to_distinct_rescue_templates(self) -> None:
        signal_scene = SimpleNamespace(
            narration="Each prediction changes the next signal.",
            visual_intent="Show behavioral feedback inside an algorithm.",
            search_keywords=(),
        )
        signal_plan = build_visual_plan(
            narration=signal_scene.narration,
            visual_intent=signal_scene.visual_intent,
            scene_key="rescue-signal",
        )
        ranking_scene = SimpleNamespace(
            narration="Rankings shape what appears next in the recommendation feed.",
            visual_intent="Reveal a machine scoring and selecting one result.",
            search_keywords=(),
        )
        ranking_plan = build_visual_plan(
            narration=ranking_scene.narration,
            visual_intent=ranking_scene.visual_intent,
            scene_key="rescue-ranking",
        )

        self.assertTrue(_eligible_for_hyperframes_rescue(signal_scene, signal_plan))
        self.assertTrue(_eligible_for_hyperframes_rescue(ranking_scene, ranking_plan))
        self.assertEqual(
            _rescue_template_for_scene(signal_scene, signal_plan),
            "consequence_map",
        )
        self.assertEqual(
            _rescue_template_for_scene(ranking_scene, ranking_plan),
            "machine_choice_explainer",
        )

    def test_legacy_renderer_cannot_overwrite_hyperframes_by_default(self) -> None:
        scene = SimpleNamespace(
            selected_asset=SimpleNamespace(provider="hyperframes")
        )
        with self.assertRaises(HTTPException) as context:
            _render_exact_visual_preserving_hyperframes(
                scene,
                "tech_behavior_motion",
                "behavior_prediction_engine",
                None,
            )
        self.assertEqual(context.exception.status_code, 409)
        self.assertIn("protected HyperFrames", str(context.exception.detail))


if __name__ == "__main__":
    unittest.main()
