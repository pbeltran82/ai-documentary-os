from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.services import media_library


class FakeResponse:
    def __init__(self, body: bytes, content_type: str, url: str) -> None:
        self.body = body
        self.offset = 0
        self.url = url
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        }

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        return None

    def read(self, size: int) -> bytes:
        chunk = self.body[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk

    def geturl(self) -> str:
        return self.url


class MediaLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_root = media_library.MEDIA_ROOT
        self.original_public_url = media_library.PUBLIC_BACKEND_URL
        media_library.MEDIA_ROOT = Path(self.temp_directory.name).resolve()
        media_library.PUBLIC_BACKEND_URL = "http://localhost:8000"

    def tearDown(self) -> None:
        media_library.MEDIA_ROOT = self.original_root
        media_library.PUBLIC_BACKEND_URL = self.original_public_url
        self.temp_directory.cleanup()

    def test_download_remote_file_writes_atomic_local_copy_and_hash(self) -> None:
        payload = b"fake mp4 bytes"
        response = FakeResponse(payload, "video/mp4", "https://cdn.example/video.mp4")

        with patch("app.services.media_library.urlopen", return_value=response):
            downloaded = media_library.download_remote_file(
                "https://cdn.example/video.mp4",
                media_library.MEDIA_ROOT / "project-0001" / "assets" / "scene-001",
                "video",
            )

        local_file = media_library.MEDIA_ROOT / downloaded.relative_path
        self.assertTrue(local_file.is_file())
        self.assertEqual(local_file.read_bytes(), payload)
        self.assertEqual(downloaded.content_type, "video/mp4")
        self.assertEqual(downloaded.size_bytes, len(payload))
        self.assertEqual(len(downloaded.checksum_sha256), 64)
        self.assertEqual(
            downloaded.public_url,
            "http://localhost:8000/media/project-0001/assets/scene-001.mp4",
        )

    def test_timeline_manifest_records_local_media_and_rights(self) -> None:
        asset = SimpleNamespace(
            provider="pixabay",
            provider_asset_id="42",
            media_type="video",
            local_path="project-0001/assets/scene-001-pixabay-42.mp4",
            local_preview_path="project-0001/assets/scene-001-pixabay-42-poster.jpg",
            content_type="video/mp4",
            file_size_bytes=1234,
            checksum_sha256="a" * 64,
            source_url="https://pixabay.com/videos/id-42/",
            remote_download_url="https://cdn.example/42.mp4",
            creator="Creator",
            creator_url="https://pixabay.com/users/creator-1/",
            license_name="Pixabay Content License",
            license_url="https://pixabay.com/service/license-summary/",
            attribution="Creator on Pixabay",
        )
        scene = SimpleNamespace(
            id=10,
            scene_number=1,
            start_seconds=0.0,
            end_seconds=5.0,
            duration_seconds=5.0,
            narration="Narration",
            visual_intent="Financial chart",
            asset_status="ready",
            selected_asset=asset,
        )
        project = SimpleNamespace(
            id=1,
            title="The Compound Blueprint",
            topic="Compound growth",
            status="timeline",
            target_minutes=8,
            visual_style="Cinematic documentary",
            scenes=[scene],
        )

        relative_path, public_url, manifest = media_library.write_timeline_manifest(project)

        manifest_path = media_library.MEDIA_ROOT / relative_path
        self.assertTrue(manifest_path.is_file())
        self.assertEqual(public_url, "http://localhost:8000/media/project-0001/timeline/manifest.json")
        self.assertEqual(manifest["summary"]["ready_scene_count"], 1)
        self.assertEqual(manifest["scenes"][0]["asset"]["local_path"], asset.local_path)
        self.assertEqual(manifest["scenes"][0]["asset"]["license_name"], asset.license_name)
        self.assertEqual(json.loads(manifest_path.read_text())["schema_version"], "0.1")

    def test_resolve_media_path_rejects_directory_traversal(self) -> None:
        self.assertIsNone(media_library.resolve_media_path("../../secret.txt"))


if __name__ == "__main__":
    unittest.main()
