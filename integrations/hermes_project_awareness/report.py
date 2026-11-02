"""Evidence-bound project report assembly and deterministic WhatsApp rendering."""

from __future__ import annotations

import json
from typing import Any

from .evidence import EVIDENCE_CLASSES, validate_evidence, validate_claim


def _evidence_map(snapshots: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], set[str]]:
    evidence: dict[str, dict[str, Any]] = {}
    for snapshot in snapshots:
        for row in snapshot.get("evidence", []):
            item = validate_evidence(row).as_dict()
            evidence[item["evidence_id"]] = item
    return evidence, set(evidence)


def build_report(snapshots: list[dict[str, Any]], *, failures: list[str] | None = None) -> dict[str, Any]:
    """Derive project states only from GitHub records; keep host observations separate."""
    failures = failures or []
    evidence, evidence_ids = _evidence_map(snapshots)
    github_by_kind = {row.get("coverage", [""])[0]: row for row in snapshots if row.get("provider_id") == "github"}
    inventory_by_kind = {row.get("coverage", [""])[0]: row for row in snapshots if row.get("provider_id") == "frameworkai1_inventory"}
    claims: list[dict[str, Any]] = []
    project_documents: list[dict[str, Any]] = []
    for snapshot in snapshots:
        if snapshot.get("provider_id") != "github" or snapshot.get("coverage") != ["read_document"]:
            continue
        evidence_ref = (snapshot.get("evidence") or [{}])[0].get("evidence_id", "")
        for row in snapshot.get("records", []):
            if not isinstance(row, dict):
                continue
            content = row.get("content", "")
            excerpt = ""
            if isinstance(content, str):
                meaningful = [line.strip() for line in content.splitlines()
                              if line.strip() and not line.lstrip().startswith(("#", "```", "<!--"))]
                excerpt = _plain_text(meaningful[0], 500) if meaningful else ""
            project_documents.append({"path": row.get("path", "document"), "ref": row.get("ref", "unknown"),
                                      "blob_sha": row.get("blob_sha", ""),
                                      "html_url": row.get("html_url"), "excerpt": excerpt,
                                      "evidence_id": evidence_ref})

    def add(classification: str, text: str, refs: list[str], reason: str | None = None) -> None:
        row = {"classification": classification, "text": text, "evidence_ids": refs}
        if reason:
            row["reason"] = reason
        claims.append(validate_claim(row, evidence_ids))

    for operation, category in (("issues_open", "issue"), ("pull_requests_open", "pull request")):
        snap = github_by_kind.get(operation)
        if not snap:
            continue
        refs = [row["evidence_id"] for row in snap.get("evidence", [])]
        records = snap.get("records", [])
        for record in records:
            if record.get("state") != "open":
                continue
            title = _plain_text(record.get("title") or "(untitled)", 220)
            labels = {str(label.get("name", "")).lower() for label in record.get("labels", []) if isinstance(label, dict)}
            number = record.get("number")
            url = record.get("html_url")
            detail = f" [#{number}]({url})" if number and isinstance(url, str) else ""
            if "blocked" in labels or "status: blocked" in labels:
                add("Blocked", f"{category.capitalize()}{detail}: {title}", refs)
            elif "proposed" in labels or "status: proposed" in labels:
                add("Proposed", f"{category.capitalize()}{detail}: {title}", refs)
            elif category == "pull request":
                add("In progress", f"Open {category}{detail}: {title}", refs)
            else:
                add("Unverified", f"Open issue{detail}: {title}", refs,
                    "An open issue is an outstanding record, but its state does not prove implementation has started.")

    closed_issues = github_by_kind.get("issues_closed")
    if closed_issues:
        refs = [row["evidence_id"] for row in closed_issues.get("evidence", [])]
        for record in closed_issues.get("records", []):
            number = record.get("number")
            url = record.get("html_url")
            title = _plain_text(record.get("title") or "(untitled)", 220)
            link = f" [#{number}]({url})" if number and isinstance(url, str) else ""
            if record.get("state_reason") == "completed":
                add("Verified complete", f"Completed issue{link}: {title}", refs)
            else:
                add("Unverified", f"Closed issue{link}: {title}", refs,
                    "The issue was closed without a verified completed state reason.")

    closed_prs = github_by_kind.get("pull_requests_closed")
    if closed_prs:
        refs = [row["evidence_id"] for row in closed_prs.get("evidence", [])]
        for record in closed_prs.get("records", []):
            if not record.get("merged_at"):
                continue
            url = record.get("html_url")
            number = record.get("number")
            title = _plain_text(record.get("title") or "(untitled)", 220)
            link = f" [#{number}]({url})" if number and isinstance(url, str) else ""
            add("Verified complete", f"Merged pull request{link}: {title}", refs)

    for label in ("Proposed", "Blocked"):
        if not any(row["classification"] == label for row in claims):
            source_refs = [row["evidence_id"] for op in ("issues", "pull_requests")
                           for row in github_by_kind.get(op, {}).get("evidence", [])]
            if source_refs:
                add(label, f"No {label.lower()} GitHub records were identified in the retrieved open lists.", source_refs)

    host_summary = inventory_by_kind.get("host_summary")
    for provider in dict.fromkeys(failures):
        label = _failure_label(provider)
        add("Unverified", f"{label} could not be verified during this request.", [],
            "The provider did not return a complete, attributable live snapshot.")
    if not claims:
        add("Unverified", "No project state was returned.", [], "No authoritative provider evidence was available.")
    return {"report_version": "1.0", "observed_at": max((row.get("observed_at", "") for row in snapshots), default=""),
            "claims": claims, "evidence": list(evidence.values()), "provider_failures": list(dict.fromkeys(failures)),
            "project_documents": project_documents,
            "host_inventory": {key: value for key, value in inventory_by_kind.items()},
            "github_activity": {key: value for key, value in github_by_kind.items()
                                if key in {"repository_summary", "recent_commits", "branches"}
                                or key.startswith("pull_request_reviews_")},
            "partial_snapshots": [{"provider": row.get("provider_id"), "coverage": row.get("coverage"),
                                   "reason": row.get("partial_reason") or "some configured sources were unavailable"}
                                  for row in snapshots if row.get("status") == "partial"]}


def render_report(report: dict[str, Any]) -> str:
    evidence = {row["evidence_id"]: row for row in report.get("evidence", [])}
    lines = ["Framework Desktop AI Lab — evidence-based status", f"Observed: {report.get('observed_at') or 'unknown'}", ""]
    for partial in report.get("partial_snapshots", []):
        lines.append(f"Partial data: {partial.get('provider')} / {', '.join(partial.get('coverage') or [])}: {partial.get('reason')}.")
    if report.get("partial_snapshots"):
        lines.append("")
    documents = report.get("project_documents") or []
    if documents:
        lines.extend(["Authoritative project documents retrieved from GitHub"])
        for row in documents:
            label = _plain_text(row.get("path", "document"), 180)
            url = row.get("html_url")
            rendered_path = f"[{label}]({url})" if isinstance(url, str) and url.startswith("https://github.com/Dukeraider2/framework-desktop-ai-lab/") else label
            excerpt = f" — {row['excerpt']}" if row.get("excerpt") else ""
            lines.append(f"• {rendered_path}{excerpt} (ref {row.get('ref', 'unknown')}; blob {str(row.get('blob_sha', ''))[:12]}; evidence {row.get('evidence_id', 'unavailable')})")
        lines.append("")
    for classification in EVIDENCE_CLASSES:
        rows = [claim for claim in report.get("claims", []) if claim.get("classification") == classification]
        lines.append(f"{classification}")
        if not rows:
            lines.append("• No supported claims in this category.")
            continue
        for claim in rows:
            refs = []
            for evidence_id in claim.get("evidence_ids", []):
                row = evidence.get(evidence_id)
                if row and row.get("source_url"):
                    refs.append(f"[{evidence_id}]({row['source_url']})")
                elif row:
                    refs.append(evidence_id)
            citation = " Evidence: " + ", ".join(refs) if refs else ""
            reason = f" Reason: {claim['reason']}" if claim.get("reason") else ""
            lines.append(f"• {claim['text']}{citation}{reason}")
    host = report.get("host_inventory") or {}
    if host:
        lines.extend(["", "Host observations (not project-completion claims)"])
        for kind, snapshot in host.items():
            evs = snapshot.get("evidence", [])
            refs = ", ".join(row.get("evidence_id", "") for row in evs)
            lines.append(f"• {kind}: snapshot at {snapshot.get('observed_at')}; evidence {refs or 'unavailable'}.")
            if snapshot.get("unavailable_sources"):
                lines.append(f"  - unavailable approved sources: {', '.join(snapshot['unavailable_sources'])}")
            for source in snapshot.get("sources", []):
                # Source paths are not returned to WhatsApp; provider-side path aliases are
                # intended to be generic (e.g. os_release, gpu_devices, model_catalog).
                details = source.get("fields", {})
                if "entries" in source:
                    entries = source["entries"]
                    details = {"count": len(entries), "sample": entries[:20],
                               "additional_entries": max(0, len(entries) - 20)}
                lines.append(f"  - {source.get('source_id', 'inventory source')}: {json.dumps(details, ensure_ascii=False, sort_keys=True)}")
    activity = report.get("github_activity") or {}
    repository = activity.get("repository_summary")
    if repository and repository.get("records"):
        row = repository["records"][0]
        url = row.get("html_url")
        name = row.get("full_name") or "Framework Desktop AI Lab repository"
        label = f"[{name}]({url})" if isinstance(url, str) else str(name)
        evidence_ids = ", ".join(item.get("evidence_id", "") for item in repository.get("evidence", []))
        lines.insert(2, f"Repository: {label}; default branch {row.get('default_branch', 'unknown')} (evidence {evidence_ids})")
    commits = activity.get("recent_commits")
    if commits:
        lines.extend(["", "Recent GitHub activity"])
        evidence_ids = [row.get("evidence_id", "") for row in commits.get("evidence", [])]
        evidence_ref = ", ".join(evidence_ids)
        for row in commits.get("records", [])[:10]:
            message = _plain_text(row.get("message") or "(no commit message)", 240)
            sha = str(row.get("sha") or "")[:12]
            url = row.get("html_url")
            link = f"[{sha}]({url})" if sha and isinstance(url, str) else sha or "commit"
            lines.append(f"• {link}: {message} (evidence {evidence_ref})")
    branches = activity.get("branches")
    if branches:
        lines.append("Branches (first page)")
        branch_evidence = ", ".join(row.get("evidence_id", "") for row in branches.get("evidence", []))
        for row in branches.get("records", [])[:20]:
            name = _plain_text(row.get("name") or "(unnamed)", 160)
            lines.append(f"• {name} (evidence {branch_evidence})")
    reviews = [(key, value) for key, value in report.get("github_activity", {}).items()
               if key.startswith("pull_request_reviews_")]
    if reviews:
        lines.extend(["", "Pull request review records"])
        for key, snapshot in sorted(reviews):
            number = key.removeprefix("pull_request_reviews_")
            states = sorted({str(row.get("state", "UNKNOWN")) for row in snapshot.get("records", [])})
            state_text = ", ".join(states) if states else "no review events"
            evidence_ids = [row.get("evidence_id", "") for row in snapshot.get("evidence", [])]
            evidence_ref = ", ".join(evidence_ids)
            lines.append(f"• PR #{number}: retrieved review events include {state_text}; this is not a synthesized current review decision (evidence {evidence_ref}).")
    return "\n".join(lines)


def _plain_text(value: Any, max_chars: int) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").replace("`", "'").replace("[", "(").replace("]", ")")
    return " ".join(text.split())[:max_chars]


def _failure_label(value: str) -> str:
    labels = {
        "github:repository_summary": "GitHub repository metadata",
        "github:issues": "open GitHub issues",
        "github:pull_requests": "GitHub pull requests",
        "github:recent_commits": "recent GitHub commits",
        "github:branches": "GitHub branches",
        "inventory:host_summary": "host inventory",
        "inventory:model_catalog": "local model catalog",
        "inventory:service_inventory": "selected service inventory",
        "inventory:project_directories": "project-directory inventory",
    }
    if value.startswith("github:reviews:"):
        return f"review records for pull request #{value.rsplit(':', 1)[-1]}"
    return labels.get(value, value.replace(":", " "))
