from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.schemas import AssetCandidate
from app.services.assets import PROVIDERS
from app.services.assets.common import clean_html, public_search_url
from app.services.assets.nasa import normalize_item as normalize_nasa
from app.services.assets.pixabay import (
    normalize_photo as normalize_pixabay_photo,
    normalize_video as normalize_pixabay_video,
    rank_hits as rank_pixabay_hits,
)
from app.services.assets.search_intelligence import (
    build_search_plan,
    merge_candidate_batches,
)
from app.services.assets.unsplash import normalize_photo as normalize_unsplash_photo
from app.services.assets.wikimedia import normalize_photo as normalize_wikimedia_photo


class MultiProviderAssetTests(unittest.TestCase):
    def test_pixabay_video_prefers_landscape_full_hd_file(self) -> None:
        candidate = normalize_pixabay_video(
            {
                "id": 42,
                "pageURL": "https://pixabay.com/videos/id-42/",
                "duration": 8,
                "user": "Creator",
                "user_id": 12,
                "videos": {
                    "tiny": {
                        "url": "https://cdn.example/tiny.mp4",
                        "width": 640,
                        "height": 360,
                        "thumbnail": "https://cdn.example/tiny.jpg",
                    },
                    "large": {
                        "url": "https://cdn.example/hd.mp4",
                        "width": 1920,
                        "height": 1080,
                        "thumbnail": "https://cdn.example/hd.jpg",
                    },
                    "portrait": {
                        "url": "https://cdn.example/portrait.mp4",
                        "width": 1080,
                        "height": 1920,
                        "thumbnail": "https://cdn.example/portrait.jpg",
                    },
                },
            }
        )

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.provider, "pixabay")
        self.assertEqual(candidate.download_url, "https://cdn.example/hd.mp4")
        self.assertEqual(candidate.preview_url, "https://cdn.example/hd.jpg")
        self.assertEqual(candidate.width, 1920)
        self.assertEqual(candidate.license_name, "Pixabay Content License")

    def test_pixabay_photo_preserves_source_creator_and_rights(self) -> None:
        candidate = normalize_pixabay_photo(
            {
                "id": 7,
                "pageURL": "https://pixabay.com/photos/id-7/",
                "largeImageURL": "https://cdn.example/original.jpg",
                "webformatURL": "https://cdn.example/preview.jpg",
                "imageWidth": 2400,
                "imageHeight": 1600,
                "user": "Photo Person",
                "user_id": 99,
            }
        )

        self.assertEqual(candidate.creator, "Photo Person")
        self.assertEqual(candidate.source_url, "https://pixabay.com/photos/id-7/")
        self.assertEqual(candidate.download_url, "https://cdn.example/original.jpg")
        self.assertIn("Photo Person", candidate.attribution)

    def test_unsplash_photo_adds_required_attribution_links(self) -> None:
        candidate = normalize_unsplash_photo(
            {
                "id": "abc",
                "width": 3000,
                "height": 2000,
                "urls": {
                    "regular": "https://images.unsplash.com/preview",
                    "full": "https://images.unsplash.com/full",
                },
                "links": {"html": "https://unsplash.com/photos/abc"},
                "user": {
                    "name": "Annie Example",
                    "username": "annie",
                    "links": {"html": "https://unsplash.com/@annie"},
                },
            }
        )

        self.assertEqual(candidate.provider, "unsplash")
        self.assertIn("utm_source=ai_documentary_os", candidate.source_url)
        self.assertIn("utm_source=ai_documentary_os", candidate.creator_url)
        self.assertEqual(candidate.attribution, "Photo by Annie Example on Unsplash")
        self.assertEqual(candidate.license_name, "Unsplash License")

    def test_wikimedia_normalizer_cleans_creator_and_license_html(self) -> None:
        candidate = normalize_wikimedia_photo(
            {
                "pageid": 123,
                "title": "File:Historic map.jpg",
                "imageinfo": [
                    {
                        "mime": "image/jpeg",
                        "url": "https://upload.wikimedia.org/original.jpg",
                        "thumburl": "https://upload.wikimedia.org/thumb.jpg",
                        "width": 2000,
                        "height": 1400,
                        "extmetadata": {
                            "Artist": {"value": "<b>Jane Cartographer</b>"},
                            "LicenseShortName": {"value": "CC BY-SA 4.0"},
                            "LicenseUrl": {
                                "value": "https://creativecommons.org/licenses/by-sa/4.0/"
                            },
                        },
                    }
                ],
            }
        )

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.creator, "Jane Cartographer")
        self.assertEqual(candidate.license_name, "CC BY-SA 4.0")
        self.assertTrue(candidate.source_url.startswith("https://commons.wikimedia.org/wiki/"))
        self.assertEqual(clean_html("<i>Hello</i> &amp; goodbye"), "Hello & goodbye")

    def test_nasa_normalizer_records_usage_guidelines_without_manifest(self) -> None:
        candidate = normalize_nasa(
            {
                "data": [
                    {
                        "nasa_id": "NASA-1",
                        "title": "Earth from orbit",
                        "center": "NASA Johnson",
                    }
                ],
                "links": [{"href": "https://images-assets.nasa.gov/preview.jpg"}],
            },
            "photo",
        )

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.provider, "nasa")
        self.assertEqual(candidate.creator, "NASA Johnson")
        self.assertEqual(candidate.preview_url, "https://images-assets.nasa.gov/preview.jpg")
        self.assertEqual(candidate.license_name, "NASA Media Usage Guidelines")

    def test_provider_registry_capabilities_and_key_status(self) -> None:
        self.assertEqual(PROVIDERS["pixabay"].media_types, ("video", "photo"))
        self.assertEqual(PROVIDERS["unsplash"].media_types, ("photo",))
        self.assertTrue(PROVIDERS["wikimedia"].configured)
        self.assertTrue(PROVIDERS["nasa"].configured)

        with patch.dict(os.environ, {"PIXABAY_API_KEY": "saved-key"}, clear=False):
            self.assertTrue(PROVIDERS["pixabay"].configured)

        with patch.dict(os.environ, {"PIXABAY_API_KEY": ""}, clear=False):
            self.assertFalse(PROVIDERS["pixabay"].configured)

    def test_manual_search_urls_are_provider_specific(self) -> None:
        self.assertEqual(
            public_search_url("pixabay", "compound growth", "video"),
            "https://pixabay.com/videos/search/compound%20growth/",
        )
        self.assertIn(
            "commons.wikimedia.org",
            public_search_url("wikimedia", "historic map", "photo"),
        )
        self.assertIn(
            "images.nasa.gov/search",
            public_search_url("nasa", "moon landing", "video"),
        )

    def test_asset_candidate_accepts_rights_metadata(self) -> None:
        candidate = AssetCandidate(
            provider="wikimedia",
            provider_asset_id="123",
            media_type="photo",
            source_url="https://example.com/source",
            preview_url="https://example.com/preview.jpg",
            download_url="https://example.com/file.jpg",
            creator="Creator",
            creator_url="https://example.com/creator",
            license_name="CC BY 4.0",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            attribution="Creator · CC BY 4.0",
        )
        self.assertEqual(candidate.license_name, "CC BY 4.0")

    def test_search_plan_turns_abstract_finance_terms_into_visual_queries(self) -> None:
        plan = build_search_plan(
            "calendar time lapse investment growth",
            ["calendar time lapse", "investment growth", "stock chart"],
            "Calendar pages and long-term market growth",
            "video",
            max_queries=2,
        )

        self.assertEqual(
            plan,
            ["stock market chart animation", "calendar time lapse"],
        )

    def test_pixabay_ranking_prefers_anchor_matches_over_generic_timelapses(self) -> None:
        hits = [
            {"id": 1, "tags": "clouds, sky, time lapse", "likes": 1000},
            {"id": 2, "tags": "calendar, date, time lapse", "likes": 10},
            {"id": 3, "tags": "calendar, pages, schedule", "likes": 5},
            {"id": 4, "tags": "calendar, clock, deadline", "likes": 1},
        ]

        ranked = rank_pixabay_hits(hits, "calendar time lapse")

        self.assertEqual([item["id"] for item in ranked], [2, 3, 4])

    def test_candidate_batches_are_interleaved_and_deduplicated(self) -> None:
        def candidate(asset_id: str) -> AssetCandidate:
            return AssetCandidate(
                provider="pixabay",
                provider_asset_id=asset_id,
                media_type="video",
                source_url=f"https://example.com/{asset_id}",
                preview_url=f"https://example.com/{asset_id}.jpg",
                download_url=f"https://example.com/{asset_id}.mp4",
            )

        merged = merge_candidate_batches(
            [
                [candidate("chart-1"), candidate("shared")],
                [candidate("calendar-1"), candidate("shared")],
            ],
            4,
        )

        self.assertEqual(
            [item.provider_asset_id for item in merged],
            ["chart-1", "calendar-1", "shared"],
        )


if __name__ == "__main__":
    unittest.main()
