from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.services.database_safety import assert_destructive_database_is_safe
from app.services.hyperframes_renderer import supports
from app.services.visuals.diversity_guard import (
    VisualDiversityGuard,
    canonical_url,
    choose_unused_exact_template,
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
        self.assertFalse(supports("finance_motion", "compound_growth"))


if __name__ == "__main__":
    unittest.main()
