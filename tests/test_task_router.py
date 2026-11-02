from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from agents.task_router import AgentTaskRouter
from agents.event_ledger import EventLedger


class TaskRouterTests(unittest.TestCase):
    def test_discovery_exposes_identities_and_descriptive_actions_only(self):
        discovered = AgentTaskRouter.discover()
        self.assertEqual(set(discovered), {"moncappytime", "dolly", "robin", "betty",
                                           "richardfeynman", "alanwatts", "fultonjsheen"})
        self.assertIn("review", discovered["betty"])
        self.assertNotIn("model", str(discovered).lower())

    def test_router_uses_durable_queue_and_lease_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = EventLedger(Path(td) / "events.sqlite3")
            ledger.bootstrap("2026-11-01T00:00:00Z")
            router = AgentTaskRouter(ledger, clock=lambda: datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc))
            self.assertIsNone(router.claim("betty"))
            self.assertTrue(ledger.verify_audit())


if __name__ == "__main__":
    unittest.main()
