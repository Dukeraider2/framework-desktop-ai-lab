from __future__ import annotations

import unittest

from agents.review_policy import route_review


class ReviewPolicyTests(unittest.TestCase):
    def test_betty_is_default_and_cannot_review_her_own_work(self):
        route = route_review(implementer="robin", action="review")
        self.assertTrue(route.allowed)
        self.assertEqual(route.reviewer, "betty")
        self.assertEqual(route_review(implementer="betty", action="review").reason,
                         "self_review_forbidden")

    def test_feynman_can_challenge_betty_but_not_himself(self):
        route = route_review(implementer="betty", action="challenge", requested_reviewer="richardfeynman")
        self.assertTrue(route.allowed)
        self.assertFalse(route_review(implementer="richardfeynman", action="challenge",
                                     requested_reviewer="richardfeynman").allowed)

    def test_moncapy_is_reviewable_by_another_agent(self):
        self.assertTrue(route_review(implementer="moncappytime", action="review", requested_reviewer="betty").allowed)

    def test_unknown_or_non_review_action_is_rejected(self):
        self.assertFalse(route_review(implementer="unknown", action="review").allowed)
        self.assertFalse(route_review(implementer="robin", action="merge").allowed)


if __name__ == "__main__":
    unittest.main()
