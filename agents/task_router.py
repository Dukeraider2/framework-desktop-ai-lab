"""Local task-queue interface for a future per-agent sandbox launcher.

This router only claims durable tasks. It intentionally does not launch Hermes
profiles, choose models, mount host resources, or post GitHub responses.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from agents.dispatch_policy import AGENT_ACTIONS
from agents.event_ledger import EventLedger


class AgentTaskRouter:
    def __init__(self, ledger: EventLedger, *, clock=lambda: datetime.now(timezone.utc)):
        self.ledger = ledger
        self.clock = clock

    @staticmethod
    def discover() -> dict[str, tuple[str, ...]]:
        """Return stable IDs and assigned task categories, never credentials/models."""
        return {agent_id: tuple(sorted(actions)) for agent_id, actions in AGENT_ACTIONS.items()}

    def claim(self, agent_id: str) -> dict[str, Any] | None:
        now = self.clock().astimezone(timezone.utc).replace(microsecond=0)
        claimed_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        expired_before = (now - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
        task = self.ledger.claim_task(agent_id, claimed_at=claimed_at,
                                     lease_expired_before=expired_before)
        if task is not None:
            task["issue_url"] = f"https://github.com/Dukeraider2/framework-desktop-ai-lab/issues/{task['issue_number']}"
        return task

    def complete(self, task: dict[str, Any], *, result_url: str) -> None:
        self.ledger.finish_task(task["task_id"], agent_id=task["agent_id"],
                                result_ref=result_url,
                                completed_at=self.clock().astimezone(timezone.utc).isoformat(timespec="seconds"))
