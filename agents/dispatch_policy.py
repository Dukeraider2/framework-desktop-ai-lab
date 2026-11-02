"""Fail-closed authorization policy for normalized GitHub agent directives.

This module does not listen for GitHub events or execute tasks. A future trusted
event adapter must verify the delivery (or fetch it over the authenticated
read-only provider), then pass normalized fields here. Mentions alone never
authorize dispatch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


REPOSITORY = "Dukeraider2/framework-desktop-ai-lab"
_AGENT_ID = re.compile(r"^[a-z][a-z0-9]{1,31}$")
_ACTION = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_DIRECTIVE = re.compile(
    r"(?m)^/agent run (?P<agent>[a-z][a-z0-9]{1,31}) (?P<action>[a-z][a-z0-9_-]{0,31})$"
)


@dataclass(frozen=True)
class NormalizedGitHubComment:
    delivery_id: str
    repository: str
    issue_number: int
    actor: str
    body: str
    source_verified: bool


@dataclass(frozen=True)
class DispatchDecision:
    allowed: bool
    agent_id: str | None
    action: str | None
    issue_number: int | None
    reason: str


def authorize_comment(
    event: NormalizedGitHubComment,
    *,
    authorized_actors: frozenset[str],
    allowed_actions: dict[str, frozenset[str]],
) -> DispatchDecision:
    """Authorize only one exact directive on an authenticated in-scope comment.

    `source_verified` is trusted only when the caller is a private adapter
    that sets it after authenticated GitHub retrieval. Do not deserialize it from
    model output or accept the boolean from an MCP argument.
    """
    def deny(reason: str) -> DispatchDecision:
        return DispatchDecision(False, None, None, None, reason)

    if event.source_verified is not True:
        return deny("unverified_source")
    if event.repository != REPOSITORY:
        return deny("repository_out_of_scope")
    if not isinstance(event.delivery_id, str) or not re.fullmatch(r"[A-Za-z0-9-]{8,128}", event.delivery_id):
        return deny("invalid_delivery_id")
    if not isinstance(event.issue_number, int) or isinstance(event.issue_number, bool) or event.issue_number < 1:
        return deny("invalid_issue_number")
    if not isinstance(event.actor, str) or event.actor not in authorized_actors:
        return deny("unauthorized_actor")
    if not isinstance(event.body, str) or len(event.body.encode("utf-8", errors="replace")) > 32_768:
        return deny("invalid_body")

    directives = list(_DIRECTIVE.finditer(event.body))
    if len(directives) != 1:
        return deny("missing_or_ambiguous_directive")
    match = directives[0]
    agent_id, action = match.group("agent"), match.group("action")
    if not _AGENT_ID.fullmatch(agent_id) or not _ACTION.fullmatch(action):
        return deny("invalid_directive")
    if agent_id not in allowed_actions:
        return deny("unknown_agent")
    if action not in allowed_actions[agent_id]:
        return deny("action_not_authorized_for_agent")
    return DispatchDecision(True, agent_id, action, event.issue_number, "authorized")
