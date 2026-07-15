from __future__ import annotations

import unittest

from app.routers.assets import normalize_photo, normalize_video, public_search_url


class AssetPlannerTests(unittest.TestCase):
    def test_video_normalizer_prefers_landscape_hd_file(self) -> None:
        candidate = normalize_video(
            {
                "id": 42,
                "url": "https://www.pexels.com/video/42/",
                "image": "https://images.example/preview.jpg",
                "duration": 8,
                "user": {
                    "name": "Creator",
                    "url": "https://www.pexels.com/@creator",
                },
                "video_files": [
                    {
                        "quality": "sd",
                        "file_type": "video/mp4",
                        "width": 640,
                        "height": 360,
                        "link": "https://files.example/sd.mp4",
                    },
                    {
                        "quality": "hd",
                        "file_type": "video/mp4",
                        "width": 1920,
                        "height": 1080,
                        "link": "https://files.example/hd.mp4",
                    },
                ],
            }
        )

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.download_url, "https://files.example/hd.mp4")
        self.assertEqual(candidate.width, 1920)
        self.assertEqual(candidate.media_type, "video")

    def test_photo_normalizer_preserves_creator_and_original_file(self) -> None:
        candidate = normalize_photo(
            {
                "id": 7,
                "url": "https://www.pexels.com/photo/7/",
                "width": 2400,
                "height": 1600,
                "photographer": "Photo Person",
                "photographer_url": "https://www.pexels.com/@photo-person",
                "src": {
                    "large": "https://images.example/preview.jpg",
                    "original": "https://images.example/original.jpg",
                },
            }
        )

        self.assertEqual(candidate.creator, "Photo Person")
        self.assertEqual(candidate.preview_url, "https://images.example/preview.jpg")
        self.assertEqual(candidate.download_url, "https://images.example/original.jpg")
        self.assertEqual(candidate.media_type, "photo")

    def test_public_search_url_handles_video_queries(self) -> None:
        self.assertEqual(
            public_search_url("compound growth", "video"),
            "https://www.pexels.com/search/videos/compound%20growth/",
        )


if __name__ == "__main__":
    unittest.main()
