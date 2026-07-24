from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.visuals import runtime
from app.services.visuals.asset_director import _clean_supplied
from app.services.visuals.diversity_guard import VisualDiversityGuard
from app.services.visuals.types import ExecutionMode, VisualFamily


class HyperFramesRescueRegressionTests(unittest.TestCase):
    def _plan(self):
        return SimpleNamespace(
            asset=SimpleNamespace(execution_mode=ExecutionMode.ASSET_FIRST),
            intent=SimpleNamespace(
                concept_terms=(),
                interface_score=0,
                data_score=0,
            ),
            strategy=SimpleNamespace(family=VisualFamily.EDITORIAL_SYMBOLIC),
        )

    def test_legacy_tech_visual_is_rescued_even_without_classifier_terms(self) -> None:
        scene = SimpleNamespace(
            id=2,
            scene_number=2,
            narration="A quiet transition with no explicit technology vocabulary.",
            visual_intent="",
            search_keywords=(),
            selected_asset=SimpleNamespace(
                provider="generated",
                provider_asset_id="tech-signal_feedback_loop-scene-2",
                source_url=(
                    "local://exact-visual/tech_behavior_motion/"
                    "signal_feedback_loop/premium_motion/youtube"
                ),
                local_path="project-0001/assets/scene-002-tech-signal_feedback_loop.mp4",
            ),
        )

        def should_not_run(*_args, **_kwargs):
            raise AssertionError("Legacy exact visual should bypass asset-first search")

        with patch.object(runtime, "_ORIGINAL_EXECUTE_SCENE", should_not_run), patch.object(
            runtime,
            "_run_hyperframes_rescue",
            return_value={"status": "completed", "exact_renderer": "hyperframes_rescue"},
        ) as rescue:
            result = runtime._execute_scene_with_hyperframes_rescue(
                scene,
                self._plan(),
                6,
                object(),
                None,
            )

        self.assertEqual(result["exact_renderer"], "hyperframes_rescue")
        rescue.assert_called_once()

    def test_existing_hyperframes_asset_stays_on_controlled_redirect_path(self) -> None:
        scene = SimpleNamespace(
            id=10,
            scene_number=10,
            narration="Rankings shape what you see next.",
            visual_intent="",
            search_keywords=(),
            selected_asset=SimpleNamespace(
                provider="hyperframes",
                provider_asset_id="hyperframes-consequence_map-scene-10",
                source_url="local://hyperframes/tech_behavior_motion/consequence_map",
                local_path="project-0001/assets/scene-010-hyperframes-consequence_map.mp4",
            ),
        )

        def should_not_run(*_args, **_kwargs):
            raise AssertionError("Existing HyperFrames visual should not return to stock search")

        with patch.object(runtime, "_ORIGINAL_EXECUTE_SCENE", should_not_run), patch.object(
            runtime,
            "_run_hyperframes_rescue",
            return_value={"status": "completed", "exact_renderer": "hyperframes_rescue"},
        ) as rescue:
            result = runtime._execute_scene_with_hyperframes_rescue(
                scene,
                self._plan(),
                6,
                object(),
                VisualDiversityGuard(),
            )

        self.assertEqual(result["exact_renderer"], "hyperframes_rescue")
        rescue.assert_called_once()

    def test_project_snapshot_excludes_current_scene_but_preserves_other_templates(self) -> None:
        scene_2 = SimpleNamespace(
            id=2,
            selected_asset=SimpleNamespace(
                provider="hyperframes",
                provider_asset_id="hyperframes-consequence_map-scene-2",
                download_url="/scene-2.mp4",
                media_type="video",
                source_url="local://hyperframes/tech_behavior_motion/consequence_map",
            ),
        )
        scene_10 = SimpleNamespace(
            id=10,
            selected_asset=SimpleNamespace(
                provider="hyperframes",
                provider_asset_id="hyperframes-consequence_map-scene-10",
                download_url="/scene-10.mp4",
                media_type="video",
                source_url="local://hyperframes/tech_behavior_motion/consequence_map",
            ),
        )
        project = SimpleNamespace(scenes=[scene_2, scene_10])

        guard = VisualDiversityGuard.from_project(project, ignore_scene_id=10)

        self.assertIn(
            ("tech_behavior_motion", "consequence_map"),
            guard.exact_templates,
        )
        self.assertNotIn(
            ("hyperframes", "hyperframes-consequence_map-scene-10"),
            guard.asset_ids,
        )

    def test_legacy_asset_identity_guides_distinct_rescue_template(self) -> None:
        ranking_scene = SimpleNamespace(
            narration="",
            visual_intent="",
            search_keywords=(),
            selected_asset=SimpleNamespace(
                provider="generated",
                provider_asset_id="tech-ranking_feed-scene-10",
                source_url=(
                    "local://exact-visual/tech_behavior_motion/"
                    "ranking_feed/premium_motion/youtube"
                ),
                local_path="project-0001/assets/scene-010-tech-ranking_feed.mp4",
            ),
        )
        signal_scene = SimpleNamespace(
            narration="",
            visual_intent="",
            search_keywords=(),
            selected_asset=SimpleNamespace(
                provider="generated",
                provider_asset_id="tech-signal_feedback_loop-scene-2",
                source_url=(
                    "local://exact-visual/tech_behavior_motion/"
                    "signal_feedback_loop/premium_motion/youtube"
                ),
                local_path="project-0001/assets/scene-002-tech-signal_feedback_loop.mp4",
            ),
        )

        self.assertEqual(
            runtime._rescue_template_for_scene(ranking_scene, self._plan()),
            "machine_choice_explainer",
        )
        self.assertEqual(
            runtime._rescue_template_for_scene(signal_scene, self._plan()),
            "consequence_map",
        )

    def test_weak_single_word_search_terms_are_discarded(self) -> None:
        cleaned = _clean_supplied(
            [
                "open",
                "invisible",
                "even",
                "moments",
                "smartphone",
                "person scrolling smartphone",
            ]
        )
        self.assertEqual(cleaned, ("smartphone", "person scrolling smartphone"))


if __name__ == "__main__":
    unittest.main()
