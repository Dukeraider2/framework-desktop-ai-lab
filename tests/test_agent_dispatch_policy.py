from __future__ import annotations

import unittest

from agents.dispatch_policy import NormalizedGitHubComment, authorize_comment


class AgentDispatchPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = {"betty": frozenset({"inspect", "review"}), "dolly": frozenset({"onboard"})}
        self.event = NormalizedGitHubComment(
            delivery_id="delivery-12345678",
            repository="Dukeraider2/framework-desktop-ai-lab",
            issue_number=5,
            actor="Dukeraider2",
            body="Please review this.\n/agent run betty review\n",
            source_verified=True,
        )

    def test_authorized_explicit_directive_is_bound_to_issue(self):
        result = authorize_comment(self.event, authorized_actors=frozenset({"Dukeraider2"}),
                                  allowed_actions=self.policy)
        self.assertTrue(result.allowed)
        self.assertEqual((result.agent_id, result.action, result.issue_number), ("betty", "review", 5))

    def test_plain_mention_does_not_authorize(self):
        event = self.event.__class__(**{**self.event.__dict__, "body": "@Betty please review this"})
        result = authorize_comment(event, authorized_actors=frozenset({"Dukeraider2"}),
                                  allowed_actions=self.policy)
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "missing_or_ambiguous_directive")

    def test_sender_source_scope_agent_and_action_fail_closed(self):
        authorized = frozenset({"Dukeraider2"})
        for changes, reason in [
            ({"source_verified": False}, "unverified_source"),
            ({"actor": "external-user"}, "unauthorized_actor"),
            ({"repository": "attacker/other"}, "repository_out_of_scope"),
            ({"body": "/agent run unknown review"}, "unknown_agent"),
            ({"body": "/agent run betty merge"}, "action_not_authorized_for_agent"),
            ({"body": "/agent run betty review\n/agent run dolly onboard"}, "missing_or_ambiguous_directive"),
        ]:
            event = self.event.__class__(**{**self.event.__dict__, **changes})
            result = authorize_comment(event, authorized_actors=authorized, allowed_actions=self.policy)
            self.assertFalse(result.allowed, changes)
            self.assertEqual(result.reason, reason)


if __name__ == "__main__":
    unittest.main()
