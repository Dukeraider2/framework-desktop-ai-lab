"""Dispatch authorization for events retrieved by the trusted GitHub poller.

This module accepts only a sealed record constructed from the authenticated,
repository-pinned GitHub provider response. It does not accept model arguments,
webhook bodies, or a caller-supplied authentication boolean.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


REPOSITORY = "Dukeraider2/framework-desktop-ai-lab"
_AGENT_ID = re.compile(r"^[a-z][a-z0-9]{1,31}$")
_ACTION = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_COMMENT_ID = re.compile(r"^[1-9][0-9]{0,24}$")
_PROVIDER_SEAL = object()
_DIRECTIVES = (
    re.compile(r"(?m)^/agent run (?P<agent>[a-z][a-z0-9]{1,31}) (?P<action>[a-z][a-z0-9_-]{0,31})$"),
    re.compile(r"(?m)^/agent review$"),
    re.compile(r"(?m)^/agent challenge (?P<agent>[a-z][a-z0-9]{1,31})$"),
)

# These are task categories, not Hermes tools or permission grants. Every action
# still requires an allowlisted GitHub actor and an issue label assigning the task.
AGENT_ACTIONS: dict[str, frozenset[str]] = {
    "moncappytime": frozenset({"coordinate", "summarize", "triage", "review", "challenge"}),
    "dolly": frozenset({"onboard", "facilitate", "review", "challenge"}),
    "robin": frozenset({"ideate", "prototype", "review", "challenge"}),
    "betty": frozenset({"inspect", "review", "challenge"}),
    "richardfeynman": frozenset({"inspect", "test", "review", "challenge"}),
    "alanwatts": frozenset({"analyze", "review", "challenge"}),
    "fultonjsheen": frozenset({"governance_review", "review", "challenge"}),
}


@dataclass(frozen=True, init=False)
class NormalizedGitHubComment:
    comment_id: str
    repository: str
    issue_number: int
    actor: str
    body: str
    issue_labels: frozenset[str]

    def __init__(self, *, comment_id: str, repository: str, issue_number: int,
                 actor: str, body: str, issue_labels: frozenset[str], _seal: object):
        if _seal is not _PROVIDER_SEAL:
            raise TypeError("GitHub comments must be constructed by the trusted provider adapter")
        object.__setattr__(self, "comment_id", comment_id)
        object.__setattr__(self, "repository", repository)
        object.__setattr__(self, "issue_number", issue_number)
        object.__setattr__(self, "actor", actor)
        object.__setattr__(self, "body", body)
        object.__setattr__(self, "issue_labels", issue_labels)


def _from_provider_records(comment: dict[str, Any], issue: dict[str, Any]) -> NormalizedGitHubComment:
    """Seal an event only after it came from the private AF_UNIX GitHub reader."""
    if not isinstance(comment, dict) or not isinstance(issue, dict):
        raise ValueError("provider event shape is invalid")
    number = comment.get("issue_number")
    labels = issue.get("labels")
    if (not isinstance(number, int) or isinstance(number, bool) or issue.get("number") != number
            or not isinstance(labels, list) or any(not isinstance(label, str) for label in labels)):
        raise ValueError("provider issue assignment is invalid")
    return NormalizedGitHubComment(
        comment_id=str(comment.get("id", "")), repository=REPOSITORY,
        issue_number=number, actor=str(comment.get("actor", "")),
        body=comment.get("body") if isinstance(comment.get("body"), str) else "",
        issue_labels=frozenset(labels), _seal=_PROVIDER_SEAL,
    )


@dataclass(frozen=True)
class DispatchDecision:
    allowed: bool
    agent_id: str | None
    action: str | None
    issue_number: int | None
    reason: str
    event_id: str | None = None


def _directive(body: str) -> tuple[str, str] | None:
    matches: list[tuple[str, str]] = []
    for index, pattern in enumerate(_DIRECTIVES):
        for match in pattern.finditer(body):
            if index == 0:
                matches.append((match.group("agent"), match.group("action")))
            elif index == 1:
                matches.append(("betty", "review"))
            else:
                matches.append((match.group("agent"), "challenge"))
    return matches[0] if len(matches) == 1 else None


def authorize_comment(event: NormalizedGitHubComment, *, authorized_actors: frozenset[str],
                      allowed_actions: dict[str, frozenset[str]] | None = None) -> DispatchDecision:
    def deny(reason: str) -> DispatchDecision:
        comment_id = getattr(event, "comment_id", "")
        return DispatchDecision(False, None, None, None, reason,
                                f"github-comment:{comment_id}" if isinstance(comment_id, str) else None)

    if type(event) is not NormalizedGitHubComment:
        return DispatchDecision(False, None, None, None, "untrusted_event_type")
    if event.repository != REPOSITORY:
        return deny("repository_out_of_scope")
    if not _COMMENT_ID.fullmatch(event.comment_id):
        return deny("invalid_comment_id")
    if not isinstance(event.issue_number, int) or isinstance(event.issue_number, bool) or event.issue_number < 1:
        return deny("invalid_issue_number")
    if not isinstance(event.actor, str) or event.actor not in authorized_actors:
        return deny("unauthorized_actor")
    if not isinstance(event.body, str) or len(event.body.encode("utf-8", errors="replace")) > 32_768:
        return deny("invalid_body")
    directive = _directive(event.body)
    if directive is None:
        return deny("missing_or_ambiguous_directive")
    agent_id, action = directive
    actions = allowed_actions if allowed_actions is not None else AGENT_ACTIONS
    if not _AGENT_ID.fullmatch(agent_id) or not _ACTION.fullmatch(action):
        return deny("invalid_directive")
    if agent_id not in actions:
        return deny("unknown_agent")
    if action not in actions[agent_id]:
        return deny("action_not_authorized_for_agent")
    # An explicit label assigns this issue to the requested agent. A mention or
    # comment directive without the independently maintained assignment label is
    # only a notification and cannot enqueue work.
    if f"agent:{agent_id}" not in event.issue_labels:
        return deny("agent_not_assigned_to_issue")
    if action in {"review", "challenge"}:
        implementers = [label.removeprefix("implementer:") for label in event.issue_labels
                        if label.startswith("implementer:")]
        if len(implementers) != 1 or not _AGENT_ID.fullmatch(implementers[0]):
            return deny("implementer_assignment_missing_or_ambiguous")
        from agents.review_policy import route_review
        review_route = route_review(implementer=implementers[0], action=action,
                                    requested_reviewer=agent_id)
        if not review_route.allowed:
            return deny(review_route.reason)
    return DispatchDecision(True, agent_id, action, event.issue_number, "authorized",
                            f"github-comment:{event.comment_id}")
