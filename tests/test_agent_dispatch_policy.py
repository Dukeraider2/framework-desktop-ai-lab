from __future__ import annotations

import unittest

from agents.dispatch_policy import NormalizedGitHubComment, _from_provider_records, authorize_comment


def trusted(body="/agent run betty review", *, comment_id=12345678, labels=None):
    comment = {"id": comment_id, "issue_number": 5, "actor": "Dukeraider2", "body": body}
    issue = {"number": 5, "labels": labels or ["agent:betty", "implementer:robin"]}
    return _from_provider_records(comment, issue)


class AgentDispatchPolicyTests(unittest.TestCase):
    def test_model_output_cannot_construct_a_trusted_event(self):
        with self.assertRaises(TypeError):
            NormalizedGitHubComment(comment_id="12345678", repository="Dukeraider2/framework-desktop-ai-lab",
                                    issue_number=5, actor="Dukeraider2", body="/agent run betty review",
                                    issue_labels=frozenset({"agent:betty"}), _seal=True)
        decision = authorize_comment({"source_verified": True, "body": "/agent run betty review"},
                                     authorized_actors=frozenset({"Dukeraider2"}))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "untrusted_event_type")

    def test_authenticated_provider_event_requires_actor_and_assignment(self):
        event = trusted()
        decision = authorize_comment(event, authorized_actors=frozenset({"Dukeraider2"}))
        self.assertTrue(decision.allowed)
        self.assertEqual((decision.agent_id, decision.action, decision.issue_number), ("betty", "review", 5))
        self.assertEqual(decision.event_id, "github-comment:12345678")

    def test_plain_mention_is_notification_only(self):
        event = trusted("@Betty please review this")
        decision = authorize_comment(event, authorized_actors=frozenset({"Dukeraider2"}))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "missing_or_ambiguous_directive")

    def test_default_review_routes_to_betty_and_feynman_can_challenge(self):
        review = trusted("/agent review", labels=["agent:betty", "implementer:moncappytime"])
        review_decision = authorize_comment(review, authorized_actors=frozenset({"Dukeraider2"}))
        self.assertTrue(review_decision.allowed)
        self.assertEqual(review_decision.agent_id, "betty")
        challenge = trusted("/agent challenge richardfeynman",
                            labels=["agent:richardfeynman", "implementer:betty"])
        challenge_decision = authorize_comment(challenge, authorized_actors=frozenset({"Dukeraider2"}))
        self.assertTrue(challenge_decision.allowed)
        self.assertEqual(challenge_decision.action, "challenge")

    def test_implementer_cannot_review_own_work_and_missing_assignment_denied(self):
        self_review = trusted("/agent run betty review", labels=["agent:betty", "implementer:betty"])
        self.assertEqual(authorize_comment(self_review, authorized_actors=frozenset({"Dukeraider2"})).reason,
                         "self_review_forbidden")
        unassigned = trusted("/agent run betty review", labels=["implementer:robin"])
        self.assertEqual(authorize_comment(unassigned, authorized_actors=frozenset({"Dukeraider2"})).reason,
                         "agent_not_assigned_to_issue")

    def test_fail_closed_actor_repo_directive_and_capability_rules(self):
        cases = [
            (trusted(), frozenset({"another-owner"}), "unauthorized_actor"),
            (trusted("/agent run unknown review"), frozenset({"Dukeraider2"}), "unknown_agent"),
            (trusted("/agent run betty merge"), frozenset({"Dukeraider2"}), "action_not_authorized_for_agent"),
            (trusted("/agent run betty review\n/agent run dolly onboard"), frozenset({"Dukeraider2"}), "missing_or_ambiguous_directive"),
        ]
        for event, actors, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(authorize_comment(event, authorized_actors=actors).reason, reason)

    def test_provider_factory_rejects_issue_number_mismatch_and_bad_labels(self):
        comment = {"id": 12345678, "issue_number": 5, "actor": "Dukeraider2", "body": "/agent review"}
        with self.assertRaises(ValueError):
            _from_provider_records(comment, {"number": 6, "labels": ["agent:betty"]})


if __name__ == "__main__":
    unittest.main()
