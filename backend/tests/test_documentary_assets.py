from __future__ import annotations

import unittest

from PIL import Image, ImageChops, ImageDraw

from app.services import documentary_assets


class DocumentaryAssetTests(unittest.TestCase):
    def render(self, asset_id: str, *, state: str = "default") -> Image.Image:
        image = Image.new("RGB", (420, 320), (8, 15, 25))
        documentary_assets.render_asset(
            ImageDraw.Draw(image),
            asset_id,
            (210, 160),
            scale=1.0,
            accent=(67, 185, 166),
            state=state,
        )
        return image

    def test_catalog_exposes_recurring_documentary_objects(self) -> None:
        catalog = documentary_assets.asset_catalog()
        self.assertEqual(
            {item["asset_id"] for item in catalog},
            {"wallet", "payment_card", "home", "groceries", "calendar", "bank", "paycheck", "phone"},
        )

    def test_every_registered_asset_renders(self) -> None:
        for asset in documentary_assets.asset_catalog():
            with self.subTest(asset=asset["asset_id"]):
                image = self.render(str(asset["asset_id"]))
                self.assertIsNotNone(image.getbbox())

    def test_semantic_states_are_visually_distinct(self) -> None:
        for asset_id, state in (("wallet", "empty"), ("payment_card", "declined"), ("paycheck", "received"), ("phone", "alert")):
            with self.subTest(asset=asset_id, state=state):
                default = self.render(asset_id)
                changed = self.render(asset_id, state=state)
                self.assertIsNotNone(ImageChops.difference(default, changed).getbbox())

    def test_unknown_assets_fail_loudly(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown documentary asset"):
            self.render("mystery-object")


if __name__ == "__main__":
    unittest.main()
