from __future__ import annotations

import unittest
from unittest.mock import patch

from app.routers.adaptive_assets import adaptive_visual_search
from app.schemas import AssetCandidate, ShotBrief, VisualDirectorResponse


def brief(scene_id: int, media_label: str) -> ShotBrief:
    return ShotBrief(
        scene_id=scene_id,
        subject="An empty wallet",
        action="Show no money remains",
        setting="Personal finance",
        framing="Close-up",
        mood="Consequential",
        must_show=["empty wallet"],
        must_avoid=["dice"],
        query_variants=[f"empty wallet {media_label}"],
    )


def candidate(media_type: str) -> AssetCandidate:
    return AssetCandidate(
        provider="unsplash" if media_type == "photo" else "pixabay",
        provider_asset_id=f"{media_type}-1",
        media_type=media_type,
        source_url="https://example.com/source",
        preview_url="https://example.com/preview.jpg",
        download_url="https://example.com/media.jpg",
        creator="Creator",
        creator_url="https://example.com/creator",
        width=1920,
        height=1080,
        license_name="Test license",
        license_url="https://example.com/license",
        attribution="Creator attribution",
        description="empty wallet",
        keywords=["empty", "wallet"],
        query_variant=f"empty wallet {media_type}",
        director_score=72,
        director_reasons=["Provider metadata explicitly supports empty wallet"],
        shortlist_rank=1,
    )


class AdaptiveVisualFeedTests(unittest.TestCase):
    def response(self, media_type: str, candidates: list[AssetCandidate]) -> VisualDirectorResponse:
        return VisualDirectorResponse(
            media_type=media_type,
            shot_brief=brief(3, media_type),
            search_queries=[f"empty wallet {media_type}"],
            providers_searched=["pixabay"] if media_type == "video" else ["unsplash", "wikimedia"],
            rate_limit_remaining=100 if media_type == "video" else 80,
            rejected_count=2,
            candidates=candidates,
        )

    def test_keeps_defensible_video_without_photo_search(self) -> None:
        video = self.response("video", [candidate("video")])
        with patch(
            "app.routers.adaptive_assets.direct_visual_search",
            return_value=video,
        ) as search:
            result = adaptive_visual_search(3, "video", 6, db=object())

        self.assertEqual(result.media_type, "video")
        self.assertEqual(result.candidates[0].media_type, "video")
        self.assertEqual(search.call_count, 1)

    def test_falls_back_to_motion_ready_photos_when_video_is_empty(self) -> None:
        video = self.response("video", [])
        photo = self.response("photo", [candidate("photo")])
        with patch(
            "app.routers.adaptive_assets.direct_visual_search",
            side_effect=[video, photo],
        ) as search:
            result = adaptive_visual_search(3, "video", 6, db=object())

        self.assertEqual(search.call_count, 2)
        self.assertEqual(result.media_type, "photo")
        self.assertEqual(result.providers_searched, ["pixabay", "unsplash", "wikimedia"])
        self.assertEqual(result.rate_limit_remaining, 80)
        self.assertIn("Motion-ready still fallback", result.candidates[0].director_reasons[0])
        self.assertIn("editorial still motion", result.candidates[0].director_warnings[-1])

    def test_returns_truthful_empty_result_when_both_formats_fail(self) -> None:
        video = self.response("video", [])
        photo = self.response("photo", [])
        with patch(
            "app.routers.adaptive_assets.direct_visual_search",
            side_effect=[video, photo],
        ):
            result = adaptive_visual_search(3, "video", 6, db=object())

        self.assertEqual(result.media_type, "video")
        self.assertEqual(result.candidates, [])
        self.assertEqual(result.providers_searched, ["pixabay", "unsplash", "wikimedia"])
        self.assertEqual(
            result.search_queries,
            ["empty wallet video", "empty wallet photo"],
        )


if __name__ == "__main__":
    unittest.main()
