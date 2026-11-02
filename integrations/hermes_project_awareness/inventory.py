"""Host inventory provider. Reads only exact sources declared by its root-owned manifest."""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import tomllib
from pathlib import Path
from typing import Any

from .evidence import Evidence, utc_now


MANIFEST = Path("/etc/hermes-inventory/sources.toml")
MAX_MANIFEST_BYTES = 128 * 1024
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_DIRECTORY_ENTRIES = 500
_FIXED_PROBES = frozenset({"host_summary", "model_catalog", "project_directories", "service_inventory"})
_SENSITIVE_KEY = re.compile(r"(?i)(token|secret|password|credential|private.?key|api.?key|auth)")


class InventoryError(RuntimeError):
    pass


class SourceUnavailable(InventoryError):
    pass


def _read_manifest(path: Path = MANIFEST, *, require_root_owner: bool = True) -> dict[str, Any]:
    try:
        st = path.lstat()
    except OSError as exc:
        raise InventoryError("inventory manifest is unavailable or invalid") from exc
    if (not stat.S_ISREG(st.st_mode) or st.st_size > MAX_MANIFEST_BYTES
            or (require_root_owner and st.st_uid != 0) or st.st_mode & 0o022):
        raise InventoryError("inventory manifest is unavailable or invalid")
    with path.open("rb") as f:
        config = tomllib.loads(f.read(MAX_MANIFEST_BYTES + 1).decode("utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("sources", {}), dict):
        raise InventoryError("inventory manifest schema is invalid")
    return config


def _safe_path(raw: Any, path_allowlist: list[str]) -> Path:
    if not isinstance(raw, str) or not raw.startswith("/") or raw not in path_allowlist:
        raise InventoryError("source is not on the exact path allowlist")
    path = Path(raw)
    # Reject symlinks in every component. Resolving alone would let an allowed link target
    # broaden the service's readable filesystem set.
    current = Path("/")
    for component in path.parts[1:]:
        current = current / component
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                raise InventoryError("symlink sources are not permitted")
        except FileNotFoundError as exc:
            raise SourceUnavailable("approved source is missing") from exc
    resolved = path.resolve(strict=True)
    if str(resolved) != raw:
        raise InventoryError("source path does not resolve to its allowlisted spelling")
    return resolved


def _source_records(config: dict[str, Any], probe: str) -> list[dict[str, Any]]:
    if probe not in _FIXED_PROBES:
        raise InventoryError("unknown inventory operation")
    sources = config.get("sources", {})
    records = sources.get(probe, [])
    if not isinstance(records, list):
        raise InventoryError("source list is malformed")
    return records


def _file_source(entry: dict[str, Any], allowed: list[str]) -> dict[str, Any]:
    raw_path = entry.get("path")
    source_path = _safe_path(raw_path, allowed)
    try:
        st = source_path.stat()
        limit = min(int(entry.get("max_bytes", MAX_SOURCE_BYTES)), MAX_SOURCE_BYTES)
        if not stat.S_ISREG(st.st_mode) or (st.st_size and st.st_size > limit):
            raise InventoryError("source is not a bounded regular file")
        with source_path.open("rb") as source:
            data = source.read(limit + 1)
        if len(data) > limit:
            raise InventoryError("source exceeded its byte limit")
    except FileNotFoundError as exc:
        raise SourceUnavailable("approved source is missing") from exc
    except OSError as exc:
        raise SourceUnavailable("approved source could not be read") from exc
    text = data.decode("utf-8", errors="replace")
    source_format = entry.get("format")
    fields = entry.get("fields")
    if not isinstance(fields, list) or not fields or any(not isinstance(key, str) for key in fields):
        raise InventoryError("file sources require an explicit non-empty field allowlist")
    if source_format == "os_release":
        parsed: dict[str, Any] = {}
        for line in text.splitlines():
            match = re.fullmatch(r"([A-Z0-9_]+)=(.*)", line)
            if match:
                parsed[match.group(1)] = match.group(2).strip().strip('"')
    elif source_format == "json":
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise InventoryError("approved JSON source is not an object")
    elif source_format == "toml":
        parsed = tomllib.loads(text)
    elif source_format in {"proc_cpuinfo", "proc_meminfo"}:
        parsed = {}
        wanted = set(fields)
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            if key in wanted:
                values = parsed.setdefault(key, [])
                normalized = value.strip()
                if normalized and normalized not in values:
                    values.append(normalized)
        parsed = {key: ", ".join(values) for key, values in parsed.items()}
    elif source_format == "sysfs_text":
        if fields != ["value"]:
            raise InventoryError("sysfs text sources may expose only the value field")
        parsed = {"value": text.strip()[:256]}
    elif source_format == "dpkg_status":
        if len(fields) > 40 or any(not re.fullmatch(r"[a-z0-9][a-z0-9+.-]{0,99}", package) for package in fields):
            raise InventoryError("installed-package allowlist is invalid")
        wanted = set(fields)
        parsed = {}
        for paragraph in re.split(r"\n\s*\n", text):
            package = version = status = None
            for line in paragraph.splitlines():
                if line.startswith("Package: "):
                    package = line[9:].strip()
                elif line.startswith("Version: "):
                    version = line[9:].strip()
                elif line.startswith("Status: "):
                    status = line[8:].strip()
            if package in wanted and status == "install ok installed" and version:
                parsed[package] = version
    else:
        raise InventoryError("file source format is not supported")
    if any(_SENSITIVE_KEY.search(key) for key in fields):
        raise InventoryError("sensitive configuration keys are not permitted")
    if len(fields) > 40:
        raise InventoryError("field allowlist exceeds the configured limit")
    selected = {key: parsed[key] for key in fields if key in parsed}
    # Do not return nested arbitrary configuration: the allowlist is top-level and scalar-only.
    if any(value is None or isinstance(value, (dict, list)) for value in selected.values()):
        raise InventoryError("allowlisted configuration fields must be scalar values")
    if any(isinstance(value, str) and len(value) > 512 for value in selected.values()):
        raise InventoryError("allowlisted text value exceeds its output limit")
    return {"source_id": _source_id(entry), "fields": selected}


def _directory_source(entry: dict[str, Any], allowed: list[str]) -> dict[str, Any]:
    raw_path = entry.get("path")
    source_path = _safe_path(raw_path, allowed)
    try:
        st = source_path.stat()
        if not stat.S_ISDIR(st.st_mode):
            raise InventoryError("source is not a directory")
        items = []
        with os.scandir(source_path) as scan:
            for item in scan:
                if len(items) >= MAX_DIRECTORY_ENTRIES:
                    raise InventoryError("directory inventory exceeds its entry limit")
                if item.is_symlink():
                    continue
                info = item.stat(follow_symlinks=False)
                items.append({
                    "name": item.name[:255],
                    "kind": "directory" if stat.S_ISDIR(info.st_mode) else "file" if stat.S_ISREG(info.st_mode) else "other",
                    "size_bytes": info.st_size if stat.S_ISREG(info.st_mode) else None,
                })
        return {"source_id": _source_id(entry), "entries": sorted(items, key=lambda row: row["name"])}
    except OSError as exc:
        raise InventoryError("approved directory could not be inventoried") from exc


def _disk_usage_source(entry: dict[str, Any], allowed: list[str]) -> dict[str, Any]:
    raw_path = entry.get("path")
    source_path = _safe_path(raw_path, allowed)
    try:
        if not source_path.is_dir():
            raise InventoryError("storage source is not an approved directory")
        usage = shutil.disk_usage(source_path)
    except FileNotFoundError as exc:
        raise SourceUnavailable("approved storage path is missing") from exc
    except OSError as exc:
        raise SourceUnavailable("approved storage path could not be inspected") from exc
    return {"source_id": _source_id(entry), "fields": {
        "total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free}}


def _source_id(entry: dict[str, Any]) -> str:
    value = entry.get("id")
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value):
        raise InventoryError("manifest source needs a stable, non-path source id")
    return value


def collect(probe: str, *, manifest: Path = MANIFEST, observed_at: str | None = None,
            require_root_owner: bool = True) -> dict[str, Any]:
    """Return a bounded snapshot; path arguments are never accepted from the caller."""
    if probe not in _FIXED_PROBES:
        raise InventoryError("unknown inventory operation")
    config = _read_manifest(manifest, require_root_owner=require_root_owner)
    allowed_paths = config.get("allowed_paths", [])
    if not isinstance(allowed_paths, list) or any(not isinstance(item, str) for item in allowed_paths):
        raise InventoryError("manifest path allowlist is malformed")
    records = _source_records(config, probe)
    if not records:
        raise InventoryError("no approved sources are configured for this inventory operation")
    sources = []
    missing = []
    for entry in records:
        if not isinstance(entry, dict) or entry.get("kind") not in {"file", "directory_metadata", "disk_usage"}:
            raise InventoryError("manifest source entry is malformed")
        try:
            if entry["kind"] == "file":
                row = _file_source(entry, allowed_paths)
            elif entry["kind"] == "directory_metadata":
                row = _directory_source(entry, allowed_paths)
            else:
                row = _disk_usage_source(entry, allowed_paths)
            sources.append({"status": "ok", **row})
        except SourceUnavailable:
            missing.append(_source_id(entry))
    timestamp = observed_at or utc_now()
    evidence = Evidence(
        evidence_id=f"inventory:{probe}:{timestamp}", provider="frameworkai1_inventory",
        kind=probe, observed_at=timestamp,
        summary=f"Collected {len(sources)} approved source(s); {len(missing)} unavailable for {probe}.",
        source_ref="local host snapshot",
    )
    if not sources:
        raise InventoryError("no approved inventory source was available")
    return {"provider_id": "frameworkai1_inventory", "schema_version": "1.0",
            "observed_at": timestamp, "status": "partial" if missing else "ok", "coverage": [probe],
            "sources": sources, "unavailable_sources": missing, "evidence": [evidence.as_dict()]}
