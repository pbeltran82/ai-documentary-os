from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models import Asset, Project, Scene
from app.services import production_pipeline


class ProductionPipelineTests(unittest.TestCase):
    def project(self) -> Project:
        project = Project(id=7, title="Atlas Test", topic="History", target_minutes=1)
        first = Scene(
            id=1, project_id=7, scene_number=1, start_seconds=0, end_seconds=5,
            duration_seconds=5, narration="Why did this happen?", visual_intent="Evidence",
            search_keywords=[], animation_plan={}, asset_status="missing",
        )
        second = Scene(
            id=2, project_id=7, scene_number=2, start_seconds=5, end_seconds=10,
            duration_seconds=5, narration="The record gives an answer.", visual_intent="Archive",
            search_keywords=[], animation_plan={"version": "manual"}, asset_status="ready",
        )
        second.selected_asset = Asset(
            scene_id=2, provider="generated", provider_asset_id="scene-2", media_type="video",
            source_url="local://scene-2", preview_url="/preview.jpg", download_url="/scene.mp4",
            local_path="project-0007/assets/scene.mp4",
        )
        project.scenes = [first, second]
        return project

    def test_status_reports_ordered_blockers_and_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(production_pipeline, "project_directory", return_value=Path(directory)), \
             patch.object(production_pipeline, "load_voiceover", return_value=None):
            status = production_pipeline.build_pipeline_status(self.project())
        self.assertEqual(status["visual_coverage_percent"], 50)
        self.assertEqual(status["missing_direction_scene_ids"], [1])
        self.assertEqual(status["missing_visual_scene_ids"], [1])
        self.assertIn("Prepare direction", status["next_action"])

    def test_prepare_fills_only_missing_direction(self) -> None:
        project = self.project()
        original = project.scenes[1].animation_plan
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(production_pipeline, "project_directory", return_value=Path(directory)), \
             patch.object(production_pipeline, "load_voiceover", return_value=None):
            status = production_pipeline.prepare_project_direction(project)
        self.assertEqual(status["prepared_scene_ids"], [1])
        self.assertEqual(project.scenes[0].animation_plan["preset_id"], "investigate")
        self.assertIs(project.scenes[1].animation_plan, original)


if __name__ == "__main__":
    unittest.main()
