from __future__ import annotations

import unittest

from app.models import Asset, Project, Scene
from app.services import timeline_subject_motion as subject


class SubjectAwareStillMotionTests(unittest.TestCase):
    def scene(
        self,
        *,
        narration: str,
        visual_intent: str,
        width: int,
        height: int,
        duration: float = 5,
        scene_number: int = 1,
    ) -> Scene:
        project = Project(
            id=1,
            title="Still Motion",
            topic="Documentary",
            target_minutes=1,
            audience="General audience",
            tone="Cinematic",
            visual_style="Documentary",
            status="timeline",
        )
        scene = Scene(
            id=scene_number,
            project_id=1,
            scene_number=scene_number,
            start_seconds=0,
            end_seconds=duration,
            duration_seconds=duration,
            narration=narration,
            visual_intent=visual_intent,
            search_keywords=[],
            preferred_asset_type="stock_image",
            asset_status="ready",
        )
        scene.selected_asset = Asset(
            id=scene_number,
            scene_id=scene_number,
            provider="unsplash",
            provider_asset_id=f"still-{scene_number}",
            media_type="photo",
            source_url="https://example.com/source",
            preview_url="https://example.com/preview.jpg",
            download_url="https://example.com/image.jpg",
            width=width,
            height=height,
            license_name="Test",
        )
        scene.project = project
        return scene

    def test_human_subject_uses_upper_third_focus(self) -> None:
        direction = subject.direct_still(
            self.scene(
                narration="A worker checks the paycheck.",
                visual_intent="Portrait of a person reviewing finances",
                width=1200,
                height=1600,
            ),
            0,
        )
        self.assertEqual(direction.motion, "zoom_in")
        self.assertEqual(direction.composition_profile, "human_upper_third")
        self.assertLess(direction.focal_y, 0.45)
        self.assertIn("human subject", direction.reason.lower())

    def test_portrait_source_preserves_headroom(self) -> None:
        direction = subject.direct_still(
            self.scene(
                narration="A quiet financial decision.",
                visual_intent="Vertical editorial photograph",
                width=900,
                height=1600,
                scene_number=2,
            ),
            1,
        )
        self.assertEqual(direction.composition_profile, "portrait_safe")
        self.assertEqual(direction.motion, "zoom_in")
        self.assertLess(direction.focal_y, 0.45)
        self.assertGreater(direction.blur_sigma, 30)

    def test_wide_archival_source_receives_documentary_pan(self) -> None:
        direction = subject.direct_still(
            self.scene(
                narration="The factory expanded across the city.",
                visual_intent="Wide historic factory panorama",
                width=2600,
                height=1000,
                duration=6,
            ),
            0,
        )
        self.assertEqual(direction.motion, "pan_left")
        self.assertEqual(direction.composition_profile, "wide_documentary_pan")

    def test_readability_content_remains_static(self) -> None:
        direction = subject.direct_still(
            self.scene(
                narration="The balance appears on screen.",
                visual_intent="Banking app interface",
                width=1920,
                height=1080,
            ),
            0,
        )
        self.assertEqual(direction.motion, "static")
        self.assertEqual(direction.composition_profile, "readability_hold")

    def test_zoom_expression_anchors_to_focal_point(self) -> None:
        clip = {
            "motion_effect": "zoom_in",
            "focal_point": {"x": 0.42, "y": 0.34},
        }
        zoom, x_position, y_position = subject._zoom_parameters(clip, 150, 5)
        self.assertIn("0.065", zoom)
        self.assertIn("0.420", x_position)
        self.assertIn("0.340", y_position)


if __name__ == "__main__":
    unittest.main()
