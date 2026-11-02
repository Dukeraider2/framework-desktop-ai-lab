#!/usr/bin/env python3
"""Collect local Ollama model metadata without reading credentials or model blobs.

Default mode is metadata-only. --benchmark makes one small local inference request
per installed model and records Ollama's returned timing counters; it is opt-in.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


MODEL_NAME = re.compile(r"^[A-Za-z0-9_.:/-]{1,128}$")
METADATA_LABELS = {
    "architecture", "parameters", "context length", "embedding length", "quantization",
    "active parameters", "total parameters", "family", "format", "parameter size",
}


def run_cli(*args: str) -> tuple[int, str, str]:
    try:
        result = subprocess.run(["ollama", *args], capture_output=True, text=True,
                                timeout=20, check=False, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"})
        return result.returncode, result.stdout, result.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", type(exc).__name__


def installed_models() -> list[dict[str, str]]:
    code, output, error = run_cli("list")
    if code:
        raise RuntimeError(f"ollama list failed ({error.strip() or code})")
    lines = output.splitlines()
    if not lines:
        return []
    models = []
    for line in lines[1:]:
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) == 4 and MODEL_NAME.fullmatch(parts[0]):
            models.append({"name": parts[0], "id_prefix": parts[1][:16], "size": parts[2][:64],
                           "modified": parts[3][:80]})
    return models[:200]


def metadata(model_name: str) -> dict[str, str]:
    code, output, _error = run_cli("show", "--verbose", model_name)
    if code:
        return {"metadata_status": "unavailable"}
    fields = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized = " ".join(key.strip().lower().split())
        if normalized in METADATA_LABELS and value.strip() and len(value.strip()) <= 128:
            fields[normalized.replace(" ", "_")] = value.strip()
    fields["metadata_status"] = "ok" if fields else "no_selected_metadata"
    return fields


def active_models() -> list[dict[str, str]]:
    code, output, _error = run_cli("ps")
    if code:
        return []
    lines = output.splitlines()
    return [{"row": " ".join(line.split())[:240]} for line in lines[1:] if line.strip()][:64]


def benchmark(model_name: str) -> dict[str, Any]:
    if (not isinstance(model_name, str) or not MODEL_NAME.fullmatch(model_name)
            or any(part in {"", ".", ".."} for part in model_name.split("/"))):
        raise ValueError("invalid model name")
    payload = json.dumps({"model": model_name, "prompt": "Reply with the word READY.",
                          "stream": False, "keep_alive": "0s",
                          "options": {"num_predict": 32}}).encode("utf-8")
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=payload,
                                     headers={"Content-Type": "application/json", "Accept": "application/json"},
                                     method="POST")
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            body = response.read(1024 * 1024 + 1)
            if len(body) > 1024 * 1024:
                return {"status": "response_too_large"}
            data = json.loads(body)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        return {"status": "unavailable", "error": type(exc).__name__}
    if not isinstance(data, dict):
        return {"status": "invalid_response"}
    duration_keys = ("total_duration", "load_duration", "prompt_eval_count", "prompt_eval_duration",
                     "eval_count", "eval_duration")
    result = {key: data[key] for key in duration_keys if isinstance(data.get(key), int)}
    eval_count, eval_duration = result.get("eval_count"), result.get("eval_duration")
    if isinstance(eval_count, int) and isinstance(eval_duration, int) and eval_duration > 0:
        result["eval_tokens_per_second"] = round(eval_count * 1_000_000_000 / eval_duration, 2)
    prompt_count, prompt_duration = result.get("prompt_eval_count"), result.get("prompt_eval_duration")
    if isinstance(prompt_count, int) and isinstance(prompt_duration, int) and prompt_duration > 0:
        result["prompt_tokens_per_second"] = round(prompt_count * 1_000_000_000 / prompt_duration, 2)
    result["status"] = "ok"
    return result


def hardware_snapshot() -> dict[str, Any]:
    result: dict[str, Any] = {"lscpu": None, "memory_bytes": None, "cgroup": {}, "rocm": {}}
    code, output, _ = run_cli("--version")
    result["ollama_cli"] = output.strip()[:120] if code == 0 else "unavailable"
    try:
        lscpu = subprocess.run(["lscpu", "--json"], capture_output=True, text=True, timeout=5, check=False,
                               env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"})
        if lscpu.returncode == 0:
            rows = json.loads(lscpu.stdout).get("lscpu", [])
            wanted = {"Model name", "CPU(s)", "Core(s) per socket", "Thread(s) per core"}
            result["lscpu"] = {row.get("field", "").strip().rstrip(":"): row.get("data")
                               for row in rows if row.get("field", "").strip().rstrip(":") in wanted}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    try:
        memory = Path("/proc/meminfo").read_text(encoding="ascii")
        result["memory_bytes"] = {key: int(value.split()[0]) * 1024 for key, value in
                                  re.findall(r"^(MemTotal|MemAvailable|SwapTotal|SwapFree):\s+([0-9]+\s+kB)$", memory, re.M)}
    except OSError:
        pass
    cgroup = Path("/sys/fs/cgroup")
    for key in ("memory.max", "memory.current", "cpu.max", "cpuset.cpus.effective"):
        try:
            result["cgroup"][key] = (cgroup / key).read_text(encoding="ascii").strip()[:128]
        except OSError:
            result["cgroup"][key] = "unavailable"
    for path in ("/sys/class/dmi/id/sys_vendor", "/sys/class/dmi/id/product_name"):
        try:
            result["rocm"][Path(path).name] = Path(path).read_text(encoding="utf-8").strip()[:128]
        except OSError:
            pass
    result["rocm"]["kfd_present"] = Path("/dev/kfd").exists()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", action="store_true", help="run one short local generation per model")
    args = parser.parse_args()
    try:
        models = installed_models()
    except RuntimeError as exc:
        print(json.dumps({"status": "unavailable", "reason": str(exc), "hardware": hardware_snapshot()}, indent=2))
        return 2
    for model in models:
        model.update(metadata(model["name"]))
        if args.benchmark:
            model["benchmark"] = benchmark(model["name"])
    print(json.dumps({"status": "ok", "models": models, "active_models": active_models(),
                      "hardware": hardware_snapshot(), "benchmark_requested": args.benchmark}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
