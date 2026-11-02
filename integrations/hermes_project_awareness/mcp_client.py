"""A bounded MCP stdio client for the project-awareness Hermes tool wrapper."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any


MAX_STDIO_BYTES = 2 * 1024 * 1024
CALL_TIMEOUT = 30


def call_provider(provider: str, operation: str, arguments: dict[str, Any] | None = None,
                  *, request_id: str | None = None) -> dict[str, Any]:
    if provider not in {"github", "inventory"}:
        raise ValueError("unknown provider")
    root = Path(__file__).resolve().parents[2]
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONPATH": str(root), "PYTHONNOUSERSITE": "1"}
    tool_arguments = dict(arguments or {})
    tool_arguments["request_id"] = request_id or uuid.uuid4().hex
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "hermes-frameworklab-awareness", "version": "0.1.0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": operation, "arguments": tool_arguments}},
    ]
    payload = b"".join(json.dumps(row, separators=(",", ":")).encode("utf-8") + b"\n" for row in messages)
    if len(payload) > MAX_STDIO_BYTES:
        raise ValueError("MCP request exceeds the transport limit")
    module_root = "integrations.hermes_project_awareness.mcp_stdio"
    try:
        proc = subprocess.run([sys.executable, "-m", module_root, provider], input=payload,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              timeout=CALL_TIMEOUT, env=env, close_fds=True, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("MCP provider could not be reached") from exc
    if proc.returncode != 0 or len(proc.stdout) > MAX_STDIO_BYTES:
        raise RuntimeError("MCP provider returned an invalid response")
    try:
        rows = [json.loads(line) for line in proc.stdout.splitlines() if line]
        next(row for row in rows if row.get("id") == 1 and "result" in row)
        response = next(row for row in rows if row.get("id") == 2)
        if "error" in response:
            raise RuntimeError("MCP provider rejected the request")
        result = response.get("result")
        if not isinstance(result, dict) or result.get("isError"):
            raise RuntimeError("MCP provider reported an unavailable source")
        content = result.get("content")
        if not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict):
            raise RuntimeError("MCP provider returned malformed content")
        decoded = json.loads(content[0].get("text", ""))
        if not isinstance(decoded, dict):
            raise RuntimeError("MCP provider returned an unexpected response")
        return decoded
    except (StopIteration, ValueError, TypeError, KeyError) as exc:
        raise RuntimeError("MCP provider returned malformed JSON-RPC data") from exc
