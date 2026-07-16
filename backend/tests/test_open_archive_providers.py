from __future__ import annotations

import unittest

from app.services.assets import PROVIDERS
from app.services.assets import archive_hub, library_of_congress, met, openverse


class OpenArchiveProviderTests(unittest.TestCase):
    def test_openverse_accepts_commercial_license_and_rejects_unsafe_media(self) -> None:
        safe = openverse.normalize_photo(
            {
                "id": "safe-1",
                "title": "Empty leather wallet",
                "url": "https://images.example.com/wallet.jpg",
                "thumbnail": "https://images.example.com/wallet-thumb.jpg",
                "foreign_landing_url": "https://source.example.com/wallet",
                "creator": "Creator",
                "creator_url": "https://source.example.com/creator",
                "license": "by",
                "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "width": 1920,
                "height": 1080,
                "watermarked": False,
                "tags": [{"name": "empty wallet"}, {"name": "no money"}],
            }
        )
        self.assertIsNotNone(safe)
        assert safe is not None
        self.assertEqual(safe.provider, "openverse")
        self.assertIn("empty", safe.keywords)

        noncommercial = openverse.normalize_photo(
            {
                "id": "unsafe-1",
                "title": "Wallet",
                "url": "https://images.example.com/wallet.jpg",
                "thumbnail": "https://images.example.com/wallet-thumb.jpg",
                "foreign_landing_url": "https://source.example.com/wallet",
                "license": "by-nc",
                "width": 1920,
                "height": 1080,
            }
        )
        self.assertIsNone(noncommercial)

        watermarked = openverse.normalize_photo(
            {
                "id": "unsafe-2",
                "title": "Wallet",
                "url": "https://images.example.com/wallet.jpg",
                "thumbnail": "https://images.example.com/wallet-thumb.jpg",
                "foreign_landing_url": "https://source.example.com/wallet",
                "license": "cc0",
                "width": 1920,
                "height": 1080,
                "watermarked": True,
            }
        )
        self.assertIsNone(watermarked)

    def test_library_of_congress_requires_explicit_public_use_rights(self) -> None:
        base = {
            "id": "https://www.loc.gov/pictures/item/123/",
            "title": "Empty wallet during the Depression",
            "image_url": [
                "https://tile.loc.gov/storage-services/service/pnp/test/default.jpg",
                "https://tile.loc.gov/storage-services/service/pnp/test/default_1140px.jpg",
            ],
            "contributor_names": ["Historic Photographer"],
            "subject": ["Wallets", "Economic hardship"],
        }
        safe = library_of_congress.normalize_photo(
            {
                **base,
                "rights": ["No known restrictions on publication."],
            }
        )
        self.assertIsNotNone(safe)
        assert safe is not None
        self.assertEqual(safe.provider, "loc")
        self.assertEqual(safe.license_name, "No known restrictions on publication")

        restricted = library_of_congress.normalize_photo(
            {
                **base,
                "rights": ["Copyright held by the photographer. Permission required."],
            }
        )
        self.assertIsNone(restricted)

        unknown = library_of_congress.normalize_photo(base)
        self.assertIsNone(unknown)

    def test_met_requires_public_domain_and_primary_image(self) -> None:
        public_domain = met.normalize_photo(
            {
                "objectID": 1,
                "isPublicDomain": True,
                "primaryImage": "https://images.metmuseum.org/original.jpg",
                "primaryImageSmall": "https://images.metmuseum.org/preview.jpg",
                "objectURL": "https://www.metmuseum.org/art/collection/search/1",
                "title": "The Money Changer",
                "artistDisplayName": "Historic Artist",
                "objectName": "Painting",
                "classification": "Paintings",
                "tags": [{"term": "Money"}, {"term": "Commerce"}],
            }
        )
        self.assertIsNotNone(public_domain)
        assert public_domain is not None
        self.assertEqual(public_domain.license_name, "CC0 1.0")
        self.assertIn("money", public_domain.keywords)

        copyrighted = met.normalize_photo(
            {
                "objectID": 2,
                "isPublicDomain": False,
                "primaryImage": "https://images.metmuseum.org/original.jpg",
                "primaryImageSmall": "https://images.metmuseum.org/preview.jpg",
                "objectURL": "https://www.metmuseum.org/art/collection/search/2",
            }
        )
        self.assertIsNone(copyrighted)

        missing_image = met.normalize_photo(
            {
                "objectID": 3,
                "isPublicDomain": True,
                "objectURL": "https://www.metmuseum.org/art/collection/search/3",
            }
        )
        self.assertIsNone(missing_image)

    def test_archive_hub_preserves_origin_and_rejects_low_quality(self) -> None:
        candidate = openverse.normalize_photo(
            {
                "id": "safe-2",
                "title": "Historic bank counter",
                "url": "https://images.example.com/bank.jpg",
                "thumbnail": "https://images.example.com/bank-thumb.jpg",
                "foreign_landing_url": "https://source.example.com/bank",
                "creator": "Creator",
                "license": "cc0",
                "width": 1920,
                "height": 1080,
                "tags": [{"name": "historic bank"}],
            }
        )
        assert candidate is not None
        archived = archive_hub.archive_candidate(candidate, "Openverse")
        self.assertEqual(archived.provider, "wikimedia")
        self.assertTrue(archived.provider_asset_id.startswith("openverse:"))
        self.assertIn("Source collection: Openverse", archived.description)
        self.assertTrue(archive_hub.passes_hard_gate(archived))

        low_quality = candidate.model_copy(update={"width": 640, "height": 360})
        self.assertFalse(archive_hub.passes_hard_gate(low_quality))

    def test_registry_exposes_one_no_key_open_archives_provider(self) -> None:
        provider = PROVIDERS["wikimedia"]
        self.assertEqual(provider.label, "Open Archives")
        self.assertTrue(provider.configured)
        self.assertIn("Library of Congress", provider.setup_hint)
        self.assertNotIn("openverse", PROVIDERS)
        self.assertNotIn("loc", PROVIDERS)
        self.assertNotIn("met", PROVIDERS)


if __name__ == "__main__":
    unittest.main()
