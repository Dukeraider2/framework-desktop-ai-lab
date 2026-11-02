"""Independent-review assignment policy, separate from identity and model choice."""

from __future__ import annotations

from dataclasses import dataclass

from agents.dispatch_policy import AGENT_ACTIONS


DEFAULT_QA_REVIEWER = "betty"


@dataclass(frozen=True)
class ReviewRoute:
    reviewer: str | None
    implementer: str
    action: str
    allowed: bool
    reason: str


def route_review(*, implementer: str, action: str, requested_reviewer: str | None = None) -> ReviewRoute:
    if implementer not in AGENT_ACTIONS:
        return ReviewRoute(None, implementer, action, False, "unknown_implementer")
    if action not in {"review", "challenge"}:
        return ReviewRoute(None, implementer, action, False, "unsupported_review_action")
    reviewer = requested_reviewer or DEFAULT_QA_REVIEWER
    if reviewer not in AGENT_ACTIONS or action not in AGENT_ACTIONS[reviewer]:
        return ReviewRoute(reviewer, implementer, action, False, "reviewer_action_not_authorized")
    if reviewer == implementer:
        return ReviewRoute(reviewer, implementer, action, False, "self_review_forbidden")
    return ReviewRoute(reviewer, implementer, action, True, "independent_reviewer_assigned")
