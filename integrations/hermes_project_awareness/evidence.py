"""Small, validated evidence records shared by the providers and report tool."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


EVIDENCE_CLASSES = (
    "Verified complete",
    "In progress",
    "Proposed",
    "Blocked",
    "Unverified",
)


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    provider: str
    kind: str
    observed_at: str
    summary: str
    source_url: str | None = None
    source_ref: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_evidence(value: Any) -> Evidence:
    if not isinstance(value, dict):
        raise ValueError("evidence must be an object")
    fields = ("evidence_id", "provider", "kind", "observed_at", "summary")
    if any(not isinstance(value.get(key), str) or not value[key].strip() for key in fields):
        raise ValueError("evidence is missing a required string field")
    if value.get("source_url") is not None and not isinstance(value["source_url"], str):
        raise ValueError("source_url must be a string or null")
    if value.get("source_ref") is not None and not isinstance(value["source_ref"], str):
        raise ValueError("source_ref must be a string or null")
    return Evidence(**{key: value.get(key) for key in (
        "evidence_id", "provider", "kind", "observed_at", "summary", "source_url", "source_ref")})


def validate_claim(value: Any, evidence_ids: set[str]) -> dict[str, Any]:
    """Validate the five report classes and require evidence for factual assertions."""
    if not isinstance(value, dict):
        raise ValueError("claim must be an object")
    classification, text, references = value.get("classification"), value.get("text"), value.get("evidence_ids")
    if classification not in EVIDENCE_CLASSES or not isinstance(text, str) or not text.strip():
        raise ValueError("claim is missing a classification or text")
    if not isinstance(references, list) or any(not isinstance(ref, str) for ref in references):
        raise ValueError("claim evidence_ids must be a string list")
    if any(ref not in evidence_ids for ref in references):
        raise ValueError("claim references evidence that was not returned by an authoritative provider")
    if classification != "Unverified" and not references:
        raise ValueError("factual claims require authoritative evidence")
    if classification == "Unverified" and not value.get("reason"):
        raise ValueError("unverified claims must state why they are unverified")
    return {"classification": classification, "text": text.strip(),
            "evidence_ids": list(dict.fromkeys(references)),
            **({"reason": str(value["reason"])} if value.get("reason") else {})}
