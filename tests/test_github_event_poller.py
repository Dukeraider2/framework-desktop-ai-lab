from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from agents.event_ledger import EventLedger
from agents.github_event_poller import GitHubEventPoller, PollerError


class FakeProvider:
    def __init__(self, comment, *, partial=False, fail_issue=False):
        self.comment = comment
        self.partial = partial
        self.fail_issue = fail_issue
        self.calls = []

    def __call__(self, operation, arguments):
        self.calls.append((operation, arguments))
        if operation == "issue_comments":
            return {"provider_id": "github", "status": "partial" if self.partial else "ok",
                    "records": [self.comment]}
        if operation == "issue":
            if self.fail_issue:
                raise PollerError("simulated provider failure")
            return {"provider_id": "github", "status": "ok", "records": [
                {"number": self.comment["issue_number"], "labels": ["agent:betty", "implementer:robin"]}]}
        raise AssertionError(operation)


class GitHubEventPollerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = EventLedger(Path(self.temp.name) / "events.db")
        self.now = datetime(2026, 11, 1, 12, 5, tzinfo=timezone.utc)
        self.comment = {"id": 987654321, "issue_number": 5, "actor": "Dukeraider2",
                        "body": "/agent review", "created_at": "2026-11-01T12:06:00Z",
                        "updated_at": "2026-11-01T12:06:00Z"}

    def tearDown(self):
        self.temp.cleanup()

    def test_authenticated_provider_comment_is_routed_and_cursor_commits(self):
        provider = FakeProvider(self.comment)
        poller = GitHubEventPoller(self.ledger, authorized_actors=frozenset({"Dukeraider2"}),
                                   fetch=provider, clock=lambda: self.now)
        result = poller.run_once()
        self.assertEqual(result["authorized"], 1)
        self.assertEqual(self.ledger.cursor(), ("2026-11-01T12:05:00Z", 1))
        self.assertEqual([call[0] for call in provider.calls], ["issue_comments", "issue"])

    def test_provider_failure_keeps_cursor_for_retry(self):
        provider = FakeProvider(self.comment, fail_issue=True)
        poller = GitHubEventPoller(self.ledger, authorized_actors=frozenset({"Dukeraider2"}),
                                   fetch=provider, clock=lambda: self.now)
        with self.assertRaises(PollerError):
            poller.run_once()
        self.assertEqual(self.ledger.cursor(), ("2026-11-01T12:05:00Z", 1))

    def test_page_cursor_advances_only_after_records_are_persisted(self):
        provider = FakeProvider(self.comment, partial=True)
        poller = GitHubEventPoller(self.ledger, authorized_actors=frozenset({"Dukeraider2"}),
                                   fetch=provider, clock=lambda: self.now)
        result = poller.run_once()
        self.assertEqual(result["new"], 1)
        self.assertEqual(self.ledger.cursor(), ("2026-11-01T12:05:00Z", 2))
        provider.fail_issue = True
        with self.assertRaises(PollerError):
            poller.run_once()
        self.assertEqual(self.ledger.cursor(), ("2026-11-01T12:05:00Z", 2))

    def test_unknown_actor_is_recorded_denied_and_never_queued(self):
        self.comment["actor"] = "random-account"
        provider = FakeProvider(self.comment)
        poller = GitHubEventPoller(self.ledger, authorized_actors=frozenset({"Dukeraider2"}),
                                   fetch=provider, clock=lambda: self.now)
        result = poller.run_once()
        self.assertEqual(result["denied"], 1)
        self.assertEqual(result["authorized"], 0)
        self.assertIsNone(self.ledger.claim_task("betty", claimed_at="2026-11-01T12:06:00Z"))


if __name__ == "__main__":
    unittest.main()
