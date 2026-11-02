from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from agents.dispatch_policy import _from_provider_records, authorize_comment
from agents.event_ledger import EventLedger, LedgerError


class EventLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "events.sqlite3"
        self.ledger = EventLedger(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def _batch(self):
        record = {"id": 12345678, "issue_number": 5, "actor": "Dukeraider2",
                  "body": "/agent review", "updated_at": "2026-11-01T12:00:00Z"}
        issue = {"number": 5, "labels": ["agent:betty", "implementer:robin"]}
        decision = authorize_comment(_from_provider_records(record, issue),
                                     authorized_actors=frozenset({"Dukeraider2"}))
        return [record], [decision], ["a" * 64]

    def test_durable_cursor_bootstrap_and_advance(self):
        self.assertIsNone(self.ledger.cursor())
        self.ledger.bootstrap("2026-11-01T00:00:00Z")
        self.assertEqual(self.ledger.cursor(), ("2026-11-01T00:00:00Z", 1))
        records, decisions, hashes = self._batch()
        result = self.ledger.process_page(records, decisions, body_hashes=hashes,
                                          next_since="2026-11-01T11:59:00Z", next_page=1,
                                          observed_at="2026-11-01T12:00:01Z")
        self.assertEqual(result, {"new": 1, "duplicates": 0, "authorized": 1, "denied": 0})
        self.assertEqual(self.ledger.cursor(), ("2026-11-01T11:59:00Z", 1))
        self.assertTrue(self.ledger.verify_audit())

    def test_replayed_delivery_is_rejected_and_not_routed_twice(self):
        self.ledger.bootstrap("2026-11-01T00:00:00Z")
        records, decisions, hashes = self._batch()
        args = dict(body_hashes=hashes, next_since="2026-11-01T11:59:00Z", next_page=1,
                    observed_at="2026-11-01T12:00:01Z")
        first = self.ledger.process_page(records, decisions, **args)
        replay = self.ledger.process_page(records, decisions, **args)
        self.assertEqual(first["authorized"], 1)
        self.assertEqual(replay, {"new": 0, "duplicates": 1, "authorized": 0, "denied": 0})
        claimed = self.ledger.claim_task("betty", claimed_at="2026-11-01T12:01:00Z")
        self.assertEqual(claimed["action"], "review")
        self.assertIsNone(self.ledger.claim_task("betty", claimed_at="2026-11-01T12:02:00Z"))
        self.ledger.finish_task(claimed["task_id"], agent_id="betty",
                                result_ref="https://github.com/Dukeraider2/framework-desktop-ai-lab/issues/5",
                                completed_at="2026-11-01T12:03:00Z")
        self.assertTrue(self.ledger.verify_audit())

    def test_expired_claim_is_recovered_and_wrong_agent_cannot_complete(self):
        self.ledger.bootstrap("2026-11-01T00:00:00Z")
        records, decisions, hashes = self._batch()
        self.ledger.process_page(records, decisions, body_hashes=hashes,
                                 next_since="2026-11-01T11:59:00Z", next_page=1,
                                 observed_at="2026-11-01T12:00:01Z")
        first = self.ledger.claim_task("betty", claimed_at="2026-11-01T12:00:00Z")
        with self.assertRaises(LedgerError):
            self.ledger.finish_task(first["task_id"], agent_id="robin",
                                    result_ref="https://github.com/Dukeraider2/framework-desktop-ai-lab/issues/5",
                                    completed_at="2026-11-01T12:01:00Z")
        recovered = self.ledger.claim_task("betty", claimed_at="2026-11-01T12:20:00Z",
                                           lease_expired_before="2026-11-01T12:05:00Z")
        self.assertEqual(recovered["task_id"], first["task_id"])
        self.assertTrue(self.ledger.verify_audit())

    def test_failed_durable_processing_does_not_advance_cursor(self):
        self.ledger.bootstrap("2026-11-01T00:00:00Z")
        records, _, hashes = self._batch()
        with self.assertRaises((AttributeError, LedgerError)):
            self.ledger.process_page(records, [object()], body_hashes=hashes,
                                     next_since="2026-11-01T12:00:00Z", next_page=1,
                                     observed_at="2026-11-01T12:00:01Z")
        self.assertEqual(self.ledger.cursor(), ("2026-11-01T00:00:00Z", 1))
        self.assertTrue(self.ledger.verify_audit())

    def test_audit_tampering_is_detected(self):
        self.ledger.bootstrap("2026-11-01T00:00:00Z")
        db = sqlite3.connect(self.path)
        try:
            db.execute("UPDATE audit SET payload='{}' WHERE sequence=1")
            db.commit()
        finally:
            db.close()
        self.assertFalse(self.ledger.verify_audit())

    def test_symlink_database_is_rejected(self):
        link = Path(self.temp.name) / "link.sqlite3"
        link.symlink_to(self.path)
        with self.assertRaises((LedgerError, OSError)):
            EventLedger(link)


if __name__ == "__main__":
    unittest.main()
