"""Trusted, read-only GitHub comment poller and durable local dispatcher.

The process has no GitHub credential. It reads only the authenticated provider's
AF_UNIX interface, stores authorized work in SQLite, and never launches workers
or writes to GitHub.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from agents.dispatch_policy import NormalizedGitHubComment, _from_provider_records, authorize_comment
from agents.event_ledger import EventLedger
from integrations.hermes_project_awareness.ipc import request as ipc_request


PROVIDER_SOCKET = "/run/hermes-github/provider.sock"
LEDGER_PATH = Path("/var/lib/hermes-agent-dispatch/events.sqlite3")
ACTORS_PATH = Path("/etc/hermes-agent-dispatch/authorized-github-actors")
POLL_SECONDS = 60
MAX_BATCH_PAGES = 1000
_LOG = logging.getLogger("frameworklab.github_dispatch")


class PollerError(RuntimeError):
    pass


def _utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise PollerError("GitHub timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PollerError("GitHub timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise PollerError("GitHub timestamp lacks a timezone")
    return parsed.astimezone(timezone.utc)


def _stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_authorized_actors(path: Path = ACTORS_PATH) -> frozenset[str]:
    try:
        metadata = path.lstat()
        if (not path.is_file() or path.is_symlink() or metadata.st_uid != 0
                or metadata.st_size > 16_384 or metadata.st_mode & 0o137
                or not metadata.st_mode & 0o040):
            raise PollerError("authorized actor list ownership or permissions are unsafe")
        actors = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                  if line.strip() and not line.lstrip().startswith("#")}
    except OSError as exc:
        raise PollerError("authorized actor list is unavailable") from exc
    if any(not re.fullmatch(r"[A-Za-z0-9-]{1,39}", actor) for actor in actors):
        raise PollerError("authorized actor list contains an invalid login")
    return frozenset(actors)


def _provider_fetch(operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
    response = ipc_request(PROVIDER_SOCKET, {"request_id": uuid.uuid4().hex,
                                             "operation": operation, "arguments": arguments})
    result = response.get("result") if isinstance(response, dict) else None
    if (not isinstance(result, dict) or result.get("provider_id") != "github"
            or result.get("status") not in {"ok", "partial"}
            or not isinstance(result.get("records"), list)):
        raise PollerError("trusted GitHub provider returned an invalid response")
    return result


class GitHubEventPoller:
    def __init__(self, ledger: EventLedger, *, authorized_actors: frozenset[str],
                 fetch: Callable[[str, dict[str, Any]], dict[str, Any]] = _provider_fetch,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.ledger = ledger
        self.authorized_actors = authorized_actors
        self.fetch = fetch
        self.clock = clock

    def run_once(self) -> dict[str, int]:
        cursor = self.ledger.cursor()
        if cursor is None:
            since = _stamp(self.clock())
            self.ledger.bootstrap(since)
            cursor = (since, 1)
        since, page = cursor
        if page > MAX_BATCH_PAGES:
            raise PollerError("event pagination exceeded the configured safety limit")
        result = self.fetch("issue_comments", {"since": since, "page": page})
        comments = result["records"]
        decisions = []
        hashes = []
        for comment in comments:
            if not isinstance(comment, dict) or not isinstance(comment.get("id"), int) or isinstance(comment.get("id"), bool):
                raise PollerError("GitHub comment record is invalid")
            issue_result = self.fetch("issue", {"number": comment.get("issue_number")})
            issue_records = issue_result.get("records") if isinstance(issue_result, dict) else None
            if not isinstance(issue_records, list) or len(issue_records) != 1:
                raise PollerError("GitHub issue assignment could not be verified")
            sealed = _from_provider_records(comment, issue_records[0])
            decisions.append(authorize_comment(sealed, authorized_actors=self.authorized_actors))
            body = comment.get("body")
            if not isinstance(body, str):
                raise PollerError("GitHub comment body is invalid")
            hashes.append(hashlib.sha256(body.encode("utf-8")).hexdigest())

        has_more = result.get("status") == "partial"
        if has_more:
            next_since, next_page = since, page + 1
        elif comments:
            max_updated = max(_utc(row.get("updated_at") or row.get("created_at")) for row in comments)
            candidate = max_updated - timedelta(seconds=60)
            next_since = _stamp(max(_utc(since), candidate))
            next_page = 1
        else:
            next_since, next_page = since, 1
        counts = self.ledger.process_page(
            comments, decisions, body_hashes=hashes, next_since=next_since,
            next_page=next_page, observed_at=_stamp(self.clock()),
        )
        _LOG.info("event=poll_complete new=%d duplicate=%d authorized=%d denied=%d page=%d more=%s",
                  counts["new"], counts["duplicates"], counts["authorized"], counts["denied"], page, has_more)
        return counts


def run_forever() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ledger = EventLedger(LEDGER_PATH)
    poller = GitHubEventPoller(ledger, authorized_actors=load_authorized_actors())
    while True:
        try:
            poller.run_once()
        except Exception as exc:
            # Cursor changes occur only in the same transaction as durable events;
            # provider/audit failures are retried without accepting partial input.
            _LOG.error("event=poll_failed error=%s", type(exc).__name__)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run_forever()
