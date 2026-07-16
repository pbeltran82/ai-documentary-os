from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models import Asset, Project, Scene
from app.schemas import AssetCandidate
from app.services import media_library, visual_feedback
from app.services.visual_director import (
    build_shot_brief,
    director_shortlist,
    provider_priority,
)


class VisualDirectorTests(unittest.TestCase):
    def project_with_scene(self, narration: str, visual_intent: str = "") -> tuple[Project, Scene]:
        project = Project(
            id=1,
            title="Compound Blueprint",
            topic="Personal finance",
            target_minutes=1,
            audience="General audience",
            tone="Cinematic and credible",
            visual_style="Cinematic documentary",
            status="assets",
        )
        scene = Scene(
            id=10,
            project_id=1,
            scene_number=3,
            start_seconds=14,
            end_seconds=16,
            duration_seconds=2,
            narration=narration,
            visual_intent=visual_intent,
            search_keywords=["zero balance", "empty wallet"],
            preferred_asset_type="stock_video",
            asset_status="missing",
        )
        scene.project = project
        project.scenes = [scene]
        return project, scene

    def candidate(
        self,
        asset_id: str,
        description: str,
        *,
        creator: str = "Creator",
        width: int = 1920,
        height: int = 1080,
    ) -> AssetCandidate:
        return AssetCandidate(
            provider="pixabay",
            provider_asset_id=asset_id,
            media_type="video",
            source_url=f"https://example.com/{asset_id}",
            preview_url=f"https://example.com/{asset_id}.jpg",
            download_url=f"https://example.com/{asset_id}.mp4",
            creator=creator,
            creator_url="https://example.com/creator",
            width=width,
            height=height,
            duration_seconds=6,
            license_name="Test License",
            license_url="https://example.com/license",
            attribution="Test attribution",
            description=description,
            keywords=description.lower().split(),
            query_variant="bank account zero balance video",
        )

    def test_empty_balance_scene_builds_literal_brief(self) -> None:
        _project, scene = self.project_with_scene(
            "Spoiler alert: there’s never anything left.",
            "A banking app or wallet showing an empty balance after spending.",
        )
        brief = build_shot_brief(scene, "video")

        self.assertIn("empty wallet", brief.must_show)
        self.assertIn("zero bank balance", brief.must_show)
        self.assertIn("dice", brief.must_avoid)
        self.assertIn("bank account zero balance video", brief.query_variants)

    def test_dice_is_ranked_below_zero_balance(self) -> None:
        _project, scene = self.project_with_scene(
            "Spoiler alert: there’s never anything left.",
        )
        brief = build_shot_brief(scene, "video")
        strong = self.candidate(
            "strong",
            "bank account zero balance empty wallet declined card",
        )
        dice = self.candidate(
            "dice",
            "casino gambling dice money risk",
        )

        shortlist = director_shortlist(scene, brief, [dice, strong], set(), 6)

        self.assertEqual(shortlist[0].provider_asset_id, "strong")
        self.assertGreater(shortlist[0].director_score, 70)
        self.assertNotIn("dice", [item.provider_asset_id for item in shortlist])

    def test_search_query_is_not_visual_evidence(self) -> None:
        _project, scene = self.project_with_scene(
            "Spoiler alert: there’s never anything left.",
        )
        brief = build_shot_brief(scene, "video")
        unrelated = self.candidate(
            "stock-chart",
            "stock market graph finance analytics investment",
        )

        shortlist = director_shortlist(scene, brief, [unrelated], set(), 6)

        self.assertEqual(shortlist, [])

    def test_partial_phrase_overlap_is_not_a_strong_match(self) -> None:
        _project, scene = self.project_with_scene(
            "Spoiler alert: there’s never anything left.",
        )
        brief = build_shot_brief(scene, "video")
        partial = self.candidate(
            "partial",
            "bank account balance chart finance business",
        )

        shortlist = director_shortlist(scene, brief, [partial], set(), 6)

        self.assertEqual(shortlist, [])

    def test_attribution_and_source_url_are_not_concept_evidence(self) -> None:
        _project, scene = self.project_with_scene(
            "Spoiler alert: there’s never anything left.",
        )
        brief = build_shot_brief(scene, "video")
        misleading = self.candidate("misleading", "abstract people standing on platform")
        misleading = misleading.model_copy(
            update={
                "attribution": "zero bank balance empty wallet",
                "source_url": "https://example.com/empty-wallet-zero-balance",
            }
        )

        shortlist = director_shortlist(scene, brief, [misleading], set(), 6)

        self.assertEqual(shortlist, [])

    def test_rejected_candidate_is_removed_from_future_shortlists(self) -> None:
        _project, scene = self.project_with_scene(
            "Spoiler alert: there’s never anything left.",
        )
        brief = build_shot_brief(scene, "video")
        candidate = self.candidate(
            "reject-me",
            "bank account zero balance empty wallet",
        )

        shortlist = director_shortlist(
            scene,
            brief,
            [candidate],
            {("pixabay", "reject-me")},
            6,
        )
        self.assertEqual(shortlist, [])

    def test_creator_repetition_receives_diversity_penalty(self) -> None:
        project, scene = self.project_with_scene(
            "Spoiler alert: there’s never anything left.",
        )
        other_scene = Scene(
            id=11,
            project_id=1,
            scene_number=2,
            start_seconds=7,
            end_seconds=14,
            duration_seconds=7,
            narration="Expenses drain the paycheck.",
            visual_intent="Expense montage",
            search_keywords=["expenses"],
            preferred_asset_type="stock_video",
            asset_status="ready",
        )
        other_scene.project = project
        other_scene.selected_asset = Asset(
            id=20,
            scene_id=11,
            provider="pixabay",
            provider_asset_id="old",
            media_type="video",
            source_url="https://example.com/old",
            preview_url="https://example.com/old.jpg",
            download_url="https://example.com/old.mp4",
            creator="Repeated Creator",
            creator_url="https://example.com/creator",
            width=1920,
            height=1080,
            duration_seconds=6,
            license_name="Test",
            license_url="https://example.com/license",
            attribution="Test",
        )
        project.scenes = [other_scene, scene]

        repeated = self.candidate(
            "repeated",
            "bank account zero balance empty wallet",
            creator="Repeated Creator",
        )
        fresh = self.candidate(
            "fresh",
            "bank account zero balance empty wallet",
            creator="Fresh Creator",
        )
        shortlist = director_shortlist(scene, build_shot_brief(scene, "video"), [repeated, fresh], set(), 6)

        self.assertEqual(shortlist[0].provider_asset_id, "fresh")

    def test_default_finance_video_search_does_not_call_nasa(self) -> None:
        _project, scene = self.project_with_scene(
            "Route ten percent automatically into a low-cost S&P 500 index fund.",
        )
        brief = build_shot_brief(scene, "video")
        providers = provider_priority("video", brief, ["pixabay", "nasa"])
        self.assertEqual(providers, ["pixabay"])


class VisualFeedbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.media_patch = patch.object(media_library, "MEDIA_ROOT", self.root)
        self.feedback_patch = patch.object(visual_feedback, "project_directory", lambda project_id: self.root / f"project-{project_id:04d}")
        self.media_patch.start()
        self.feedback_patch.start()

    def tearDown(self) -> None:
        self.feedback_patch.stop()
        self.media_patch.stop()
        self.temporary.cleanup()

    def test_feedback_persists_and_resets(self) -> None:
        visual_feedback.record_rejection(1, 10, "pixabay", "abc", "too_generic")
        records = visual_feedback.scene_feedback(1, 10)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["reason"], "too_generic")
        self.assertEqual(visual_feedback.clear_scene_feedback(1, 10), 1)
        self.assertEqual(visual_feedback.scene_feedback(1, 10), [])


if __name__ == "__main__":
    unittest.main()
