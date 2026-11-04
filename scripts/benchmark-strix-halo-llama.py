#!/usr/bin/env python3
"""Benchmark a running llama.cpp server and sample AMD GPU metrics."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_MODEL = "/models/Qwen3-0.6B-Q8_0.gguf"
PROMPT = (
    "Local inference uses a shared memory system where the processor and graphics "
    "processor can access the same physical memory. Explain the tradeoffs between "
    "capacity, memory bandwidth, latency, and power use. Describe how model weights, "
    "attention state, prompt length, and generated tokens affect memory demand. "
    "Give a practical method for comparing two inference runs while controlling "
    "for prompt length, output length, warm-up, and background GPU activity. "
)


def request_json(url: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {} if data is None else {"Content-Type": "application/json"}
    req = Request(url, data=data, headers=headers)
    with urlopen(req, timeout=300) as response:
        decoded = json.loads(response.read())
    if not isinstance(decoded, dict):
        raise ValueError(f"Expected a JSON object from {url}")
    return decoded


def metric_value(node: Any, key: str) -> float | int | None:
    if isinstance(node, dict):
        if key in node and isinstance(node[key], dict):
            value = node[key].get("value")
            if isinstance(value, (int, float)):
                return value
        for value in node.values():
            found = metric_value(value, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = metric_value(value, key)
            if found is not None:
                return found
    return None


class GpuSampler(threading.Thread):
    def __init__(self, interval: float) -> None:
        super().__init__(daemon=True)
        self.interval = interval
        self.samples: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.stop_event = threading.Event()
        self.stage_lock = threading.Lock()
        self.stage = "starting"

    def set_stage(self, stage: str) -> None:
        with self.stage_lock:
            self.stage = stage

    def run(self) -> None:
        while not self.stop_event.is_set():
            sampled_at = datetime.now(timezone.utc).isoformat()
            try:
                result = subprocess.run(
                    ["amd-smi", "metric", "--usage", "--mem-usage", "--json"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                payload = json.loads(result.stdout)
                with self.stage_lock:
                    stage = self.stage
                self.samples.append(
                    {
                        "timestamp_utc": sampled_at,
                        "stage": stage,
                        "gfx_activity_percent": metric_value(payload, "gfx_activity"),
                        "used_gtt_mb": metric_value(payload, "used_gtt"),
                        "free_gtt_mb": metric_value(payload, "free_gtt"),
                        "used_vram_mb": metric_value(payload, "used_vram"),
                        "free_vram_mb": metric_value(payload, "free_vram"),
                    }
                )
            except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
                self.errors.append(f"{type(exc).__name__}: {exc}")
            self.stop_event.wait(self.interval)

    def stop(self) -> None:
        self.stop_event.set()
        self.join(timeout=12)


def summarize(runs: list[dict[str, Any]], field: str) -> dict[str, float | None]:
    values = [float(run[field]) for run in runs if run.get(field) is not None]
    if not values:
        return {"mean": None, "median": None, "min": None, "max": None}
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:18080")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--tokens", type=int, default=256, help="Generated tokens per measured run")
    parser.add_argument("--prompt-repeats", type=int, default=12)
    parser.add_argument("--sample-interval", type=float, default=1.0)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "results" / "strix-halo-llama",
    )
    args = parser.parse_args()
    if args.warmups < 0 or args.runs < 1 or args.tokens < 1 or args.prompt_repeats < 1:
        parser.error("warmups must be nonnegative; runs, tokens and prompt-repeats must be positive")
    if args.sample_interval <= 0:
        parser.error("sample-interval must be positive")
    return args


def main() -> int:
    args = parse_args()
    base_url = args.url.rstrip("/")
    health = request_json(f"{base_url}/health")
    if health.get("status") != "ok":
        raise RuntimeError(f"llama.cpp server is not healthy: {health}")
    model_list = request_json(f"{base_url}/v1/models")
    model_ids = [item.get("id") for item in model_list.get("data", [])]
    if args.model not in model_ids:
        raise RuntimeError(f"Model {args.model!r} is not served. Available models: {model_ids}")

    prompt = (PROMPT + "\n\n") * args.prompt_repeats
    sampler = GpuSampler(args.sample_interval)
    sampler.start()
    measured: list[dict[str, Any]] = []
    warmup_results: list[dict[str, Any]] = []
    error: Exception | None = None
    try:
        for index in range(args.warmups):
            sampler.set_stage(f"warmup_{index + 1}")
            start = time.perf_counter()
            response = request_json(
                f"{base_url}/completion",
                {
                    "prompt": prompt,
                    "n_predict": min(64, args.tokens),
                    "temperature": 0,
                    "stream": False,
                    "cache_prompt": False,
                },
            )
            timings = response.get("timings", {})
            warmup_results.append(
                {
                    "prompt_tokens": timings.get("prompt_n"),
                    "generated_tokens": timings.get("predicted_n"),
                    "client_latency_ms": round((time.perf_counter() - start) * 1000, 3),
                }
            )
        for index in range(args.runs):
            sampler.set_stage(f"run_{index + 1}")
            start = time.perf_counter()
            response = request_json(
                f"{base_url}/completion",
                {
                    "prompt": prompt,
                    "n_predict": args.tokens,
                    "temperature": 0,
                    "stream": False,
                    "cache_prompt": False,
                },
            )
            client_latency_ms = (time.perf_counter() - start) * 1000
            timings = response.get("timings", {})
            required = ("prompt_n", "prompt_ms", "prompt_per_second", "predicted_n", "predicted_ms", "predicted_per_second")
            missing = [key for key in required if key not in timings]
            if missing:
                raise RuntimeError(f"llama.cpp response omitted timing fields: {missing}")
            measured.append(
                {
                    "run": index + 1,
                    "prompt_tokens": timings["prompt_n"],
                    "prompt_processing_ms": timings["prompt_ms"],
                    "prompt_tokens_per_second": timings["prompt_per_second"],
                    "generated_tokens": timings["predicted_n"],
                    "generation_ms": timings["predicted_ms"],
                    "generation_tokens_per_second": timings["predicted_per_second"],
                    "client_total_latency_ms": round(client_latency_ms, 3),
                }
            )
    except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError) as exc:
        error = exc
    finally:
        sampler.set_stage("finished")
        sampler.stop()

    metrics = sampler.samples
    numeric_samples = lambda key: [s[key] for s in metrics if isinstance(s.get(key), (int, float))]
    sample_times = [
        datetime.fromisoformat(sample["timestamp_utc"]).timestamp()
        for sample in metrics
    ]
    sample_intervals = [later - earlier for earlier, later in zip(sample_times, sample_times[1:])]
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": "strix-halo-llama.cpp",
        "endpoint": base_url,
        "model": args.model,
        "host": {
            "platform": platform.platform(),
            "kernel": platform.release(),
            "machine": platform.machine(),
        },
        "warmups_requested": args.warmups,
        "warmups": warmup_results,
        "runs_requested": args.runs,
        "tokens_requested_per_run": args.tokens,
        "prompt_repeats": args.prompt_repeats,
        "prompt_text_chars": len(prompt),
        "runs": measured,
        "summary": {
            "prompt_processing_ms": summarize(measured, "prompt_processing_ms"),
            "prompt_tokens_per_second": summarize(measured, "prompt_tokens_per_second"),
            "generation_ms": summarize(measured, "generation_ms"),
            "generation_tokens_per_second": summarize(measured, "generation_tokens_per_second"),
            "client_total_latency_ms": summarize(measured, "client_total_latency_ms"),
        },
        "gpu": {
            "sampler": "amd-smi metric --usage --mem-usage --json",
            "requested_sample_interval_seconds": args.sample_interval,
            "actual_sample_interval_seconds_mean": statistics.fmean(sample_intervals) if sample_intervals else None,
            "samples": metrics,
            "sample_errors": sampler.errors,
            "gfx_activity_percent_min": min(numeric_samples("gfx_activity_percent"), default=None),
            "gfx_activity_percent_max": max(numeric_samples("gfx_activity_percent"), default=None),
            "used_gtt_mb_min": min(numeric_samples("used_gtt_mb"), default=None),
            "used_gtt_mb_max": max(numeric_samples("used_gtt_mb"), default=None),
            "used_vram_mb_min": min(numeric_samples("used_vram_mb"), default=None),
            "used_vram_mb_max": max(numeric_samples("used_vram_mb"), default=None),
        },
        "error": None if error is None else f"{type(error).__name__}: {error}",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = args.output_dir / f"strix-halo-llama-benchmark-{stamp}.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Saved benchmark JSON: {output}")
    print(json.dumps(result["summary"], indent=2))
    print(
        "GPU samples: "
        f"{len(metrics)}; gfx max {result['gpu']['gfx_activity_percent_max']}%; "
        f"GTT max {result['gpu']['used_gtt_mb_max']} MB; "
        f"VRAM max {result['gpu']['used_vram_mb_max']} MB"
    )
    if error is not None:
        print(result["error"])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
