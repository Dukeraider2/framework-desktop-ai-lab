"""Host inventory provider. Reads only exact sources declared by its root-owned manifest."""

from __future__ import annotations

import json
import http.client
import os
import re
import socket
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
_FIXED_PROBES = frozenset({
    "host_summary", "model_catalog", "project_directories", "service_inventory",
    "ollama_models", "comfyui_status", "comfyui_models", "gpu_inventory",
})
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


def _model_directory_source(entry: dict[str, Any], allowed: list[str]) -> dict[str, Any]:
    """Expose model file names and sizes only, never directory contents or symlinks."""
    source_path = _safe_path(entry.get("path"), allowed)
    extensions = entry.get("extensions")
    if (not isinstance(extensions, list) or not extensions or len(extensions) > 20
            or any(not isinstance(x, str) or not re.fullmatch(r"\.[a-zA-Z0-9]{1,12}", x) for x in extensions)):
        raise InventoryError("model directory requires a bounded extension allowlist")
    try:
        if not source_path.is_dir():
            raise InventoryError("model source is not an approved directory")
        rows = []
        with os.scandir(source_path) as scan:
            for item in scan:
                if item.is_symlink() or not item.is_file(follow_symlinks=False):
                    continue
                suffix = Path(item.name).suffix.lower()
                if suffix not in {x.lower() for x in extensions} or item.name.startswith("."):
                    continue
                info = item.stat(follow_symlinks=False)
                rows.append({"name": item.name[:180], "size_bytes": info.st_size})
                if len(rows) > MAX_DIRECTORY_ENTRIES:
                    raise InventoryError("model inventory exceeds its entry limit")
        return {"source_id": _source_id(entry), "models": sorted(rows, key=lambda row: row["name"])}
    except OSError as exc:
        raise InventoryError("approved model directory could not be inventoried") from exc


def _loopback_json(port: int, path: str, *, max_bytes: int = 1024 * 1024) -> Any:
    """Query one fixed local HTTP service; caller cannot choose host, port, or path."""
    if port not in {11434, 8188} or path not in {
        "/api/tags", "/system_stats", "/models/checkpoints", "/models/loras",
        "/models/vae", "/models/controlnet", "/models/upscale_models",
    }:
        raise InventoryError("local runtime endpoint is not approved")
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2.0)
    try:
        connection.request("GET", path, headers={"Accept": "application/json", "Connection": "close"})
        response = connection.getresponse()
        if response.status != 200:
            raise SourceUnavailable("local runtime returned a non-success status")
        if response.getheader("Transfer-Encoding", "").lower() not in {"", "identity", "chunked"}:
            raise InventoryError("local runtime used an unsupported response encoding")
        length = response.getheader("Content-Length")
        if length and int(length) > max_bytes:
            raise InventoryError("local runtime response exceeded its size limit")
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise InventoryError("local runtime response exceeded its size limit")
        try:
            return json.loads(body)
        except (ValueError, UnicodeDecodeError) as exc:
            raise InventoryError("local runtime returned malformed JSON") from exc
    except (OSError, http.client.HTTPException, ValueError) as exc:
        if isinstance(exc, InventoryError):
            raise
        raise SourceUnavailable("approved local runtime is unavailable") from exc
    finally:
        connection.close()


def _ollama_models(entry: dict[str, Any]) -> dict[str, Any]:
    data = _loopback_json(11434, "/api/tags")
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list) or len(models) > MAX_DIRECTORY_ENTRIES:
        raise InventoryError("Ollama model response schema is invalid")
    output = []
    for model in models:
        if not isinstance(model, dict):
            raise InventoryError("Ollama model entry is invalid")
        details = model.get("details") if isinstance(model.get("details"), dict) else {}
        output.append({key: model.get(key) for key in ("name", "model", "size", "modified_at", "digest") if key in model}
                      | {key: details.get(key) for key in ("format", "family", "parameter_size", "quantization_level") if key in details})
    return {"source_id": _source_id(entry), "models": output}


def _comfyui_status(entry: dict[str, Any]) -> dict[str, Any]:
    data = _loopback_json(8188, "/system_stats")
    if not isinstance(data, dict):
        raise InventoryError("ComfyUI system response schema is invalid")
    system = data.get("system") if isinstance(data.get("system"), dict) else {}
    devices = data.get("devices") if isinstance(data.get("devices"), list) else []
    if len(devices) > 32:
        raise InventoryError("ComfyUI device list exceeds its limit")
    safe_devices = []
    for device in devices:
        if not isinstance(device, dict):
            continue
        safe_devices.append({key: device.get(key) for key in
                             ("name", "type", "index", "vram_total", "vram_free", "torch_version", "driver_version")
                             if isinstance(device.get(key), (str, int, float, bool))})
    return {"source_id": _source_id(entry), "fields": {
        key: system[key] for key in ("os", "python_version", "embedded_python", "pytorch_version")
        if isinstance(system.get(key), (str, int, float, bool))}, "devices": safe_devices}


def _comfyui_models(entry: dict[str, Any]) -> dict[str, Any]:
    categories = entry.get("categories")
    approved = {"checkpoints": "/models/checkpoints", "loras": "/models/loras", "vae": "/models/vae",
                "controlnet": "/models/controlnet", "upscale_models": "/models/upscale_models"}
    if not isinstance(categories, list) or not categories or any(x not in approved for x in categories):
        raise InventoryError("ComfyUI model categories are not allowlisted")
    inventories = {}
    for category in categories:
        data = _loopback_json(8188, approved[category])
        if not isinstance(data, list) or len(data) > MAX_DIRECTORY_ENTRIES:
            raise InventoryError("ComfyUI model list schema is invalid")
        if any(not isinstance(name, str) or len(name) > 180 or "/" in name or "\\" in name for name in data):
            raise InventoryError("ComfyUI model list contains an invalid name")
        inventories[category] = sorted(data)
    return {"source_id": _source_id(entry), "models": inventories}


def _gpu_inventory(entry: dict[str, Any]) -> dict[str, Any]:
    """Read only selected DMI and DRM sysfs fields; never inspect /dev or run rocminfo."""
    dmi_root = Path("/sys/class/dmi/id")
    dmi_fields = {"vendor": "sys_vendor", "product": "product_name", "board": "board_name"}
    output: dict[str, Any] = {"source_id": _source_id(entry), "hardware": {}}
    for label, name in dmi_fields.items():
        path = dmi_root / name
        try:
            value = path.read_text(encoding="utf-8").strip()
            if value and len(value) <= 256:
                output["hardware"][label] = value
        except OSError:
            continue
    devices = []
    drm_root = Path("/sys/class/drm")
    try:
        cards = sorted(card for card in drm_root.glob("card[0-9]*")
                       if re.fullmatch(r"card[0-9]+", card.name))
        for card in cards[:32]:
            device = card / "device"
            try:
                resolved = device.resolve(strict=True)
                if not resolved.is_relative_to(Path("/sys/devices")):
                    continue
                row: dict[str, Any] = {"card": card.name}
                for field, key in (("vendor", "vendor"), ("device", "device"),
                                   ("vram_total_bytes", "mem_info_vram_total"),
                                   ("vram_used_bytes", "mem_info_vram_used")):
                    try:
                        raw = (device / key).read_text(encoding="ascii").strip()
                        row[field] = int(raw, 0) if key in {"vendor", "device"} else int(raw)
                    except (OSError, ValueError):
                        continue
                devices.append(row)
            except OSError:
                continue
        output["devices"] = devices
    except OSError:
        output["devices"] = []
    output["provider_kfd_visible"] = Path("/dev/kfd").exists()
    return output


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
        if not isinstance(entry, dict) or entry.get("kind") not in {
            "file", "disk_usage", "model_directory", "ollama_api", "comfyui_system",
            "comfyui_models", "gpu_sysfs",
        }:
            raise InventoryError("manifest source entry is malformed")
        try:
            kind = entry["kind"]
            if kind == "file":
                row = _file_source(entry, allowed_paths)
            elif kind == "disk_usage":
                row = _disk_usage_source(entry, allowed_paths)
            elif kind == "model_directory":
                row = _model_directory_source(entry, allowed_paths)
            elif kind == "ollama_api" and probe == "ollama_models":
                row = _ollama_models(entry)
            elif kind == "comfyui_system" and probe == "comfyui_status":
                row = _comfyui_status(entry)
            elif kind == "comfyui_models" and probe == "comfyui_models":
                row = _comfyui_models(entry)
            elif kind == "gpu_sysfs" and probe == "gpu_inventory":
                row = _gpu_inventory(entry)
            else:
                raise InventoryError("source kind is not valid for this fixed operation")
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
