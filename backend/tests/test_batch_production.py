from __future__ import annotations

import inspect
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.routers import finance_motion
from app.services import manifest_events


class BatchProductionTests(unittest.TestCase):
    def session(self) -> MagicMock:
        session = MagicMock(spec=Session)
        session.info = {}
        return session

    def test_batch_transaction_defers_manifest_refresh(self) -> None:
        session = self.session()
        session.info[manifest_events.MANIFEST_PROJECT_IDS] = {7}
        manifest_events.defer_manifest_refresh(session)

        with patch.object(manifest_events, "refresh_project_manifests") as refresh:
            manifest_events.refresh_timeline_manifests(session)

        refresh.assert_not_called()
        self.assertNotIn(manifest_events.MANIFEST_PROJECT_IDS, session.info)
        self.assertNotIn(manifest_events.DEFER_MANIFEST_REFRESH, session.info)

    def test_normal_transaction_still_refreshes_immediately(self) -> None:
        session = self.session()
        bind = object()
        session.get_bind.return_value = bind
        session.info[manifest_events.MANIFEST_PROJECT_IDS] = {9}

        with patch.object(manifest_events, "refresh_project_manifests") as refresh:
            manifest_events.refresh_timeline_manifests(session)

        refresh.assert_called_once_with(bind, {9})

    def test_rollback_clears_batch_flags(self) -> None:
        session = self.session()
        session.info[manifest_events.MANIFEST_PROJECT_IDS] = {4}
        session.info[manifest_events.DEFER_MANIFEST_REFRESH] = True
        manifest_events.clear_manifest_project_ids(session)
        self.assertEqual(session.info, {})

    def test_generation_endpoint_exposes_deferred_manifest_switch(self) -> None:
        signature = inspect.signature(finance_motion.generate_exact_visual)
        self.assertIn("defer_manifest", signature.parameters)
        self.assertTrue(callable(finance_motion.finalize_exact_visual_batch))


if __name__ == "__main__":
    unittest.main()
