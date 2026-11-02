"""Hermes tool wrapper: sender authorization first, then MCP-backed provider reads."""

from __future__ import annotations

import logging
import os
import re
import stat
import sys
import uuid
from pathlib import Path
from typing import Any


_PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from integrations.hermes_project_awareness.mcp_client import call_provider  # noqa: E402
from integrations.hermes_project_awareness.report import build_report, render_report  # noqa: E402
from integrations.hermes_project_awareness.audit import record as audit_record  # noqa: E402


logger = logging.getLogger("hermes.project_awareness")
SENDER_ALLOWLIST = Path("/etc/hermes-project-awareness/authorized-whatsapp-senders")
MAX_ALLOWLIST_BYTES = 16 * 1024
_SENDER_RE = re.compile(r"^[A-Za-z0-9+:.@_-]{3,96}$")
_FOCUSES = frozenset({"overall", "infrastructure", "models", "tasks", "github_activity", "technical_progress"})
_PROJECT_DOC_PATHS = ("README.md", "docs/PLAN.md", "docs/STATUS_2026-10-26.md")

PROJECT_STATUS_SCHEMA = {
    "name": "frameworklab_project_status",
    "description": (
        "Return a current, read-only Framework Desktop AI Lab status report using live GitHub and host-provider evidence. "
        "Use for project status, infrastructure, models, outstanding tasks, GitHub activity, or technical progress. "
        "Every returned project claim has one of the five evidence classifications and linked evidence IDs."
    ),
    "parameters": {
        "type": "object",
        "properties": {"focus": {"type": "string", "enum": sorted(_FOCUSES),
                                  "description": "Report focus; use overall for the complete project report."}},
        "additionalProperties": False,
    },
}


def _sender_allowed(*, allowlist_path: Path = SENDER_ALLOWLIST, require_root_owner: bool = True) -> bool:
    """Use trusted gateway context, never a model argument, and fail closed on any uncertainty."""
    try:
        from gateway.session_context import get_session_env
        platform = get_session_env("HERMES_SESSION_PLATFORM", "").strip().lower()
        chat_type = get_session_env("HERMES_SESSION_CHAT_TYPE", "").strip().lower()
        sender = get_session_env("HERMES_SESSION_USER_ID", "").strip()
        chat = get_session_env("HERMES_SESSION_CHAT_ID", "").strip()
        # Meta's WhatsApp Agent Platform registers under its own Hermes platform
        # key, and the adapter's canonical participant ID is ``user:<id>``.
        # Do not accept the similarly named Baileys ``whatsapp`` transport here:
        # this report tool is deployed only through the inspected Agent Platform.
        if (platform != "whatsapp_agent_platform" or chat_type not in {"dm", "direct"}
                or not sender.startswith("user:") or sender != chat):
            return False
        if not _SENDER_RE.fullmatch(sender):
            return False
        st = allowlist_path.lstat()
        if (not stat.S_ISREG(st.st_mode) or st.st_size > MAX_ALLOWLIST_BYTES
                or st.st_mode & 0o137 or not st.st_mode & 0o040
                or (st.st_gid != os.getgid() and st.st_gid not in os.getgroups())
                or (require_root_owner and st.st_uid != 0)):
            return False
        entries = allowlist_path.read_text(encoding="utf-8").splitlines()
        authorized = {line.strip() for line in entries if line.strip() and not line.lstrip().startswith("#")}
        return sender in authorized
    except Exception:
        return False


def _operations(focus: str) -> list[tuple[str, str, dict[str, Any]]]:
    github: list[tuple[str, str, dict[str, Any]]] = []
    inventory: list[tuple[str, str, dict[str, Any]]] = []
    if focus in {"overall", "tasks", "github_activity", "technical_progress"}:
        github.extend([
            ("github", "repository_summary", {}),
            ("github", "issues", {"state": "open"}),
            ("github", "issues", {"state": "closed"}),
            ("github", "pull_requests", {"state": "open"}),
            ("github", "pull_requests", {"state": "closed"}),
            ("github", "recent_commits", {"limit": 10}),
        ])
    if focus == "github_activity":
        github.append(("github", "branches", {}))
    if focus in {"overall", "infrastructure", "technical_progress"}:
        inventory.append(("inventory", "host_summary", {}))
        inventory.extend([
            ("inventory", "gpu_inventory", {}),
            ("inventory", "comfyui_status", {}),
        ])
    if focus in {"overall", "infrastructure"}:
        inventory.append(("inventory", "service_inventory", {}))
    if focus in {"overall", "models", "technical_progress"}:
        inventory.extend([
            ("inventory", "model_catalog", {}),
            ("inventory", "ollama_models", {}),
            ("inventory", "comfyui_models", {}),
        ])
    return github + inventory


def _run_status(args: dict[str, Any], **_kwargs: Any) -> str:
    request_id = uuid.uuid4().hex
    if not _sender_allowed():
        try:
            audit_record({"request_id": request_id, "event": "denied", "provider": "hermes",
                          "operation": "project_status", "result": "denied"})
        except Exception:
            pass
        logger.warning("event=project_status_denied request_id=%s", request_id)
        return "Access denied. This sender is not authorized for project and infrastructure reports."
    focus = args.get("focus", "overall") if isinstance(args, dict) else ""
    if focus not in _FOCUSES:
        return "The requested report focus is not supported."
    logger.info("event=project_status_started request_id=%s focus=%s", request_id, focus)
    try:
        audit_record({"request_id": request_id, "event": "started", "provider": "hermes", "operation": "project_status"})
    except Exception:
        logger.error("event=project_status_audit_unavailable request_id=%s", request_id)
        return "Project status is unavailable because the required audit log could not be written. No provider data was requested."
    snapshots: list[dict[str, Any]] = []
    failures: list[str] = []
    for provider, operation, arguments in _operations(focus):
        try:
            snapshot = call_provider(provider, operation, arguments, request_id=request_id)
            snapshots.append(snapshot)
            if provider == "github" and operation == "repository_summary":
                rows = snapshot.get("records", [])
                default_branch = rows[0].get("default_branch") if rows and isinstance(rows[0], dict) else None
                if isinstance(default_branch, str) and default_branch:
                    for path in _PROJECT_DOC_PATHS:
                        try:
                            snapshots.append(call_provider("github", "read_document",
                                                           {"path": path, "ref": default_branch}, request_id=request_id))
                        except Exception as exc:
                            failures.append(f"github:document:{path}")
                            logger.warning("event=project_status_provider_error request_id=%s provider=github error=%s",
                                           request_id, type(exc).__name__)
            if provider == "github" and operation == "pull_requests" and arguments.get("state") == "open":
                for record in snapshot.get("records", [])[:20]:
                    number = record.get("number")
                    if isinstance(number, int) and number > 0:
                        try:
                            snapshots.append(call_provider("github", "pull_request_reviews",
                                                           {"number": number}, request_id=request_id))
                        except Exception as exc:
                            failures.append(f"github:reviews:{number}")
                            logger.warning("event=project_status_provider_error request_id=%s provider=github error=%s",
                                           request_id, type(exc).__name__)
        except Exception as exc:
            failures.append(f"{provider}:{operation}")
            logger.warning("event=project_status_provider_error request_id=%s provider=%s error=%s",
                           request_id, provider, type(exc).__name__)
    report = build_report(snapshots, failures=failures)
    output = render_report(report)
    try:
        audit_record({"request_id": request_id, "event": "completed", "provider": "hermes",
                      "operation": "project_status",
                      "evidence_ids": [row.get("evidence_id", "") for row in report.get("evidence", [])]})
    except Exception:
        logger.error("event=project_status_audit_unavailable request_id=%s", request_id)
        return "Project status is unavailable because the completed report could not be audited. No status data was released."
    logger.info("event=project_status_completed request_id=%s providers=%s evidence_count=%d failures=%d",
                request_id, ",".join(sorted({row.get("provider_id", "unknown") for row in snapshots})),
                len(report.get("evidence", [])), len(failures))
    return output


def register(ctx) -> None:
    """Register a single sender-gated tool; raw provider tools are not injected into WhatsApp."""
    ctx.register_tool(name="frameworklab_project_status", toolset="frameworklab-awareness",
                      schema=PROJECT_STATUS_SCHEMA, handler=_run_status, emoji="📊")
